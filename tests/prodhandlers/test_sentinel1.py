#  Copyright (c) 2025-2026 by EOPF Sample Service team and contributors
#  Permissions are hereby granted under the terms of the Apache 2.0 License:
#  https://opensource.org/license/apache-2-0.

import datetime
from unittest import TestCase
from unittest.mock import patch

import numpy as np
import pyproj
import pystac
import xarray as xr
from xcube.util.jsonschema import JsonObjectSchema

from tests.helpers.sentinel1 import sen1_grd_slc_analysis_dataset
from xcube_eopf.prodhandler import ProductHandlerRegistry
from xcube_eopf.prodhandlers.sentinel1 import (
    Sen1Level1GRDProductHandler,
    Sen1Level1SLCProductHandler,
    Sen1Level2OCNProductHandler,
    register,
)


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


class Sentinel1Level1ProductHandlerTest(TestCase):
    def setUp(self):
        self.handler = Sen1Level1GRDProductHandler()

    def test_get_open_data_params_schema(self):
        schema = self.handler.get_open_data_params_schema()
        self.assertIsInstance(schema, JsonObjectSchema)
        self.assertEqual("Opening parameters for Sentinel-1 products.", schema.title)
        self.assertCountEqual(
            [
                "variables",
                "spatial_res",
                "time_range",
                "bbox",
                "crs",
                "tile_size",
                "query",
                "interp_methods",
                "dem",
                "apply_rtc",
                "footprint_scale_factor",
            ],
            list(schema.properties),
        )
        self.assertCountEqual(["time_range", "bbox"], schema.required)
        self.assertFalse(schema.additional_properties)

    def test_prepare_stac_queries(self):
        open_params = {
            "bbox": [610000, 5880000, 630000, 5900000],
            "time_range": ["2026-03-18", "2026-03-25"],
            "crs": "EPSG:32632",
            "query": {"sat:orbit_state": {"eq": "descending"}},
        }
        with (
            patch("xcube_eopf.prodhandlers.sentinel1.reproject_bbox") as mock_reproject,
            patch("xcube_eopf.prodhandlers.sentinel1.bbox_to_geojson") as mock_geojson,
        ):
            mock_reproject.return_value = [9.0, 53.0, 10.0, 54.0]
            mock_geojson.return_value = {"type": "Polygon"}
            query = self.handler.prepare_stac_queries("sentinel-1-l1-grd", open_params)

        mock_reproject.assert_called_once_with(
            open_params["bbox"], open_params["crs"], "EPSG:4326"
        )
        mock_geojson.assert_called_once_with([9.0, 53.0, 10.0, 54.0])
        self.assertEqual(
            {
                "collections": ["sentinel-1-l1-grd"],
                "datetime": ["2026-03-18", "2026-03-25"],
                "intersects": {"type": "Polygon"},
                "query": open_params["query"],
            },
            query,
        )

    def test_open_data_normalizes_crs_and_delegates(self):
        grouped_items_array = np.empty(1, dtype=object)
        grouped_items_array[0] = []
        grouped_items = xr.DataArray(
            grouped_items_array,
            dims=("time",),
            coords={"time": [np.datetime64("2026-03-18T10:00:00")]},
        )
        ds = xr.Dataset({"gamma0_vv": (("y", "x"), np.ones((1, 1), dtype=np.float32))})

        with (
            patch.object(self.handler, "group_items", return_value=grouped_items),
            patch.object(
                self.handler, "generate_cube", return_value=ds
            ) as mock_generate,
            patch(
                "xcube_eopf.prodhandlers.sentinel1.add_attributes", return_value=ds
            ) as mock_add_attributes,
        ):
            result = self.handler.open_data(
                "sentinel-1-l1-grd",
                [],
                bbox=[0.0, 0.0, 1.0, 1.0],
                time_range=["2026-03-18", "2026-03-25"],
                crs="EPSG:32632",
            )

        self.assertIs(result, ds)
        self.assertIsInstance(mock_generate.call_args.kwargs["crs"], pyproj.CRS)
        self.assertEqual(
            pyproj.CRS.from_string("EPSG:32632"), mock_generate.call_args.kwargs["crs"]
        )
        mock_add_attributes.assert_called_once()

    def test_generate_cube_skips_missing_and_zero_sized_datasets(self):
        dt0 = datetime.datetime(2026, 3, 18, 10, 0, 0)
        dt1 = datetime.datetime(2026, 3, 19, 10, 0, 0)
        items = [
            _make_item("item-0", dt0, "descending", 12, "S1A", "file://missing-0"),
            _make_item("item-1", dt0, "descending", 12, "S1A", "file://good-0"),
            _make_item("item-2", dt1, "ascending", 13, "S1B", "file://small-0"),
            _make_item("item-3", dt1, "ascending", 13, "S1B", "file://good-1"),
        ]
        grouped_items = Sen1Level1GRDProductHandler.group_items(items)
        ds_good_0 = sen1_grd_slc_analysis_dataset()
        ds_good_1 = sen1_grd_slc_analysis_dataset()
        ds_small = sen1_grd_slc_analysis_dataset(shape=(1, 2), chunks=(1, 2))

        def _mosaic(datasets):
            self.assertGreaterEqual(len(datasets), 1)
            return datasets[0]

        with (
            patch("xcube_eopf.prodhandlers.sentinel1.get_dem") as mock_get_dem,
            patch(
                "xcube_eopf.prodhandlers.sentinel1.xr.open_dataset"
            ) as mock_open_dataset,
            patch(
                "xcube_eopf.prodhandlers.sentinel1.mosaic_spatial_take_first",
                side_effect=_mosaic,
            ) as mock_mosaic,
        ):
            mock_get_dem.return_value = xr.Dataset()
            mock_open_dataset.side_effect = [
                FileNotFoundError("missing"),
                ds_good_0,
                ds_small,
                ds_good_1,
            ]
            ds = self.handler.generate_cube(
                grouped_items,
                bbox=[0.0, 0.0, 1.0, 1.0],
                spatial_res=10,
                crs=pyproj.CRS.from_string("EPSG:32632"),
                variables=["gamma0_vv"],
            )

        mock_get_dem.assert_called_once_with(
            [0.0, 0.0, 1.0, 1.0],
            resolution=10,
            crs=pyproj.CRS.from_string("EPSG:32632"),
        )
        self.assertEqual(4, mock_open_dataset.call_count)
        self.assertEqual(2, mock_mosaic.call_count)
        self.assertIsInstance(ds, xr.Dataset)
        self.assertEqual(2, ds.sizes["time"])
        self.assertEqual(2, ds.sizes["y"])
        self.assertEqual(3, ds.sizes["x"])
        self.assertTrue(np.array_equal(ds.time.values, grouped_items.time.values))


