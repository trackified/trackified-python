# Contributing

```sh
python -m venv .venv && . .venv/bin/activate
pip install -e '.[dev]'
ruff check . && ruff format --check .
mypy
pytest
```

Unit tests never touch the network. `tests/test_live.py` runs against the real API only when
`TRACKIFIED_API_KEY` is set; it creates one tracking and deletes it.

Sync and async resources live side by side in `src/trackified/_resources.py`; change both together.
Open a pull request against `main`; CI must pass.
