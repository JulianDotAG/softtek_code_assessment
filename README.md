# softtek_code_assessment

Softtek Code Assessment

## Dependencies

The environment is managed with [uv](https://docs.astral.sh/uv/). `pyproject.toml` declares the
version ranges, `uv.lock` pins the exact versions and hashes, and `.python-version` pins
Python 3.12 — so `uv sync` recreates an identical virtualenv on any machine.

```bash
uv sync
```

`requirements.txt` is **generated** from `uv.lock`, never edited by hand. It exists so the project
can also be installed with plain `pip` (`pip install --require-hashes -r requirements.txt`) when
`uv` is not available.

Regenerate it after changing any dependency:

```bash
uv export --format requirements-txt --output-file requirements.txt
```
