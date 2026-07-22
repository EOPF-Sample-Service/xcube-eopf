#  Copyright (c) 2025-2026 by EOPF Sample Service team and contributors
#  Permissions are hereby granted under the terms of the Apache 2.0 License:
#  https://opensource.org/license/apache-2-0.

from unittest import TestCase

import xarray as xr

from xcube_eopf.constants import SCHEMA_DEM, JsonPythonTypeSchema


class JsonPythonTypeSchemaTest(TestCase):

    def test_to_dict_exposes_object_type(self):
        schema = JsonPythonTypeSchema(xr.DataArray, title="Example schema")

        schema_dict = schema.to_dict()

        self.assertEqual("object", schema_dict["type"])
        self.assertEqual("Example schema", schema_dict["title"])

    def test_validate_instance_checks_python_type(self):
        schema = JsonPythonTypeSchema(xr.DataArray)
        valid_instance = xr.DataArray([1, 2, 3])

        schema.validate_instance(valid_instance)
        self.assertIs(schema._to_unvalidated_instance(valid_instance), valid_instance)
        self.assertIs(schema._from_validated_instance(valid_instance), valid_instance)

        with self.assertRaises(TypeError) as cm:
            schema.validate_instance([1, 2, 3])

        self.assertEqual("Expected DataArray, got list", str(cm.exception))

    def test_schema_dem_uses_json_python_type_schema(self):
        schema_dict = SCHEMA_DEM.to_dict()

        self.assertEqual("object", schema_dict["type"])
        self.assertEqual(xr.DataArray, SCHEMA_DEM.python_type)
