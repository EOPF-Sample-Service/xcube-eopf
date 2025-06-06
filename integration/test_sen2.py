#  Copyright (c) 2025 by EOPF Sample Service team and contributors
#  Permissions are hereby granted under the terms of the Apache 2.0 License:
#  https://opensource.org/license/apache-2-0.

from unittest import TestCase
import time

import xarray as xr
from xcube.core.store import new_data_store

from xcube_eopf.utils import reproject_bbox


allowed_open_time = 30  # seconds
show_chunking = False


class timeit:
    """A context manager used to measure time it takes
    to execute its with-block.
    The result is available as `time_delta` attribute.

    Args:
        label: A text label
        silent: Whether to suppress printing the result
    """

    def __init__(self, label: str | None = None, silent: bool = False):
        self.label = label
        self.silent = silent
        self.start_time: float | None = None
        self.time_delta: float | None = None

    def __enter__(self) -> "timeit":
        self.start_time = time.process_time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.time_delta = time.process_time() - self.start_time
        if not self.silent:
            print(f"{self.label or 'code block'} took {self.time_delta:.3f} seconds")


class Sentinel2Test(TestCase):
    def setUp(self):
        self.store = new_data_store("eopf-zarr")
        self.bbox = [9.7, 53.4, 10.3, 53.7]
        self.crs_utm = "EPSG:32632"
        self.bbox_utm = reproject_bbox(self.bbox, "EPSG:4326", self.crs_utm)

    def test_open_data_sen2l1c(self):
        with timeit("open 'sentinel-2-l1c'") as result:
            ds = self.store.open_data(
                data_id="sentinel-2-l1c",
                bbox=self.bbox_utm,
                time_range=["2025-05-01", "2025-05-07"],
                spatial_res=10,
                crs=self.crs_utm,
                variables=["b02", "b03", "b04"],
            )
        self.assertTrue(result.time_delta < allowed_open_time)
        self.assertIsInstance(ds, xr.Dataset)
        self.assertCountEqual(["b02", "b03", "b04"], list(ds.data_vars))
        self.assertCountEqual(
            [3, 3394, 4023], [ds.sizes["time"], ds.sizes["y"], ds.sizes["x"]]
        )
        self.assertEqual(
            [1, 1830, 1830],
            [ds.chunksizes["time"][0], ds.chunksizes["y"][0], ds.chunksizes["x"][0]],
        )
        self.assertIn("stac_url", ds.attrs)
        self.assertIn("stac_items", ds.attrs)
        self.assertIn("open_params", ds.attrs)
        self.assertIn("xcube_eopf_version", ds.attrs)

    def test_open_data_sen2l2a(self):
        with timeit("open 'sentinel-2-l2a'") as result:
            ds = self.store.open_data(
                data_id="sentinel-2-l2a",
                bbox=self.bbox_utm,
                time_range=["2025-05-01", "2025-05-07"],
                spatial_res=10,
                crs=self.crs_utm,
                variables=["b02", "b03", "b04", "scl"],
            )
        self.assertTrue(result.time_delta < allowed_open_time)
        self.assertIsInstance(ds, xr.Dataset)
        self.assertCountEqual(["b02", "b03", "b04", "scl"], list(ds.data_vars))
        self.assertCountEqual(
            [3, 3394, 4023], [ds.sizes["time"], ds.sizes["y"], ds.sizes["x"]]
        )
        self.assertEqual(
            [1, 1830, 1830],
            [ds.chunksizes["time"][0], ds.chunksizes["y"][0], ds.chunksizes["x"][0]],
        )
        self.assertIn("stac_url", ds.attrs)
        self.assertIn("stac_items", ds.attrs)
        self.assertIn("open_params", ds.attrs)
        self.assertIn("xcube_eopf_version", ds.attrs)

    def test_open_data_sen2l2a_with_reprojection(self):
        with timeit("open 'sentinel-2-l2a'") as result:
            ds = self.store.open_data(
                data_id="sentinel-2-l2a",
                bbox=self.bbox,
                time_range=["2025-05-01", "2025-05-07"],
                spatial_res=10 / 111320,  # meter in degree,
                crs="EPSG:4326",
                variables=["b02", "b03", "b04", "scl"],
            )
        self.assertTrue(result.time_delta < allowed_open_time)
        self.assertIsInstance(ds, xr.Dataset)
        self.assertCountEqual(["b02", "b03", "b04", "scl"], list(ds.data_vars))
        self.assertCountEqual(
            [3, 6681, 3341], [ds.sizes["time"], ds.sizes["lon"], ds.sizes["lat"]]
        )
        self.assertEqual(
            [1, 1830, 1830],
            [
                ds.chunksizes["time"][0],
                ds.chunksizes["lon"][0],
                ds.chunksizes["lat"][0],
            ],
        )
        self.assertIn("stac_url", ds.attrs)
        self.assertIn("stac_items", ds.attrs)
        self.assertIn("open_params", ds.attrs)
        self.assertIn("xcube_eopf_version", ds.attrs)
