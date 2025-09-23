## Accessing EOPF Sentinel Zarr Data Cubes with xcube

The `"eopf-zarr"` xcube data store enables you to create analysis-ready data cubes 
(ARDCs) from Sentinel Zarr sample products published by the 
[EOPF Sentinel Zarr Sample Service](https://zarr.eopf.copernicus.eu/).

This plugin provides convenient access to analysis-ready data from the Sentinel-1,
Sentinel-2, and Sentinel-3 missions.
Currently, only Sentinel-2 products are supported.

This guide walks you through:

1. **Set up a EOPF Data Store**
2. **Selecting a Product**
3. **Opening a Spatiotemporal Data Cube**
4. **Inspecting, Visualizing, and Saving the Data Cube**

---

### 1. Set up a EOPF Data Store

To instantiate the data store:
```python
from xcube.core.store import new_data_store

store = new_data_store("eopf-zarr")
```
### 2. Select a Data Product

Data products from Sentinel-1, -2, and -3 are accessed via the `data_id` parameter, 
which corresponds to collection names in the [EOPF STAC API](https://stac.browser.user.eopf.eodc.eu/).

To list all available data IDs:
```python
store.list_data_ids()
```
Each `data_id` is documented in the respective sections for the 
[supported missions](#specific-parameters-for-supported-sentinel-missions) below.

### 3. Open a Spatiotemporal Data Cube

To open a cube (e.g., for Sentinel-2 Level-2A):
```python
ds = store.open_data(
    data_id="sentinel-2-l2a",
    bbox=[9.7, 53.4, 10.3, 53.7],
    time_range=["2025‑05‑01", "2025‑05‑07"],
    spatial_res=10 / 111320,  # here approx. 10m in degrees
    crs="EPSG:4326",
)
```
It uses the [xarray-eopf](https://eopf-sample-service.github.io/xarray-eopf/) backend  as a reading routine to open the EOPF Zarr 
Samples. 

> 💡 **Note**  
> `open_data()` builds a Dask graph and returns a lazy `xarray.Dataset`.
> No actual data is loaded at this point. 

**Required parameters:**

- `bbox`: Bounding box ["west", "south", "est", "north"] in CRS coordinates.
- `time_range`: Temporal extent ["YYYY-MM-DD", "YYYY-MM-DD"].
- `spatial_res`: Spatial resolution in meter of degree (depending on the CRS).
- `crs`: Coordinate reference system (e.g. `"EPSG:4326"`).

These parameters control the STAC API query and define the output cube's spatial grid.

## Optional Parameters

- `variables`: Variables to include in the dataset. Accepts a single name, a regex pattern, or an iterable of either.
- `tile_size`: Spatial tile size of the returned dataset, given as `(width, height)`.
- `query`: Additional filtering options for STAC Items by their properties. See the 
  [STAC Query Extension](https://github.com/stac-api-extensions/query) for details.
- `agg_methods`: Aggregation method(s) for downsampling spatial variables. Accepts:  
  - A single method applied to all variables, or  
  - A dictionary mapping variable names or dtypes to methods.

  Supported methods include:  
  `"center"`, `"count"`, `"first"`, `"last"`, `"max"`, `"mean"`, `"median"`,  
  `"mode"`, `"min"`, `"prod"`, `"std"`, `"sum"`, `"var"`.  

  *Default:* `"center"` for integer arrays, `"mean"` otherwise.  
  For details, see the [xcube-resampling documentation](https://xcube-dev.github.io/xcube-resampling/).  

- `interp_methods`: Interpolation method(s) for upsampling spatial variables. Accepts:  
  - A single method applied to all variables, or  
  - A dictionary mapping variable names or dtypes to methods.  

  Supported methods include:  
  - `0` — nearest neighbor (*default for categorical / integer datasets*)  
  - `1` — linear / bilinear (*default for float datasets*)  
  - `"nearest"` - alias for `0` 
  - `"triangular"` - linearly interpolate between 4 points using two triangles 
  - `"bilinear"` - alias for `1` 

  For details, see the [xcube-resampling documentation](https://xcube-dev.github.io/xcube-resampling/). 


### 4. Inspect, Visualize, and Save the Data Cube

You can visualize a time slice:

```python
ds.b04.isel(time=0).plot()
```
> ⚠️ **Warning**  
> This operation triggers data downloads and processing. For large regions, use with care.

#### Saving the Data Cube

Although the EOPF xcube plugin focuses on data access, it integrates seamlessly with 
the broader xcube ecosystem for post-processing and storage.

To persist the data cube, write it to a local file or S3-compatible object storage 
using the `file` or `s3` xcube data store backends:

**Local Filesystem Data Store:**
```python
storage = new_data_store("file")
```
**S3 Data Store:**
```python
storage = new_data_store(
    "s3",
    root="bucket-name",
    storage_options=dict(
        anon=False,
        key="your_s3_key",
        secret="your_s3_secret",
    ),
)
```
More info: [Filesystem-based data stores](https://xcube.readthedocs.io/en/latest/dataaccess.html#filesystem-based-data-stores).

Then, write the cube:

```python
storage.write_data(ds, "path/to/file.zarr")
```

#### Visualize in xcube Viewer
Once saved as Zarr, you can use [xcube Viewer](https://xcube-dev.github.io/xcube-viewer/build_viewer/#build-and-deploy),
to visualize the cube:

```python
from xcube.webapi.viewer import Viewer

viewer = Viewer()
ds = storage.open_data("path/to/file.zarr")
viewer.add_dataset(ds)
viewer.show()
```

To retrieve the temporary URL of the launched viewer as a web app:

```python
viewer.info()
```


---
## Specific Parameters for supported Sentinel Missions

### 🛰️ Sentinel-1

Support for Sentinel-1 will be added in an upcoming release.

---

### 🛰️ Sentinel-2

Sentinel-2 provides multi-spectral imagery at different native resolutions:

- 10m: b02, b03, b04, b08 
- 20m: b05, b06, b07, b8a, b11, b12 
- 60m: b01, b09, b10

Sentinel-2 products are organized as STAC Items, each representing a single tile. 
These tiles are stored in their native UTM CRS, which varies by geographic location.

**Data Identifiers**

The EOPF xcube data store supports two Sentinel-2 product types via the `data_id` argument:

| Data ID             | Description                                            |
|---------------------|--------------------------------------------------------|
| `sentinel-2-l1c`    | Level‑1C top‑of‑atmosphere (TOA) reflectance           |
| `sentinel-2-l2a`    | Level‑2A atmospherically corrected surface reflectance |


**Supported Variables**

- **Surface reflectance bands**:  
  `b01`, `b02`, `b03`, `b04`, `b05`, `b06`, `b07`, `b08`, `b8a`, `b09`, `b11`, `b12`
- **Classification/Quality layers** (L2A only):  
  `cld`, `scl`, `snw`

**Data Cube Generation Workflow**

1. **STAC Query:** A STAC API request returns relevant STAC Items (tiles) based on 
   spatial and temporal extent (`bbox` and `time_range` argument).
2. **Sorting:** Items are ordered by solar acquisition time and Tile ID.
3. **Native Alignment:** Within each UTM zone, tiles from the same solar day are 
   aligned in the native UMT without reprojection. Overlaps are resolved by selecting 
   the first non-NaN pixel value in item order.
4. **Cube Assembly:** The method of cube creation depends on the user's request,
  as summarized below:

| Scenario         | Native Resolution Preservation                                                                                                                                                                                                                                                      | Reprojected or Resampled Cube                                                                                                                                                              |
|------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Condition        | Requested bounding box lies within a single UTM zone, native CRS is requested, and the spatial resolution matches the native resolution.                                                                                                                                            | Data spans multiple UTM zones, a different CRS is requested (e.g., EPSG:4326), or a custom spatial resolution is requested.                                                                |
| Processing steps | Only upsampling or downsampling is applied to align the differing resolutions of the spectral bands. Data cube is directly cropped using the requested bounding box, preserving original pixel values. Spatial extent may deviate slightly due to alignment with native pixel grid. | A target grid mapping is computed from bounding box, spatial resolution, and CRS. Data from each UTM zone is reprojected/resampled to this grid. Overlaps resolved by first non-NaN pixel. |

Users can specify any spatial resolution and coordinate reference system (CRS) when 
opening data with `open_data`. As a result, spectral bands may be resampled — either 
upsampled or downsampled — and reprojected to match the target grid. If reprojection 
is needed at a lower resolution, the process first downsamples the data and 
subsequently performs the reprojection. Upsampling and downsampling are controlled using the `agg_methods` and `interp_methods`
parameters (see [Optional Parameters](#optional-parameters)).





### 🛰️ Sentinel-3

Sentinel-3 has two instruments on board: 

🌊 **OLCI — Ocean and Land Colour Instrument**

- **Purpose**: Primarily designed for ocean and land surface monitoring.
- **Spectral bands**: 21 bands (400–1020 nm).
- **Spatial resolution**: 300 m.
- **Swath width**: ~1,270 km

🔥 **SLSTR — Sea and Land Surface Temperature Radiometer**

- **Purpose**: Measures global sea and land surface temperatures with high accuracy.
- **Spectral bands**: 9 bands (visible to thermal infrared, 0.55–12 μm).
- **Spatial resolution**: 500 m (visible & shortwave infrared bands) and 1 km 
  (thermal infrared bands).
- **Swath width**: ~1,400 km

Sentinel-3 data products are distributed as **STAC Items**, where each item 
corresponds to a single tile. The datasets are provided in their 
**native 2D irregular grid** and typically require rectification for analysis-ready 
applications. 

**Data Identifiers**

The EOPF xcube data store so far supports three Sentinel-3 product types via the 
`data_id` argument:

| Data ID                   | Description                                                           |
|---------------------------|-----------------------------------------------------------------------|
| `sentinel-3-olci-l1-efr`  | Level-1 full-resolution top-of-atmosphere radiances from the OLCI     |
| `sentinel-3-olci-l2-lfr`  | Level-2 land and atmospheric geophysical parameters derived from OLCI |
| `sentinel-3-slstr-l2-lst` | Level-2 land surface temperature products derived from SLSTR          |


**Supported Variables**

- `sentinel-3-olci-l1-efr`:  
  `oa01_radiance`, `oa02_radiance`, `oa03_radiance`, `oa04_radiance`, `oa05_radiance`,
  `oa06_radiance`, `oa07_radiance`, `oa08_radiance`, `oa09_radiance`, `oa10_radiance`,
  `oa11_radiance`, `oa12_radiance`, `oa13_radiance`, `oa14_radiance`, `oa15_radiance`,
  `oa16_radiance`, `oa17_radiance`, `oa18_radiance`, `oa19_radiance`, `oa20_radiance`,
  `oa21_radiance`
- `sentinel-3-olci-l2-lfr`:  
  `gifapar`, `iwv`, `otci`, `rc681`, `rc865`
- `sentinel-3-slstr-l2-lst`:  
  `lst`

**Data Cube Generation Workflow**

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

⚠️ **Important considerations**:  

- Rectification (irregular → regular grid) is computationally expensive and may 
  slow down cube generation.  
- Users can specify any spatial resolution and coordinate reference system (CRS) when 
  opening data with `open_data`. During rectification, spectral bands are internally 
  reprojected to the target grid. If a lower-resolution grid is requested, 
  downsampling is applied prior to rectification.  
- Resampling behavior is controlled via the [`agg_methods`](#optional-parameters) 
  (downsampling) and [`interp_methods`](#optional-parameters) 
  (upsampling/interpolation) parameters.  

---
