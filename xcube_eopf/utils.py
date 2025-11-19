#  Copyright (c) 2025 by EOPF Sample Service team and contributors
#  Permissions are hereby granted under the terms of the Apache 2.0 License:
#  https://opensource.org/license/apache-2-0.

import datetime
from collections.abc import Sequence

import dask.array as da
import numpy as np
import pyproj
import pystac
import xarray as xr
from xcube_resampling.utils import get_spatial_coords

from .constants import STAC_URL
from .version import version


def normalize_crs(crs: str | pyproj.CRS) -> pyproj.CRS:
    """Normalizes a CRS input by converting it to a pyproj.CRS object.

    If the input is already a `pyproj.CRS` instance, it is returned unchanged.
    If the input is a string (e.g., an EPSG code or PROJ string), it is converted
    to a `pyproj.CRS` object using `CRS.from_string`.

    Args:
        crs: A CRS specified as a string or a `pyproj.CRS` object.

    Returns:
        A `pyproj.CRS` object representing the normalized CRS.
    """
    if isinstance(crs, pyproj.CRS):
        return crs
    else:
        return pyproj.CRS.from_string(crs)


def add_nominal_datetime(items: Sequence[pystac.Item]) -> Sequence[pystac.Item]:
    """Adds the nominal (solar) time to each STAC item's properties under the key
    "datetime_nominal", based on the item's original UTC datetime.

    Args:
        items: A list of STAC item objects.

    Returns:
        A list of STAC item objects with the "datetime_nominal" field added to their
        properties.
    """

    for item in items:
        item.properties["center_point"] = get_center_from_bbox(item.bbox)
        item.properties["datetime_nominal"] = convert_to_solar_time(
            item.datetime, item.properties["center_point"][0]
        )
    return items


def get_center_from_bbox(bbox: Sequence[int | float]) -> Sequence[int | float]:
    """Calculates the center point of a bounding box.

    Args:
        bbox: The bounding box, in the form (min_x, min_y, max_x, max_y).

    Returns:
        A tuple (center_x, center_y) representing the center coordinates of the
        bounding box.
    """
    return (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2


def convert_to_solar_time(
    utc: datetime.datetime, longitude: float
) -> datetime.datetime:
    """Converts a UTC datetime to an approximate solar time based on longitude.

    The conversion assumes that each 15 degrees of longitude corresponds to a 1-hour
    offset from UTC, effectively snapping the time offset to whole-hour increments.
    This provides a simplified approximation of local solar time.

    Args:
        utc: The datetime in UTC.
        longitude: The longitude in degrees, where positive values are east of
        the meridian.

    Returns:
        A datetime object representing the approximate solar time.
    """
    offset_seconds = int(longitude / 15) * 3600
    return utc + datetime.timedelta(seconds=offset_seconds)


def mosaic_spatial_take_first(list_ds: list[xr.Dataset]) -> xr.Dataset:
    """Creates a spatial mosaic from a list of datasets by taking the first
    non-NaN value encountered across datasets at each pixel location.

    The function assumes all datasets share the same spatial dimensions and coordinate
    system. Only variables with 2D spatial dimensions (y, x) are processed. At each
    spatial location, the first non-NaN value across the dataset stack
    is selected.

    Args:
        list_ds: A list of datasets to be mosaicked.

    Returns:
        A new dataset representing the mosaicked result, using the first valid
        value encountered across the input datasets for each spatial position.
    """
    if len(list_ds) == 1:
        return list_ds[0]

    x_coord, y_coord = get_spatial_coords(list_ds[0])
    ds_mosaic = xr.Dataset()
    for key in list_ds[0]:
        if list_ds[0][key].dims[-2:] == (y_coord, x_coord):
            da_arr = da.stack([ds[key].data for ds in list_ds], axis=0)
            nonnan_mask = ~da.isnan(da_arr)
            first_non_nan_index = nonnan_mask.argmax(axis=0)
            da_arr_select = da.choose(first_non_nan_index, da_arr)
            ds_mosaic[key] = xr.DataArray(
                da_arr_select,
                dims=list_ds[0][key].dims,
                coords=list_ds[0][key].coords,
                attrs=list_ds[0][key].attrs,
            )

    # attributes are taken from the first UTM dataset
    ds_mosaic.attrs = list_ds[0].attrs

    return ds_mosaic


def add_attributes(
    ds: xr.Dataset, grouped_items: xr.DataArray, **open_params
) -> xr.Dataset:
    """Adds metadata attributes to the final dataset.

    This function enriches the input dataset with additional metadata attributes:
    - 'stac_url': A predefined URL for the EOPF STAC API.
    - 'stac_items': A mapping from time steps to lists of STAC item IDs.
    - 'open_params': Opening parameters.
    - 'xcube_eopf_version': The version of the xcube-eopf package being used.

    Parameters:
        ds: The input dataset to which attributes will be added.
        grouped_items: An array containing STAC items grouped by time and tile ID.
        **open_params: Opening parameters that are stored as a metadata attribute.

    Returns:
        The modified dataset with added metadata attributes.
    """
    ds.attrs["stac_url"] = STAC_URL
    ds.attrs["stac_items"] = dict(
        {
            dt.astype("datetime64[ms]")
            .astype("O")
            .isoformat(): [
                item.id for item in np.sum(grouped_items.sel(time=dt).values)
            ]
            for dt in grouped_items.time.values
        }
    )
    ds.attrs["open_params"] = open_params
    ds.attrs["xcube_eopf_version"] = version

    return ds


def filter_items_deprecated(items: list[pystac.Item]) -> list[pystac.Item]:
    """Filter out deprecated STAC items, which are deprecated.

    Args:
        items: A list of STAC items to filter.

    Returns:
        A list of STAC items that are not marked as deprecated.
    """
    sel_items = []
    for item in items:
        deprecated = item.properties.get("deprecated", False)
        if not deprecated:
            sel_items.append(item)
    return sel_items


def filter_items_wrong_footprint(items: list[pystac.Item]) -> list[pystac.Item]:
    """Filter out STAC items with incorrectly assigned footprints at the antimeridian.

    Some items may have footprints crossing the antimeridian where the west and east
    boundaries are swapped, resulting in a longitude span greater than 180°.
    This function removes such items by checking the difference between the minimum
    and maximum longitude values in the item's bounding box.

    Args:
        items: A list of STAC items to filter.

    Returns:
        A list of STAC items whose bounding boxes do not exceed 180°
        in longitude extent.

    Notes:
        See related issue: https://github.com/EOPF-Sample-Service/eopf-stac/issues/39
    """
    sel_items = []
    for item in items:
        if abs(item.bbox[2] - item.bbox[0]) < 180:
            sel_items.append(item)
    return sel_items


def bbox_to_geojson(bbox):
    """
    Convert a bounding box to a GeoJSON Polygon.

    Args:
        bbox: list or tuple of four numbers [min_x, min_y, max_x, max_y]

    Returns:
        dict: GeoJSON Polygon
    """
    min_x, min_y, max_x, max_y = bbox
    return {
        "type": "Polygon",
        "coordinates": [
            [
                [min_x, min_y],
                [max_x, min_y],
                [max_x, max_y],
                [min_x, max_y],
                [min_x, min_y],
            ]
        ],
    }
