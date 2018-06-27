'''
Leaf Package Manager

@author:    Sébastien MB <smassot@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
import argparse

from leaf.cli.cliutils import LeafMetaCommand, LeafCommand, initCommonArgs
from leaf.model.environment import Environment
from leaf.model.package import PackageIdentifier
from leaf.utils import envListToMap


class EnvMetaCommand(LeafMetaCommand):

    def __init__(self):
        LeafMetaCommand.__init__(
            self,
            "env",
            "display environement variables")

    def getSubCommands(self):
        return [EnvBuiltinCommand(),
                EnvUserCommand(),
                EnvWorkspaceCommand(),
                EnvProfileCommand(),
                EnvPackageCommand()]

    def getDefaultSubCommand(self):
        return EnvPrintCommand()


class EnvPrintCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(
            self,
            "print",
            "display all environment variables to use the current (or given) profile")

    def initArgs(self, parser):
        super().initArgs(parser)
        initCommonArgs(parser, withEnvScripts=True)
        parser.add_argument('profiles', nargs=argparse.OPTIONAL,
                            metavar='PROFILE', help='the profile name')

    def execute(self, args):
        logger = self.getLogger(args)
        workspace = self.getWorkspace(args, checkInitialized=False)

        env = None
        if not workspace.isInitialized():
            env = Environment.build(
                self.getPackageManager(args).getLeafEnvironment(),
                self.getPackageManager(args).getUserEnvironment())
        else:
            # Get profile name, key could not exist if command is default
            # command
            name = args.profiles if "profiles" in vars(
                args) and args.profiles is not None else workspace.getCurrentProfileName()
            profile = workspace.getProfile(name)
            if not workspace.isProfileSync(profile):
                raise ValueError(
                    "Profile %s is out of sync, please run 'leaf profile sync %s'" % (name, name))
            env = workspace.getFullEnvironment(profile)
        logger.displayItem(env)
        if 'activateScript' in vars(args):
            env.generateScripts(args.activateScript, args.deactivateScript)


class EnvBuiltinCommand(LeafCommand):
    def __init__(self):
        LeafCommand.__init__(
            self,
            "builtin",
            "display environment variables exported by leaf application")

    def initArgs(self, parser):
        super().initArgs(parser)
        initCommonArgs(parser, withEnvScripts=True)

    def execute(self, args):
        logger = self.getLogger(args)
        packageManager = self.getPackageManager(args)

        env = packageManager.getLeafEnvironment()
        logger.displayItem(env)
        env.generateScripts(args.activateScript, args.deactivateScript)


class EnvUserCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(
            self,
            "user",
            "display and update environment variables exported by user configuration")

    def initArgs(self, parser):
        super().initArgs(parser)
        initCommonArgs(parser, addRemoveEnv=True, withEnvScripts=True)

    def execute(self, args):
        logger = self.getLogger(args)
        packageManager = self.getPackageManager(args)

        if args.envAddList is not None or args.envRmList is not None:
            packageManager.updateUserEnv(setMap=envListToMap(args.envAddList),
                                         unsetList=args.envRmList)

        env = packageManager.getUserEnvironment()
        logger.displayItem(env)
        env.generateScripts(args.activateScript, args.deactivateScript)


class EnvWorkspaceCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(
            self,
            "workspace",
            "display and update environment variables exported by workspace")

    def initArgs(self, parser):
        super().initArgs(parser)
        initCommonArgs(parser, addRemoveEnv=True, withEnvScripts=True)

    def execute(self, args):
        logger = self.getLogger(args)
        workspace = self.getWorkspace(args)

        if args.envAddList is not None or args.envRmList is not None:
            workspace.updateWorkspaceEnv(setMap=envListToMap(args.envAddList),
                                         unsetList=args.envRmList)

        env = workspace.getWorkspaceEnvironment()
        logger.displayItem(env)
        env.generateScripts(args.activateScript, args.deactivateScript)


class EnvProfileCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(
            self,
            "profile",
            "display and update environment variables exported by profile")

    def initArgs(self, parser):
        super().initArgs(parser)
        initCommonArgs(parser, addRemoveEnv=True, withEnvScripts=True)
        parser.add_argument('profiles', nargs=argparse.OPTIONAL,
                            metavar='PROFILE', help='the profile name')

    def execute(self, args):
        logger = self.getLogger(args)
        workspace = self.getWorkspace(args)
        name = args.profiles if args.profiles is not None else workspace.getCurrentProfileName()
        profile = workspace.getProfile(name)

        if args.envAddList is not None or args.envRmList is not None:
            profile.updateEnv(setMap=envListToMap(args.envAddList),
                              unsetList=args.envRmList)
            profile = workspace.updateProfile(profile)

        env = profile.getEnvironment()
        logger.displayItem(env)
        env.generateScripts(args.activateScript, args.deactivateScript)


class EnvPackageCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(
            self,
            "package",
            "display environment variables exported by packages")

    def initArgs(self, parser):
        super().initArgs(parser)
        initCommonArgs(parser, withEnvScripts=True)
        parser.add_argument(dest='pisList',
                            metavar='PKGID',
                            nargs=argparse.REMAINDER)

    def execute(self, args):
        logger = self.getLogger(args)
        app = self.getPackageManager(args)
        env = app.getPackagesEnvironment(
            [PackageIdentifier.fromString(pis) for pis in args.pisList])
        logger.displayItem(env)
        env.generateScripts(args.activateScript, args.deactivateScript)
