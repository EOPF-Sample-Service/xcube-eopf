#  Copyright (c) 2025 by EOPF Sample Service team and contributors
#  Permissions are hereby granted under the terms of the Apache 2.0 License:
#  https://opensource.org/license/apache-2-0.

import datetime

import pyproj
import pystac


def reproject_bbox(
    source_bbox: tuple[int] | tuple[float] | list[int] | list[float],
    source_crs: pyproj.CRS | str,
    target_crs: pyproj.CRS | str,
    buffer: float = 0.0,
) -> tuple[int] | tuple[float]:
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


def add_nominal_datetime(items: list[pystac.Item]) -> list[pystac.Item]:
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


def get_center_from_bbox(
    bbox: tuple[float] | tuple[int] | list[float] | list[int],
) -> tuple[float, float]:
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
