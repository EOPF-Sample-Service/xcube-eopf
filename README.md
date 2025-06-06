# xcube-eopf

`xcube-eopf` is a Python package and
[xcube plugin](https://xcube.readthedocs.io/en/latest/plugins.html) that adds a
[data store](https://xcube.readthedocs.io/en/latest/api.html#data-store-framework)
named `eopf` to xcube. The data store is used to access ESA EOPF data products as an 
analysis-ready datacube (ARDC).


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

### Documentation

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
