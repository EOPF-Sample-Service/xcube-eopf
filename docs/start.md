# Getting Started

The `xcube-eopf` package can be installed into an existing Python environment
using

```bash
pip install xcube-eopf
```

or

```bash
conda install -c conda-forge xcube-eopf
```

After installation, you are ready to go and use the `"eopf-zarr"`
argument to initiate a xcube EOPF data store.

```python
from xcube.core.store import new_data_store

store = new_data_store("eopf-stac")
ds = store.open_data(
    data_id="sentinel-2-l2a",
    bbox=[9.7, 53.4, 10.3, 53.7],
    time_range=["2025-05-01", "2025-05-07"],
    spatial_res=10 / 111320,  # meters converted to degrees (approx.)
    crs="EPSG:4326",
    variables=["b02", "b03", "b04", "scl"],
)
```
