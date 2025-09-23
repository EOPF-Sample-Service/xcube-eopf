#  Copyright (c) 2025 by EOPF Sample Service team and contributors
#  Permissions are hereby granted under the terms of the Apache 2.0 License:
#  https://opensource.org/license/apache-2-0.

import datetime
import unittest

import numpy as np
import pyproj
import pystac
import xarray as xr
from xcube.core.store import DataStoreError
from xcube_resampling.gridmapping import GridMapping

from xcube_eopf.utils import (
    add_nominal_datetime,
    get_gridmapping,
    get_spatial_dims,
    mosaic_spatial_take_first,
    normalize_crs,
    reproject_bbox,
)


class UtilsTest(unittest.TestCase):

    def test_reproject_bbox(self):
        bbox_wgs84 = [2, 50, 3, 51]
        crs_wgs84 = "EPSG:4326"
        crs_3035 = "EPSG:3035"
        bbox_3035 = [3748675.9529771, 3011432.8944597, 3830472.1359979, 3129432.4914285]
        self.assertEqual(bbox_wgs84, reproject_bbox(bbox_wgs84, crs_wgs84, crs_wgs84))
        self.assertEqual(bbox_3035, reproject_bbox(bbox_3035, crs_3035, crs_3035))
        np.testing.assert_almost_equal(
            reproject_bbox(bbox_wgs84, crs_wgs84, crs_3035), bbox_3035
        )
        np.testing.assert_almost_equal(
            reproject_bbox(
                reproject_bbox(bbox_wgs84, crs_wgs84, crs_3035, buffer=0.0),
                crs_3035,
                crs_wgs84,
                buffer=0.0,
            ),
            [
                1.829619451017442,
                49.93464594063249,
                3.1462425554926226,
                51.06428203128216,
            ],
        )

        crs_utm = "EPSG:32601"
        bbox_utm = [
            213372.0489639729,
            5540547.369934658,
            362705.63410562894,
            5768595.563692021,
        ]
        np.testing.assert_almost_equal(
            reproject_bbox(bbox_utm, crs_utm, crs_wgs84, buffer=0.02),
            [178.77930769, 49.90632759, -178.87064939, 52.09298731],
        )

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

    def test_get_spatial_dims(self):
        ds = xr.Dataset()
        ds["var"] = xr.DataArray(
            data=np.ones((2, 2)), dims=("y", "x"), coords=dict(y=[0, 10], x=[0, 10])
        )
        self.assertEqual(("y", "x"), get_spatial_dims(ds))
        ds = xr.Dataset()
        ds["var"] = xr.DataArray(
            data=np.ones((2, 2)),
            dims=("lat", "lon"),
            coords=dict(lat=[0, 10], lon=[0, 10]),
        )
        self.assertEqual(("lat", "lon"), get_spatial_dims(ds))
        ds = xr.Dataset()
        ds["var"] = xr.DataArray(
            data=np.ones((2, 2)),
            dims=("dim_false0", "dim_false1"),
            coords=dict(dim_false0=[0, 10], dim_false1=[0, 10]),
        )
        with self.assertRaises(DataStoreError) as cm:
            get_spatial_dims(ds)
        self.assertEqual(
            "No spatial dimensions found in dataset.",
            f"{cm.exception}",
        )

    def test_get_gridmapping(self):
        bbox = [0, 50, 1, 51]
        spatial_res = 0.0001
        crs = "EPSG:4326"
        tile_size = 2000
        gm = get_gridmapping(bbox, spatial_res, crs, tile_size)
        self.assertIsInstance(gm, GridMapping)
        self.assertEqual((0.0001, 0.0001), gm.xy_res)
        self.assertEqual(pyproj.CRS.from_epsg(4326), gm.crs)
        self.assertEqual((2000, 2000), gm.tile_size)
        self.assertEqual((10001, 10001), gm.size)
