#  Copyright (c) 2025 by EOPF Sample Service team and contributors
#  Permissions are hereby granted under the terms of the Apache 2.0 License:
#  https://opensource.org/license/apache-2-0.

from abc import ABC
from collections import defaultdict

import dask.array as da
import numpy as np
import pyproj
import pystac
import xarray as xr
from xcube.util.jsonschema import JsonObjectSchema
from xcube_resampling.gridmapping import GridMapping
from xcube_resampling.spatial import resample_in_space

from xcube_eopf.constants import (
    CONVERSION_FACTOR_DEG_METER,
    SCHEMA_ADDITIONAL_QUERY,
    SCHEMA_AGG_METHODS,
    SCHEMA_BBOX,
    SCHEMA_CRS,
    SCHEMA_INTERP_METHODS,
    SCHEMA_SPATIAL_RES,
    SCHEMA_TILE_SIZE,
    SCHEMA_TIME_RANGE,
    SCHEMA_VARIABLES,
)
from xcube_eopf.prodhandler import ProductHandler, ProductHandlerRegistry
from xcube_eopf.utils import (
    add_attributes,
    add_nominal_datetime,
    get_gridmapping,
    mosaic_spatial_take_first,
    normalize_crs,
    reproject_bbox,
)

_SEN2_SPATIAL_RES = np.array([10, 20, 60])
_TILE_SIZE = 1830  # chunk size of 10m resolution and a multiple of 20m and 60m
_ATTRIBUTE_KEYS = [
    "_eopf_attrs",
    "long_name",
    "flag_values",
    "flag_meanings",
    "flag_colors",
    "grid_mapping",
]


class Sen2ProductHandler(ProductHandler, ABC):
    """General Sentinel-2 product handles, defining methods applicable
    for L1C and L2A product.
    """

    # noinspection PyMethodMayBeStatic
    def get_open_data_params_schema(self) -> JsonObjectSchema:
        return JsonObjectSchema(
            title="Opening parameters for Sentinel-2 products.",
            properties=dict(
                variables=SCHEMA_VARIABLES,
                spatial_res=SCHEMA_SPATIAL_RES,
                time_range=SCHEMA_TIME_RANGE,
                bbox=SCHEMA_BBOX,
                crs=SCHEMA_CRS,
                tile_size=SCHEMA_TILE_SIZE,
                query=SCHEMA_ADDITIONAL_QUERY,
                agg_methods=SCHEMA_AGG_METHODS,
                interp_methods=SCHEMA_INTERP_METHODS,
            ),
            required=["time_range", "bbox", "crs", "spatial_res"],
            additional_properties=False,
        )

    def open_data(self, items: list[pystac.Item], **open_params) -> xr.Dataset:
        # get STAC items grouped by solar day and MRGS tile
        grouped_items = group_items(items)

        # generate cube by mosaicking and stacking tiles
        ds = generate_cube(grouped_items, **open_params)

        # add attributes
        ds = add_attributes(ds, grouped_items, **open_params)

        # TODO how to handle solar and viewing angles

        return ds


class Sen2L1CProductHandler(Sen2ProductHandler):
    data_id = "sentinel-2-l1c"


class Sen2L2AProductHandler(Sen2ProductHandler):
    data_id = "sentinel-2-l2a"


def register(registry: ProductHandlerRegistry):
    registry.register(Sen2L1CProductHandler)
    registry.register(Sen2L2AProductHandler)


def group_items(items: list[pystac.Item]) -> xr.DataArray:
    """Group STAC items by solar day and tile ID.

    Organizes a list of Sentinel-2 STAC items into an `xarray.DataArray` with
    dimensions `(time, tile_id)`, where:
    - `time` represents the solar acquisition date (date only, time of day is ignored).
    - `tile_id` corresponds to the Sentinel-2 MGRS tile code.

    Args:
        items: A list of STAC items. Each item must include:
            - `properties["datetime_nominal"]`: The nominal acquisition datetime.
            - `properties["grid:code"]`: The MGRS tile code.

    Returns:
        A 2D `xarray.DataArray` of shape (time, tile_id), where each cell contains a
        list of STAC items for the given date and tile ID. The `time` coordinate is
        derived from the nominal acquisition datetime of the first item in each
        (date, tile) group.

    Notes:
        - Each cell in the returned array contains a list of items because tiles may
          be split across multiple files.
    """
    items = add_nominal_datetime(items)

    # TODO: So far no handling of processing version,
    #       STAC items with multiple processing versions are added to the list and
    #       mosaicked by taking the fist non-NaN value.
    #       For proper handling wait for STAC item update (see https://github.com/EOPF-Sample-Service/eopf-stac/issues/28)
    # get dates and tile IDs of the items
    dates = []
    tile_ids = []
    for item in items:
        dates.append(item.properties["datetime_nominal"].date())
        tile_ids.append(item.properties["grid:code"])
    dates = np.unique(dates)
    tile_ids = np.unique(tile_ids)

    # sort items by date and tile ID into a data array
    grouped_items = np.full((len(dates), len(tile_ids)), None, dtype=object)
    for item in items:
        date = item.properties["datetime_nominal"].date()
        tile_id = item.properties["grid:code"]
        idx_date = np.where(dates == date)[0][0]
        idx_tile_id = np.where(tile_ids == tile_id)[0][0]
        if grouped_items[idx_date, idx_tile_id] is None:
            grouped_items[idx_date, idx_tile_id] = [item]
        else:
            grouped_items[idx_date, idx_tile_id].append(item)
    for idx_date in range(grouped_items.shape[0]):
        for idx_tile_id in range(grouped_items.shape[1]):
            if grouped_items[idx_date, idx_tile_id] is None:
                grouped_items[idx_date, idx_tile_id] = []
    grouped_items = xr.DataArray(
        grouped_items,
        dims=("time", "tile_id"),
        coords=dict(time=dates, tile_id=tile_ids),
    )

    # replace date by datetime from first item
    dts = []
    for date in grouped_items.time.values:
        item = np.sum(grouped_items.sel(time=date).values)[0]
        dts.append(item.datetime.replace(tzinfo=None))
    grouped_items = grouped_items.assign_coords(
        time=np.array(dts, dtype="datetime64[ns]")
    )
    grouped_items["time"].encoding["units"] = "seconds since 1970-01-01"
    grouped_items["time"].encoding["calendar"] = "standard"

    return grouped_items


def generate_cube(grouped_items: xr.DataArray, **open_params) -> xr.Dataset:
    """Generate a spatiotemporal data cube from grouped STAC items.

    This function takes grouped STAC items and generates a unified xarray
    dataset, mosaicking and stacking the data across spatial tiles and time.

    Args:
        grouped_items: A 2D data array indexed by time and tile_id, where each element
            contains a list of STAC items for the given date and tile ID.
        **open_params: Optional keyword arguments for data opening and processing:
            - bbox (list): Bounding box used for spatial subsetting.
            - crs (str): Coordinate reference system of the bounding box.
            - spatial_res (int | float | tuple): spatial resolution of the
                final datacube.

    Returns:
        A dataset representing the spatiotemporal cube.
    """
    # Group the tile IDs by UTM zones
    utm_tile_id = defaultdict(list)
    for tile_id in grouped_items.tile_id.values:
        item = np.sum(grouped_items.sel(tile_id=tile_id).values)[0]
        crs = item.properties["proj:code"]
        utm_tile_id[crs].append(tile_id)

    # Insert the tile data per UTM zone
    list_ds_utm = []
    for crs, tile_ids in utm_tile_id.items():
        ds = _generate_utm_cube(grouped_items.sel(tile_id=tile_ids), crs, **open_params)
        list_ds_utm.append(ds)

    # Reproject datasets from different UTM zones to a common grid reference system
    # and merge them into a single unified dataset for seamless spatial analysis.
    ds_final = _merge_utm_zones(list_ds_utm, **open_params)

    return ds_final


