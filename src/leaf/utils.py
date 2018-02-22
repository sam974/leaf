'''
Leaf Package Manager

@author:    Sébastien MB <smassot@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''

import hashlib
import os
from pathlib import Path
import random
import re
import requests
import string
from tarfile import TarFile
import time
import urllib
from urllib.parse import urlparse, urlunparse

from leaf.constants import LeafConstants


_IGNORED_PATTERN = re.compile('^.*_ignored[0-9]*$')


def resolveUrl(remoteUrl, subPath):
    '''
    Resolves a relative URL
    '''
    url = urlparse(remoteUrl)
    newPath = Path(url.path).parent / subPath
    url = url._replace(path=str(newPath))
    return urlunparse(url)


def getCachedArtifactName(filename, sha1sum):
    '''
    Compute a unique name for files in cache
    '''
    prefixLen = 7
    if sha1sum is not None and len(sha1sum) >= prefixLen:
        prefix = sha1sum[:prefixLen]
    else:
        prefix = ''.join(random.choice(string.ascii_uppercase + string.digits)
                         for _ in range(prefixLen))
    return "%s-%s" % (prefix, filename)


def isFolderIgnored(folder):
    '''
    Checks if a package folder should be ignored
    '''
    return _IGNORED_PATTERN.match(folder.name) is not None


def markFolderAsIgnored(folder):
    '''
    Marks the given folder as ignored
    '''
    oldname = folder.name
    newname = oldname + "_ignored" + str(int(time.time()))
    if _IGNORED_PATTERN.match(newname) is None:
        raise ValueError('Invalid ignored folder name: ' + newname)
    out = folder.parent / newname
    folder.rename(out)
    return out


def openOutputTarFile(path):
    '''
    Opens a tar file with the correct compression given its extension
    '''
    suffix = LeafConstants.LEAF_COMPRESSION.get(path.suffix, 'xz')
    mode = "w"
    if len(suffix) > 0:
        mode += ":" + suffix
    return TarFile.open(str(path), mode)


def computeSha1sum(file):
    '''
    Return the sha1 of the given file
    '''
    BLOCKSIZE = 4096
    hasher = hashlib.sha1()
    with open(str(file), 'rb') as fp:
        buf = fp.read(BLOCKSIZE)
        while len(buf) > 0:
            hasher.update(buf)
            buf = fp.read(BLOCKSIZE)
    return hasher.hexdigest()


def downloadFile(url, folder, logger, filename=None, sha1sum=None):
    '''
    Download an artifact and eventually check its sha1
    '''
    parsedUrl = urlparse(url)
    if filename is None:
        filename = Path(parsedUrl.path).name
    targetFile = folder / filename
    if targetFile.exists():
        if sha1sum is None:
            logger.printDetail("File exists but cannot be verified,",
                               targetFile.name, " will be re-downloaded")
            os.remove(str(targetFile))
        elif sha1sum != computeSha1sum(targetFile):
            logger.printDetail("File exists but SHA1 differs,",
                               targetFile.name, " will be re-downloaded")
            os.remove(str(targetFile))
        else:
            logger.printDetail(
                "File already in cache:", targetFile.name)
    if not targetFile.exists():
        if parsedUrl.scheme.startswith("http"):
            req = requests.get(url,
                               stream=True,
                               timeout=LeafConstants.DOWNLOAD_TIMEOUT)
            size = int(req.headers.get('content-length', -1))
            logger.progressStart('download', total=size)
            currentSize = 0
            with open(str(targetFile), 'wb') as fp:
                for data in req.iter_content(1024 * 1024):
                    currentSize += len(data)
                    logger.progressWorked('download',
                                          "Downloading " + targetFile.name,
                                          worked=currentSize,
                                          total=size,
                                          sameLine=True)
                    fp.write(data)
        else:
            logger.progressStart('download')
            urllib.request.urlretrieve(url, str(targetFile))
        logger.progressDone('download',
                            "File downloaded: " + str(targetFile))
        if sha1sum is not None and sha1sum != computeSha1sum(targetFile):
            raise ValueError(
                "Invalid SHA1 sum for " + targetFile.name + ", expecting " + sha1sum)
    return targetFile