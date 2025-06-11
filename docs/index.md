# xcube EOPF Data Store

`xcube-eopf` is a Python package that extends [xcube](https://xcube.readthedocs.io/en/latest/dataaccess.html#available-data-stores) with a new [data store](https://xcube.readthedocs.io/en/latest/dataaccess.html#available-data-stores)
called `"eopf-zarr"`. This plugin enables the creation of analysis-ready data cubes 
(ARDC) from Sentinel products published by the [EOPF Sentinel Zarr Sample Service](https://zarr.eopf.copernicus.eu/).

## Overview

Once installed, the package gives access to EOPF data products in an analysis-ready data cube format  
through the standard xcube data store interface. You can:

- List available data sources
- Check data availability
- Describe data sources
- View available open parameters for each source
- Open data sources directly as xarray datasets

To explore all available functions, see the [Python API](api.md).

The data retrieval process uses the [EOPF STAC API](https://stac.browser.user.eopf.eodc.eu/),  
which allows querying observations over a specified time range and spatial extent. The resulting datasets are  
mosaicked per time step and stacked into a 3D data cube with dimensions: `time`, `latitude`, and `longitude`.

Each data variable is returned as a chunked **Dask array**, supporting efficient out-of-core computations and visualization.

Internally, the package uses the [xarray-eopf](https://eopf-sample-service.github.io/xarray-eopf/) backend for reading,  
and leverages [xcube](https://xcube.readthedocs.io/en/latest/dataaccess.html#available-data-stores) to construct spatiotemporal analysis-ready data cubes.

## Features

> **IMPORTANT**  
> `xcube-eopf` is currently under active development.  
> Some features may be partially implemented or still in progress.

The EOPF xcube data store is designed to provide analysis-ready data cubes from the
EOPF Sentinel Zarr samples for Sentinel-1, Sentinel-2, and Sentinel-3 missions.

Currently, support is focused on **Sentinel-2** products.

---

### Sentinel-1

Support for Sentinel-1 will be added in an upcoming release.

---

### Sentinel-2

The current implementation supports two Sentinel-2 product levels, available as `data_id` values:

- `sentinel-2-l1c`: Level-1C top-of-atmosphere reflectance
- `sentinel-2-l2a`: Level-2A atmospherically corrected surface reflectance

#### Cube Generation Workflow

The workflow for building 3D analysis-ready cubes from Sentinel-2 products involves the following steps:

1. **Query** products using the [EOPF STAC API](https://stac.browser.user.eopf.eodc.eu/) for a given time range and spatial extent.
2. **Retrieve** observations as cloud-optimized Zarr chunks via the [xarray-eopf backend](https://eopf-sample-service.github.io/xarray-eopf/).
3. **Mosaic** spatial tiles into single images per timestamp.
4. **Stack** the mosaicked scenes along the temporal axis to form a 3D cube.

#### Supported Variables

- **Surface reflectance bands**:  
  `b01`, `b02`, `b03`, `b04`, `b05`, `b06`, `b07`, `b08`, `b8a`, `b09`, `b11`, `b12`
- **Classification/Quality layers** (L2A only):  
  `cld`, `scl`, `snw`

#### Example: Sentinel-2 L2A

```python
from xcube.core.store import new_data_store

store = new_data_store("eopf-stac")
ds = store.open_data(
    data_id="sentinel-2-l2a",
    bbox=[9.7, 53.4, 10.3, 53.7],
    time_range=["2025-05-01", "2025-05-07"],
    spatial_res=10 / 111320,  # meters to degrees (approx.)
    crs="EPSG:4326",
    variables=["b02", "b03", "b04", "scl"],
)
```
--- 
### Sentinel-3

Support for Sentinel-3 products will be added in an upcoming release.

---
## License

The package is open source and released under the 
[Apache 2.0 license](https://www.apache.org/licenses/LICENSE-2.0.html) license. :heart:

