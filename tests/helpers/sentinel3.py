#  Copyright (c) 2025 by EOPF Sample Service team and contributors
#  Permissions are hereby granted under the terms of the Apache 2.0 License:
#  https://opensource.org/license/apache-2-0.

import dask.array as da
import numpy as np
import pyproj
import xarray as xr


def sen3_ol1efr_data():
    height = 1485
    width = 1856
    tile_height = 1024
    tile_width = 1024

    # band data
    bands = [f"oa{i:02d}_radiance" for i in range(1, 3)]
    mock_data = {
        band: (
            ("lat", "lon"),
            da.ones(
                (height, width), chunks=(tile_height, tile_width), dtype=np.float32
            ),
        )
        for band in bands
    }

    # geolocation data
    lon = np.linspace(5.0, 10.0, width, dtype=np.float32)
    lat = np.linspace(57.0, 53.0, height, dtype=np.float32)
    coords = {
        "lon": lon,
        "lat": lat,
        "spatial_ref": xr.DataArray(
            0, attrs=pyproj.CRS.from_string("epsg:4326").to_cf()
        ),
    }
    return xr.Dataset(mock_data, coords=coords)
