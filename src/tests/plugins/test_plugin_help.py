"""
@author: Legato Tooling Team <letools@sierrawireless.com>
"""

import os

from tests.testutils import PROJECT_ROOT_FOLDER, LeafTestCaseWithCli


class TestPluginHelp(LeafTestCaseWithCli):
    def setUp(self):
        LeafTestCaseWithCli.setUp(self)
        TestPluginHelp.OLD_MANPATH = os.environ.get("MANPATH")
        mandir = PROJECT_ROOT_FOLDER / "resources" / "man"
        self.assertTrue(mandir.is_dir())
        if TestPluginHelp.OLD_MANPATH is None:
            os.environ["MANPATH"] = str(mandir.resolve())
        else:
            os.environ["MANPATH"] = "{folder}:{previous}".format(folder=mandir.resolve(), previous=TestPluginHelp.OLD_MANPATH)
        print("Update MANPATH:", os.environ["MANPATH"])

    def tearDown(self):
        if TestPluginHelp.OLD_MANPATH is None:
            del os.environ["MANPATH"]
        else:
            os.environ["MANPATH"] = TestPluginHelp.OLD_MANPATH
        LeafTestCaseWithCli.tearDown(self)

    def test_help(self):
        self.simple_exec("help")
        self.simple_exec("help config")
        self.simple_exec("help unknownpage", expected_rc=3)
        self.simple_exec("help --list")
        self.simple_exec("help -l")
        self.simple_exec("help config --foo", expected_rc=2)
