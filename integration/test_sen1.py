#  Copyright (c) 2025-2026 by EOPF Sample Service team and contributors
#  Permissions are hereby granted under the terms of the Apache 2.0 License:
#  https://opensource.org/license/apache-2-0.

import datetime
from unittest import TestCase
from unittest.mock import patch

import numpy as np
import pystac
import xarray as xr
from xcube.core.store import new_data_store


class _FakeSearch:
    def __init__(self, items):
        self._items = items

    def items(self):
        return iter(self._items)


class _FakeCatalog:
    def __init__(self, items):
        self._items = items
        self.last_search_kwargs = None

    def search(self, **kwargs):
        self.last_search_kwargs = kwargs
        return _FakeSearch(self._items)


def _make_item(
    item_id: str,
    dt: datetime.datetime,
    orbit_state: str,
    relative_orbit: int,
    platform: str,
    href: str,
    bbox: list[float] | None = None,
) -> pystac.Item:
    return pystac.Item(
        id=item_id,
        geometry=None,
        bbox=bbox or [0.0, 0.0, 1.0, 1.0],
        datetime=dt,
        properties={
            "sat:orbit_state": orbit_state,
            "sat:relative_orbit": relative_orbit,
            "platform": platform,
        },
        assets={"product": pystac.Asset(href)},
    )


def _make_xy_dataset(data_var: str = "gamma0_vv") -> xr.Dataset:
    return xr.Dataset(
        {data_var: (("y", "x"), np.arange(6, dtype=np.float32).reshape(2, 3))},
        coords={
            "x": ("x", np.arange(3, dtype=np.float32)),
            "y": ("y", np.arange(2, dtype=np.float32)),
        },
    ).chunk({"y": 1, "x": 3})


def _make_latlon_dataset() -> xr.Dataset:
    base = np.arange(6, dtype=np.float32).reshape(2, 3)
    return xr.Dataset(
        {
            "wind_speed": (("lat", "lon"), base),
            "wind_direction": (("lat", "lon"), base + 100.0),
        },
        coords={
            "lon": ("lon", np.linspace(0.0, 2.0, 3, dtype=np.float32)),
            "lat": ("lat", np.linspace(2.0, 0.0, 2, dtype=np.float32)),
        },
    ).chunk({"lat": 1, "lon": 3})


def _make_dem() -> xr.DataArray:
    return xr.DataArray(
        np.zeros((2, 3), dtype=np.float32),
        dims=("y", "x"),
        coords={
            "x": ("x", np.arange(3, dtype=np.float32)),
            "y": ("y", np.arange(2, dtype=np.float32)),
        },
    )


