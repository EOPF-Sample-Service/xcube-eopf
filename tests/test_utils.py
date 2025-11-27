#  Copyright (c) 2025 by EOPF Sample Service team and contributors
#  Permissions are hereby granted under the terms of the Apache 2.0 License:
#  https://opensource.org/license/apache-2-0.

import datetime
import unittest

import numpy as np
import pyproj
import pystac
import xarray as xr

from xcube_eopf.utils import (
    add_nominal_datetime,
    mosaic_spatial_take_first,
    normalize_crs,
)


class UtilsTest(unittest.TestCase):

    def test_normalize_crs(self):
        crs_str = "EPSG:4326"
        crs_pyproj = pyproj.CRS.from_string(crs_str)
        self.assertEqual(crs_pyproj, normalize_crs(crs_str))
        self.assertEqual(crs_pyproj, normalize_crs(crs_pyproj))

    def test_add_nominal_datetime(self):
        item0 = pystac.Item(
            id="item0",
            geometry=None,
            bbox=[0, 50, 1, 51],
            datetime=datetime.datetime(2024, 6, 1, 12, 0, 0),
            properties=dict(),
        )
        item1 = pystac.Item(
            id="item1",
            geometry=None,
            bbox=[150, 50, 151, 51],
            datetime=datetime.datetime(2024, 7, 1, 16, 0, 0),
            properties=dict(),
        )
        items = [item0, item1]
        items_nominal_time = add_nominal_datetime(items)

        item = items_nominal_time[0]
        self.assertIn("datetime_nominal", item.properties)
        self.assertEqual(
            datetime.datetime(2024, 6, 1, 12, 0, 0),
            item.properties["datetime_nominal"],
        )
        self.assertIn("center_point", item.properties)
        self.assertEqual((0.5, 50.5), item.properties["center_point"])

        item = items_nominal_time[1]
        self.assertIn("datetime_nominal", item.properties)
        self.assertEqual(
            datetime.datetime(2024, 7, 2, 2, 0, 0),
            item.properties["datetime_nominal"],
        )
        self.assertIn("center_point", item.properties)
        self.assertEqual((150.5, 50.5), item.properties["center_point"])

    def test_mosaic_spatial_take_first(self):
        list_ds = []
        # first tile
        data = np.array(
            [
                [[1, 2, 3], [4, 5, 6], [7, 8, 9]],
                [[10, 11, 12], [13, 14, np.nan], [np.nan, np.nan, np.nan]],
                [[19, 20, 21], [np.nan, np.nan, np.nan], [np.nan, np.nan, np.nan]],
            ],
            dtype=float,
        )
        dims = ("time", "lat", "lon")
        coords = {
            "time": np.array(
                ["2025-01-01", "2025-01-02", "2025-01-03"], dtype="datetime64"
            ),
            "lat": [10.0, 20.0, 30.0],
            "lon": [100.0, 110.0, 120.0],
        }
        da = xr.DataArray(data, dims=dims, coords=coords)
        list_ds.append(xr.Dataset({"B01": da}))
        # second tile
        data = np.array(
            [
                [[np.nan, np.nan, np.nan], [np.nan, np.nan, 106], [107, 108, 109]],
                [[np.nan, np.nan, np.nan], [113, 114, 115], [116, 117, 118]],
                [[np.nan, np.nan, 120], [121, 122, 123], [124, 125, 126]],
            ],
            dtype=float,
        )
        dims = ("time", "lat", "lon")
        coords = {
            "time": np.array(
                ["2025-01-01", "2025-01-02", "2025-01-03"], dtype="datetime64"
            ),
            "lat": [10.0, 20.0, 30.0],
            "lon": [100.0, 110.0, 120.0],
        }
        da = xr.DataArray(data, dims=dims, coords=coords)
        list_ds.append(xr.Dataset({"B01": da}))

        # test only one tile
        ds_test = mosaic_spatial_take_first(list_ds[:1])
        self.assertIsInstance(ds_test, xr.Dataset)
        xr.testing.assert_allclose(ds_test, list_ds[0])

        # test two tiles
        ds_test = mosaic_spatial_take_first(list_ds)
        self.assertIsInstance(ds_test, xr.Dataset)
        data = np.array(
            [
                [[1, 2, 3], [4, 5, 6], [7, 8, 9]],
                [[10, 11, 12], [13, 14, 115], [116, 117, 118]],
                [[19, 20, 21], [121, 122, 123], [124, 125, 126]],
            ],
            dtype=float,
        )
        dims = ("time", "lat", "lon")
        coords = {
            "time": np.array(
                ["2025-01-01", "2025-01-02", "2025-01-03"],
                dtype="datetime64",
            ),
            "lat": [10.0, 20.0, 30.0],
            "lon": [100.0, 110.0, 120.0],
        }
        da = xr.DataArray(data, dims=dims, coords=coords)
        ds_expected = xr.Dataset({"B01": da})
        xr.testing.assert_allclose(ds_test, ds_expected)

        # test two tiles, where spatial ref is given in spatial_ref coord
        spatial_ref = xr.DataArray(np.array(0), attrs=dict(crs_wkt="testing"))
        for i, ds in enumerate(list_ds):
            ds.coords["spatial_ref"] = spatial_ref
            list_ds[i] = ds
        ds_expected = xr.Dataset({"B01": da})
        ds_expected = ds_expected.assign_coords({"spatial_ref": spatial_ref})
        ds_test = mosaic_spatial_take_first(list_ds)
        self.assertIsInstance(ds_test, xr.Dataset)
        xr.testing.assert_allclose(ds_test, ds_expected)
