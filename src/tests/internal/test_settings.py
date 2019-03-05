"""
@author: Legato Tooling Team <letools@sierrawireless.com>
"""

import os

from leaf.core.constants import LeafSettings
from leaf.core.settings import EnumValidator, RegexValidator, Setting, StaticSettings
from tests.testutils import LeafTestCase

KEY = "LEAF_TEST_MYSETTING"


class TestSettings(LeafTestCase):
    def setUp(self):
        if KEY in os.environ:
            del os.environ[KEY]
        self.assertFalse(KEY in os.environ)

    def test_regex_validator(self):
        v = RegexValidator(r"[A-Z]+")
        self.assertTrue(v("A"))
        self.assertTrue(v("AA"))
        self.assertFalse(v("a"))
        self.assertFalse(v("aA"))
        self.assertFalse(v(""))

        v = RegexValidator(r"[A-Z]+")
        self.assertTrue(v("A"))
        self.assertTrue(v("AA"))
        self.assertFalse(v("a"))
        self.assertFalse(v("aA"))
        self.assertFalse(v(""))

    def test_enum_validator(self):
        v = EnumValidator(["None", None, 1, "A", "A"])
        self.assertTrue(v("A"))
        self.assertTrue(v("None"))
        self.assertTrue(v(None))
        self.assertFalse(v("AA"))

    def test_setting_simple(self):
        s = Setting(KEY)
        self.assertEqual(None, s.value)

        s.value = "1"
        self.assertEqual("1", s.value)
        self.assertEqual("1", os.getenv(KEY))

        s.value = 1
        self.assertEqual("1", s.value)
        self.assertEqual("1", os.getenv(KEY))

        s.value = None
        self.assertEqual(None, s.value)
        self.assertFalse(KEY in os.environ)

        os.environ[KEY] = "123"
        self.assertEqual("123", s.value)

    def test_setting_regex(self):
        s = Setting(KEY, default="MyDefaultValue", validator=RegexValidator("[A-Za-z]+"))

        self.assertEqual("MyDefaultValue", s.value)
        self.assertFalse(KEY in os.environ)

        s.value = "A"
        self.assertEqual("A", s.value)
        self.assertEqual("A", os.getenv(KEY))

        with self.assertRaises(ValueError):
            s.value = 1
        self.assertEqual("A", s.value)
        self.assertEqual("A", os.getenv(KEY))

        with self.assertRaises(ValueError):
            s.value = "1"
        self.assertEqual("A", s.value)
        self.assertEqual("A", os.getenv(KEY))

        s.value = None
        self.assertEqual("MyDefaultValue", s.value)
        self.assertFalse(KEY in os.environ)

        os.environ[KEY] = "ABC"
        self.assertEqual("ABC", s.value)

        os.environ[KEY] = "123"
        self.assertEqual("MyDefaultValue", s.value)

        with self.assertRaises(ValueError):
            s = Setting(KEY, default="123", validator=RegexValidator("[A-Za-z]+"))

    def test_setting_enum(self):
        with self.assertRaises(ValueError):
            s = Setting(KEY, default="B", validator=EnumValidator(("A", 1)))

        s = Setting(KEY, validator=EnumValidator(("A", "1", 2, None)))

        self.assertEqual(None, s.value)

        s.value = "A"
        self.assertEqual("A", s.value)

        s.value = 1
        self.assertEqual("1", s.value)

        s.value = None
        self.assertEqual(None, s.value)

        s.value = "1"
        self.assertEqual("1", s.value)

        with self.assertRaises(ValueError):
            s.value = 2
        with self.assertRaises(ValueError):
            s.value = "2"

    def test_boolean(self):

        s = Setting(KEY)
        self.assertFalse(s.as_boolean())

        for v, b in (
            ("0", False),
            ("False", False),
            ("FALSE", False),
            ("NO", False),
            ("no", False),
            ("", False),
            ("  ", False),
            ("1", True),
            (" 1 ", True),
            ("A", True),
            ("True", True),
        ):
            s.value = v
            self.assertEqual(v, s.value)
            self.assertEqual(b, s.as_boolean())

    def test_leaf_settings(self):
        for e in LeafSettings.values():
            if e.default is not None:
                self.assertIsNotNone(e.value)
        self.assertIsNotNone(LeafSettings.get_by_key("LEAF_DEBUG"))

    def test_misc(self):
        class SettingsA(StaticSettings):
            A = Setting(KEY)

        class SettingsB(SettingsA):
            B = Setting(KEY)

        SettingsA.A.value = 1
        self.assertEqual("1", SettingsB.A.value)
        self.assertEqual("1", SettingsB.B.value)

        self.assertEqual(1, len(SettingsA.values()))
        self.assertEqual(1, len(SettingsB.values()))

        self.assertIsNotNone(SettingsA.get_by_key(KEY))
        self.assertIsNotNone(SettingsB.get_by_key(KEY))
