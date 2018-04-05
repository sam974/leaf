
'''
Constants to tweak the tests
'''
from leaf.cli_packagemanager import PackageManagerCli
from leaf.cli_profile import ProfileCli
from leaf.constants import LeafConstants, LeafFiles
from leaf.core import LeafRepository
from leaf.logger import TextLogger
from leaf.model import Manifest
import os
from pathlib import Path
import shutil
import subprocess
from tempfile import mkdtemp
import unittest
from unittest.case import TestCase


DEBUG_TESTS = os.environ.get("LEAF_UT_KEEP")
SEPARATOR = "--------------------"
ALT_FILENAMES = {
    "compress-tar_1.0": 'compress-tar_1.0.tar',
    "compress-xz_1.0":  'compress-xz_1.0.tar.xz',
    "compress-bz2_1.0": 'compress-bz2_1.0.tar.bz2',
    "compress-gz_1.0":  'compress-gz_1.0.tar.gz'
}


class AbstractTestWithRepo(unittest.TestCase):

    ROOT_FOLDER = None
    REPO_FOLDER = None
    VOLATILE_FOLDER = None

    def __init__(self, methodName):
        TestCase.__init__(self, methodName)

    @classmethod
    def setUpClass(cls):
        if DEBUG_TESTS is not None:
            AbstractTestWithRepo.ROOT_FOLDER = Path("/tmp/leaf")
        else:
            AbstractTestWithRepo.ROOT_FOLDER = Path(
                mkdtemp(prefix="leaf_tests_"))

        AbstractTestWithRepo.REPO_FOLDER = AbstractTestWithRepo.ROOT_FOLDER / "repository"
        AbstractTestWithRepo.VOLATILE_FOLDER = AbstractTestWithRepo.ROOT_FOLDER / "volatile"

        shutil.rmtree(str(AbstractTestWithRepo.ROOT_FOLDER),
                      ignore_errors=True)

        resourcesFolder = Path("tests/resources/")
        assert resourcesFolder.exists(), "Cannot find resources folder!"
        generateRepo(resourcesFolder,
                     AbstractTestWithRepo.REPO_FOLDER,
                     TextLogger(TextLogger.LEVEL_QUIET))

    @classmethod
    def tearDownClass(cls):
        if not DEBUG_TESTS is not None:
            shutil.rmtree(str(AbstractTestWithRepo.ROOT_FOLDER), True)

    def setUp(self):
        shutil.rmtree(str(AbstractTestWithRepo.VOLATILE_FOLDER),
                      ignore_errors=True)
        AbstractTestWithRepo.VOLATILE_FOLDER.mkdir()

    def tearDown(self):
        pass

    def getRemoteUrl(self):
        return (AbstractTestWithRepo.REPO_FOLDER / "index.json").as_uri()

    def getVolatileItem(self, name, mkdir=True):
        out = AbstractTestWithRepo.VOLATILE_FOLDER / name
        if mkdir and not out.is_dir():
            out.mkdir()
        return out

    def getConfigurationFile(self):
        return self.getVolatileItem("config.json", mkdir=False)

    def getInstallFolder(self):
        return self.getVolatileItem("packages")

    def getRemoteCacheFile(self):
        return self.getVolatileItem("cache.json", mkdir=False)

    def getWorkspaceFolder(self):
        return self.getVolatileItem("workspace")

    def getAltWorkspaceFolder(self):
        return self.getVolatileItem("alt-workspace")

    def checkInstalledPackages(self, *pisList):
        for pis in pisList:
            folder = self.getInstallFolder() / str(pis)
            self.assertTrue(folder.is_dir(), msg=str(folder))
        folderItemCount = 0
        for i in self.getInstallFolder().iterdir():
            if i.is_dir():
                folderItemCount += 1
        self.assertEqual(len(pisList),
                         folderItemCount)

    def checkCurrentProfile(self, name):
        lnk = self.getWorkspaceFolder() / LeafFiles.WS_DATA_FOLDERNAME / \
            LeafFiles.CURRENT_PROFILE
        if name is None:
            self.assertFalse(lnk.exists())
        else:
            self.assertEqual(name, lnk.resolve().name)

    def checkProfileContent(self, profileName, *content):
        pfFolder = self.getWorkspaceFolder() / LeafFiles.WS_DATA_FOLDERNAME / profileName
        self.assertTrue(pfFolder.exists())
        symlinkCount = 0
        for item in pfFolder.iterdir():
            if item.is_symlink():
                symlinkCount += 1
            self.assertTrue(item.name in content, "Unexpected link %s" % item)
        self.assertEqual(symlinkCount, len(content))


