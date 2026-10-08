# PR_DRAFT.md — PR 草稿（禁止擅自提交，仅草稿）

> 状态：**未创建 PR**。本文件按任务书要求准备；提交动作需人工确认。
> 注：本 fork 为练习用途（约定不向上游提 PR）。若未来要向 fastapi/typer 提交，
> 建议先在 GitHub 上对照上游最新 master rebase 并重跑验证。

## 建议标题

```
✨ tests: add regression tests for testing utils, bash completion version check, app dir layouts, and optional enums
```

（若拆分为多个 PR 更符合上游粒度，见文末"拆分建议"。）

## 描述

### Summary

- Add 15 tests covering previously untested behaviors: `Result.__repr__` in `typer.testing`, the Bash completion version gate (`BashComplete._check_version`), the documented per-platform `get_app_dir` layouts (incl. `force_posix`), and `Optional[Enum]` option defaults.
- Deduplicate the shared help-assertion block repeated across 5 markup-mode tests into a single `_assert_markup_mode_help()` helper (net -39 lines, no assertion changes).
- Add missing docstrings to public/internal API surface (`typer/models.py`, `typer/utils.py`, `typer/main.py`) and a root `CONTRIBUTING.md` newcomer guide.

### Motivation

The core package is at ~100% statement coverage, but branch coverage showed real gaps (e.g. `typer/testing.py`'s `Result.__repr__` was never exercised; `_completion_classes.py`'s old-Bash warning path was unreached; the documented `get_app_dir` layouts were only tested via the patched `app_dir` fixture, not the real implementation). These tests pin down documented behavior that could silently regress.

### Changes

**Tests**
- `tests/test_result_repr.py` — new: `Result.__repr__` for success and exception outcomes.
- `tests/test_completion/test_bash_version.py` — new: warning for Bash < 4.4, silence for ≥ 5, message for unparsable version output (mocked `shutil.which` / `subprocess.run`, asserting real stderr behavior).
- `tests/test_get_app_dir_paths.py` — new: `get_app_dir` roaming/not-roaming/`force_posix`/darwin/XDG layouts (platform constants monkeypatched where physically unreachable on Windows) and `_posixify`.
- `tests/test_optional_enum_default.py` — new: `Optional[Enum]` option keeps `None` default, converts valid values, rejects invalid ones.
- `tests/test_rich_markup_mode.py` — refactor: extract `_assert_markup_mode_help()` used by 5 tests; per-test parametrizations unchanged (28 passed + 2 xfailed before and after).

**Docs**
- `typer/main.py` (22 functions), `typer/models.py` (8 classes), `typer/utils.py` (4 exception classes + 2 functions): concise Google-style docstrings.
- New root `CONTRIBUTING.md` linking the official guidelines plus a practical newcomer supplement (env setup, official test entrypoint, the three required env vars, Windows pitfalls, coverage tips).

### Verification

```console
$ export TERMINAL_WIDTH=3000 _TYPER_FORCE_DISABLE_TERMINAL=1 _TYPER_RUN_INSTALL_COMPLETION_TESTS=1
$ pytest --cov --cov-report=term-missing --numprocesses=auto
1503 passed, 15 skipped, 2 xfailed          # was 1488 passed before this branch
$ ruff check typer tests docs_src scripts && ruff format --check typer tests docs_src scripts
All checks passed! / 646 files already formatted
```

Coverage deltas (branch-aware where relevant):

| module | before | after |
|---|---|---|
| `typer/testing.py` | 99% branch (124–125 missing) | 100% |
| `typer/_completion_classes.py` | 99% (line 83) | 100% |
| `typer/_click/utils.py` | 97% (45, 366–372) | 100% statements |
| repo-wide missing statements | 177 | 168 |

`mypy typer` and `ty check typer` show only pre-existing findings (verified
identical on the base commit via `git stash` comparison).

### Related issues

No open bug issues existed at the time (verified via GitHub search API).
Regression coverage for recently closed bugs #1787, #1353, #1156 was verified
present; this PR adds no behavioral source changes.

### Checklist

- [x] Tests pass locally (full suite, 3 OS-relevant env vars set)
- [x] `ruff check` / `ruff format --check` clean
- [x] No public API behavior changes (tests + docs + test-internal refactor only)
- [ ] CI green on all 3 platforms (needs upstream CI run)

### 拆分建议（若按上游粒度拆分）

1. `test: add regression tests for untested behaviors`（4 个新测试文件）
2. `refactor: deduplicate markup-mode help assertions`（test_rich_markup_mode.py）
3. `docs: add docstrings and CONTRIBUTING newcomer guide`（docstring + CONTRIBUTING.md）
