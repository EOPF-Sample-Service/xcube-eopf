# About the `xcube-eopf` project

## Changelog

You can find the complete `xcube-eopf` changelog 
[here](https://github.com/EOPF-Sample-Service/xcube-eopf/blob/main/CHANGES.md). 

## Reporting

If you have suggestions, ideas, feature requests, or if you have identified
a malfunction or error, then please 
[post an issue](https://github.com/EOPF-Sample-Service/xcube-eopf/issues). 

## Contributions

The `xcube-eopf` project welcomes contributions of any form
as long as you respect our 
[code of conduct](https://github.com/EOPF-Sample-Service/xcube-eopf/blob/main/CODE_OF_CONDUCT.md)
and follow our 
[contribution guide](https://github.com/EOPF-Sample-Service/xcube-eopf/blob/main/CONTRIBUTING.md).

If you'd like to submit code or documentation changes, we ask you to provide a 
pull request (PR) 
[here](https://github.com/EOPF-Sample-Service/xcube-eopf/pulls). 
For code and configuration changes, your PR must be linked to a 
corresponding issue. 

## Development

To install the `xcube-eopf` development environment into an existing Python 
environment, do

```bash
pip install .[dev,doc]
```

or create a new environment using `conda` or `mamba`

```bash
mamba env create 
```

### Testing and Coverage

`xcube-eopf` uses [pytest](https://docs.pytest.org/) for unit-level testing 
and code coverage analysis.

```bash
pytest tests/ --cov=xarray_eopf --cov-report html
```

### Code Style

The `xcube-eopf` source code is formatted and quality-controlled 
using [ruff](https://docs.astral.sh/ruff/):

```bash
ruff format
ruff check
```

### Documentation

The `xcube-eopf` documentation is built using the 
[mkdocs](https://www.mkdocs.org/) tool.

With repository root as current working directory:

```bash
pip install .[doc]

mkdocs build
mkdocs serve
mkdocs gh-deploy
```

## License

`xcube-eopf` is open source made available under the terms and conditions of the 
[Apache 2.0 license](https://www.apache.org/licenses/LICENSE-2.0.html).