def _generate_utm_cube(
    grouped_items: xr.DataArray,
    crs_utm: str,
    **open_params,
) -> xr.Dataset:
    """Load and insert tile data for a specific UTM zone into a unified dataset.

    This method processes the assets from selected STAC items within a particular
    UTM zone. It opens the respective tiles, clips it to the target bounding box
    (reprojected to the UTM CRS), mosaics overlapping spatial datasets by taking the
    first valid pixel, and inserts the processed data into an aggregated dataset for
    that UTM zone.

    Args:
        grouped_items: A 2D data array indexed by time and tile_id, where each element
            contains a list of STAC items for the given date and tile ID.
        crs_utm: The target UTM coordinate reference system identifier.
        **open_params: Additional parameters to control data opening and processing,
            including 'bbox' (bounding box) and 'crs' (coordinate reference system).

    Returns:
        A dataset containing mosaicked and stacked 3d datacubes
        (time, spatial_y, spatial_x) for all requested spectral bands within the
        specified UTM zone.
    """
    items_bbox = _get_bounding_box(grouped_items)
    final_bbox = reproject_bbox(open_params["bbox"], open_params["crs"], crs_utm)
    spatial_res = _get_spatial_res(open_params)
    xarray_open_params = dict(
        resolution=spatial_res,
        interp_methods=open_params.get("interp_method"),
        agg_methods=open_params.get("agg_methods"),
        variables=open_params.get("variables"),
    )

    final_ds = None
    for dt_idx, dt in enumerate(grouped_items.time.values):
        for tile_id in grouped_items.tile_id.values:
            items = grouped_items.sel(tile_id=tile_id, time=dt).item()
            multi_tiles = []
            for item in items:
                ds = xr.open_dataset(
                    item.assets["product"].href,
                    engine="eopf-zarr",
                    chunks={},
                    **xarray_open_params,
                )
                ds = ds.sel(
                    x=slice(final_bbox[0], final_bbox[2]),
                    y=slice(final_bbox[3], final_bbox[1]),
                )
                if any(size == 0 for size in ds.sizes.values()):
                    continue
                multi_tiles.append(ds)
            if not multi_tiles:
                continue
            mosaicked_ds = mosaic_spatial_take_first(multi_tiles)
            if final_ds is None:
                final_ds = _create_empty_dataset(
                    mosaicked_ds, grouped_items, items_bbox, final_bbox, spatial_res
                )
            final_ds = _insert_tile_data(final_ds, mosaicked_ds, dt_idx)

    return final_ds


def _insert_tile_data(final_ds: xr.Dataset, ds: xr.Dataset, dt_idx: int) -> xr.Dataset:
    """Insert spatial data from a smaller dataset into a larger asset dataset at
    the correct spatiotemporal indices.

    This method locates the spatial coordinates of the input dataset `ds` within
    the larger `final_ds` along the 'x' and 'y' dimensions, then inserts the data
    from `ds` into the corresponding slice of `final_ds` for the specified time
    index `dt_idx`.

    Args:
        final_ds: The larger dataset representing the final data cube for one UTM zone.
        ds: The smaller xarray Dataset containing data to be inserted.
        dt_idx: The time index in `final_ds` at which to insert the data.

    Returns:
        The updated `final_ds` with data from `ds` inserted at the appropriate
        spatial location.
    """
    xmin = final_ds.indexes["x"].get_loc(ds.x[0].item())
    xmax = final_ds.indexes["x"].get_loc(ds.x[-1].item())
    ymin = final_ds.indexes["y"].get_loc(ds.y[0].item())
    ymax = final_ds.indexes["y"].get_loc(ds.y[-1].item())
    for var in ds.data_vars:
        final_ds[var][dt_idx, ymin : ymax + 1, xmin : xmax + 1] = ds[var]
    return final_ds


