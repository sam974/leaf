'''
Leaf Package Manager

@author:    Sébastien MB <smassot@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
import argparse
from leaf.cli.cliutils import LeafCommand, LeafMetaCommand
from leaf.core.dependencies import DependencyType
from leaf.core.tags import TagManager
from leaf.model.filtering import MetaPackageFilter
from leaf.model.package import Manifest
from leaf.utils import mkTmpLeafRootDir, envListToMap
from pathlib import Path


class PackageSearchCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(
            self,
            "search",
            "search for available packages")

    def initArgs(self, parser):
        super().initArgs(parser)
        parser.add_argument("-a", "--all",
                            dest="allPackages",
                            action="store_true",
                            help="display all packages, not only master packages")
        parser.add_argument("-t", "--tag",
                            dest="tags",
                            action="append",
                            metavar="TAG",
                            help="filter search results matching with given tag")
        parser.add_argument('keywords',
                            nargs=argparse.ZERO_OR_MORE)

    def execute(self, args):
        logger = self.getLogger(args)
        app = self.getApp(args, logger=logger)

        pkgFilter = MetaPackageFilter()
        if not args.allPackages:
            pkgFilter.onlyMasterPackages()

        if args.tags is not None:
            for t in args.tags:
                pkgFilter.withTag(t)

        if args.keywords is not None and len(args.keywords) > 0:
            for kw in args.keywords:
                pkgFilter.withKeyword(kw)

        # Pkg list
        mfList = sorted(app.listAvailablePackages().values(),
                        key=Manifest.getIdentifier)
        # manage tags
        TagManager().tagLatest(mfList)
        TagManager().tagInstalled(mfList, app.listInstalledPackages().keys())

        # Print filtered packages
        logger.printDefault("Filter:", pkgFilter)
        for mf in mfList:
            if pkgFilter.matches(mf):
                logger.displayItem(mf)


class PackageMetaCommand(LeafMetaCommand):

    def __init__(self):
        LeafMetaCommand.__init__(self,
                                 "package",
                                 "core package manager commands",
                                 cmdAliases=["pkg"])

    def getSubCommands(self):
        return [PackageListSubCommand(),
                PackageInstallSubCommand(),
                PackageRemoveSubCommand(),
                PackageEnvSubCommand(),
                PackageDependsSubCommand(),
                PackagePrereqSubCommand()]


class PackageListSubCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(self,
                             "list",
                             "list installed packages",
                             cmdAliases=["ls"])

    def initArgs(self, parser):
        super().initArgs(parser)
        parser.add_argument("-a", "--all",
                            dest="allPackages",
                            action="store_true",
                            help="display all packages, not only master packages")
        parser.add_argument("-t", "--tag",
                            dest="tags",
                            action="append",
                            metavar="tag",
                            help="filter search results matching with given tag")
        parser.add_argument('keywords',
                            nargs=argparse.ZERO_OR_MORE)

    def execute(self, args):
        logger = self.getLogger(args)
        app = self.getApp(args, logger=logger)

        pkgFilter = MetaPackageFilter()
        if not args.allPackages:
            pkgFilter.onlyMasterPackages()

        if args.tags is not None:
            for t in args.tags:
                pkgFilter.withTag(t)

        if args.keywords is not None and len(args.keywords) > 0:
            for kw in args.keywords:
                pkgFilter.withKeyword(kw)

        # Print filtered packages
        logger.printDefault("Filter:", pkgFilter)
        for mf in sorted(app.listInstalledPackages().values(),
                         key=Manifest.getIdentifier):
            if pkgFilter.matches(mf):
                logger.displayItem(mf)


class PackageDependsSubCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(self,
                             "dependencies",
                             "Build the dependency chain",
                             cmdAliases=["deps"])

    def initArgs(self, parser):
        super().initArgs(parser)
        group = parser.add_mutually_exclusive_group()
        group.add_argument("--installed",
                           dest="dependencyType",
                           action="store_const",
                           const=DependencyType.INSTALLED,
                           default=DependencyType.INSTALLED,
                           help="build dependency list from installed packages")
        group.add_argument("--available",
                           dest="dependencyType",
                           action="store_const",
                           const=DependencyType.AVAILABLE,
                           help="build dependency list from available packages")
        group.add_argument("--install",
                           dest="dependencyType",
                           action="store_const",
                           const=DependencyType.INSTALL,
                           help="build dependency list to install")
        group.add_argument("--uninstall",
                           dest="dependencyType",
                           action="store_const",
                           const=DependencyType.UNINSTALL,
                           help="build dependency list to uninstall")
        group.add_argument("--prereq",
                           dest="dependencyType",
                           action="store_const",
                           const=DependencyType.PREREQ,
                           help="build dependency list for prereq install")
        parser.add_argument('--env',
                            dest='customEnvList',
                            action='append',
                            metavar='KEY=VALUE',
                            help='add given environment variable')
        parser.add_argument('packages',
                            nargs=argparse.REMAINDER)

    def execute(self, args):
        logger = self.getLogger(args)
        app = self.getApp(args, logger=logger)
        items = app.listDependencies(args.packages,
                                     args.dependencyType,
                                     envMap=envListToMap(args.customEnvList))
        for i in items:
            logger.displayItem(i)


class PackageInstallSubCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(self,
                             "install",
                             "install packages (download + extract)",
                             cmdAliases=["i"])

    @staticmethod
    def initInstallArguments(subparser):
        subparser.add_argument('-k', "--keep",
                               dest="keepOnError",
                               action="store_true",
                               help="keep package folder in case of installation error")

    def initArgs(self, parser):
        super().initArgs(parser)
        PackageInstallSubCommand.initInstallArguments(parser)
        parser.add_argument('packages',
                            nargs=argparse.REMAINDER)

    def execute(self, args):
        logger = self.getLogger(args)
        app = self.getApp(args, logger=logger)

        items = app.installFromRemotes(args.packages,
                                       keepFolderOnError=args.keepOnError)
        if len(items) > 0:
            logger.printQuiet("Packages installed: " +
                              ' '.join([str(p.getIdentifier()) for p in items]))


class PackagePrereqSubCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(self,
                             "prereq",
                             "check prereq packages")

    def initArgs(self, parser):
        super().initArgs(parser)
        parser.add_argument("--target",
                            dest="prereqRootFolder",
                            type=Path,
                            help="a alternative root folder for required packages installation")
        parser.add_argument('packages',
                            nargs=argparse.REMAINDER)

    def execute(self, args):
        logger = self.getLogger(args)
        app = self.getApp(args, logger=logger)

        tmpRootFolder = args.prereqRootFolder
        if tmpRootFolder is None:
            tmpRootFolder = mkTmpLeafRootDir()
        logger.printQuiet("Prereq root folder: %s" % tmpRootFolder)
        errorCount = app.installPrereqFromRemotes(args.packages,
                                                  tmpRootFolder,
                                                  raiseOnError=False)
        logger.printQuiet("Prereq installed with %d error(s)" % errorCount)
        return errorCount


class PackageRemoveSubCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(self,
                             "remove",
                             "remove packages",
                             cmdAliases=["rm"])

    def initArgs(self, parser):
        super().initArgs(parser)
        parser.add_argument('packages', nargs=argparse.REMAINDER)

    def execute(self, args):
        logger = self.getLogger(args)
        app = self.getApp(args, logger=logger)

        app.uninstallPackages(args.packages)


class PackageEnvSubCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(self,
                             "env",
                             "display environment variables exported by packages")

    def initArgs(self, parser):
        super().initArgs(parser)
        parser.add_argument('packages', nargs=argparse.REMAINDER)

    def execute(self, args):
        logger = self.getLogger(args)
        app = self.getApp(args, logger=logger)

        env = app.getPackageEnv(args.packages)
        logger.displayItem(env)
