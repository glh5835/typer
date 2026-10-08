# Contributing to Typer

Thanks for your interest in contributing! 🎉

For the general contribution workflow (PRs, reviews, style), please follow the
[official contributing guidelines](https://tiangolo.com/open-source/contributing/)
referenced in [docs/contributing.md](docs/contributing.md).

The rest of this file is a **practical newcomer supplement**: the shortest path
from a fresh clone to a green local test run, including platform quirks that
are easy to trip over.

## Quick start (newcomer supplement)

### 1. Create an environment

The project requires **Python >= 3.10**. Any virtualenv tool works; with plain
`venv`:

```console
$ python -m venv venv
$ source venv/bin/activate        # Linux/macOS
$ venv\Scripts\activate           # Windows
$ pip install -e ".[dev]"         # or: uv sync
```

Verify you are importing the **local source tree**, not a site-packages copy:

```console
$ python -c "import typer; print(typer.__file__)"
/path/to/typer_newble/typer/__init__.py
```

### 2. Run the tests (the official way)

The official entrypoint is `scripts/test.sh`:

```console
$ bash scripts/test.sh
```

It runs pytest with coverage and three environment variables that the suite
depends on:

```console
$ export TERMINAL_WIDTH=3000
$ export _TYPER_FORCE_DISABLE_TERMINAL=1
$ export _TYPER_RUN_INSTALL_COMPLETION_TESTS=1
$ pytest --cov --cov-report=term-missing --numprocesses=auto
```

> **Windows note:** `scripts/test.sh` calls `pytest` directly, so make sure the
> *venv's* `pytest` is first on `PATH`. If you see
> `ModuleNotFoundError: No module named 'annotated_doc'`, the shell picked up
> the system Python. The robust form is:
> `venv/Scripts/python.exe -m pytest ...` with the same arguments and variables
> as the script.

Why these variables matter:

* `TERMINAL_WIDTH=3000` keeps help output unwrapped so assertions on help text
  are stable.
* `_TYPER_FORCE_DISABLE_TERMINAL=1` disables terminal detection inside tests.
* `_TYPER_RUN_INSTALL_COMPLETION_TESTS=1` opts in to the completion-install
  tests (they are skipped otherwise).

### 3. Lint and type-check

```console
$ bash scripts/lint.sh
```

which runs `mypy typer`, `ty check typer`, and `ruff check`/`ruff format`
over `typer`, `tests`, `docs_src`, and `scripts`. New test files must pass
`ruff check` and `ruff format --check` too — note that ruff's isort config
treats `typer` as a third-party import, and the `UP` rules require
`X | None` instead of `Optional[X]`.

### 4. Understand the layout before changing code

* `typer/main.py` — the `Typer` class and the app→command compilation pipeline.
* `typer/core.py` — `TyperCommand`/`TyperGroup`/`TyperOption`/`TyperArgument`,
  the seams over vendored Click.
* `typer/_click/` — **vendored copy of Click 8.3.1**, adapted. Changes here
  diverge from upstream Click; keep them minimal and justified.
* `typer/params.py` / `typer/models.py` — the `Option()`/`Argument()` public
  API surface; most of the file is user-facing docs in `Doc(...)` annotations.
* `tests/test_tutorial/**` — one test per `docs_src/` example, keeping the
  documentation executable. If you change a docs example, its test changes too.
* `pyproject.toml` sets `filterwarnings = ["error"]`: any deprecation warning
  raised by your change fails the suite.

### 5. Writing a good test

The house style is:

```python
from typer.testing import CliRunner

runner = CliRunner()

def test_my_feature():
    result = runner.invoke(app, ["--my-option", "value"])
    assert result.exit_code == 0
    assert "expected output" in result.stdout
```

Assert real behavior (exit code + stdout/stderr content). For
platform-specific branches, monkeypatch the module constant (e.g. `WIN`) and
assert the documented layout — do not fake coverage for physically
unreachable code.

### 6. Coverage tips

The core package is already at ~100% statement coverage; to find remaining
gaps use branch coverage:

```console
$ pytest --cov=typer --cov-branch --cov-report=term-missing
```

To combine branch data, `branch = true` must also be set in
`[tool.coverage.run]` (temporarily) — subprocess coverage spawned by the test
suite reads the config file, not the `--cov-branch` CLI flag, and mixing the
two modes makes the combine step crash. Clean stale files in `coverage/`
before switching modes.

### 7. Before you commit

```console
$ bash scripts/test.sh && bash scripts/lint.sh
$ git status && git diff --check   # only intended files, no whitespace errors
```

Commit messages follow
[conventional commits](https://www.conventionalcommits.org/) with emoji, e.g.
`🐛 Fix ...`, `✨ Add ...`, `📝 Docs ...` (see `git log` for examples).
