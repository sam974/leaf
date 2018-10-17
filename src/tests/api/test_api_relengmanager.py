'''
@author: Legato Tooling Team <letools@sierrawireless.com>
'''

import json
import os
import time
from tarfile import TarFile

from tests.testutils import AbstractTestWithRepo, RESOURCE_FOLDER, checkMime

from leaf.constants import JsonConstants, LeafFiles
from leaf.core.error import LeafException
from leaf.core.relengmanager import RelengManager
from leaf.format.logger import Verbosity
from leaf.model.package import AvailablePackage
from leaf.utils import computeHash, jsonLoadFile, jsonWriteFile


VERBOSITY = Verbosity.DEFAULT


class TestRelengManager(AbstractTestWithRepo):

    def __init__(self, methodName):
        AbstractTestWithRepo.__init__(self, methodName)

    def setUp(self):
        AbstractTestWithRepo.setUp(self)
        self.rm = RelengManager(VERBOSITY, True)

    def testPackageCompression(self):
        pkgFolder = RESOURCE_FOLDER / "install_1.0"

        def checkAllCompressions(extension, defaultMime):
            outputFile = self.getWorkspaceFolder() / ("myPackage" + extension)
            for compression, mime in (('tar', 'x-tar'),
                                      ('gz', 'gzip'),
                                      ('bz2', 'x-bzip2'),
                                      ('xz', 'x-xz'),
                                      (None, defaultMime)):
                self.rm.createPackage(pkgFolder, outputFile,
                                      compression=compression)
                checkMime(outputFile, mime)
        checkAllCompressions('.bin', 'x-xz')
        checkAllCompressions('.tar', 'x-tar')
        checkAllCompressions('.tar.gz', 'gzip')
        checkAllCompressions('.tar.bz2', 'x-bzip2')
        checkAllCompressions('.tar.xz', 'x-xz')
        checkAllCompressions('.leaf', 'x-xz')

    def testExternalInfoFile(self):
        pkgFolder = RESOURCE_FOLDER / "install_1.0"
        artifactFile = self.getWorkspaceFolder() / "myPackage.leaf"
        infoFile = self.getWorkspaceFolder() / "myPackage.leaf.info"

        self.rm.createPackage(pkgFolder, artifactFile,
                              storeExtenalInfo=False)
        self.assertTrue(artifactFile.exists())
        self.assertFalse(infoFile.exists())

        self.rm.createPackage(pkgFolder, artifactFile,
                              storeExtenalInfo=True)
        self.assertTrue(artifactFile.exists())
        self.assertTrue(infoFile.exists())
        self.assertEquals(infoFile, self.rm._getExternalInfoFile(artifactFile))
        self.assertEquals(computeHash(artifactFile),
                          AvailablePackage(jsonLoadFile(infoFile), None).getHash())

        with self.assertRaises(LeafException):
            self.rm.createPackage(pkgFolder, artifactFile,
                                  storeExtenalInfo=False)

    def testPackageWithTimestamp(self):
        TIMESTAMP = 946684800

        pkgFolder = RESOURCE_FOLDER / "install_1.0"
        outputFile1a = self.getWorkspaceFolder() / "myPackage1a.tar"
        outputFile1b = self.getWorkspaceFolder() / "myPackage1b.tar"
        outputFile2a = self.getWorkspaceFolder() / "myPackage2a.tar"
        outputFile2b = self.getWorkspaceFolder() / "myPackage2b.tar"

        self.rm.createPackage(pkgFolder, outputFile1a)
        self.rm.createPackage(pkgFolder, outputFile1b)
        self.rm.createPackage(pkgFolder, outputFile2a,
                              forceTimestamp=TIMESTAMP)
        self.rm.createPackage(pkgFolder, outputFile2b,
                              forceTimestamp=TIMESTAMP)

        self.assertEquals(computeHash(outputFile1a),
                          computeHash(outputFile1b))
        self.assertEquals(computeHash(outputFile2a),
                          computeHash(outputFile2b))
        self.assertNotEquals(computeHash(outputFile1a),
                             computeHash(outputFile2a))

        outputFolder1 = self.getWorkspaceFolder() / "extract1"
        with TarFile.open(str(outputFile1a)) as tf:
            tf.extractall(str(outputFolder1))
        manifestFile1 = outputFolder1 / LeafFiles.MANIFEST
        self.assertTrue(manifestFile1.exists())
        self.assertNotEquals(TIMESTAMP, manifestFile1.stat().st_mtime)

        outputFolder2 = self.getWorkspaceFolder() / "extract2"
        with TarFile.open(str(outputFile2a)) as tf:
            tf.extractall(str(outputFolder2))
        manifestFile2 = outputFolder2 / LeafFiles.MANIFEST
        self.assertTrue(manifestFile2.exists())
        self.assertEquals(TIMESTAMP, manifestFile2.stat().st_mtime)

    def testManifestInfoMap(self):
        manifestFile = self.getWorkspaceFolder() / LeafFiles.MANIFEST
        self.rm.generateManifest(
            manifestFile,
            infoMap={
                JsonConstants.INFO_NAME: "foo",
                JsonConstants.INFO_VERSION: "1.0",
                JsonConstants.INFO_DESCRIPTION: "lorem ipsum",
                JsonConstants.INFO_DATE: "2012-12-12 12:12:12",
                JsonConstants.INFO_MASTER: True,
                JsonConstants.INFO_LEAF_MINVER: "0.42",
                JsonConstants.INFO_REQUIRES: ["a_1", "b_1", "a_1"],
                JsonConstants.INFO_DEPENDS: ["a_1", "b_1(FOO=BAR)", "a_1"],
                JsonConstants.INFO_TAGS: ["foo", "bar", "foo"],
                "ignored_extra_key": "hello",
            })
        self.assertTrue(manifestFile.exists())
        with open(str(manifestFile), 'r') as fp:
            self.assertEquals({
                JsonConstants.INFO: {
                    JsonConstants.INFO_NAME: "foo",
                    JsonConstants.INFO_VERSION: "1.0",
                    JsonConstants.INFO_DESCRIPTION: "lorem ipsum",
                    JsonConstants.INFO_DATE: "2012-12-12 12:12:12",
                    JsonConstants.INFO_MASTER: True,
                    JsonConstants.INFO_LEAF_MINVER: "0.42",
                    JsonConstants.INFO_REQUIRES: ["a_1", "b_1"],
                    JsonConstants.INFO_DEPENDS: ["a_1", "b_1(FOO=BAR)"],
                    JsonConstants.INFO_TAGS: ["foo", "bar"], }},
                json.load(fp))

    def testManifestFragments(self):
        manifestFile = self.getWorkspaceFolder() / LeafFiles.MANIFEST

        fragmentA = self.getWorkspaceFolder() / "a.json"
        jsonWriteFile(
            fragmentA,
            {
                'a': 1,
                'info': {
                    'tags': ['tag1']
                }
            })

        fragmentB = self.getWorkspaceFolder() / "b.json"
        jsonWriteFile(
            fragmentB,
            {
                'a': 2
            })

        fragmentC = self.getWorkspaceFolder() / "c.json"
        jsonWriteFile(
            fragmentC,
            {
                'b': True,
                'info': {
                    'tags': ['tag2']

                }
            })

        self.rm.generateManifest(
            manifestFile,
            fragmentFiles=[fragmentA, fragmentB, fragmentC],
            infoMap={
                JsonConstants.INFO_NAME: "foo",
                JsonConstants.INFO_VERSION: "1.0",
                JsonConstants.INFO_TAGS: ["foo", "bar", "foo"],
                "ignored_extra_key": "hello",
            })
        self.assertTrue(manifestFile.exists())
        with open(str(manifestFile), 'r') as fp:
            self.assertEquals(
                {
                    JsonConstants.INFO: {
                        JsonConstants.INFO_NAME: "foo",
                        JsonConstants.INFO_VERSION: "1.0",
                        JsonConstants.INFO_TAGS: ["tag1", "tag2", "foo", "bar"],
                    },
                    "a": 2,
                    "b": True
                },
                json.load(fp))

    def testManifestWithEnv(self, resolveEnv=True):

        manifestFile = self.getWorkspaceFolder() / LeafFiles.MANIFEST

        try:
            os.environ["LEAF_TEST_VARIABLE"] = "hello"

            fragmentA = self.getWorkspaceFolder() / "a.json"
            jsonWriteFile(
                fragmentA,
                {
                    'a': "#{LEAF_TEST_VARIABLE} #{LEAF_TEST_VARIABLE}"
                })

            self.rm.generateManifest(
                manifestFile,
                fragmentFiles=[fragmentA, ],
                infoMap={
                    JsonConstants.INFO_NAME: "foo",
                    JsonConstants.INFO_VERSION: "1.0",
                    JsonConstants.INFO_DESCRIPTION: "#{LEAF_TEST_VARIABLE} #{LEAF_TEST_VARIABLE}"
                },
                resolveEnvVariables=resolveEnv)
            self.assertTrue(manifestFile.exists())
            with open(str(manifestFile), 'r') as fp:
                motif = 'hello hello' if resolveEnv else '#{LEAF_TEST_VARIABLE} #{LEAF_TEST_VARIABLE}'
                self.assertEquals(
                    {
                        JsonConstants.INFO: {
                            JsonConstants.INFO_NAME: "foo",
                            JsonConstants.INFO_VERSION: "1.0",
                            JsonConstants.INFO_DESCRIPTION: motif
                        },
                        "a": motif
                    },
                    json.load(fp))

        finally:
            del os.environ["LEAF_TEST_VARIABLE"]

    def testManifestWithoutEnv(self):
        self.testManifestWithEnv(resolveEnv=False)

    def testIndex(self):
        indexFile = self.getWorkspaceFolder() / "index.json"

        # Build some packages
        for pis in ("install_1.0",
                    "condition_1.0",
                    "condition-A_1.0",
                    "condition-A_2.0",
                    "condition-B_1.0",
                    "condition-C_1.0",
                    "condition-D_1.0",
                    "condition-E_1.0",
                    "condition-F_1.0",
                    "condition-G_1.0",
                    "condition-H_1.0"):
            pkgFolder = RESOURCE_FOLDER / pis
            outputFile = self.getWorkspaceFolder() / (pis + '.leaf')
            self.rm.createPackage(pkgFolder, outputFile)

        self.rm.generateIndex(
            indexFile,
            self.getWorkspaceFolder().glob("condition*.leaf"),
            prettyprint=True)
        indexContent = jsonLoadFile(indexFile)
        self.assertEquals(10, len(indexContent[JsonConstants.REMOTE_PACKAGES]))

        self.rm.generateIndex(
            indexFile,
            self.getWorkspaceFolder().glob("*.leaf"),
            prettyprint=False)
        indexContent = jsonLoadFile(indexFile)
        self.assertEquals(11, len(indexContent[JsonConstants.REMOTE_PACKAGES]))

    def testIndexSameArtifactDifferentHash(self):
        (self.getWorkspaceFolder() / 'a').mkdir()
        (self.getWorkspaceFolder() / 'b').mkdir()

        self.rm.generateManifest(
            self.getWorkspaceFolder() / 'a' / LeafFiles.MANIFEST,
            infoMap={JsonConstants.INFO_NAME: "foo",
                     JsonConstants.INFO_VERSION: "1",
                     JsonConstants.INFO_DESCRIPTION: "Some description"})

        self.rm.generateManifest(
            self.getWorkspaceFolder() / 'b' / LeafFiles.MANIFEST,
            infoMap={JsonConstants.INFO_NAME: "foo",
                     JsonConstants.INFO_VERSION: "1",
                     JsonConstants.INFO_DESCRIPTION: "Different description"})

        self.rm.createPackage(
            self.getWorkspaceFolder() / 'a',
            self.getWorkspaceFolder() / 'a.leaf')
        self.rm.createPackage(
            self.getWorkspaceFolder() / 'b',
            self.getWorkspaceFolder() / 'b.leaf')

        self.rm.generateIndex(
            self.getWorkspaceFolder() / 'indexA.json',
            [self.getWorkspaceFolder() / 'a.leaf',
             self.getWorkspaceFolder() / 'a.leaf'],
            prettyprint=True)
        self.rm.generateIndex(
            self.getWorkspaceFolder() / 'indexB.json',
            [self.getWorkspaceFolder() / 'b.leaf',
             self.getWorkspaceFolder() / 'b.leaf'],
            prettyprint=True)
        with self.assertRaises(ValueError):
            self.rm.generateIndex(
                self.getWorkspaceFolder() / 'indexAB.json',
                [self.getWorkspaceFolder() / 'a.leaf',
                 self.getWorkspaceFolder() / 'b.leaf'],
                prettyprint=True)

    def testReproductibleBuild(self):
        # Build some packages
        pis = "install_1.0"
        pkgFolder = RESOURCE_FOLDER / pis
        manifest = pkgFolder / LeafFiles.MANIFEST
        self.assertTrue(manifest.exists())

        def touchManifest():
            time.sleep(1)
            os.utime(str(manifest), None)

        for compression in ("tar", "xz", "bz2"):
            outputFileA1 = self.getWorkspaceFolder() / ('%s.%s.%d' %
                                                        (pis, compression, 1))
            outputFileA2 = self.getWorkspaceFolder() / ('%s.%s.%d' %
                                                        (pis, compression, 2))
            outputFileB1 = self.getWorkspaceFolder() / ('%s.%s.%d' %
                                                        (pis, compression, 3))
            outputFileB2 = self.getWorkspaceFolder() / ('%s.%s.%d' %
                                                        (pis, compression, 4))

            self.rm.createPackage(pkgFolder, outputFileA1,
                                  compression=compression, storeExtenalInfo=False)
            touchManifest()
            self.rm.createPackage(pkgFolder, outputFileA2,
                                  compression=compression, storeExtenalInfo=False)
            touchManifest()
            self.rm.createPackage(pkgFolder, outputFileB1,
                                  compression=compression, storeExtenalInfo=False,
                                  forceTimestamp=1234, forceRootOwner=True)
            touchManifest()
            self.rm.createPackage(pkgFolder, outputFileB2,
                                  compression=compression, storeExtenalInfo=False,
                                  forceTimestamp=1234, forceRootOwner=True)

            self.assertTrue(outputFileA1.exists())
            self.assertTrue(outputFileA2.exists())
            self.assertTrue(outputFileB1.exists())
            self.assertTrue(outputFileB2.exists())

            self.assertNotEquals(computeHash(outputFileA1),
                                 computeHash(outputFileA2))
            self.assertNotEquals(computeHash(outputFileA1),
                                 computeHash(outputFileB1))
            self.assertEquals(computeHash(outputFileB1),
                              computeHash(outputFileB2))
