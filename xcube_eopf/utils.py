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
from xcube.core.store import DataStoreError
from xcube_resampling.gridmapping import GridMapping

from .constants import STAC_URL
from .version import version


def reproject_bbox(
    source_bbox: Sequence[int | float],
    source_crs: pyproj.CRS | str,
    target_crs: pyproj.CRS | str,
    buffer: float = 0.0,
) -> Sequence[int | float]:
    """Reprojects a bounding box from a source CRS to a target CRS, with optional
    buffering.

    The function transforms a bounding box defined in the source coordinate reference
    system (CRS) to the target CRS using `pyproj`. If the source and target CRS are
    the same, no transformation is performed. An optional buffer (as a fraction of
    width/height) can be applied to expand the resulting bounding box.

    Args:
        source_bbox: The bounding box to reproject, in the form
            (min_x, min_y, max_x, max_y).
        source_crs: The source CRS, as a `pyproj.CRS` or string.
        target_crs: The target CRS, as a `pyproj.CRS` or string.
        buffer: Optional buffer to apply to the transformed bounding box, expressed as
                a fraction (e.g., 0.1 for 10% padding). Default is 0.0 (no buffer).

    Returns:
        A tuple representing the reprojected (and optionally buffered) bounding box:
        (min_x, min_y, max_x, max_y).
    """
    source_crs = normalize_crs(source_crs)
    target_crs = normalize_crs(target_crs)
    if source_crs != target_crs:
        t = pyproj.Transformer.from_crs(source_crs, target_crs, always_xy=True)
        target_bbox = t.transform_bounds(*source_bbox, densify_pts=21)
    else:
        target_bbox = source_bbox
    if buffer > 0.0:
        x_min = target_bbox[0]
        x_max = target_bbox[2]
        if target_crs.is_geographic and x_min > x_max:
            x_max += 360
        buffer_x = abs(x_max - x_min) * buffer
        buffer_y = abs(target_bbox[3] - target_bbox[1]) * buffer
        target_bbox = (
            target_bbox[0] - buffer_x,
            target_bbox[1] - buffer_y,
            target_bbox[2] + buffer_x,
            target_bbox[3] + buffer_y,
        )

    return target_bbox


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

    y_coord, x_coord = get_spatial_dims(list_ds[0])
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


def get_spatial_dims(ds: xr.Dataset) -> (str, str):
    """Identifies the spatial coordinate names in a dataset.

    The function checks for common spatial dimension naming conventions: ("lat", "lon")
    or ("y", "x"). If neither pair is found, it raises a DataStoreError.

    Args:
        ds: The dataset to inspect.

    Returns:
        A tuple of strings representing the names of the spatial dimensions.

    Raises:
        DataStoreError: If no recognizable spatial dimensions are found.
    """
    if "lat" in ds and "lon" in ds:
        y_coord, x_coord = "lat", "lon"
    elif "y" in ds and "x" in ds:
        y_coord, x_coord = "y", "x"
    else:
        raise DataStoreError("No spatial dimensions found in dataset.")
    return y_coord, x_coord


def get_gridmapping(
    bbox: get_spatial_dims,
    spatial_res: float | int | tuple[float | int, float | int],
    crs: str | pyproj.crs.CRS,
    tile_size: int | tuple[int, int],
) -> GridMapping:
    """Creates a regular GridMapping object based on a bounding box, spatial resolution,
    and CRS.

    Args:
        bbox: The bounding box in the form (min_x, min_y, max_x, max_y).
        spatial_res: Spatial resolution as a single value or a (x_res, y_res) tuple.
        crs: Coordinate reference system as a `pyproj.CRS` or a string
            (e.g., "EPSG:4326").
        tile_size: Tile size as a single integer or a (width, height) tuple.

    Returns:
        A xcube `GridMapping` object representing the regular grid layout defined
        by the input parameters.
    """
    if not isinstance(spatial_res, tuple):
        spatial_res = (spatial_res, spatial_res)
    x_size = np.ceil((bbox[2] - bbox[0]) / spatial_res[0]) + 1
    y_size = np.ceil(abs(bbox[3] - bbox[1]) / spatial_res[1]) + 1
    return GridMapping.regular(
        size=(x_size, y_size),
        xy_min=(bbox[0] - spatial_res[0] / 2, bbox[1] - spatial_res[1] / 2),
        xy_res=spatial_res,
        crs=crs,
        tile_size=tile_size,
    )


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
