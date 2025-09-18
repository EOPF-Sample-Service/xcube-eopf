#  Copyright (c) 2025 by EOPF Sample Service team and contributors
#  Permissions are hereby granted under the terms of the Apache 2.0 License:
#  https://opensource.org/license/apache-2-0.

import dask.array as da
import numpy as np
import xarray as xr


def sen3_ol1efr_data():
    height = 4091
    width = 4865
    tile_height = 1024
    tile_width = 1024

    # band data
    bands = [f"oa{i:02d}_radiance" for i in range(1, 22)]
    mock_data = {
        band: (
            ("rows", "columns"),
            da.ones(
                (height, width), chunks=(tile_height, tile_width), dtype=np.float32
            ),
        )
        for band in bands
    }

    # geolocation data
    lon = da.linspace(0, 15, width, chunks=tile_width, dtype=np.float32)
    lon *= da.linspace(0.5, 1.5, width, chunks=tile_width, dtype=np.float32)
    lat = da.linspace(50, 60, height, chunks=tile_height, dtype=np.float32)
    lat *= da.linspace(0.5, 1.5, height, chunks=tile_height, dtype=np.float32)
    lon, lat = da.meshgrid(lon, lat, indexing="xy")
    coords = {
        "longitude": (("rows", "columns"), lon),
        "latitude": (("rows", "columns"), lat),
        "time_stamp": (("rows",), np.arange(height).astype("datetime64[ns]")),
    }
    return xr.Dataset(mock_data, coords=coords)