class Sentinel1IntegrationTest(TestCase):
    def setUp(self):
        self.store = new_data_store("eopf-zarr")

    def _open_with_fake_catalog(
        self, data_id, items, open_dataset_path, side_effect, **open_params
    ):
        catalog = _FakeCatalog(items)
        with (
            patch("pystac_client.Client.open", return_value=catalog),
            patch(open_dataset_path, side_effect=side_effect),
        ):
            ds = self.store.open_data(data_id=data_id, **open_params)
        return ds, catalog

    def test_open_data_sen1_l1_grd(self):
        items = [
            _make_item(
                "grd-0",
                datetime.datetime(2026, 5, 15, 10, 0),
                "descending",
                12,
                "S1A",
                "file://missing",
            ),
            _make_item(
                "grd-1",
                datetime.datetime(2026, 5, 15, 10, 10),
                "descending",
                12,
                "S1A",
                "file://good-0",
            ),
            _make_item(
                "grd-2",
                datetime.datetime(2026, 5, 16, 10, 0),
                "ascending",
                13,
                "S1B",
                "file://good-1",
            ),
        ]
        with patch("xcube_eopf.prodhandlers.sentinel1.get_dem") as mock_get_dem:
            mock_get_dem.return_value = xr.DataArray(
                np.zeros((2, 3), dtype=np.float32), dims=("y", "x")
            )
            ds, catalog = self._open_with_fake_catalog(
                "sentinel-1-l1-grd",
                items,
                "xcube_eopf.prodhandlers.sentinel1.xr.open_dataset",
                [FileNotFoundError("missing"), _make_xy_dataset(), _make_xy_dataset()],
                bbox=[5.3, 43.1, 5.7, 43.4],
                time_range=["2026-05-15", "2026-05-16"],
                spatial_res=10,
                crs="EPSG:4326",
            )

        self.assertEqual(
            ["sentinel-1-l1-grd"], catalog.last_search_kwargs["collections"]
        )
        self.assertEqual(
            ["2026-05-15", "2026-05-16"], catalog.last_search_kwargs["datetime"]
        )
        self.assertIsInstance(ds, xr.Dataset)
        self.assertIn("gamma0_vv", ds.data_vars)
        self.assertEqual(2, ds.sizes["time"])
        self.assertEqual(2, ds.sizes["y"])
        self.assertEqual(3, ds.sizes["x"])
        self.assertIn("stac_url", ds.attrs)
        self.assertIn("stac_items", ds.attrs)
        self.assertIn("open_params", ds.attrs)
        self.assertIn("xcube_eopf_version", ds.attrs)

    def test_open_data_sen1_l1_slc(self):
        items = [
            _make_item(
                "slc-0",
                datetime.datetime(2026, 5, 16, 10, 0),
                "descending",
                12,
                "S1A",
                "file://good-0",
            ),
            _make_item(
                "slc-1",
                datetime.datetime(2026, 5, 16, 10, 10),
                "descending",
                12,
                "S1A",
                "file://good-1",
            ),
        ]
        with patch("xcube_eopf.prodhandlers.sentinel1.get_dem") as mock_get_dem:
            mock_get_dem.return_value = xr.DataArray(
                np.zeros((2, 3), dtype=np.float32), dims=("y", "x")
            )
            ds, _ = self._open_with_fake_catalog(
                "sentinel-1-l1-slc",
                items,
                "xcube_eopf.prodhandlers.sentinel1.xr.open_dataset",
                [_make_xy_dataset(), _make_xy_dataset()],
                bbox=[5.3, 43.1, 5.7, 43.4],
                time_range=["2026-05-16", "2026-05-16"],
                spatial_res=10,
                crs="EPSG:4326",
            )

        self.assertIsInstance(ds, xr.Dataset)
        self.assertIn("gamma0_vv", ds.data_vars)
        self.assertEqual(1, ds.sizes["time"])
        self.assertEqual(2, ds.sizes["y"])
        self.assertEqual(3, ds.sizes["x"])
        self.assertIn("stac_url", ds.attrs)
        self.assertIn("stac_items", ds.attrs)
        self.assertIn("open_params", ds.attrs)
        self.assertIn("xcube_eopf_version", ds.attrs)

    def test_open_data_sen1_l2_ocn(self):
        items = [
            _make_item(
                "ocn-0",
                datetime.datetime(2026, 5, 27, 8, 0),
                "ascending",
                12,
                "S1A",
                "file://good-0",
            ),
            _make_item(
                "ocn-1",
                datetime.datetime(2026, 5, 27, 9, 0),
                "ascending",
                13,
                "S1B",
                "file://good-1",
            ),
            _make_item(
                "ocn-2",
                datetime.datetime(2026, 5, 28, 8, 0),
                "descending",
                14,
                "S1A",
                "file://good-2",
            ),
        ]
        ds, _ = self._open_with_fake_catalog(
            "sentinel-1-l2-ocn",
            items,
            "xcube_eopf.prodhandlers.sentinel3.xr.open_dataset",
            [_make_latlon_dataset(), _make_latlon_dataset(), _make_latlon_dataset()],
            bbox=[0.0, 38.0, 5.0, 43.0],
            time_range=["2026-05-27", "2026-05-31"],
            spatial_res=1000 / 111320,
            crs="EPSG:4326",
        )

        self.assertIsInstance(ds, xr.Dataset)
        self.assertIn("wind_speed", ds.data_vars)
        self.assertIn("wind_direction", ds.data_vars)
        self.assertEqual(2, ds.sizes["time"])
        self.assertEqual(2, ds.sizes["lat"])
        self.assertEqual(3, ds.sizes["lon"])
        self.assertIn("stac_url", ds.attrs)
        self.assertIn("stac_items", ds.attrs)
        self.assertIn("open_params", ds.attrs)
        self.assertIn("xcube_eopf_version", ds.attrs)
