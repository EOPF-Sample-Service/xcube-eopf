# xcube EOPF Data Store

`xcube-eopf` is a Python package that extends [xcube](https://xcube.readthedocs.io/en/latest) with a new [data store](https://xcube.readthedocs.io/en/latest/dataaccess.html#available-data-stores)
called `"eopf-zarr"`. This plugin enables the creation of analysis-ready data cubes 
(ARDC) from Sentinel products published by the [EOPF Sentinel Zarr Sample Service](https://zarr.eopf.copernicus.eu/).

## Overview

Once installed, the package gives access to EOPF data products in an analysis-ready 
data cube format through the standard xcube data store interface. You can:

- List available data sources
- Check data availability
- Get metadata of the data sources
- View available open parameters for each source
- Open data source directly as [xcube Dataset](https://xcube.readthedocs.io/en/latest/cubespec.html)

To explore all available functions, see the [Python API](api.md).

The data retrieval process uses the [EOPF STAC API](https://stac.browser.user.eopf.eodc.eu/), which allows querying 
observations over a specified time range and spatial extent. The resulting datasets 
are mosaicked per time step and stacked into a 3D spatiotemporal data cube.

Each data variable is returned as a chunked **Dask array**, supporting efficient 
out-of-core computations and visualization.

Internally, the package uses the [xarray-eopf](https://eopf-sample-service.github.io/xarray-eopf/) backend for reading, and leverages 
[xcube](https://xcube.readthedocs.io/en/latest/dataaccess.html#available-data-stores) to construct spatiotemporal analysis-ready data cubes.

## Features

> **IMPORTANT**  
> `xcube-eopf` is currently under active development.  
> Some features may be partially implemented or still in progress.

The EOPF xcube data store is designed to provide analysis-ready data cubes from the 
EOPF Sentinel Zarr samples for Sentinel-1, Sentinel-2, and Sentinel-3 missions. The
main features are summarized below. A more in depth documentation is given in the 
[User Guide](guide.md). 

Currently, support is focused on **Sentinel-2** and **Sentinel-3** products.

---

### Sentinel-1

Support for Sentinel-1 will be added in an upcoming release.

---

### Sentinel-2

The current implementation supports two Sentinel-2 product levels, available as 
`data_id` values:

- `sentinel-2-l1c`: Level-1C top-of-atmosphere reflectance
- `sentinel-2-l2a`: Level-2A atmospherically corrected surface reflectance

#### Cube Generation Workflow

The workflow for building 3D analysis-ready cubes from Sentinel-2 products involves 
the following steps:

1. **Query** products using the [EOPF STAC API](https://stac.browser.user.eopf.eodc.eu/) for a given time range and 
   spatial extent.
2. **Retrieve** observations as cloud-optimized Zarr chunks via the 
   [xarray-eopf backend](https://eopf-sample-service.github.io/xarray-eopf/).
3. **Mosaic** spatial tiles into single images per timestamp.
4. **Stack** the mosaicked scenes along the temporal axis to form a 3D cube.

#### Supported Variables

- **Surface reflectance bands**:  
  `b01`, `b02`, `b03`, `b04`, `b05`, `b06`, `b07`, `b08`, `b8a`, `b09`, `b11`, `b12`
- **Classification/Quality layers** (L2A only):  
  `cld`, `scl`, `snw`

**Example: Sentinel-2 L2A**
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

The current implementation supports three Sentinel-3 product levels, available as 
`data_id` values:

- `sentinel-3-olci-l1-efr`: Level-1 top-of-atmosphere radiance from OLCI instrument
- `sentinel-3-olci-l2-lfr`: Level-2 land and atmospheric geophysical parameters 
   derived from OLCI instrument
- `sentinel-3-slstr-l1-rbt`: Level-1 radiances and brightness temperatures (RBT)
   derived from SLSTR instrument
- `sentinel-3-slstr-l2-lst`: Level-2  land surface temperature derived from SLSTR 
   instrument

#### Cube Generation Workflow

The workflow for building 3D analysis-ready cubes from Sentinel-3 products involves 
the following steps:

1. **Query** tiles using the [EOPF Zarr Sample Service STAC API](https://stac.core.eopf.eodc.eu/) for a given time range and 
   spatial extent.
2. **Group** items by solar day.
3. **Rectify** data from the native 2D irregular grid to a regular grid using 
   [xcube-resampling](https://xcube-dev.github.io/xcube-resampling/guide/#3-rectification).
4. **Mosaic** adjacent tiles into seamless daily scenes.
5. **Stack** the daily mosaics along the temporal axis to form 3D data cubes 
   for each variable (e.g., spectral bands).

#### Supported Variables

- `sentinel-3-olci-l1-efr`:  
  `oa01_radiance`, `oa02_radiance`, `oa03_radiance`, `oa04_radiance`, `oa05_radiance`,
  `oa06_radiance`, `oa07_radiance`, `oa08_radiance`, `oa09_radiance`, `oa10_radiance`,
  `oa11_radiance`, `oa12_radiance`, `oa13_radiance`, `oa14_radiance`, `oa15_radiance`,
  `oa16_radiance`, `oa17_radiance`, `oa18_radiance`, `oa19_radiance`, `oa20_radiance`,
  `oa21_radiance`
- `sentinel-3-olci-l2-lfr`:  
  `gifapar`, `iwv`, `otci`, `rc681`, `rc865`
- `sentinel-3-slstr-l1-rbt`:
  `s1_radiance_an`, `s2_radiance_an`, `s3_radiance_an`, `s4_radiance_an`,
  `s5_radiance_an`, `s6_radiance_an`, `s1_radiance_ao`, `s2_radiance_ao`,
  `s3_radiance_ao`, `s4_radiance_ao`, `s5_radiance_ao`, `s6_radiance_ao`,
  `s4_radiance_bn`, `s5_radiance_bn`, `s6_radiance_bn`, `s4_radiance_bo`,
  `s5_radiance_bo`, `s6_radiance_bo`, `f1_bt_fn`, `f1_bt_fo`, `f2_bt_in`,
  `f2_bt_io`, `s7_bt_in`, `s8_bt_in`, `s9_bt_in`, `s7_bt_io`, `s8_bt_io`,
  `s9_bt_io`
- `sentinel-3-slstr-l2-lst`:
  `lst`

**Example: Sentinel-3 SLSTR Level-2 LST**
```python
from xcube.core.store import new_data_store

store = new_data_store("eopf-stac")
ds = store.open_data(
    data_id="sentinel-3-slstr-l2-lst",
    bbox=[9., 53., 11., 54.],
    time_range=["2025-06-01", "2025-06-05"],
    spatial_res=300 / 111320, # conversion to degree approx.
    crs="EPSG:4326"
)
```

---
## License

The package is open source and released under the 
[Apache 2.0 license](https://www.apache.org/licenses/LICENSE-2.0.html) license. :heart:

