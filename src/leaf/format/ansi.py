'''
Fake Ansi module to manage the lack of colorama module

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
import re

from leaf.constants import LeafConstants
from leaf.format.formatutils import isatty
from leaf.utils import versionComparator_lt


# Ansi chars regex
ansiCharsRegex = re.compile(r'\x1b[^m]*m')


def removeAnsiChars(text):
    return ansiCharsRegex.sub('', text)


class _FakeAnsiFore():
    '''
    Optional module colorama is not installed, let's use dummy implementation
    '''
    BLACK = ""
    RED = ""
    GREEN = ""
    YELLOW = ""
    BLUE = ""
    MAGENTA = ""
    CYAN = ""
    WHITE = ""
    RESET = ""

    # These are fairly well supported, but not part of the standard.
    LIGHTBLACK_EX = ""
    LIGHTRED_EX = ""
    LIGHTGREEN_EX = ""
    LIGHTYELLOW_EX = ""
    LIGHTBLUE_EX = ""
    LIGHTMAGENTA_EX = ""
    LIGHTCYAN_EX = ""
    LIGHTWHITE_EX = ""


class _FakeAnsiBack():
    '''
    Optional module colorama is not installed, let's use dummy implementation
    '''
    BLACK = ""
    RED = ""
    GREEN = ""
    YELLOW = ""
    BLUE = ""
    MAGENTA = ""
    CYAN = ""
    WHITE = ""
    RESET = ""

    # These are fairly well supported, but not part of the standard.
    LIGHTBLACK_EX = ""
    LIGHTRED_EX = ""
    LIGHTGREEN_EX = ""
    LIGHTYELLOW_EX = ""
    LIGHTBLUE_EX = ""
    LIGHTMAGENTA_EX = ""
    LIGHTCYAN_EX = ""
    LIGHTWHITE_EX = ""


class _FakeAnsiStyle():
    '''
    Optional module colorama is not installed, let's use dummy implementation
    '''
    BRIGHT = ""
    DIM = ""
    NORMAL = ""
    RESET_ALL = ""


class _Ansi():
    def __init__(self):
        self.force = False
        self._fakeFore = _FakeAnsiFore()
        self._fakeBack = _FakeAnsiBack()
        self._fakeStyle = _FakeAnsiStyle()
        self.moduleLoaded = False
        try:
            import colorama
            self.moduleLoaded = True
            if '__version__' in dir(colorama) and versionComparator_lt(colorama.__version__, LeafConstants.COLORAMA_MIN_VERSION):
                self.moduleLoaded = False
            elif 'VERSION' in dir(colorama) and versionComparator_lt(colorama.VERSION, LeafConstants.COLORAMA_MIN_VERSION):
                self.moduleLoaded = False
            if self.moduleLoaded:
                self._coloramaFore = colorama.Fore
                self._coloramaBack = colorama.Back
                self._coloramaStyle = colorama.Style
        except ImportError:
            self.moduleLoaded = False

    def isEnabled(self):
        return self.moduleLoaded and (self.force or isatty())

    def fore(self):
        if self.isEnabled():
            return self._coloramaFore
        return self._fakeFore

    def back(self):
        if self.isEnabled():
            return self._coloramaBack
        return self._fakeBack

    def style(self):
        if self.isEnabled():
            return self._coloramaStyle
        return self._fakeStyle


ANSI = _Ansi()
