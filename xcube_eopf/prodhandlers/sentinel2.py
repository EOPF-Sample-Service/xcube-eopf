#  Copyright (c) 2025 by EOPF Sample Service team and contributors
#  Permissions are hereby granted under the terms of the Apache 2.0 License:
#  https://opensource.org/license/apache-2-0.

from abc import ABC

from xcube.util.jsonschema import JsonObjectSchema
import xarray as xr
import pystac
import numpy as np

from xcube_eopf.prodhandler import ProductHandler, ProductHandlerRegistry
from xcube_eopf.constants import (
    SCHEMA_VARIABLES,
    SCHEMA_SPATIAL_RES,
    SCHEMA_TIME_RANGE,
    SCHEMA_BBOX,
    SCHEMA_CRS,
    SCHEMA_TILE_SIZE,
    SCHEMA_ADDITIONAL_QUERY,
    STAC_CATALOG,
)
from xcube_eopf.utils import reproject_bbox, add_nominal_datetime


class Sen2ProductHandler(ProductHandler, ABC):

    def get_open_data_params_schema(self) -> JsonObjectSchema:
        return JsonObjectSchema(
            properties=dict(
                variables=SCHEMA_VARIABLES,
                spatial_res=SCHEMA_SPATIAL_RES,
                time_range=SCHEMA_TIME_RANGE,
                bbox=SCHEMA_BBOX,
                crs=SCHEMA_CRS,
                tile_size=SCHEMA_TILE_SIZE,
                query=SCHEMA_ADDITIONAL_QUERY,
            ),
            required=["time_range", "bbox", "crs", "spatial_res"],
            additional_properties=False,
        )

    def open_data(self, **open_params) -> xr.Dataset:
        schema = self.get_open_data_params_schema()
        schema.validate_instance(open_params)

        # search for items
        bbox_wgs84 = reproject_bbox(
            open_params["bbox"], open_params["crs"], "EPSG:4326"
        )
        search_params = dict(
            collections=[self.data_id],
            datetime=open_params["time_range"],
            bbox=bbox_wgs84,
            query=open_params.get("query"),
        )
        items = list(STAC_CATALOG.search(**search_params).items())

        # get STAC items grouped by solar day


class Sen2L1CProductHandler(Sen2ProductHandler):
    data_id = "sentinel-2-l1c"


class Sen2L2AProductHandler(Sen2ProductHandler):
    data_id = "sentinel-2-l2a"


def register(registry: ProductHandlerRegistry):
    registry.register(Sen2L1CProductHandler)
    registry.register(Sen2L2AProductHandler)


def groupby_solar_day(items: list[pystac.Item]) -> xr.DataArray:
    """Group STAC items by solar day, tile ID, and processing version.

    This method organizes a list of Sentinel-2 STAC items into an `xarray.DataArray`
    with dimensions `(time, tile_id, idx)`, where:
    - `time` corresponds to the solar acquisition date (ignoring time of day),
    - `tile_id` is the Sentinel-2 MGRS tile code,
    - `idx` accounts for up to two acquisitions per tile (e.g., due to multiple
      observations for the same tile),
    - The most recent processing version is selected if multiple exist.

    Args:
        items: List of STAC items to group. Each item must have:
            - `properties["datetime_nominal"]`: Nominal acquisition datetime.
            - `properties["grid:code"]`: Tile ID (MGRS grid).
            - A processing version recognizable by `_get_processing_version`.

    Returns:
        A 3D DataArray of shape (time, tile_id, idx) containing STAC items.
        Time coordinate values are actual datetimes (not just dates), derived
        from the nominal acquisition datetime of the first item per date/tile
        combination.

    Notes:
        - Only up to two items per (date, tile_id) and processing version
          are considered.
        - If more than two items exist for the same (date, tile_id, proc_version),
          a warning is logged and only the first two are used.
        - Among multiple processing versions, only the latest is retained.
    """
    items = add_nominal_datetime(items)

    # get dates and tile IDs of the items
    dates = []
    tile_ids = []
    for item in items:
        dates.append(item.properties["datetime_nominal"].date())
        tile_ids.append(item.properties["grid:code"])
    dates = np.unique(dates)
    tile_ids = np.unique(tile_ids)

    # sort items by date and tile ID into a data array
    grouped = xr.DataArray(
        np.empty((len(dates), len(tile_ids)), dtype=object),
        dims=("time", "tile_id"),
        coords=dict(time=dates, tile_id=tile_ids),
    )
    for idx, item in enumerate(items):
        date = item.properties["datetime_nominal"].date()
        tile_id = item.properties["grid:code"]
        if not grouped.sel(time=date, tile_id=tile_id).values:
            grouped.loc[date, tile_id] = [item]
        else:
            grouped.loc[date, tile_id].append(item)

    # replace date by datetime from first item
    dts = []
    for date in grouped.time.values:
        next_item = next(
            value for value in grouped.sel(time=date, idx=0).values if value is not None
        )
        dts.append(
            np.datetime64(
                next_item.properties["datetime_nominal"].replace(tzinfo=None)
            ).astype("datetime64[ns]")
        )
    grouped = grouped.assign_coords(time=dts)

    return grouped