def _merge_utm_zones(list_ds_utm: list[xr.Dataset], **open_params) -> xr.Dataset:
    """Merge multiple Sentinel-2 datacubes for different UTM zones into a
    single dataset.

    This function takes a list of Sentinel-2 datasets (each in a different UTM zone),
    resamples them to a common grid defined by a target CRS and spatial resolution,
    and mosaics them into a single output using a "take first" strategy for overlaps.

    Parameters:
        list_ds_utm: A list of xarray Datasets, one for each UTM zone.
        open_params: Dictionary of parameters required for constructing the target grid,
            including:
            - crs: Target coordinate reference system (string or EPSG code).
            - spatial_res: Spatial resolution as a single value or tuple (x_res, y_res).
            - bbox: Bounding box for the output grid (minx, miny, maxx, maxy).
            - tile_size (optional): Tile size for the target grid.

    Returns:
        A single xarray Dataset reprojected to the target CRS and resolution,
        containing merged data from all input UTM zones.

    Notes:
        - If one input dataset already matches the target CRS and resolution,
          its grid mapping is reused unless resolution mismatches are found.
        - Overlapping regions are resolved by selecting the first non-NaN value.
    """
    # get correct target gridmapping
    crss = [pyproj.CRS.from_cf(ds["spatial_ref"].attrs) for ds in list_ds_utm]
    target_crs = pyproj.CRS.from_string(open_params["crs"])
    crss_equal = [target_crs == crs for crs in crss]
    if any(crss_equal):
        true_index = crss_equal.index(True)
        ds = list_ds_utm[true_index]
        target_gm = GridMapping.from_dataset(ds)
        spatial_res = open_params["spatial_res"]
        if not isinstance(spatial_res, tuple):
            spatial_res = (spatial_res, spatial_res)
        if (
            ds.x[1] - ds.x[0] != spatial_res[0]
            or abs(ds.y[1] - ds.y[0]) != spatial_res[1]
        ):
            target_gm = get_gridmapping(
                open_params["bbox"],
                open_params["spatial_res"],
                open_params["crs"],
                open_params.get("tile_size", _TILE_SIZE),
            )
    else:
        target_gm = get_gridmapping(
            open_params["bbox"],
            open_params["spatial_res"],
            open_params["crs"],
            open_params.get("tile_size", _TILE_SIZE),
        )

    resampled_list_ds = []
    for ds in list_ds_utm:
        resampled_list_ds.append(_resample_dataset_soft(ds, target_gm, **open_params))
    return mosaic_spatial_take_first(resampled_list_ds)


def _resample_dataset_soft(
    ds: xr.Dataset, target_gm: GridMapping, **open_params
) -> xr.Dataset:
    """Resample a dataset to a target grid mapping, using either affine transform
    or reprojection.

    If the source and target grid mappings are close, the dataset is returned unchanged.
    If they share the same CRS but differ spatially, an affine transformation is
    applied. Otherwise, the dataset is reprojected to the target grid.

    Parameters:
        ds: The source xarray Dataset to be resampled.
        target_gm: The target grid mapping

    Returns:
        The resampled dataset aligned with the target grid mapping.
    """
    source_gm = GridMapping.from_dataset(ds)
    if source_gm.is_close(target_gm):
        return ds
    ds = resample_in_space(
        ds,
        target_gm=target_gm,
        source_gm=source_gm,
        interp_methods=open_params.get("interp_methods"),
        agg_methods=open_params.get("agg_methods"),
    )
    return ds


def _get_bounding_box(grouped_items: xr.DataArray) -> list[float | int]:
    """Compute the overall bounding box that covers all tiles for the given grouped
     STAC items.

    Iterates through each tile ID in `grouped_items` to extract the bounding box
    from its STAC item and calculates the minimum bounding rectangle encompassing all
    tiles.

    Parameters:
        grouped_items: A 2D data array indexed by time and tile_id, where each element
            contains a list of STAC items for the given date and tile ID.

    Returns:
        A list with four elements [xmin, ymin, xmax, ymax] representing the
        bounding box that encloses all tiles.
    """
    xmin, ymin, xmax, ymax = np.inf, np.inf, -np.inf, -np.inf
    for tile_id in grouped_items.tile_id.values:
        item = np.sum(grouped_items.sel(tile_id=tile_id).values)[0]
        # take an assets which is available in L1C and L2A and read out
        # the bounding box in UTM coordinates.
        bbox = item.assets["B02_10m"].extra_fields["proj:bbox"]
        if xmin > bbox[0]:
            xmin = bbox[0]
        if ymin > bbox[1]:
            ymin = bbox[1]
        if xmax < bbox[2]:
            xmax = bbox[2]
        if ymax < bbox[3]:
            ymax = bbox[3]
    return [xmin, ymin, xmax, ymax]


