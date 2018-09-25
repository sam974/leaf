'''
@author: Legato Tooling Team <letools@sierrawireless.com>
'''

import json
import unittest
from collections import OrderedDict
from tempfile import mktemp

from leaf.cli.external import grepDescription
from leaf.constants import JsonConstants
from leaf.core.coreutils import groupPackageIdentifiersByName
from leaf.model.base import JsonObject
from leaf.model.modelutils import layerModelDiff, layerModelUpdate
from leaf.model.package import Feature, PackageIdentifier
from leaf.utils import checkSupportedLeaf, jsonLoadFile, jsonWriteFile
from tests.testutils import EXTENSIONS_FOLDER, RESOURCE_FOLDER


class TestMisc(unittest.TestCase):

    def testGrepDescription(self):
        file = RESOURCE_FOLDER / "leaf-foo.sh"
        self.assertTrue(file.exists())
        description = grepDescription(file)
        self.assertEqual("The description of my command", description)

        file = RESOURCE_FOLDER / "install_1.0" / "manifest.json"
        self.assertTrue(file.exists())
        description = grepDescription(file)
        self.assertIsNone(description)

        for extension in EXTENSIONS_FOLDER.iterdir():
            description = grepDescription(extension)
            print(extension, description)
            self.assertIsNotNone(description)

    def testLeafMinVersion(self):
        self.assertTrue(checkSupportedLeaf(None))
        self.assertTrue(checkSupportedLeaf("2.0", "2.0"))
        self.assertFalse(checkSupportedLeaf("2.1", "2.0"))
        with self.assertRaises(ValueError):
            self.assertFalse(checkSupportedLeaf("2.1", "2.0",
                                                exceptionMessage="foo"))

    def testJo(self):
        jo = JsonObject({})
        self.assertIsNone(jo.jsonpath(["a"]))
        self.assertIsNotNone(jo.jsonpath(["a"], {}))
        self.assertIsNotNone(jo.jsonpath(["a"]))

        self.assertIsNone(jo.jsonpath(["a", "b"]))
        self.assertIsNotNone(jo.jsonpath(["a", "b"], {}))
        self.assertIsNotNone(jo.jsonpath(["a", "b"]))

        self.assertIsNone(jo.jsonpath(["a", "b", "c"]))
        self.assertEqual("hello", jo.jsonpath(["a", "b", "c"], "hello"))
        self.assertEqual("hello", jo.jsonpath(["a", "b", "c"], "world"))
        self.assertEqual("hello", jo.jsonpath(["a", "b", "c"]))

        tmpFile = mktemp(".json", "leaf-ut")
        jsonWriteFile(tmpFile, jo.json, pp=True)
        jo = JsonObject(jsonLoadFile(tmpFile))

        self.assertEqual("hello", jo.jsonpath(["a", "b", "c"], "hello"))
        self.assertEqual("hello", jo.jsonpath(["a", "b", "c"], "world"))
        self.assertEqual("hello", jo.jsonpath(["a", "b", "c"]))

        with self.assertRaises(ValueError):
            jo.jsonget("z", mandatory=True)
        with self.assertRaises(ValueError):
            jo.jsonpath(["a", "b", "c", "d"])
        with self.assertRaises(ValueError):
            jo.jsonpath(["a", "d", "e"])

    def testFeaturesEquals(self):
        self.assertEqual(Feature("id1", {
            JsonConstants.INFO_FEATURE_KEY: "KEY1",
            JsonConstants.INFO_FEATURE_VALUES: {"enum1": "value1"},
            JsonConstants.INFO_FEATURE_DESCRIPTION: "message"
        }), Feature("id1", {
            JsonConstants.INFO_FEATURE_KEY: "KEY1",
            JsonConstants.INFO_FEATURE_VALUES: {"enum1": "value1"},
            JsonConstants.INFO_FEATURE_DESCRIPTION: "message"
        }))

        # Different name
        self.assertNotEqual(Feature("id1", {
            JsonConstants.INFO_FEATURE_KEY: "KEY1",
            JsonConstants.INFO_FEATURE_VALUES: {"enum1": "value1"},
            JsonConstants.INFO_FEATURE_DESCRIPTION: "message"
        }), Feature("id2", {
            JsonConstants.INFO_FEATURE_KEY: "KEY1",
            JsonConstants.INFO_FEATURE_VALUES: {"enum1": "value1"},
            JsonConstants.INFO_FEATURE_DESCRIPTION: "message"
        }))

        # Different key
        self.assertNotEqual(Feature("id1", {
            JsonConstants.INFO_FEATURE_KEY: "KEY1",
            JsonConstants.INFO_FEATURE_VALUES: {"enum1": "value1"},
            JsonConstants.INFO_FEATURE_DESCRIPTION: "message"
        }), Feature("id1", {
            JsonConstants.INFO_FEATURE_KEY: "KEY2",
            JsonConstants.INFO_FEATURE_VALUES: {"enum1": "value1"},
            JsonConstants.INFO_FEATURE_DESCRIPTION: "message"
        }))

        # Different enum
        self.assertNotEqual(Feature("id1", {
            JsonConstants.INFO_FEATURE_KEY: "KEY1",
            JsonConstants.INFO_FEATURE_VALUES: {"enum1": "value1"},
            JsonConstants.INFO_FEATURE_DESCRIPTION: "message"
        }), Feature("id1", {
            JsonConstants.INFO_FEATURE_KEY: "KEY1",
            JsonConstants.INFO_FEATURE_VALUES: {"enum2": "value1"},
            JsonConstants.INFO_FEATURE_DESCRIPTION: "message"
        }))

        # Different value
        self.assertNotEqual(Feature("id1", {
            JsonConstants.INFO_FEATURE_KEY: "KEY1",
            JsonConstants.INFO_FEATURE_VALUES: {"enum1": "value1"},
            JsonConstants.INFO_FEATURE_DESCRIPTION: "message"
        }), Feature("id1", {
            JsonConstants.INFO_FEATURE_KEY: "KEY1",
            JsonConstants.INFO_FEATURE_VALUES: {"enum1": "value2"},
            JsonConstants.INFO_FEATURE_DESCRIPTION: "message"
        }))

        # Different size
        self.assertNotEqual(Feature("id1", {
            JsonConstants.INFO_FEATURE_KEY: "KEY1",
            JsonConstants.INFO_FEATURE_VALUES: {"enum1": "value1"},
            JsonConstants.INFO_FEATURE_DESCRIPTION: "message"
        }), Feature("id1", {
            JsonConstants.INFO_FEATURE_KEY: "KEY1",
            JsonConstants.INFO_FEATURE_VALUES: {"enum1": "value1", "enum2": "value1"},
            JsonConstants.INFO_FEATURE_DESCRIPTION: "message"
        }))

        # Different description
        self.assertNotEqual(Feature("id1", {
            JsonConstants.INFO_FEATURE_KEY: "KEY1",
            JsonConstants.INFO_FEATURE_VALUES: {"enum1": "value1"},
            JsonConstants.INFO_FEATURE_DESCRIPTION: "message"
        }), Feature("id1", {
            JsonConstants.INFO_FEATURE_KEY: "KEY1",
            JsonConstants.INFO_FEATURE_VALUES: {"enum1": "value1"},
            JsonConstants.INFO_FEATURE_DESCRIPTION: "message2"
        }))

        # Different description: None
        self.assertNotEqual(Feature("id1", {
            JsonConstants.INFO_FEATURE_KEY: "KEY1",
            JsonConstants.INFO_FEATURE_VALUES: {"enum1": "value1"},
            JsonConstants.INFO_FEATURE_DESCRIPTION: "message"
        }), Feature("id1", {
            JsonConstants.INFO_FEATURE_KEY: "KEY1",
            JsonConstants.INFO_FEATURE_VALUES: {"enum1": "value1"},
            JsonConstants.INFO_FEATURE_DESCRIPTION: None
        }))

        # Different description: missing
        self.assertNotEqual(Feature("id1", {
            JsonConstants.INFO_FEATURE_KEY: "KEY1",
            JsonConstants.INFO_FEATURE_VALUES: {"enum1": "value1"},
            JsonConstants.INFO_FEATURE_DESCRIPTION: "message"
        }), Feature("id1", {
            JsonConstants.INFO_FEATURE_KEY: "KEY1",
            JsonConstants.INFO_FEATURE_VALUES: {"enum1": "value1"}
        }))

    def testFeaturesAlias(self):
        feature = Feature("id1", {
            JsonConstants.INFO_FEATURE_KEY: "KEY1",
            JsonConstants.INFO_FEATURE_VALUES: {"enum1": "value1"},
        })
        feature_newValue = Feature("id1", {
            JsonConstants.INFO_FEATURE_KEY: "KEY1",
            JsonConstants.INFO_FEATURE_VALUES: {"enum1": "value1",
                                                "enum2": "value2"},
        })
        feature_dupValue = Feature("id1", {
            JsonConstants.INFO_FEATURE_KEY: "KEY1",
            JsonConstants.INFO_FEATURE_VALUES: {"enum1": "value3",
                                                "enum3": None},
        })
        feature_altKey = Feature("id1", {
            JsonConstants.INFO_FEATURE_KEY: "KEY2",
            JsonConstants.INFO_FEATURE_VALUES: {"enum1": "value1"},
        })
        otherFeature = Feature("id2", {
            JsonConstants.INFO_FEATURE_KEY: "KEY1",
            JsonConstants.INFO_FEATURE_VALUES: {"enum1": "value1"},
        })

        testFeature = Feature("id1", {JsonConstants.INFO_FEATURE_KEY: "KEY1"})
        testFeature.check()
        with self.assertRaises(ValueError):
            testFeature.getValue("enum1")

        testFeature = Feature("id1", {JsonConstants.INFO_FEATURE_KEY: "KEY1"})
        testFeature.addAlias(feature)
        testFeature.check()
        with self.assertRaises(ValueError):
            testFeature.getValue("enum2")

        testFeature = Feature("id1", {JsonConstants.INFO_FEATURE_KEY: "KEY1"})
        testFeature.addAlias(feature)
        testFeature.addAlias(feature_newValue)
        testFeature.check()
        self.assertEqual("value1", testFeature.getValue("enum1"))
        self.assertEqual("value2", testFeature.getValue("enum2"))

        testFeature = Feature("id1", {JsonConstants.INFO_FEATURE_KEY: "KEY1"})
        testFeature.addAlias(feature)
        testFeature.addAlias(feature_newValue)
        testFeature.addAlias(feature_dupValue)
        testFeature.check()
        with self.assertRaises(ValueError):
            testFeature.getValue("enum1")
        self.assertEqual("value2", testFeature.getValue("enum2"))
        self.assertEqual(None, testFeature.getValue("enum3"))

        testFeature = Feature("id1", {JsonConstants.INFO_FEATURE_KEY: "KEY1"})
        testFeature.addAlias(feature)
        testFeature.addAlias(feature_newValue)
        testFeature.addAlias(feature_dupValue)
        testFeature.addAlias(feature_altKey)
        with self.assertRaises(ValueError):
            testFeature.check()

        testFeature = Feature("id1", {JsonConstants.INFO_FEATURE_KEY: "KEY1"})
        with self.assertRaises(ValueError):
            testFeature.addAlias(otherFeature)

    def testModelUpdate(self):
        def json2model(s):
            return json.loads(s, object_pairs_hook=OrderedDict)

        def assertJson(left, diff, right):
            if diff is None:
                self.assertEqual(json2model(left), json2model(right))
            else:
                self.assertEqual(
                    layerModelUpdate(json2model(left), json2model(diff)),
                    json2model(right))
                self.assertEqual(
                    layerModelDiff(json2model(left), json2model(right)),
                    json2model(diff))

        assertJson(
            '{}',
            None,
            '{}')
        assertJson(
            '{"number":1,"string":"A","object":{"list":[1,2,3],"object":{"number":42,"string":"foo","boolean":true}}}',
            None,
            '{"number":1,"string":"A","object":{"list":[1,2,3],"object":{"number":42,"string":"foo","boolean":true}}}')
        assertJson(
            '{"number":1,"string":"A","object":{"list":[1,2,3],"object":{"number":42,"string":"foo","boolean":true}}}',
            '{"object":{"object":{"number":1,"boolean":false}}}',
            '{"number":1,"string":"A","object":{"list":[1,2,3],"object":{"number":1,"string":"foo","boolean":false}}}')
        assertJson(
            '{"number":1,"string":"A","object":{"list":[1,2,3],"object":{"number":42,"string":"foo","boolean":true}}}',
            '{"string":null,"object":{"object":{"number":1,"boolean":false}},"string2":"A"}',
            '{"number":1,"object":{"list":[1,2,3],"object":{"number":1,"string":"foo","boolean":false}},"string2":"A"}')

    def testSortPi(self):
        a10 = PackageIdentifier.fromString("a_1.0")
        a20 = PackageIdentifier.fromString("a_2.0")
        a11 = PackageIdentifier.fromString("a_1.1")
        a21 = PackageIdentifier.fromString("a_2.1")
        b10 = PackageIdentifier.fromString("b_1.0")
        b20 = PackageIdentifier.fromString("b_2.0")
        b11 = PackageIdentifier.fromString("b_1.1")
        b21 = PackageIdentifier.fromString("b_2.1")

        pkgMap = groupPackageIdentifiersByName(
            [a20, a10, b11, b21, a21])
        self.assertEquals(pkgMap,
                          {'a': [a10, a20, a21],
                           'b': [b11, b21]})

        pkgMap = groupPackageIdentifiersByName(
            [b10, a11, b20, a20], pkgMap=pkgMap)
        self.assertEquals(pkgMap,
                          {'a': [a10, a11, a20, a21],
                           'b': [b10, b11, b20, b21]})