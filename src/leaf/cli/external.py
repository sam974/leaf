'''
Leaf Package Manager

@author:    Sébastien MB <smassot@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
import argparse
import os
from os.path import pathsep
from pathlib import Path
import subprocess

from leaf.cli.cliutils import GenericCommand
from leaf.core.logger import TextLogger, Verbosity
from leaf.core.packagemanager import PackageManager


class ExternalCommand(GenericCommand):
    '''
    Wrapper to run external binaries as leaf subcommand.
    '''

    @staticmethod
    def tryExternalCommand(name, executable):
        '''
        Try to run --help and use the first line as help to build a new
        ExternalCommand
        '''
        try:
            desc = subprocess.check_output((str(executable), "--help"),
                                           timeout=1)
            return ExternalCommand(name,
                                   desc.decode().splitlines()[0],
                                   executable)
        except Exception:
            pass

    def __init__(self, name, description, executable):
        GenericCommand.__init__(self,
                                name,
                                description)
        self.executable = executable
        self.cmdHelp = description

    def create(self, subparsers):
        parser = subparsers.add_parser(self.cmdName,
                                       help=self.cmdHelp,
                                       aliases=self.cmdAliases,
                                       prefix_chars='+',
                                       add_help=False)
        self.initArgs(parser)

    def initArgs(self, parser):
        super().initArgs(parser)
        parser.add_argument('ARGS',
                            nargs=argparse.REMAINDER)

    def execute(self, args):
        # Create a package manager to get env
        logger = TextLogger(Verbosity.QUIET, True)
        app = PackageManager(logger, nonInteractive=args.nonInteractive)
        env = dict(os.environ)
        env.update(app.getLeafEnvironment().toMap())
        # Use args to run the external command
        command = [str(self.executable)]
        command += args.ARGS
        return subprocess.call(command,
                               env=env)


def findLeafExternalCommands(whitelistCommands=None, blacklistCommands=None):
    '''
    Find leaf-XXX binaries in $PATH to build external commands
    @param whitelistCommands: only use commands with name in list
    @param blacklistCommands: do not use commands with name in list
    @return: ExternalCommands list
    '''
    out = []
    pathFolderList = os.environ["PATH"].split(pathsep)
    for pathFolder in map(Path, pathFolderList):
        if pathFolder.is_dir():
            for candidate in pathFolder.iterdir():
                if candidate.is_file() and candidate.name.startswith("leaf-"):
                    if os.access(str(candidate), os.X_OK):
                        name = candidate.stem[5:]
                        if blacklistCommands is not None and name in blacklistCommands:
                            # Command is blacklisted
                            continue
                        if whitelistCommands is not None and name not in whitelistCommands:
                            # Command is not in whitelist
                            continue
                        ec = ExternalCommand.tryExternalCommand(name,
                                                                candidate)
                        if ec is not None:
                            out.append(ec)
    return out