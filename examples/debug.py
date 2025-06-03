
import xarray as xr


path = (
    "https://objectstore.eodc.eu:2222/e05ab01a9d56408d82ac32d69a5aae2a:202505-s02m"
    "sil1c/13/products/cpm_v256/S2A_MSIL1C_20250513T104041_N0511_R008_T32"
    "UMD_20250513T131608.zarr"
)
ds = xr.open_datatree(path, engine="zarr")
print(ds)

# store = new_data_store("eopf-zarr")
# bbox = [9.1, 53.1, 10.7, 54]
# crs_target = "EPSG:32632"
# bbox_utm = reproject_bbox(bbox, "EPSG:4326", crs_target)
#
# ds = store.open_data(
#     data_id="sentinel-2-l1c",
#     bbox=bbox_utm,
#     time_range=["2025-04-20", "2025-05-03"],
#     spatial_res=10,
#     crs=crs_target,
#     variables=["b02", "b03", "b04", "scl"],
# )
# print(ds)
