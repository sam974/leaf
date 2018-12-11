'''
@author: Legato Tooling Team <letools@sierrawireless.com>
'''

import os

from tests.testutils import LeafCliWrapper, RESOURCE_FOLDER

from leaf.cli.external import ExternalCommandUtils


class TestExtMisc(LeafCliWrapper):

    def __init__(self, methodName):
        LeafCliWrapper.__init__(self, methodName)

    def testExternalCommand(self):
        with self.assertRaises(SystemExit):
            self.leafExec("foo.sh")
        oldPath = os.environ['PATH']
        try:
            self.assertTrue(RESOURCE_FOLDER.is_dir())
            os.environ['PATH'] = oldPath + ":" + str(RESOURCE_FOLDER)
            ExternalCommandUtils.COMMANDS = None
            self.leafExec("foo.sh")
            self.leafExec("build", "bar.sh")
            self.leafExec("env", "bar.sh")
            self.leafExec("feature", "bar.sh")
            self.leafExec("package", "bar.sh")
            self.leafExec("profile", "bar.sh")
            self.leafExec("remote", "bar.sh")
        finally:
            os.environ['PATH'] = oldPath
            ExternalCommandUtils.COMMANDS = None