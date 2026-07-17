#  Copyright (c) 2025-2026 by EOPF Sample Service team and contributors
#  Permissions are hereby granted under the terms of the Apache 2.0 License:
#  https://opensource.org/license/apache-2-0.

from abc import ABC
from collections import defaultdict

import numpy as np
import pystac
import xarray as xr
from xcube.util.jsonschema import JsonObjectSchema
from xcube_resampling.utils import reproject_bbox
from xarray_eopf.amodes.sentinel1 import get_dem

from xcube_eopf.constants import (
    DEFAULT_CRS,
    SCHEMA_ADDITIONAL_QUERY,
    LOG,
    SCHEMA_DEM,
    SCHEMA_FOOTPRINT_SCALE_FACTOR,
    SCHEMA_SPATIAL_RES,
    SCHEMA_BBOX,
    SCHEMA_CRS,
    SCHEMA_INTERP_METHODS,
    SCHEMA_APPLY_RTC,
    SCHEMA_TILE_SIZE,
    SCHEMA_TIME_RANGE,
    SCHEMA_VARIABLES,
)
from xcube_eopf.prodhandler import ProductHandler, ProductHandlerRegistry
from .sentinel3 import Sen3ProductHandler
from xcube_eopf.utils import (
    add_attributes,
    add_nominal_datetime,
    mosaic_spatial_take_first,
    bbox_to_geojson,
)


class Sen1Level1ProductHandler(ProductHandler, ABC):
    """General Sentinel-1 Level 1 product handles, defining methods applicable
    for GRD and SLC product.
    """

    def get_open_data_params_schema(self) -> JsonObjectSchema:
        return JsonObjectSchema(
            title="Opening parameters for Sentinel-2 products.",
            properties=dict(
                variables=SCHEMA_VARIABLES,
                spatial_res=SCHEMA_SPATIAL_RES,
                time_range=SCHEMA_TIME_RANGE,
                bbox=SCHEMA_BBOX,
                crs=SCHEMA_CRS,
                tile_size=SCHEMA_TILE_SIZE,
                query=SCHEMA_ADDITIONAL_QUERY,
                interp_methods=SCHEMA_INTERP_METHODS,
                dem=SCHEMA_DEM,
                apply_rtc=SCHEMA_APPLY_RTC,
                footprint_scale_factor=SCHEMA_FOOTPRINT_SCALE_FACTOR,
            ),
            required=["time_range", "bbox"],
            additional_properties=False,
        )

    def prepare_stac_queries(self, data_id: str, open_params: dict) -> dict:
        target_crs = open_params.get("crs", DEFAULT_CRS)
        bbox_wgs84 = reproject_bbox(open_params["bbox"], target_crs, "EPSG:4326")
        return dict(
            collections=[data_id],
            datetime=open_params["time_range"],
            intersects=bbox_to_geojson(bbox_wgs84),
            query=open_params.get("query"),
        )

    def open_data(
        self, data_id: str, items: list[pystac.Item], **open_params
    ) -> xr.Dataset:
        if "crs" not in open_params:
            open_params["crs"] = DEFAULT_CRS

        # get STAC items grouped by solar day
        grouped_items = group_items(items)

        # generate cube by mosaicking and stacking tiles
        ds = self.generate_cube(grouped_items, **open_params)

        # add attributes
        ds = add_attributes(data_id, ds, grouped_items, **open_params)

        return ds

    def generate_cube(self, grouped_items: xr.DataArray, **open_params) -> xr.Dataset:
        resolution = open_params.get("spatial_res")
        crs = open_params.get("spatial_res")
        dem = open_params.get("dem")
        if dem is None:
            dem = get_dem(open_params["bbox"], resolution=resolution, crs=crs)
        xarray_open_params = dict(
            dem=dem,
            apply_rtc=open_params.get("apply_rtc"),
            interp_methods=open_params.get("interp_methods"),
            footprint_scale_factor=open_params.get("footprint_scale_factor"),
            variables=open_params.get("variables"),
        )
        dss_time = []
        for dt_idx, dt in enumerate(grouped_items.time.values):
            items = grouped_items.sel(time=dt).item()
            dss_spatial = []
            for item in items:
                try:
                    ds = xr.open_dataset(
                        item.assets["product"].href,
                        engine="eopf-zarr",
                        chunks={},
                        **xarray_open_params,
                    )
                except FileNotFoundError:
                    LOG.warning(
                        "File not found for STAC item %s (href=%s)",
                        item.id,
                        item.assets["product"].href,
                    )
                    continue
                if any(size <= 1 for size in ds.sizes.values()):
                    continue
                dss_spatial.append(ds)
            dss_time.append(mosaic_spatial_take_first(dss_spatial))
        ds_final = xr.concat(dss_time, dim="time", join="exact")
        ds_final = ds_final.assign_coords(dict(time=grouped_items.time))
        return ds_final


class Sen1Level1GRDProductHandler(Sen1Level1ProductHandler):
    data_id = "sentinel-1-l1-grd"


class Sen1Level1SLCProductHandler(Sen1Level1ProductHandler):
    data_id = "sentinel-1-l1-slc"


class Sen1Level2OCNProductHandler(Sen3ProductHandler):
    data_id = "sentinel-1-l2-ocn"
    default_resolution = 1000  # meter


def register(registry: ProductHandlerRegistry):
    registry.register(Sen1Level1GRDProductHandler)
    registry.register(Sen1Level1SLCProductHandler)
    registry.register(Sen1Level2OCNProductHandler)


def group_items(items: list[pystac.Item]) -> xr.DataArray:
    items = add_nominal_datetime(items)

    # get dates and tile IDs of the items
    groups = defaultdict(list)
    for item in items:
        date = item.properties["datetime_nominal"].date()
        orbit = item.properties["sat:orbit_state"]
        key = (date, orbit)
        groups[key].append(item)

    # Sort keys chronologically and descending before ascending
    orbit_order = {"descending": 0, "ascending": 1}
    sorted_keys = sorted(groups.keys(), key=lambda k: (k[0], orbit_order[k[1]]))

    grouped_items = np.empty(len(sorted_keys), dtype=object)
    for i, k in enumerate(sorted_keys):
        grouped_items[i] = groups[k]

    # Mean timestamp per group
    dts = np.empty(len(grouped_items), dtype="datetime64[s]")
    for i, items in enumerate(grouped_items):
        times = np.array(
            [np.datetime64(item.datetime.replace(tzinfo=None)) for item in items]
        )
        mean_time = np.datetime64(int(times.view("int64").mean()), "us")
        dts[i] = mean_time.astype("datetime64[s]")

    da = xr.DataArray(grouped_items, dims=("time",), coords=dict(time=dts))
    da["time"].encoding["units"] = "seconds since 1970-01-01"
    da["time"].encoding["calendar"] = "standard"

    return da
