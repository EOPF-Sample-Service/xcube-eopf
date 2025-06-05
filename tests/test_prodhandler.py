#  Copyright (c) 2025 by EOPF Sample Service team and contributors
#  Permissions are hereby granted under the terms of the Apache 2.0 License:
#  https://opensource.org/license/apache-2-0.

from unittest import TestCase

import pytest
import xarray as xr
from xcube.util.jsonschema import JsonObjectSchema

from xcube_eopf.prodhandler import ProductHandler, ProductHandlerRegistry
from xcube_eopf.prodhandlers.sentinel2 import (
    Sen2L1CProductHandler,
    Sen2L2AProductHandler,
)


class TestProductHandler(ProductHandler):
    data_id = "TEST"

    def get_open_data_params_schema(self) -> JsonObjectSchema:
        return JsonObjectSchema()

    def open_data(self, **open_params) -> xr.Dataset:
        return xr.Dataset()


class ProductHandlerTest(TestCase):
    def setUp(self):
        ProductHandler.registry.register(TestProductHandler)

    def tearDown(self):
        ProductHandler.registry.unregister(TestProductHandler)

    def test_guess_ok(self):
        self.assertIsInstance(ProductHandler.guess("TEST"), TestProductHandler)

    # noinspection PyMethodMayBeStatic
    def test_guess_fail(self):
        with pytest.raises(
            ValueError,
            match=(
                "Unable to detect product handler for 'REST'. Use `data_id` "
                "argument to pass one of 'TEST'."
            ),
        ):
            ProductHandler.guess("REST")

    def test_from_data_id(self):
        self.assertIsInstance(ProductHandler.from_data_id("TEST"), TestProductHandler)
        self.assertIsNone(ProductHandler.from_data_id("REST"))


class ProductHandlerRegistryTest(TestCase):
    # noinspection PyMethodMayBeStatic
    def get(self):
        reg = ProductHandlerRegistry()
        reg.register(Sen2L1CProductHandler)
        reg.register(Sen2L2AProductHandler)
        return reg

    def test_get(self):
        reg = self.get()
        self.assertIsInstance(reg.get("sentinel-2-l1c"), Sen2L1CProductHandler)
        self.assertIsInstance(reg.get("sentinel-2-l2a"), Sen2L2AProductHandler)
        self.assertIsNone(reg.get("sentinel-2-l3a"))

    def test_keys_and_values(self):
        reg = self.get()
        self.assertEqual(["sentinel-2-l1c", "sentinel-2-l2a"], list(reg.keys()))
        values = list(reg.values())
        self.assertEqual(2, len(values))
        self.assertIsInstance(values[0], Sen2L1CProductHandler)
        self.assertIsInstance(values[1], Sen2L2AProductHandler)

    def test_register_unregister(self):
        reg = self.get()
        reg.register(TestProductHandler)
        self.assertIsInstance(reg.get("TEST"), TestProductHandler)
        reg.unregister(TestProductHandler)
        self.assertIsNone(reg.get("TEST"))