class LeafPackageManagerCliWrapper(AbstractTestWithRepo):

    def __init__(self, methodName):
        AbstractTestWithRepo.__init__(self, methodName)
        self.preVerbArgs = []
        self.postVerbArgs = []
        self.jsonEnvValue = ""

    def setUp(self):
        AbstractTestWithRepo.setUp(self)
        self.leafPackageManagerExec("config",
                                    "--root", self.getInstallFolder())
        self.leafPackageManagerExec("remote",
                                    "--add", self.getRemoteUrl())

    def leafPackageManagerExec(self, verb, *args, expectedRc=0):
        self.eazyExecute(PackageManagerCli,
                         self.preVerbArgs + ["--non-interactive",
                                             "--config",
                                             self.getConfigurationFile()],
                         verb,
                         self.postVerbArgs,
                         args,
                         expectedRc)

    def eazyExecute(self, cliClazz, preArgs, verb, postArgs, args, expectedRc):
        command = []
        if preArgs is not None:
            command += preArgs
        if verb is not None:
            command.append(verb)
        if postArgs is not None:
            command += postArgs
        if args is not None:
            command += args
        command = [str(i) for i in command]
        print(SEPARATOR,
              '[%s] %s> %s' % (type(self).__name__,
                               cliClazz.__name__,
                               " ".join(command)))
        os.environ[LeafConstants.JSON_OUTPUT] = self.jsonEnvValue
        out = cliClazz().run(command)
        print(SEPARATOR + SEPARATOR + SEPARATOR)
        if expectedRc is not None:
            self.assertEqual(expectedRc, out, " ".join(command))
        return out


class LeafProfileCliWrapper(LeafPackageManagerCliWrapper):

    def __init__(self, methodName):
        LeafPackageManagerCliWrapper.__init__(self, methodName)

    def setUp(self):
        LeafPackageManagerCliWrapper.setUp(self)

    def leafProfileExec(self, verb, *args, altWorkspace=None, expectedRc=0):
        if altWorkspace is None:
            altWorkspace = self.getWorkspaceFolder()
        self.eazyExecute(ProfileCli,
                         self.preVerbArgs + ["--non-interactive",
                                             "--config", self.getConfigurationFile(),
                                             "--workspace", altWorkspace],
                         verb,
                         self.postVerbArgs,
                         args,
                         expectedRc)


def generateRepo(sourceFolder, outputFolder, logger):
    outputFolder.mkdir(parents=True, exist_ok=True)
    artifactsList = []
    artifactsListComposite = []

    app = LeafRepository(logger)
    for packageFolder in sourceFolder.iterdir():
        if packageFolder.is_dir():
            manifestFile = packageFolder / LeafConstants.MANIFEST
            if manifestFile.is_file():
                manifest = Manifest.parse(manifestFile)
                if str(manifest.getIdentifier()) != packageFolder.name:
                    raise ValueError("Naming error: %s != %s" % (
                        str(manifest.getIdentifier()), packageFolder.name))
                filename = ALT_FILENAMES.get(str(manifest.getIdentifier()),
                                             str(manifest.getIdentifier()) + ".leaf")
                outputFile = outputFolder / filename
                app.pack(manifestFile, outputFile)
                checkArchiveFormat(str(outputFile))
                if manifest.getName().startswith("composite"):
                    artifactsListComposite.append(outputFile)
                else:
                    artifactsList.append(outputFile)

    app.index(outputFolder / "composite.json",
              artifactsListComposite, "composite")

    app.index(outputFolder / "index.json",
              artifactsList, "composite", composites=["composite.json"])


def checkArchiveFormat(file):
    if (file.endswith(".tar")):
        checkMime(file, "x-tar")
    elif (file.endswith(".tar.gz")):
        checkMime(file, "gzip")
    elif (file.endswith(".tar.bz2")):
        checkMime(file, "x-bzip2")
    elif (file.endswith(".tar.xz")):
        checkMime(file, "x-xz")
    else:
        checkMime(file, "x-xz")


def checkMime(file, expectedMime):
    mime = subprocess.getoutput("file -bi " + str(file))
    if not mime.startswith("application/" + expectedMime):
        raise ValueError("File %s has invalid mime type %s" % (file, mime))
