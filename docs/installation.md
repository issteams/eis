# Installation

## Requirements

- Python 3.11 or newer.
- A virtual environment is recommended.

## Development installation

From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

The project is built with Hatchling. Runtime dependencies include `httpx`, `pydantic`, `pydantic-settings`, and `structlog`; development dependencies add pytest, coverage, Ruff, and mypy.

## Verify the installation

Run the repository checks:

```bash
ruff check .
ruff format --check .
mypy src
pytest --cov=eis --cov-report=term-missing
```

The project configuration requires at least 90% coverage for the configured source set.

## Editable package use

After `pip install -e '.[dev]'`, the public package can be imported as:

```python
from eis import EIS

runtime = EIS()
print(runtime.products())
```

The supported public API is exposed through `eis` and `eis.sdk`.
