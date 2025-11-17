## Changes in 0.4.0 (under development)

* Made the `crs` parameter optional and set its default to `"EPSG:4326"`.
  Added support for `crs="native"` for Sentinel-2, which allows specifying the
  bounding box in latitude/longitude while returning the data in its native
  UTM grid. (#42)


## Changes in 0.3.0

* Added workflows for generating 3D data cubes from multiple Sentinel-3 tiles.  
  The workflow includes **rectification** of 2D irregular grids, **spatial mosaicking** 
  of adjacent tiles, and **temporal stacking** of multiple observations.

  Supported products:  
  * `sentinel-3-olci-l1-efr` — Level-1 top-of-atmosphere radiance from the OLCI 
    instrument.  
  * `sentinel-3-olci-l2-lfr` — Level-2 land and atmospheric geophysical parameters 
    derived from OLCI.  
  * `sentinel-3-slstr-l2-lst` — Level-2 land surface temperature derived from SLSTR.


## Changes in 0.2.0

* Switched to [xcube-resampling](https://xcube-dev.github.io/xcube-resampling/) 
  for dataset resampling and reprojection.  
* Renamed the keyword argument `spline_orders` to `interp_methods` to align with 
  the naming convention used in xcube-resampling.  
* Fixed issue #39: resolved `AttributeError: 'dict' object has no attribute 'coords'`.


## Changes in 0.1.1

* Fixed a bug in Sentinel-2 cube generation where, during mosaicking of adjacent tiles 
  from the same solar day, data from one spectral band would overwrite all other bands 
  in the final cube.


## Changes in 0.1.0

* Implemented workflows for generating 3D data cubes from multiple Sentinel-2 tiles.
  This includes spatial mosaicking of adjacent tiles and temporal stacking of
  multiple observations.

## Changes in 0.0.1

* Initial package structure.
* Basic README and documentation.
* License and contribution guidelines.
