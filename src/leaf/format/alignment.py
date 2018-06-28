'''
Vertical and horizontal alignment code

@author:    Nicolas Lambert <nlambert@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
import math
from enum import unique, Enum


def _topAlign(lines, height):
    '''
    Vertical align a list of string based on the given height
    '''
    out = lines.copy()
    out.extend([""] * (height - len(lines)))
    return out


def _middleAlign(lines, height):
    '''
    Vertical align a list of string based on the given height
    '''
    # Calculate lines above and under
    diff = height - len(lines)
    aboveLinesCount = underLinesCount = math.floor(diff / 2)
    if diff % 2 != 0:
        underLinesCount += 1

    # Add blank lines
    out = [""] * aboveLinesCount
    out.extend(lines)
    out.extend([""] * underLinesCount)
    return out


def _bottomAlign(lines, height):
    '''
    Vertical align a list of string based on the given height
    '''
    out = [""] * (height - len(lines))
    out.extend(lines)
    return out


@unique
class HAlign(Enum):
    '''
    Types of Horizontal alignment
    '''
    LEFT = str.ljust
    CENTER = str.center
    RIGHT = str.rjust


@unique
class VAlign(Enum):
    '''
    Types of Vertical alignment
    '''
    TOP = _topAlign
    MIDDLE = _middleAlign
    BOTTOM = _bottomAlign
