'''
@author: seb
'''
import os

from leaf.constants import LeafConstants
from leaf.core.logger import TextLogger, Verbosity
from leaf.core.packagemanager import PackageManager
from leaf.model.filtering import MetaPackageFilter
from tests.testutils import AbstractTestWithRepo


class FilteringTest(AbstractTestWithRepo):

    def setUp(self):
        AbstractTestWithRepo.setUp(self)
        os.environ[LeafConstants.ENV_CONFIG_FILE] = str(
            self.getConfigurationFile())
        os.environ[LeafConstants.ENV_CACHE_FOLDER] = str(
            self.getCacheFolder())
        app = PackageManager(TextLogger(Verbosity.DEFAULT, True), True)
        app.updateUserConfiguration(remoteAddList=[self.getRemoteUrl()])
        app.fetchRemotes()
        self.content = app.listAvailablePackages().values()
        self.assertTrue(len(self.content) > 0)

    def testMaster(self):
        f = MetaPackageFilter()
        f.onlyMasterPackages()
        print("Filter:", f)
        self.assertEqual(3, len(list(filter(f.matches, self.content))))

    def testKeyword(self):
        f = MetaPackageFilter()
        f.withKeyword("compress")
        print("Filter:", f)
        self.assertEqual(4, len(list(filter(f.matches, self.content))))

        f = MetaPackageFilter()
        f.withKeyword("container")
        print("Filter:", f)
        self.assertEqual(9, len(list(filter(f.matches, self.content))))

        f = MetaPackageFilter()
        f.withKeyword("container,compress")
        print("Filter:", f)
        self.assertEqual(13, len(list(filter(f.matches, self.content))))
        f.withKeyword("gz")
        print("Filter:", f)
        self.assertEqual(1, len(list(filter(f.matches, self.content))))
        f.onlyMasterPackages()
        print("Filter:", f)
        self.assertEqual(0, len(list(filter(f.matches, self.content))))

    def testTag(self):
        f = MetaPackageFilter()
        f.withTag("foo")
        print("Filter:", f)
        self.assertEqual(5, len(list(filter(f.matches, self.content))))

        f = MetaPackageFilter()
        f.withTag("foo,bar")
        print("Filter:", f)
        self.assertEqual(7, len(list(filter(f.matches, self.content))))

        f = MetaPackageFilter()
        f.withTag("bar")
        print("Filter:", f)
        self.assertEqual(5, len(list(filter(f.matches, self.content))))
        f.withTag("foo")
        print("Filter:", f)
        self.assertEqual(3, len(list(filter(f.matches, self.content))))
        f.withTag("foo2")
        print("Filter:", f)
        self.assertEqual(0, len(list(filter(f.matches, self.content))))

        f = MetaPackageFilter()
        f.withTag("bar")
        print("Filter:", f)
        self.assertEqual(5, len(list(filter(f.matches, self.content))))
        f.withTag("foo")
        print("Filter:", f)
        self.assertEqual(3, len(list(filter(f.matches, self.content))))
        f.withKeyword("container-A")
        print("Filter:", f)
        self.assertEqual(2, len(list(filter(f.matches, self.content))))

    def testPkgName(self):
        f = MetaPackageFilter()
        f.withNames(["container-A", "version"])
        print("Filter:", f)
        self.assertEqual(7, len(list(filter(f.matches, self.content))))
        f.onlyMasterPackages()
        print("Filter:", f)
        self.assertEqual(2, len(list(filter(f.matches, self.content))))