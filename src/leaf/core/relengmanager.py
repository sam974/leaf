'''
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
import os
import re
import subprocess
from collections import OrderedDict
from datetime import datetime
from pathlib import Path

from leaf.constants import EnvConstants, JsonConstants, LeafConstants, LeafFiles
from leaf.core.dependencies import DependencyUtils
from leaf.core.error import LeafException
from leaf.core.packagemanager import LoggerManager
from leaf.model.modelutils import layerModelUpdate
from leaf.model.package import AvailablePackage, ConditionalPackageIdentifier, \
    LeafArtifact, Manifest, PackageIdentifier
from leaf.utils import computeHash, jsonLoadFile, jsonToString, jsonWriteFile


class RelengManager(LoggerManager):
    '''
    Methods needed for releng, ie generate packages and maintain repository
    '''

    def __init__(self, verbosity):
        LoggerManager.__init__(self, verbosity)

    def _getNowDate(self):
        return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    def _getExternalInfoFile(self, artifact):
        return artifact.parent / (artifact.name + LeafFiles.EXTINFO_EXTENSION)

    def _buildPackageNode(self, artifact, manifest=None):
        out = OrderedDict()
        out[JsonConstants.REMOTE_PACKAGE_HASH] = computeHash(artifact)
        out[JsonConstants.REMOTE_PACKAGE_SIZE] = artifact.stat().st_size
        if manifest is None:
            manifest = LeafArtifact(artifact)
        out[JsonConstants.INFO] = manifest.getNodeInfo()
        return out

    def createPackage(self, pkgFolder, outputFile,
                      storeExtenalInfo=True,
                      tarExtraArgs=None):
        '''
        Create a leaf artifact from given folder containing a manifest.json
        '''
        manifestFile = pkgFolder / LeafFiles.MANIFEST
        externalInfoFile = self._getExternalInfoFile(outputFile)

        if not manifestFile.exists():
            raise ValueError("Cannot find manifest: %s" % manifestFile)

        manifest = Manifest.parse(manifestFile)

        if DependencyUtils.isLatestPackage(manifest.getIdentifier()):
            raise LeafException("Invalid version for manifest %s (%s is a reserved keyword)" % (
                manifestFile, LeafConstants.LATEST))

        self.logger.printDefault("Found package %s in %s" % (
            manifest.getIdentifier(), pkgFolder))

        # Check if external info file exists
        if not storeExtenalInfo and externalInfoFile.exists():
            raise LeafException(msg="A previous info file (%s) exists for your package" % externalInfoFile,
                                hints="You should remove it with 'rm %s'" % externalInfoFile)

        self.executeTarProcess(outputFile, pkgFolder,
                               tarExtraArgs=tarExtraArgs)

        self.logger.printDefault("Leaf package created: %s" % outputFile)

        if storeExtenalInfo:
            self.logger.printDefault("Write info to %s" % (externalInfoFile))
            jsonWriteFile(
                externalInfoFile,
                self._buildPackageNode(outputFile, manifest=manifest),
                pp=True)

    def generateIndex(self, indexFile, artifacts,
                      name=None, description=None,
                      useExternalInfo=True, useExtraTags=True,
                      prettyprint=False):
        '''
        Create an index.json referencing all given artifacts
        '''

        # Create the "info" node
        infoNode = OrderedDict()
        if name is not None:
            infoNode[JsonConstants.REMOTE_NAME] = name
        if description is not None:
            infoNode[JsonConstants.REMOTE_DESCRIPTION] = description
        infoNode[JsonConstants.REMOTE_DATE] = self._getNowDate()

        # Iterate over all artifacts
        packagesMap = OrderedDict()
        for artifact in artifacts:
            artifactNode = None

            if useExternalInfo:
                externalInfoFile = self._getExternalInfoFile(artifact)
                if externalInfoFile.exists():
                    self.logger.printDefault(
                        "Reading info from %s" % externalInfoFile)
                    artifactNode = jsonLoadFile(externalInfoFile)

            if artifactNode is None:
                self.logger.printDefault("Compute info for %s" % artifact)
                artifactNode = self._buildPackageNode(artifact)

            ap = AvailablePackage(artifactNode, None)
            pi = ap.getIdentifier()
            if DependencyUtils.isLatestPackage(pi):
                raise LeafException("Invalid version for package %s (%s is a reserved keyword)" % (
                    artifact, LeafConstants.LATEST))

            if pi in packagesMap:
                self.logger.printDefault("Artifact already present: %s" % (pi))
                if ap.getHash() != AvailablePackage(packagesMap[pi], None).getHash():
                    raise ValueError(
                        "Artifact %s has multiple different artifacts for same version" % pi)
            else:
                # Read extra tags
                extraTagsFile = artifact.parent / (artifact.name + ".tags")
                if useExtraTags and extraTagsFile.exists():
                    with extraTagsFile.open('r') as fp:
                        for tag in filter(None, map(str.strip, fp.read().splitlines())):
                            if tag not in ap.getTags():
                                ap.getTags().append(tag)
                                self.logger.printDefault(
                                    "Add extra tag %s" % tag)

                self.logger.printDefault("Add package %s" % pi)
                relPath = Path(artifact).relative_to(indexFile.parent)
                artifactNode[JsonConstants.REMOTE_PACKAGE_FILE] = str(relPath)
                packagesMap[pi] = artifactNode

        # Create the json structure
        rootNode = OrderedDict()
        rootNode[JsonConstants.INFO] = infoNode
        rootNode[JsonConstants.REMOTE_PACKAGES] = list(packagesMap.values())

        jsonWriteFile(indexFile, rootNode, pp=prettyprint)
        self.logger.printDefault("Index created:", indexFile)

    def generateManifest(self, outputFile,
                         fragmentFiles=None,
                         infoMap=None,
                         resolveEnvVariables=False):
        '''
        Used to create a manifest.json file
        '''

        model = OrderedDict()

        # Load fragments
        if fragmentFiles is not None:
            for ff in fragmentFiles:
                self.logger.printDefault("Use json fragment: %s" % ff)
                layerModelUpdate(model, jsonLoadFile(ff), listAppend=True)

        # Load model
        manifest = Manifest(model)
        info = manifest.jsonget(JsonConstants.INFO, default=OrderedDict())

        # Set the common info
        if infoMap is not None:
            for key in (JsonConstants.INFO_NAME,
                        JsonConstants.INFO_VERSION,
                        JsonConstants.INFO_DESCRIPTION,
                        JsonConstants.INFO_MASTER,
                        JsonConstants.INFO_DATE,
                        JsonConstants.INFO_REQUIRES,
                        JsonConstants.INFO_DEPENDS,
                        JsonConstants.INFO_TAGS,
                        JsonConstants.INFO_LEAF_MINVER,
                        JsonConstants.INFO_AUTOUPGRADE):
                if key in infoMap:
                    value = infoMap[key]
                    if value is not None:
                        if key in (JsonConstants.INFO_REQUIRES,
                                   JsonConstants.INFO_DEPENDS,
                                   JsonConstants.INFO_TAGS):
                            # Handle lists
                            modelList = manifest.jsonpath(
                                [JsonConstants.INFO, key],
                                default=[])
                            for motif in value:
                                if motif not in modelList:
                                    if key == JsonConstants.INFO_DEPENDS:
                                        # Try to parse as a conditional package identifier
                                        ConditionalPackageIdentifier.fromString(
                                            motif)
                                    elif key == JsonConstants.INFO_REQUIRES:
                                        # Try to parse as a package identifier
                                        PackageIdentifier.fromString(motif)

                                    self.logger.printVerbose(
                                        "Add '%s' to '%s' list" % (motif, key))
                                    modelList.append(motif)
                        else:
                            self.logger.printVerbose(
                                "Set '%s' = '%s'" % (key, value))
                            info[key] = value

        # String replacement
        jsonString = jsonToString(manifest.json, pp=True)
        if resolveEnvVariables:
            for var in set(re.compile(r'#\{([a-zA-Z0-9_]+)\}').findall(jsonString)):
                value = os.environ.get(var)
                if value is None:
                    raise LeafException("Cannot find '%s' in env" % var,
                                        hints="Set the variable with 'export %s=xxx'" % var)
                self.logger.printDefault("Replace %s --> %s" % (var, value))
                jsonString = jsonString.replace("#{%s}" % var, value)

        if DependencyUtils.isLatestPackage(manifest.getIdentifier()):
            raise LeafException(
                "Invalid version (%s is a reserved keyword)" % LeafConstants.LATEST)

        self.logger.printDefault("Save '%s' manifest to %s" % (
            manifest.getIdentifier(), outputFile))

        with open(str(outputFile), 'w') as fp:
            fp.write(jsonString)

    def executeTarProcess(self, outputFile, workingFolder, tar="tar", tarExtraArgs=None):

        command = [os.getenv(EnvConstants.CUSTOM_TAR, "tar"), "-c"]
        command += ['-f', str(outputFile)]
        command += ['-C', str(workingFolder)]

        if tarExtraArgs is None or len(tarExtraArgs) == 0:
            command += ['.']
        else:
            forbiddenArgs = [arg for arg
                             in tarExtraArgs
                             if arg in ('-A', '--catenate', '--concatenate',
                                        '-c', '--create',
                                        '-d', '--diff', '--compare',
                                        '--delete',
                                        '-r', '--append',
                                        '-t', '--list',
                                        '--test-label',
                                        '-u', '--update',
                                        '-x', '--extract', '--get',
                                        '-C', '--directory',
                                        '-f', '--file')]
            if len(forbiddenArgs) > 0:
                raise LeafException(
                    "You should not use tar extra arguments: " + ''.join(forbiddenArgs))
            command += tarExtraArgs

        self.logger.printDefault("Executing command:", ' '.join(command))
        rc = subprocess.call(command,
                             stdout=None,
                             stderr=subprocess.STDOUT)
        if rc != 0:
            raise LeafException("Error executing: %s" % ' '.join(command))
