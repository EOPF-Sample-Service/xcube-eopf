#  Copyright (c) 2025 by EOPF Sample Service team and contributors
#  Permissions are hereby granted under the terms of the Apache 2.0 License:
#  https://opensource.org/license/apache-2-0.

from abc import ABC

import numpy as np
import pystac
import xarray as xr
from xcube.util.jsonschema import JsonObjectSchema
from xcube_resampling import rectify_dataset

from xcube_eopf.constants import (
    SCHEMA_ADDITIONAL_QUERY,
    SCHEMA_AGG_METHODS,
    SCHEMA_BBOX,
    SCHEMA_CRS,
    SCHEMA_INTERP_METHODS,
    SCHEMA_SPATIAL_RES,
    SCHEMA_TILE_SIZE,
    SCHEMA_TIME_RANGE,
    SCHEMA_VARIABLES,
)
from xcube_eopf.prodhandler import ProductHandler, ProductHandlerRegistry
from xcube_eopf.utils import (
    add_attributes,
    add_nominal_datetime,
    get_gridmapping,
    mosaic_spatial_take_first,
)

_TILE_SIZE = 1024  # native chunk size of EOPF Sen3 Zarr samples


class Sen3ProductHandler(ProductHandler, ABC):
    """General Sentinel-3 product handles, defining methods applicable
    for Ol1Err, Ol1Efr, Ol2Lfr, and Sl2Lst product.
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
                agg_methods=SCHEMA_AGG_METHODS,
                interp_methods=SCHEMA_INTERP_METHODS,
            ),
            required=["time_range", "bbox", "crs", "spatial_res"],
            additional_properties=False,
        )

    def open_data(self, items: list[pystac.Item], **open_params) -> xr.Dataset:
        # get STAC items grouped by solar day
        grouped_items = group_items(items)

        # generate cube by mosaicking and stacking tiles
        ds = generate_cube(grouped_items, **open_params)

        # add attributes
        ds = add_attributes(ds, grouped_items, **open_params)

        return ds


class Sen3Ol1EfrProductHandler(Sen3ProductHandler):
    data_id = "sentinel-3-olci-l1-efr"


# this will be added later, when the footprints are corrected. Note, this
# product spanns over half of the globe, and thus crosses the antimeridian in many
# datasets, resulting in a lot of falsely assigned STAC item's bbox and geometry.
# class Sen3Ol1ErrProductHandler(Sen3ProductHandler):
#     data_id = "sentinel-3-olci-l1-err"


class Sen3Ol2LfrProductHandler(Sen3ProductHandler):
    data_id = "sentinel-3-olci-l2-lfr"


# Broken data in: https://stac.browser.user.eopf.eodc.eu/collections/sentinel-3-olci-l2-lrr?.language=en
# class Sen3Ol2LrrProductHandler(Sen3ProductHandler):
#     data_id = "sentinel-3-olci-l2-lrr"


# complex data tree groups, implementation postponed;
# class Sen3Sl1RbtProductHandler(Sen3ProductHandler):
#     data_id = "sentinel-3-slstr-l1-rbt"


class Sen3Sl2LstProductHandler(Sen3ProductHandler):
    data_id = "sentinel-3-slstr-l2-lst"


def register(registry: ProductHandlerRegistry):
    registry.register(Sen3Ol1EfrProductHandler)
    # registry.register(Sen3Ol1ErrProductHandler)
    registry.register(Sen3Ol2LfrProductHandler)
    # registry.register(Sen3Ol2LrrProductHandler)
    # registry.register(Sen3Sl1RbtProductHandler)
    registry.register(Sen3Sl2LstProductHandler)


def group_items(items: list[pystac.Item]) -> xr.DataArray:
    items = add_nominal_datetime(items)

    # get dates and tile IDs of the items
    dates = []
    for item in items:
        dates.append(item.properties["datetime_nominal"].date())
    dates = np.unique(dates)

    # sort items by date and tile ID into a data array
    grouped_items = np.full(len(dates), None, dtype=object)
    for idx, item in enumerate(items):
        date = item.properties["datetime_nominal"].date()
        idx_date = np.where(dates == date)[0][0]
        if grouped_items[idx_date] is None:
            grouped_items[idx_date] = [item]
        else:
            grouped_items[idx_date].append(item)

    grouped_items = xr.DataArray(grouped_items, dims=("time",), coords=dict(time=dates))

    # replace date by datetime from first item
    dts = []
    for date in grouped_items.time.values:
        item = np.sum(grouped_items.sel(time=date).values)[0]
        dts.append(item.datetime.replace(tzinfo=None))
    grouped_items = grouped_items.assign_coords(
        time=np.array(dts, dtype="datetime64[ns]")
    )
    grouped_items["time"].encoding["units"] = "seconds since 1970-01-01"
    grouped_items["time"].encoding["calendar"] = "standard"

    return grouped_items


def generate_cube(grouped_items: xr.DataArray, **open_params) -> xr.Dataset:
    target_gm = get_gridmapping(
        open_params["bbox"],
        open_params["spatial_res"],
        open_params["crs"],
        open_params.get("tile_size", _TILE_SIZE),
    )
    dss_time = []
    for dt_idx, dt in enumerate(grouped_items.time.values):
        items = grouped_items.sel(time=dt).item()
        dss_spatial = []
        for item in items:
            ds = xr.open_dataset(
                item.assets["product"].href + "/measurements",
                engine="eopf-zarr",
                chunks={},
                **dict(op_mode="native"),
            )
            variables = open_params.get("variables")
            if variables is not None:
                ds = ds[variables]
            if "time_stamp" in ds.coords:
                ds = ds.drop_vars("time_stamp")
            ds["latitude"] = ds["latitude"].persist()
            ds["longitude"] = ds["longitude"].persist()
            ds = rectify_dataset(
                ds,
                target_gm=target_gm,
                interp_methods=open_params.get("interp_methods"),
                agg_methods=open_params.get("agg_methods"),
            )
            dss_spatial.append(ds)
        dss_time.append(mosaic_spatial_take_first(dss_spatial))
    ds_final = xr.concat(dss_time, dim="time", join="exact")
    ds_final = ds_final.assign_coords(dict(time=grouped_items.time))
    return ds_final
