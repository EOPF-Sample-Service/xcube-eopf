#  Copyright (c) 2025 by EOPF Sample Service team and contributors
#  Permissions are hereby granted under the terms of the Apache 2.0 License:
#  https://opensource.org/license/apache-2-0.

import logging
import re
import warnings
from abc import ABC
from collections import defaultdict

import numpy as np
import pystac
import xarray as xr
from xcube.util.jsonschema import JsonObjectSchema
from xcube_resampling.utils import reproject_bbox

from xcube_eopf.constants import (
    DEFAULT_CRS,
    LOG,
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
    bbox_to_geojson,
    mosaic_spatial_take_first,
)

_TILE_SIZE = 1024  # native chunk size of EOPF Sen3 Zarr samples


class IgnoreZeroSizedDimension(logging.Filter):
    def filter(self, record):
        # Return False to ignore this log record
        if "Clipped dataset contains at least one zero-sized" in record.getMessage():
            return False
        return True


logger = logging.getLogger("xcube.resampling")
logger.addFilter(IgnoreZeroSizedDimension())


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
            required=["time_range", "bbox", "spatial_res"],
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

    def open_data(self, items: list[pystac.Item], **open_params) -> xr.Dataset:
        if "crs" not in open_params:
            open_params["crs"] = DEFAULT_CRS

        # get STAC items grouped by solar day
        grouped_items = group_items(items)

        # generate cube by mosaicking and stacking tiles
        ds = self.generate_cube(grouped_items, **open_params)

        # add attributes
        ds = add_attributes(ds, grouped_items, **open_params)

        return ds

    def generate_cube(self, grouped_items: xr.DataArray, **open_params) -> xr.Dataset:
        warnings.filterwarnings(
            "ignore", message="Clipping with the specified bounding box*"
        )
        xarray_open_params = dict(
            resolution=open_params["spatial_res"],
            crs=open_params["crs"],
            bbox=open_params["bbox"],
            interp_methods=open_params.get("interp_methods"),
            agg_methods=open_params.get("agg_methods"),
            variables=open_params.get("variables"),
        )
        dss_time = []
        for dt_idx, dt in enumerate(grouped_items.time.values):
            items = grouped_items.sel(time=dt).item()
            dss_spatial = []
            for item in items:
                ds = xr.open_dataset(
                    item.assets["product"].href,
                    engine="eopf-zarr",
                    chunks={},
                    **xarray_open_params,
                )
                if any(size <= 1 for size in ds.sizes.values()):
                    continue
                dss_spatial.append(ds)
            dss_time.append(mosaic_spatial_take_first(dss_spatial))
        ds_final = xr.concat(dss_time, dim="time", join="exact")
        ds_final = ds_final.assign_coords(dict(time=grouped_items.time))
        return ds_final


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


class Sen3Sl1RbtProductHandler(Sen3ProductHandler):
    data_id = "sentinel-3-slstr-l1-rbt"


class Sen3Sl2LstProductHandler(Sen3ProductHandler):
    data_id = "sentinel-3-slstr-l2-lst"


def register(registry: ProductHandlerRegistry):
    registry.register(Sen3Ol1EfrProductHandler)
    # registry.register(Sen3Ol1ErrProductHandler)
    registry.register(Sen3Ol2LfrProductHandler)
    # registry.register(Sen3Ol2LrrProductHandler)
    registry.register(Sen3Sl1RbtProductHandler)
    registry.register(Sen3Sl2LstProductHandler)


def group_items(items: list[pystac.Item]) -> xr.DataArray:
    items = _filter_acquisition_time(items)
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


def _filter_acquisition_time(items: list[pystac.Item]) -> list[pystac.Item]:
    """Deduplicate Sentinel-3 items by acquisition, keeping NT if available, else NR.

    Args:
        items: List of Sentinel-3 STAC Items.

    Returns:
        Filtered list with one item per acquisition, preferring NT over NR.
    """
    groups = defaultdict(list)

    # Group items by base ID (sensing start/end)
    for item in items:
        base_id = _get_base_id(item.id)
        groups[base_id].append(item)

    result = []
    for base, grouped_items in groups.items():
        # Prefer NT if exists
        nt_items = [i for i in grouped_items if "_NT_" in i.id]
        if nt_items:
            # If multiple NTs, pick latest processing timestamp
            latest_nt = max(nt_items, key=lambda x: _extract_timestamps(x.id)[-1])
            result.append(latest_nt)
        else:
            # Otherwise pick NR (if exists)
            nr_items = [i for i in grouped_items if "_NR_" in i.id]
            if nr_items:
                latest_nr = max(nr_items, key=lambda x: _extract_timestamps(x.id)[-1])
                result.append(latest_nr)

    return result


def _get_base_id(item_id: str) -> str:
    # Matches YYYYMMDDThhmmss
    timestamps = _extract_timestamps(item_id)

    # Fallback if unexpected format
    if len(timestamps) < 3:
        LOG.warning(
            f"Item ID {item_id!r} does not contain 3 timestamp. "
            f"No filtering applied for this item."
        )
        return item_id

    # Remove only the final timestamp
    last_ts = timestamps[-1]
    base, _, _ = item_id.rpartition(f"_{last_ts}")
    return base


def _extract_timestamps(item_id: str) -> list[str]:
    # Matches YYYYMMDDThhmmss
    return re.findall(r"\d{8}T\d{6}", item_id)
