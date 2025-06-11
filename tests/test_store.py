#  Copyright (c) 2025 by EOPF Sample Service team and contributors
#  Permissions are hereby granted under the terms of the Apache 2.0 License:
#  https://opensource.org/license/apache-2-0.

from unittest import TestCase
from unittest.mock import patch

import numpy as np
import pytest
import xarray as xr
from xcube.core.store import DataStoreError, new_data_store
from xcube.util.jsonschema import JsonObjectSchema

from xcube_eopf.constants import CONVERSION_FACTOR_DEG_METER, DATA_STORE_ID
from xcube_eopf.utils import reproject_bbox

from .helpers import l2a_10m, l2a_60m, l2a_60m_wo_scl


class EOPFZarrDataStoreTest(TestCase):

    def setUp(self):
        self.store = new_data_store(DATA_STORE_ID)

    def test_get_data_store_params_schema(self):
        schema = self.store.get_data_store_params_schema()
        self.assertIsInstance(schema, JsonObjectSchema)
        self.assertEqual(dict(), schema.properties)
        self.assertEqual([], schema.required)
        self.assertFalse(schema.additional_properties)

    def test_get_data_types(self):
        self.assertEqual(("dataset",), self.store.get_data_types())

    def test_get_data_types_for_data(self):
        self.assertEqual(
            ("dataset",), self.store.get_data_types_for_data("sentinel-2-l1c")
        )
        self.assertEqual(
            ("dataset",), self.store.get_data_types_for_data("sentinel-2-l2a")
        )

    def test_get_data_ids(self):
        self.assertCountEqual(
            ["sentinel-2-l1c", "sentinel-2-l2a"], self.store.get_data_ids()
        )
        self.assertCountEqual(
            [("sentinel-2-l1c", {}), ("sentinel-2-l2a", {})],
            self.store.get_data_ids(include_attrs=True),
        )

    def test_has_data(self):
        self.assertTrue(self.store.has_data("sentinel-2-l1c"))
        self.assertTrue(self.store.has_data("sentinel-2-l2a"))
        self.assertFalse(self.store.has_data("sentinel-2-l3a"))
        self.assertTrue(self.store.has_data("sentinel-2-l2a", data_type="dataset"))
        with self.assertRaises(DataStoreError) as cm:
            self.store.has_data("sentinel-2-l2a", data_type="mldataset")
        self.assertEqual(
            "Data type must be 'dataset' or None, but got 'mldataset'.",
            str(cm.exception),
        )

    def test_get_data_opener_ids(self):
        self.assertEqual(("dataset:zarr:eopf-zarr",), self.store.get_data_opener_ids())
        self.assertEqual(
            ("dataset:zarr:eopf-zarr",),
            self.store.get_data_opener_ids(data_id="sentinel-2-l2a"),
        )
        with self.assertRaises(DataStoreError) as cm:
            self.store.get_data_opener_ids("sentinel-2-l3a")
        self.assertEqual(
            "Data resource 'sentinel-2-l3a' is not available.",
            str(cm.exception),
        )

    def test_get_open_data_params_schema(self):
        # no optional arguments; get all open parameters from all product handlers
        schema = self.store.get_open_data_params_schema()
        self.assertIsInstance(schema, JsonObjectSchema)
        self.assertIn("sentinel-2-l1c", schema.properties)
        self.assertIn("sentinel-2-l2a", schema.properties)

        # with data_id argument
        schema = self.store.get_open_data_params_schema(data_id="sentinel-2-l2a")
        self.assertIsInstance(schema, JsonObjectSchema)
        self.assertIn("variables", schema.properties)
        self.assertIn("spatial_res", schema.properties)
        self.assertIn("time_range", schema.properties)
        self.assertIn("bbox", schema.properties)
        self.assertIn("crs", schema.properties)
        self.assertIn("tile_size", schema.properties)
        self.assertIn("query", schema.properties)
        self.assertNotIn("test", schema.properties)
        self.assertCountEqual(
            ["time_range", "bbox", "crs", "spatial_res"], schema.required
        )

        # with invalid opener_id
        with self.assertRaises(DataStoreError) as cm:
            self.store.get_open_data_params_schema(opener_id="dataset:netcdf:eopf-zarr")
        self.assertEqual(
            "Data opener identifier must be 'dataset:zarr:eopf-zarr', "
            "but got 'dataset:netcdf:eopf-zarr'.",
            str(cm.exception),
        )

    @pytest.mark.vcr()
    @patch("xarray.open_dataset")
    def test_open_data_10m(self, mock_xarray):
        mock_xarray.return_value = l2a_10m()

        ds = self.store.open_data(
            data_id="sentinel-2-l2a",
            bbox=(610000, 5880000, 630000, 5900000),
            time_range=["2025-05-01", "2025-05-15"],
            spatial_res=10,
            crs="EPSG:32632",
            variables=["b02", "b03", "b04", "scl"],
            spline_orders={0: [np.float32], 3: ["scl"]},
        )
        self.assertIsInstance(ds, xr.Dataset)
        self.assertCountEqual(["b02", "b03", "b04", "scl"], list(ds.data_vars))
        self.assertCountEqual(
            [4, 2000, 2000], [ds.sizes["time"], ds.sizes["y"], ds.sizes["x"]]
        )
        self.assertEqual(
            [1, 1830, 1830],
            [ds.chunksizes["time"][0], ds.chunksizes["y"][0], ds.chunksizes["x"][0]],
        )
        self.assertIn("stac_url", ds.attrs)
        self.assertIn("stac_items", ds.attrs)
        self.assertIn("open_params", ds.attrs)
        self.assertIn("xcube_eopf_version", ds.attrs)

    @pytest.mark.vcr()
    @patch("xarray.open_dataset")
    def test_open_data_5m_spline_order(self, mock_xarray):
        mock_xarray.return_value = l2a_10m()

        with self.assertLogs("xcube.eopf", level="WARNING") as cm:
            ds = self.store.open_data(
                data_id="sentinel-2-l2a",
                bbox=(610000, 5880000, 630000, 5900000),
                time_range=["2025-05-01", "2025-05-15"],
                spatial_res=5,
                crs="EPSG:32632",
                variables=["b02", "b03", "b04", "scl"],
                spline_orders={0: [np.float32], 3: ["scl"]},
            )
        self.assertEqual(1, len(cm.output))
        msg = (
            f"WARNING:xcube.eopf:Spline order 3 selected for 'scl' "
            f"(categorical data). This may produce corrupted results."
        )
        self.assertEqual(msg, str(cm.output[-1]))

        self.assertIsInstance(ds, xr.Dataset)
        self.assertCountEqual(["b02", "b03", "b04", "scl"], list(ds.data_vars))
        self.assertCountEqual(
            [4, 4001, 4001], [ds.sizes["time"], ds.sizes["y"], ds.sizes["x"]]
        )
        self.assertEqual(
            [1, 1830, 1830],
            [ds.chunksizes["time"][0], ds.chunksizes["y"][0], ds.chunksizes["x"][0]],
        )
        self.assertIn("stac_url", ds.attrs)
        self.assertIn("stac_items", ds.attrs)
        self.assertIn("open_params", ds.attrs)
        self.assertIn("xcube_eopf_version", ds.attrs)

    @pytest.mark.vcr()
    @patch("xarray.open_dataset")
    def test_open_data_100m_agg_methods(self, mock_xarray):
        mock_xarray.return_value = l2a_60m()

        with self.assertLogs("xcube.eopf", level="WARNING") as cm:
            ds = self.store.open_data(
                data_id="sentinel-2-l2a",
                bbox=(610000, 5880000, 630000, 5900000),
                time_range=["2025-05-01", "2025-05-15"],
                spatial_res=100,
                crs="EPSG:32632",
                variables=["b02", "b03", "b04", "scl"],
                agg_methods={"max": [np.float32], "mean": ["scl"]},
            )
        self.assertEqual(1, len(cm.output))
        msg = (
            "WARNING:xcube.eopf:Aggregation method 'mean' selected for 'scl' "
            "(categorical data). This may produce corrupted results."
        )
        self.assertEqual(msg, str(cm.output[-1]))

        self.assertIsInstance(ds, xr.Dataset)
        self.assertCountEqual(["b02", "b03", "b04", "scl"], list(ds.data_vars))
        self.assertCountEqual(
            [4, 201, 201], [ds.sizes["time"], ds.sizes["y"], ds.sizes["x"]]
        )
        self.assertEqual(
            [1, 201, 201],
            [ds.chunksizes["time"][0], ds.chunksizes["y"][0], ds.chunksizes["x"][0]],
        )
        self.assertIn("stac_url", ds.attrs)
        self.assertIn("stac_items", ds.attrs)
        self.assertIn("open_params", ds.attrs)
        self.assertIn("xcube_eopf_version", ds.attrs)

    @pytest.mark.vcr()
    @patch("xarray.open_dataset")
    def test_open_data_geographic(self, mock_xarray):
        mock_xarray.return_value = l2a_60m_wo_scl()

        # open Sentinel-2 L2A
        bbox = [610000, 5880000, 630000, 5900000]
        bbox_wgs84 = reproject_bbox(bbox, "EPSG:32632", "EPSG:4326")
        ds = self.store.open_data(
            data_id="sentinel-2-l2a",
            bbox=bbox_wgs84,
            time_range=["2025-05-01", "2025-05-15"],
            spatial_res=50 / CONVERSION_FACTOR_DEG_METER,
            crs="EPSG:4326",
            variables=["b02", "b03", "b04"],
        )
        self.assertIsInstance(ds, xr.Dataset)
        self.assertCountEqual(["b02", "b03", "b04"], list(ds.data_vars))
        self.assertCountEqual(
            [4, 412, 684], [ds.sizes["time"], ds.sizes["lat"], ds.sizes["lon"]]
        )
        self.assertEqual(
            [1, 412, 684],
            [
                ds.chunksizes["time"][0],
                ds.chunksizes["lat"][0],
                ds.chunksizes["lon"][0],
            ],
        )
        self.assertIn("stac_url", ds.attrs)
        self.assertIn("stac_items", ds.attrs)
        self.assertIn("open_params", ds.attrs)
        self.assertIn("xcube_eopf_version", ds.attrs)

    @pytest.mark.vcr()
    @patch("xarray.open_dataset")
    def test_open_data_spline_order_raise_logs(self, mock_xarray):
        mock_xarray.return_value = l2a_60m()

        bbox = [610000, 5880000, 630000, 5900000]
        bbox_wgs84 = reproject_bbox(bbox, "EPSG:32632", "EPSG:4326")
        with self.assertLogs("xcube.eopf", level="WARNING") as cm:
            ds = self.store.open_data(
                data_id="sentinel-2-l2a",
                bbox=bbox_wgs84,
                time_range=["2025-05-01", "2025-05-15"],
                spatial_res=50 / CONVERSION_FACTOR_DEG_METER,
                crs="EPSG:4326",
                variables=["b02", "b03", "b04", "scl"],
                spline_orders=2,
            )
        self.assertEqual(1, len(cm.output))
        msg = (
            "WARNING:xcube.eopf:User-defined spline-orders is not supported yet, "
            "when reprojecting to a different CRS. Default interpolation will be "
            "used: bilinear for continuous data, and nearest-neighbor for 'scl'."
        )
        self.assertEqual(msg, str(cm.output[-1]))
        self.assertIsInstance(ds, xr.Dataset)
        self.assertCountEqual(["b02", "b03", "b04", "scl"], list(ds.data_vars))
        self.assertCountEqual(
            [4, 412, 684], [ds.sizes["time"], ds.sizes["lat"], ds.sizes["lon"]]
        )
        self.assertEqual(
            [1, 412, 684],
            [
                ds.chunksizes["time"][0],
                ds.chunksizes["lat"][0],
                ds.chunksizes["lon"][0],
            ],
        )
        self.assertIn("stac_url", ds.attrs)
        self.assertIn("stac_items", ds.attrs)
        self.assertIn("open_params", ds.attrs)
        self.assertIn("xcube_eopf_version", ds.attrs)

    @pytest.mark.vcr()
    def test_open_data_no_items_found(self):
        with self.assertRaises(DataStoreError) as cm:
            _ = self.store.open_data(
                data_id="sentinel-2-l2a",
                bbox=(610000, 5880000, 630000, 5900000),
                time_range=["2016-05-01", "2017-05-15"],
                spatial_res=10,
                crs="EPSG:32632",
                variables=["b02", "b03", "b04", "scl"],
            )
        self.assertEqual(
            str(cm.exception),
            "No items found for search_params {'collections': "
            "['sentinel-2-l2a'], 'datetime': ['2016-05-01', '2017-05-15'], "
            "'bbox': (10.641359519532669, 53.0536720941606, 10.947730608944445, "
            "53.23787163529459), 'query': None}.",
        )

    def test_describe_data(self):
        with self.assertRaises(NotImplementedError) as cm:
            self.store.describe_data("sentinel-2-l1c")
        self.assertEqual("`describe_data` is not implemented, yet.", f"{cm.exception}")

    def test_search_data(self):
        with self.assertRaises(NotImplementedError) as cm:
            self.store.search_data("sentinel-2-l1c")
        self.assertEqual(
            (
                "Search is not supported. Only Sentinel-2 L1C and L2A products "
                "are currently handled."
            ),
            f"{cm.exception}",
        )

    def test_get_search_params_schema(self):
        schema = self.store.get_search_params_schema()
        self.assertEqual(schema.properties, dict())
        self.assertEqual(schema.required, [])
        self.assertTrue(schema.additional_properties)
