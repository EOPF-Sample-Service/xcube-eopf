#  Copyright (c) 2025 by EOPF Sample Service team and contributors
#  Permissions are hereby granted under the terms of the Apache 2.0 License:
#  https://opensource.org/license/apache-2-0.

import dask.array as da
import numpy as np
import pyproj
import xarray as xr


def _sen2_sample(
    origin: tuple[int, int],
    size: tuple[int, int],
    resolution: int,
    chunksize: tuple[int, int],
    bands: list[str],
    crs_utm: pyproj.CRS,
):
    # Coordinate arrays (center of pixels)
    x = origin[0] + np.arange(size[1]) * resolution + resolution / 2
    y = origin[1] - np.arange(size[0]) * resolution - resolution / 2

    # Create dataset
    data_vars = {
        band: (
            ("y", "x"),
            da.zeros(size, chunks=chunksize, dtype=np.float64),
        )
        for band in bands
    }
    ds = xr.Dataset(
        data_vars=data_vars, coords={"x": ("x", x), "y": ("y", y), "spatial_ref": 0}
    )
    ds.coords["spatial_ref"].attrs = crs_utm.to_cf()
    if "scl" in ds:
        ds["scl"] = ds["scl"].astype(np.uint8)

    return ds


def sen2_l2a_10m() -> xr.Dataset:
    size = (10980, 10980)
    chunksize = (1830, 1830)
    resolution = 10
    origin = (600000, 5910000)
    crs_utm = pyproj.CRS.from_epsg(32632)
    bands = ["b02", "b03", "b04", "scl"]
    return _sen2_sample(origin, size, resolution, chunksize, bands, crs_utm)


def sen2_l2a_60m() -> xr.Dataset:
    size = (1830, 1830)
    chunksize = (305, 305)
    resolution = 60
    origin = (600000, 5910000)
    crs_utm = pyproj.CRS.from_epsg(32632)
    bands = ["b02", "b03", "b04", "scl"]
    return _sen2_sample(origin, size, resolution, chunksize, bands, crs_utm)


def sen2_l2a_60m_wo_scl() -> xr.Dataset:
    size = (1830, 1830)
    chunksize = (305, 305)
    resolution = 60
    origin = (600000, 5910000)
    crs_utm = pyproj.CRS.from_epsg(32632)
    bands = ["b02", "b03", "b04"]
    return _sen2_sample(origin, size, resolution, chunksize, bands, crs_utm)