def _get_spatial_res(open_params: dict) -> int:
    """Determine the appropriate Sentinel-2 spatial resolution based on the CRS.

    If the CRS is geographic (e.g., EPSG:4326), the requested spatial resolution
    (in degree) is converted to meters. The function then selects the nearest
    equal or coarser supported Sentinel-2 resolution from the native
    resolutions [10, 20, 60].

    Args:
        open_params: Dictionary of open parameters. Must include:
            - "crs": Coordinate reference system as EPSG string or identifier.
            - "spatial_res": Desired spatial resolution in meters.

    Returns:
        An integer representing the selected spatial resolution (10, 20, or 60).
        If no coarser resolution is found, defaults to 60.
    """
    crs = normalize_crs(open_params["crs"])
    if crs.is_geographic:
        spatial_res = open_params["spatial_res"] * CONVERSION_FACTOR_DEG_METER
    else:
        spatial_res = open_params["spatial_res"]
    idxs = np.where(_SEN2_SPATIAL_RES >= spatial_res)[0]
    if len(idxs) == 0:
        spatial_res = 60
    else:
        spatial_res = int(_SEN2_SPATIAL_RES[idxs[0]])

    return spatial_res


def _create_empty_dataset(
    sample_ds: xr.Dataset,
    grouped_items: xr.DataArray,
    items_bbox: list[float | int] | tuple[float | int],
    final_bbox: list[float | int] | tuple[float | int],
    spatial_res: int | float,
) -> xr.Dataset:
    """Create an empty xarray Dataset with spatial and temporal dimensions matching
    the given bounding boxes and grouped items.

    The dataset is constructed using the data variables and types from `sample_ds`,
    creating arrays filled with NaNs. It conforms to the native pixel grid and spatial
    resolution of the Sentinel-2 product, while covering the spatial extent defined
    by the input bounding boxes. The temporal dimension and coordinate values are
    derived from `grouped_items`. The resulting dataset includes coordinates for
    time, y, and x dimensions, along with a matching spatial reference coordinate
    system.

    Args:
        sample_ds: A sample dataset whose data variable names and dtypes will be used.
        grouped_items: A 2D DataArray (time, tile_id) containing grouped STAC items.
        items_bbox: The bounding box covering all input items (minx, miny, maxx, maxy).
        final_bbox: The target bounding box to define the spatial extent of the final
            datacube (minx, miny, maxx, maxy).
        spatial_res: The spatial resolution in CRS units (e.g., meters or degrees).

    Returns:
        A dataset with shape (time, y, x), filled with NaNs and ready to be populated
        with mosaicked data.
    """
    half_res = spatial_res / 2
    y_start = items_bbox[3] - spatial_res * (
        (items_bbox[3] - final_bbox[3]) // spatial_res
    )
    y_end = items_bbox[1] + spatial_res * (
        (final_bbox[1] - items_bbox[1]) // spatial_res
    )
    y = np.arange(y_start - half_res, y_end, -spatial_res)
    x_end = items_bbox[2] - spatial_res * (
        (items_bbox[2] - final_bbox[2]) // spatial_res
    )
    x_start = items_bbox[0] + spatial_res * (
        (final_bbox[0] - items_bbox[0]) // spatial_res
    )
    x = np.arange(x_start + half_res, x_end, spatial_res)

    chunks = (1, _TILE_SIZE, _TILE_SIZE)
    shape = (grouped_items.sizes["time"], len(y), len(x))
    ds = xr.Dataset(
        {
            key: (
                ("time", "y", "x"),
                da.full(shape, np.nan, dtype=var.dtype, chunks=chunks),
            )
            for (key, var) in sample_ds.data_vars.items()
        },
        coords={
            "x": x,
            "y": y,
            "time": grouped_items.time,
            "spatial_ref": sample_ds.spatial_ref,
        },
    )
    for key in sample_ds.data_vars:
        ds[key].attrs = {
            k: sample_ds[key].attrs[k]
            for k in _ATTRIBUTE_KEYS
            if k in sample_ds[key].attrs
        }

    return ds
