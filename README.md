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
