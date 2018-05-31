'''
Leaf Package Manager

@author:    Sébastien MB <smassot@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
from collections import OrderedDict
from leaf import __version__
from leaf.constants import JsonConstants
from leaf.model import Manifest, Environment
import os
import subprocess


def genEnvScript(env, activateFile=None, deactivateFile=None):
    '''
    Generates environment script to activate and desactivate a profile
    '''
    if deactivateFile is not None:
        resetMap = OrderedDict()
        for k in env.keys():
            resetMap[k] = os.environ.get(k)
        with open(str(deactivateFile), "w") as fp:
            for k, v in resetMap.items():
                # If the value was not present in env before, reset it
                if v is None:
                    fp.write(Environment.unsetCommand(k) + "\n")
                else:
                    fp.write(Environment.exportCommand(k, v) + "\n")
    if activateFile is not None:
        with open(str(activateFile), "w") as fp:

            def commentConsumer(c):
                fp.write(Environment.comment(c) + "\n")

            def kvConsumer(k, v):
                fp.write(Environment.exportCommand(k, v) + "\n")

            env.printEnv(kvConsumer=kvConsumer,
                         commentConsumer=commentConsumer)


class TagManager():
    '''
    Class used to tag packages
    '''

    LATEST = 'latest'
    INSTALLED = 'installed'
    CURRENT = 'current'

    def tagLatest(self, mfList):
        '''
        Add the 'latest' tag to packages with the latest version
        '''
        mapByName = OrderedDict()
        for mf in mfList:
            pkgName = mf.getIdentifier().name
            if pkgName not in mapByName:
                mapByName[pkgName] = []
            mapByName[pkgName].append(mf)
        for pkgList in mapByName.values():
            latest = next(iter(sorted(pkgList,
                                      key=Manifest.getIdentifier,
                                      reverse=True)))
            latest.customTags.append(TagManager.LATEST)

    def tagInstalled(self, mfList, piList):
        '''
        Tag packages from given mfList as installed if they are in the given piList 
        '''
        for mf in mfList:
            if mf.getIdentifier() in piList:
                mf.customTags.append(TagManager.INSTALLED)

    def tagCurrent(self, mfList, pf):
        '''
        Tag packages in mfList as current if they are in the given profile
        '''
        for mf in mfList:
            if str(mf.getIdentifier()) in pf.getPackages():
                mf.customTags.append(TagManager.CURRENT)


class DynamicDependencyManager():
    '''
    Used to build the dependency tree using dynamic conditions
    '''

    @staticmethod
    def computePrereqList(piList, apMap):
        '''
        Return the list of ap to install as prereq
        @return: AvailablePackage list
        '''
        out = []
        for pi in piList:
            ap = apMap.get(pi)
            if ap is None:
                raise ValueError("Cannot find package %s" % pi)
            if ap not in out:
                out.append(ap)
        out = list(sorted(out, key=Manifest.getIdentifier))
        return out

    @staticmethod
    def computeDependencyTree(piList, mfMap, env=None, reverse=False, ignoreUnknown=False):
        '''
        @return: Manifest list
        '''
        out = []
        # Get all packages to install
        for pi in piList:
            DynamicDependencyManager._recursiveGetDepends(pi,
                                                          mfMap,
                                                          env,
                                                          ignoreUnknown,
                                                          out)
        # Sort package to install
        out = DynamicDependencyManager._sortPiListForInstall(out,
                                                             mfMap,
                                                             env,
                                                             reverse=reverse)
        return out

    @staticmethod
    def computeIpToUninstall(piList, ipMap):
        '''
        @return: InstalledPackage list
        '''
        out = DynamicDependencyManager.computeDependencyTree(piList,
                                                             ipMap,
                                                             reverse=True,
                                                             ignoreUnknown=True)

        # Maintain dependencies
        for ip in ipMap.values():
            if ip not in out:
                neededIpList = []
                DynamicDependencyManager._recursiveGetDepends(ip.getIdentifier(),
                                                              ipMap,
                                                              None,
                                                              True,
                                                              neededIpList)
                out = [ip for ip in out if ip not in neededIpList]

        return out

    @staticmethod
    def computeApToInstall(piList, apMap, ipMap, env):
        '''
        @return: AvailablePackage list
        '''
        out = DynamicDependencyManager.computeDependencyTree(piList,
                                                             apMap,
                                                             env=env)

        # Remove installed packages
        out = [ap for ap in out if ap.getIdentifier() not in ipMap]

        return out

    @staticmethod
    def _recursiveGetDepends(pi, mfMap, env, ignoreUnknown, out):
        mf = mfMap.get(pi)
        if mf is None:
            if not ignoreUnknown:
                raise ValueError("Cannot find package %s" % pi)
        else:
            if mf not in out:
                out.append(mf)
                for cpi in mf.getLeafDependsFromEnv(env):
                    DynamicDependencyManager._recursiveGetDepends(cpi,
                                                                  mfMap,
                                                                  env,
                                                                  ignoreUnknown,
                                                                  out)

    @staticmethod
    def _sortPiListForInstall(mfList, mfMap, env, reverse=False):
        '''
        Sort and filter the given packages
        @return: Manifest list
        '''
        out = []

        def isTerminal(mf):
            for cpi in mf.getLeafDependsFromEnv(env):
                if cpi in mfMap and mfMap.get(cpi) not in out:
                    return False
            return True

        mfList = list(mfList)
        curLen = len(mfList)

        # Ordering
        while len(mfList) > 0:
            for mf in mfList[:]:
                if isTerminal(mf):
                    out.append(mf)
                    mfList.remove(mf)
            if curLen == len(mfList):
                raise ValueError(
                    "Infinite loop when computing dependency tree")
            curLen = len(mfList)

        # reverse
        if reverse:
            out.reverse()
        return out


class VariableResolver():

    def __init__(self, currentPkg=None, otherPkgList=None):
        self.content = {}
        if currentPkg is not None:
            self.useInstalledPackage(currentPkg, True)
        if otherPkgList is not None:
            for pkg in otherPkgList:
                self.useInstalledPackage(pkg)

    def useInstalledPackage(self, pkg, isCurrentPkg=False):
        suffix = "" if isCurrentPkg else (":%s" % pkg.getIdentifier())
        self.addVariable("DIR" + suffix, pkg.folder)
        self.addVariable("NAME" + suffix, pkg.getIdentifier().name)
        self.addVariable("VERSION" + suffix, pkg.getIdentifier().version)

    def addVariable(self, k, v):
        self.content["@{%s}" % k] = v

    def resolve(self, value, failOnUnknownVariable=True):
        out = value
        for k, v in self.content.items():
            out = out.replace(k, str(v))
        if failOnUnknownVariable and '@{' in out:
            raise ValueError("Cannot resolve all variables in: %s" % out)
        return out


class StepExecutor():
    '''
    Used to execute post install & pre uninstall steps
    '''

    def __init__(self, logger, package, variableResolver, env=None):
        self.logger = logger
        self.package = package
        self.env = env
        self.targetFolder = package.folder
        self.variableResolver = variableResolver

    def postInstall(self,):
        steps = self.package.jsonpath(JsonConstants.INSTALL, default=[])
        if len(steps) > 0:
            self.runSteps(steps, self.package, label="Post-install")

    def preUninstall(self):
        steps = self.package.jsonpath(JsonConstants.UNINSTALL, default=[])
        if len(steps) > 0:
            self.runSteps(steps, self.package, label="Pre-uninstall")

    def runSteps(self, steps, ip, label=""):
        self.logger.progressStart('Execute steps', total=len(steps))
        worked = 0
        for step in steps:
            if JsonConstants.STEP_LABEL in step:
                self.logger.printDefault(step[JsonConstants.STEP_LABEL])
            self.doExec(step)
            worked += 1
            self.logger.progressWorked('Execute steps',
                                       worked=worked,
                                       total=len(steps))
        self.logger.progressDone('Execute steps')

    def doExec(self, step):
        command = [self.resolve(arg)
                   for arg in step[JsonConstants.STEP_EXEC_COMMAND]]
        self.logger.printVerbose("Exec:", ' '.join(command))
        env = dict(os.environ)
        for k, v in step.get(JsonConstants.STEP_EXEC_ENV, {}).items():
            v = self.resolve(v)
            env[k] = v
        if self.env is not None:
            env.update(self.env.toMap())
        env["LEAF_VERSION"] = str(__version__)
        stdout = subprocess.DEVNULL
        if self.logger.isVerbose() or step.get(JsonConstants.STEP_EXEC_VERBOSE,
                                               False):
            stdout = None
        rc = subprocess.call(command,
                             cwd=str(self.targetFolder),
                             env=env,
                             stdout=stdout,
                             stderr=subprocess.STDOUT)
        if rc != 0:
            if step.get(JsonConstants.STEP_IGNORE_FAIL, False):
                self.logger.printVerbose("Return code is",
                                         rc,
                                         "but step ignores failure")
            else:
                raise ValueError("Step exited with return code " + str(rc))

    def resolve(self, value, failOnUnknownVariable=True, prefixWithFolder=False):
        out = self.variableResolver.resolve(value,
                                            failOnUnknownVariable=failOnUnknownVariable)
        if prefixWithFolder:
            return str(self.targetFolder / out)
        return out
