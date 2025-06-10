# xcube EOPF data store  

`xcube-eopf` is a Python package that enhances [xcube](https://xcube.readthedocs.io/en/latest/dataaccess.html#available-data-stores) 
by a new [data store](https://xcube.readthedocs.io/en/latest/dataaccess.html#available-data-stores) 
named `"eopf-zarr"`. This plugin allows to create analysis-ready data cubes (ARDC) from the Sentinel products
published by the Projekt [EOPF Sentinel Zarr Sample Service](https://zarr.eopf.copernicus.eu/).

## Overview

After installation of the package, you can open EOPF data products using the
usual functionalities of a xcube's data store.

> **IMPORTANT**  
> The `xcube-eopf` package is in a preliminary development state.
> The following features are only partly or not at all implemented yet.

Data variables will always be represented as chunked Dask arrays for 
efficient out-of core computations and visualisations.

The package uses the [xarray-eopf](https://eopf-sample-service.github.io/xarray-eopf/)
backend as a reading routine and uses the capabilities of [xcube](https://xcube.readthedocs.io/en/latest/dataaccess.html#available-data-stores)
to create analysis-ready tempo-spatial 3D data cubes.

## License

The package is open source and released under the 
[Apache 2.0 license](https://www.apache.org/licenses/LICENSE-2.0.html) license. :heart:

