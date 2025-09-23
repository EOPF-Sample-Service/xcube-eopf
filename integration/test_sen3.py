#  Copyright (c) 2025 by EOPF Sample Service team and contributors
#  Permissions are hereby granted under the terms of the Apache 2.0 License:
#  https://opensource.org/license/apache-2-0.

from unittest import TestCase

import xarray as xr
from xcube.core.store import new_data_store

from xcube_eopf.utils import reproject_bbox

from .helper import timeit

allowed_open_time = 120  # seconds
show_chunking = False


class Sentinel3Test(TestCase):
    def setUp(self):
        self.store = new_data_store("eopf-zarr")
        self.bbox = [9.7, 53.4, 10.3, 53.7]
        self.crs = "EPSG:4326"
        self.crs_utm = "EPSG:32632"
        self.bbox_utm = reproject_bbox(self.bbox, self.crs, self.crs_utm)

    def test_open_data_sen3ol1efr(self):
        with timeit("open 'sentinel-3-olci-l1-efr'") as result:
            ds = self.store.open_data(
                data_id="sentinel-3-olci-l1-efr",
                bbox=self.bbox,
                time_range=["2025-05-01", "2025-05-07"],
                spatial_res=300 / 111320,
                crs=self.crs,
                variables=["oa01_radiance", "oa02_radiance"],
            )
        self.assertTrue(result.time_delta < allowed_open_time)
        self.assertIsInstance(ds, xr.Dataset)
        self.assertCountEqual(["oa01_radiance", "oa02_radiance"], list(ds.data_vars))
        self.assertCountEqual(
            [1, 113, 224], [ds.sizes["time"], ds.sizes["lat"], ds.sizes["lon"]]
        )
        self.assertEqual(
            [1, 113, 224],
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

    def test_open_data_sen3ol1efr_with_projection(self):
        with timeit("open 'sentinel-3-olci-l1-efr'") as result:
            ds = self.store.open_data(
                data_id="sentinel-3-olci-l1-efr",
                bbox=self.bbox_utm,
                time_range=["2025-05-01", "2025-05-07"],
                spatial_res=300,
                crs=self.crs_utm,
                variables=["oa01_radiance", "oa02_radiance"],
            )
        self.assertTrue(result.time_delta < allowed_open_time)
        self.assertIsInstance(ds, xr.Dataset)
        self.assertCountEqual(["oa01_radiance", "oa02_radiance"], list(ds.data_vars))
        self.assertCountEqual(
            [1, 115, 136], [ds.sizes["time"], ds.sizes["y"], ds.sizes["x"]]
        )
        self.assertEqual(
            [1, 115, 136],
            [ds.chunksizes["time"][0], ds.chunksizes["y"][0], ds.chunksizes["x"][0]],
        )
        self.assertIn("stac_url", ds.attrs)
        self.assertIn("stac_items", ds.attrs)
        self.assertIn("open_params", ds.attrs)
        self.assertIn("xcube_eopf_version", ds.attrs)

    # leave out due to wrong footprint in the STAC item
    # def test_open_data_ol1err(self):
    #     with timeit("open 'sentinel-3-olci-l1-err'") as result:
    #         ds = self.store.open_data(
    #             data_id="sentinel-3-olci-l1-err",
    #             bbox=self.bbox,
    #             time_range=["2025-05-01", "2025-05-07"],
    #             spatial_res=300 / 111320,
    #             crs=self.crs,
    #             variables=["oa01_radiance", "oa02_radiance"],
    #         )
    #     self.assertTrue(result.time_delta < allowed_open_time)
    #     self.assertIsInstance(ds, xr.Dataset)
    #     self.assertCountEqual(["oa01_radiance", "oa02_radiance"], list(ds.data_vars))
    #     self.assertCountEqual(
    #         [1, 113, 224], [ds.sizes["time"], ds.sizes["lat"], ds.sizes["lon"]]
    #     )
    #     self.assertEqual(
    #         [1, 113, 224],
    #         [
    #             ds.chunksizes["time"][0],
    #             ds.chunksizes["lat"][0],
    #             ds.chunksizes["lon"][0],
    #         ],
    #     )
    #     self.assertIn("stac_url", ds.attrs)
    #     self.assertIn("stac_items", ds.attrs)
    #     self.assertIn("open_params", ds.attrs)
    #     self.assertIn("xcube_eopf_version", ds.attrs)

    def test_open_data_ol2lfr(self):
        with timeit("open 'sentinel-3-olci-l2-lfr'") as result:
            ds = self.store.open_data(
                data_id="sentinel-3-olci-l2-lfr",
                bbox=self.bbox,
                time_range=["2025-05-01", "2025-05-07"],
                spatial_res=300 / 111320,  # meter in degree,
                crs="EPSG:4326",
                variables=["gifapar", "iwv"],
            )
        self.assertTrue(result.time_delta < allowed_open_time)
        self.assertIsInstance(ds, xr.Dataset)
        self.assertCountEqual(["gifapar", "iwv"], list(ds.data_vars))
        self.assertCountEqual(
            [1, 113, 224], [ds.sizes["time"], ds.sizes["lat"], ds.sizes["lon"]]
        )
        self.assertEqual(
            [1, 113, 224],
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

    def test_open_data_sl2lst(self):
        with timeit("open 'sentinel-3-slstr-l2-lst'") as result:
            ds = self.store.open_data(
                data_id="sentinel-3-slstr-l2-lst",
                bbox=self.bbox,
                time_range=["2025-05-01", "2025-05-07"],
                spatial_res=300 / 111320,  # meter in degree,
                crs="EPSG:4326",
            )
        self.assertTrue(result.time_delta < allowed_open_time)
        self.assertIsInstance(ds, xr.Dataset)
        self.assertCountEqual(["lst"], list(ds.data_vars))
        self.assertCountEqual(
            [1, 113, 224], [ds.sizes["time"], ds.sizes["lat"], ds.sizes["lon"]]
        )
        self.assertEqual(
            [1, 113, 224],
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
