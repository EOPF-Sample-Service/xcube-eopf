#  Copyright (c) 2025-2026 by EOPF Sample Service team and contributors
#  Permissions are hereby granted under the terms of the Apache 2.0 License:
#  https://opensource.org/license/apache-2-0.

import numpy as np
import xarray as xr


def sen1_grd_slc_analysis_dataset(
    data_var: str = "gamma0_vv",
    shape: tuple[int, int] = (2, 3),
    chunks: tuple[int, int] = (1, 3),
) -> xr.Dataset:
    data = np.arange(shape[0] * shape[1], dtype=np.float32).reshape(shape)
    return xr.Dataset(
        {data_var: (("y", "x"), data)},
        coords={
            "x": ("x", np.arange(shape[1], dtype=np.float32)),
            "y": ("y", np.arange(shape[0], dtype=np.float32)),
        },
    ).chunk({"y": chunks[0], "x": chunks[1]})
