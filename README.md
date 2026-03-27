[![Build Status](https://github.com/EOPF-Sample-Service/xcube-eopf/actions/workflows/unit-tests.yml/badge.svg?branch=main)](https://github.com/EOPF-Sample-Service/xcube-eopf/actions)
[![codecov](https://codecov.io/gh/EOPF-Sample-Service/xcube-eopf/branch/main/graph/badge.svg)](https://codecov.io/gh/EOPF-Sample-Service/xcube-eopf)
[![PyPI Version](https://img.shields.io/pypi/v/xcube-eopf)](https://pypi.org/project/xcube-eopf/)
[![Anaconda-Server Badge](https://anaconda.org/conda-forge/xcube-eopf/badges/version.svg)](https://anaconda.org/conda-forge/xcube-eopf)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/charliermarsh/ruff/main/assets/badge/v0.json)](https://github.com/charliermarsh/ruff)
[![License](https://anaconda.org/conda-forge/xcube-eopf/badges/license.svg)](https://anaconda.org/conda-forge/xcube-eopf)


# xcube-eopf

`xcube-eopf` is a Python package and an [xcube plugin](https://xcube.readthedocs.io/en/latest/plugins.html) that provides a [data store](https://xcube.readthedocs.io/en/latest/api.html#data-store-framework)
named `eopf-zarr`. This data store enables access to ESA EOPF data products as 
analysis-ready datacubes (ARDCs) within the xcube framework.

## Features

> **IMPORTANT**  
> `xcube-eopf` is under active development.  
> Some features may be incomplete or subject to change.

The EOPF xcube data store is designed to provide analysis-ready data cubes from 
multiple EOPF Sentinel Zarr sample products, supporting Sentinel-1, Sentinel-2, 
and Sentinel-3 missions.

For more information, please refer to the [documentation](https://eopf-sample-service.github.io/xcube-eopf/).
