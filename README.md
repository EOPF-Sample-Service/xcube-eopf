[![Build Status](https://github.com/EOPF-Sample-Service/xcube-eopf/actions/workflows/unit-tests.yml/badge.svg?branch=main)](https://github.com/EOPF-Sample-Service/xcube-eopf/actions)
[![codecov](https://codecov.io/gh/EOPF-Sample-Service/xcube-eopf/branch/main/graph/badge.svg)](https://codecov.io/gh/EOPF-Sample-Service/xcube-eopf)
[![PyPI Version](https://img.shields.io/pypi/v/xcube-eopf)](https://pypi.org/project/xcube-eopf/)
[![Anaconda-Server Badge](https://anaconda.org/conda-forge/xcube-eopf/badges/version.svg)](https://anaconda.org/conda-forge/xcube-eopf)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/charliermarsh/ruff/main/assets/badge/v0.json)](https://github.com/charliermarsh/ruff)
[![License](https://anaconda.org/conda-forge/xcube-eopf/badges/license.svg)](https://anaconda.org/conda-forge/xcube-eopf)


# xcube-eopf

`xcube-eopf` is a Python package and [xcube plugin](https://xcube.readthedocs.io/en/latest/plugins.html) that adds a [data store](https://xcube.readthedocs.io/en/latest/api.html#data-store-framework)
named `eopf-zarr` to xcube. The data store is used to access ESA EOPF data products as an 
analysis-ready datacube (ARDC).

## Features

> **IMPORTANT**  
> `xcube-eopf` is currently under active development.  
> Some features may be partially implemented or still in progress.

The EOPF xcube data store is designed to provide analysis-ready data cubes from the 
EOPF Sentinel Zarr samples for Sentinel-1, Sentinel-2, and Sentinel-3 missions. The
main features are summarized below. A more in depth documentation is given in the 
[User Guide](guide.md). 

Currently, support is focused on **Sentinel-2** products.


### Sentinel-1

Support for Sentinel-1 will be added in an upcoming release.


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

store = new_data_store("eopf-zarr")
ds = store.open_data(
    data_id="sentinel-2-l2a",
    bbox=[9.7, 53.4, 10.3, 53.7],
    time_range=["2025-05-01", "2025-05-07"],
    spatial_res=10 / 111320,  # meters to degrees (approx.)
    crs="EPSG:4326",
    variables=["b02", "b03", "b04", "scl"],
)
```

### Sentinel-3

Support for Sentinel-3 products will be added in an upcoming release.



## Usage

The `xcube-eopf` package can be installed from PyPI (`pip install xcube-eopf`)
or conda-forge (`conda install -c conda-forge xcube-eopf`).
After installation, you are ready to go and use the `"eopf-zarr"` argument to initiate 
a xcube EOPF data store.

```python
from xcube.core.store import new_data_store

store = new_data_store("eopf-zarr")
ds = store.open_data(
    data_id="sentinel-2-l2a",
    bbox=[9.7, 53.4, 10.3, 53.7],
    time_range=["2025-05-01", "2025-05-07"],
    spatial_res=10 / 111320,  # meters converted to degrees (approx.)
    crs="EPSG:4326",
    variables=["b02", "b03", "b04", "scl"],
)
```

## Development

### Setting up a development environment

The recommended Python distribution for development is 
[miniforge](https://conda-forge.org/download/) which includes 
conda, mamba, and their dependencies.

```shell
git clone https://github.com/EOPF-Sample-Service/xcube-eopf.git
cd xcube-eopf
mamba env create
mamba activate xcube-eopf
pip install -ve .
```

### Install the library locally and test

```shell
mamba activate xcube-eopf
pip install -ve .
pytest
```
By default, this will run all unit tests. To run integration tests, use:  

```shell
pytest integration
```

To run tests and generate a coverage report, use:

```shell
pytest --cov xcube_eopf --cov-report html tests
```

### Some notes on the strategy of unit-testing

The unit test suite uses [pytest-recording](https://pypi.org/project/pytest-recording/)
to mock STAC catalogs. During development an actual HTTP request is performed
to a STAC catalog and the responses are saved in `cassettes/**.yaml` files.
During testing, only the `cassettes/**.yaml` files are used without an actual
HTTP request. During development, to save the responses to `cassettes/**.yaml`, run

```bash
pytest -v -s --record-mode new_episodes
```
Note that `--record-mode new_episodes` overwrites all cassettes. If the user only
wants to write cassettes which are not saved already, `--record-mode once` can be used.
[pytest-recording](https://pypi.org/project/pytest-recording/) supports all records modes given by [VCR.py](https://vcrpy.readthedocs.io/en/latest/usage.html#record-modes).
After recording the cassettes, testing can be performed as usual.


### Setting up a documentation environment

```shell
mamba activate xcube-eopf
pip install .[doc]
```

### Testing documentation changes

```shell
mkdocs serve
```

### Deploying documentation changes

```shell
mkdocs gh-deploy
```
