#  Copyright (c) 2025 by EOPF Sample Service team and contributors
#  Permissions are hereby granted under the terms of the Apache 2.0 License:
#  https://opensource.org/license/apache-2-0.

import unittest

from xcube.util.extension import ExtensionRegistry

from xcube_eopf.plugin import init_plugin


class XcubePluginTest(unittest.TestCase):
    def test_plugin(self):
        """Assert xcube extensions registered by xcube-stac"""
        registry = ExtensionRegistry()
        init_plugin(registry)
        self.assertEqual(
            {
                "xcube.core.store": {
                    "eopf-zarr": {
                        "component": "<not loaded yet>",
                        "description": "EOPF-Zarr DataStore",
                        "name": "eopf-zarr",
                        "point": "xcube.core.store",
                    },
                }
            },
            registry.to_dict(),
        )
