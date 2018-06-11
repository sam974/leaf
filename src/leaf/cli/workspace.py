'''
Leaf Package Manager

@author:    Sébastien MB <smassot@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
from leaf.cli.cliutils import LeafCommand, initCommonArgs
from leaf.core.tags import TagManager
from leaf.model.filtering import MetaPackageFilter
from leaf.model.package import Manifest
from leaf.utils import envListToMap
from pathlib import Path


class WorkspaceConfigCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(self,
                             "config:workspace",
                             "update workspace configuration",
                             cmdAliases=["config:w"])

    def initArgs(self, parser):
        super().initArgs(parser)
        initCommonArgs(parser,
                       withEnv=True)

    def execute(self, args):
        ws = self.getWorkspace(args)
        ws.updateWorkspaceConfiguration(envSetMap=envListToMap(args.setEnvList),
                                        envUnsetList=args.unsetEnvList)


class ProfileConfigCommand(LeafCommand):
    def __init__(self):
        LeafCommand.__init__(self,
                             "config:profile",
                             "update current profile configuration",
                             cmdAliases=["config:p"])

    def initArgs(self, parser):
        super().initArgs(parser)
        initCommonArgs(parser,
                       withEnv=True,
                       withPackages=True)

    def execute(self, args):
        ws = self.getWorkspace(args)
        ws.updateProfile(ws.getCurrentProfileName(),
                         envSetMap=envListToMap(args.setEnvList),
                         envUnsetList=args.unsetEnvList,
                         mpkgAddList=args.motifList)


class WorkspaceInitCommand(LeafCommand):
    def __init__(self):
        LeafCommand.__init__(self,
                             "init",
                             "initialize workspace")

    def execute(self, args):
        logger = self.getLogger(args)
        ws = self.getWorkspace(args, autoFindWorkspace=False)

        if ws.configFile.exists():
            raise ValueError("File %s already exist" % str(ws.configFile))
        if ws.dataFolder.exists():
            raise ValueError("Folder %s already exist" % str(ws.dataFolder))
        ws.readConfiguration(initIfNeeded=True)
        logger.printDefault("Workspace initialized", ws.rootFolder)


class ProfileCreateCommand(LeafCommand):
    def __init__(self):
        LeafCommand.__init__(self,
                             "create",
                             "create a profile")

    def initArgs(self, parser):
        super().initArgs(parser)
        initCommonArgs(parser,
                       profileNargs=1)

    def execute(self, args):
        logger = self.getLogger(args)
        ws = self.getWorkspace(args)
        pf = ws.createProfile(args.profiles[0])
        logger.printDefault("Profile %s created" % pf.name)


class ProfileUpdateCommand(LeafCommand):
    def __init__(self):
        LeafCommand.__init__(self,
                             "update",
                             "update all packages of the current profile")

    def initArgs(self, parser):
        super().initArgs(parser)
        parser.add_argument('--list',
                            dest='listOnly',
                            action='store_true',
                            help='only show available updates, do not update the profile')

    def execute(self, args):
        logger = self.getLogger(args)
        app = self.getApp(args, logger=logger)
        ws = self.getWorkspace(args, app=app)

        pf = ws.retrieveCurrentProfile()

        pkgFilter = MetaPackageFilter()
        pkgFilter.withNames([pi.name for pi in pf.getPackageIdentifiers()])

        # Pkg list
        mfList = sorted(app.listAvailablePackages().values(),
                        key=Manifest.getIdentifier)
        # manage tags
        TagManager().tagLatest(mfList)
        if pf is not None:
            TagManager().tagCurrent(mfList, pf)

        # Print filtered packages
        if not logger.isQuiet():
            logger.printDefault("Available packages for profile %s" % pf.name)
            for mf in mfList:
                if pkgFilter.matches(mf):
                    logger.displayItem(mf)
            print("")  # cosmetic empty line, do not log it

        if not args.listOnly:
            pf = ws.updateProfile(pf.name,
                                  mpkgAddList=pf.getPackageMap().keys())


class ProfileRenameCommand(LeafCommand):
    def __init__(self):
        LeafCommand.__init__(self,
                             "rename",
                             "rename current profile")

    def initArgs(self, parser):
        super().initArgs(parser)
        parser.add_argument('newName',
                            metavar='NEW_NAME',
                            nargs=1,
                            help='the new profile name')

    def execute(self, args):
        logger = self.getLogger(args)
        ws = self.getWorkspace(args)

        oldName = ws.getCurrentProfileName()
        pf = ws.updateProfile(name=oldName,
                              newName=args.newName[0])
        logger.printDefault("Profile %s renamed to %s" % (oldName, pf.name))


class ProfileDeleteCommand(LeafCommand):
    def __init__(self):
        LeafCommand.__init__(self,
                             "delete",
                             "delete current profile")

    def initArgs(self, parser):
        super().initArgs(parser)
        initCommonArgs(parser,
                       profileNargs=1)

    def execute(self, args):
        logger = self.getLogger(args)
        ws = self.getWorkspace(args)

        pf = ws.deleteProfile(args.profiles[0])
        if pf is not None:
            logger.printDefault("Profile %s deleted" % pf.name)


class ProfileEnvCommand(LeafCommand):
    def __init__(self):
        LeafCommand.__init__(self,
                             "env",
                             "display profile environment",
                             cmdAliases=["env:u", "env:user",
                                         "env:w", "env:workspace",
                                         "env:p", "env:profile"])

    def initArgs(self, parser):
        super().initArgs(parser)
        initCommonArgs(parser,
                       withEnv=True,
                       profileNargs='?')
        parser.add_argument('--activate-script',
                            dest='activateScript',
                            type=Path,
                            help="create a script to activate the env variables of the profile")
        parser.add_argument('--deactivate-script',
                            dest='deactivateScript',
                            type=Path,
                            help="create a script to deactivate the env variables of the profile")

    def execute(self, args):
        logger = self.getLogger(args)
        app = self.getApp(args, logger=logger)
        ws = self.getWorkspace(args, app=app)

        cmdName = args.command
        if cmdName == "env":
            if args.setEnvList is not None or args.unsetEnvList is not None:
                raise ValueError("Please select which env you want to set: " +
                                 "env:user, env:workspace or env:profile")
            name = args.profiles if args.profiles is not None else ws.getCurrentProfileName()
            env = ws.getProfileEnv(name)
        elif cmdName == "env:u" or cmdName == "env:user":
            app.updateUserConfiguration(envSetMap=envListToMap(args.setEnvList),
                                        envUnsetList=args.unsetEnvList)
            env = app.getUserEnvironment()
        elif cmdName == "env:w" or cmdName == "env:workspace":
            ws.updateWorkspaceConfiguration(envSetMap=envListToMap(args.setEnvList),
                                            envUnsetList=args.unsetEnvList)
            env = ws.readConfiguration().getEnvironment()
        elif cmdName == "env:p" or cmdName == "env:profile":
            name = args.profiles if args.profiles is not None else ws.getCurrentProfileName()
            pf = ws.updateProfile(name,
                                  envSetMap=envListToMap(args.setEnvList),
                                  envUnsetList=args.unsetEnvList)
            env = pf.getEnvironment()
        logger.displayItem(env)
        env.generateScripts(args.activateScript, args.deactivateScript)


class ProfileSelectCommand(LeafCommand):
    def __init__(self):
        LeafCommand.__init__(self,
                             "select",
                             "set current profile")

    def initArgs(self, parser):
        super().initArgs(parser)
        initCommonArgs(parser,
                       profileNargs=1)

    def execute(self, args):
        logger = self.getLogger(args)
        ws = self.getWorkspace(args)
        pf = ws.switchProfile(args.profiles[0])
        logger.printVerbose("Profile package folder:", pf.folder)


class ProfileSyncCommand(LeafCommand):
    def __init__(self):
        LeafCommand.__init__(self,
                             "sync",
                             "install needed packages if needed for the current profile")

    def execute(self, args):
        ws = self.getWorkspace(args)
        ws.provisionProfile(ws.getCurrentProfileName())