class Sentinel1Level2OCNProductHandlerTest(TestCase):
    def setUp(self):
        self.handler = Sen1Level2OCNProductHandler()

    def test_group_items(self):
        dt0 = datetime.datetime(2026, 5, 27, 8, 0, 0)
        dt1 = datetime.datetime(2026, 5, 27, 9, 0, 0)
        dt2 = datetime.datetime(2026, 5, 28, 8, 0, 0)
        items = [
            _make_item("item-0", dt0, "ascending", 12, "S1A", "file://good-0"),
            _make_item("item-1", dt1, "ascending", 13, "S1B", "file://good-1"),
            _make_item("item-2", dt2, "descending", 14, "S1A", "file://good-2"),
        ]

        grouped_items = self.handler.group_items(items)

        self.assertIsInstance(grouped_items, xr.DataArray)
        self.assertEqual(dict(time=2), grouped_items.sizes)
        self.assertCountEqual(
            ["item-0", "item-1"], [item.id for item in grouped_items[0].item()]
        )
        self.assertEqual(["item-2"], [item.id for item in grouped_items[1].item()])
        self.assertEqual(
            "seconds since 1970-01-01", grouped_items.time.encoding["units"]
        )
        self.assertEqual("standard", grouped_items.time.encoding["calendar"])


class Sentinel1RegisterTest(TestCase):
    def test_register(self):
        registry = ProductHandlerRegistry()
        register(registry)
        self.assertIsInstance(
            registry.get("sentinel-1-l1-grd"), Sen1Level1GRDProductHandler
        )
        self.assertIsInstance(
            registry.get("sentinel-1-l1-slc"), Sen1Level1SLCProductHandler
        )
        self.assertIsInstance(
            registry.get("sentinel-1-l2-ocn"), Sen1Level2OCNProductHandler
        )
