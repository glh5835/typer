# BASELINE.md — 环境与测试基线（阶段 1）

采集时间：2026-10-09 02:31 – 03:05（本机 Windows 10 x64 / Git Bash）

## 环境

| 项 | 值 |
|---|---|
| 平台 | Windows 10 26200 x64，Git Bash |
| Python | 3.10.11（仓库要求 >=3.10，`venv/`，typer 为本仓库 editable 导入） |
| pytest | 9.1.1（含 pytest-cov 7.1.0、pytest-xdist 3.8.0、pytest-sugar 1.1.1） |
| typer | 0.27.3（本地源码，`import typer` → `D:\LEGION\Download\typer_newble\typer\__init__.py`） |
| rich / shellingham | 已安装（满足 tests 组依赖） |

安装方式：本会话复用仓库已有 `venv/`（未重装）。**验证环境正确的一行命令**：
`venv/Scripts/python.exe -c "import typer; print(typer.__file__, typer.__version__)"`

## 官方测试命令（与 scripts/test.sh 等价）

```bash
export TERMINAL_WIDTH=3000 _TYPER_FORCE_DISABLE_TERMINAL=1 _TYPER_RUN_INSTALL_COMPLETION_TESTS=1
venv/Scripts/python.exe -m pytest --cov --cov-report=term-missing \
  -o console_output_style=progress --showlocals --numprocesses=auto
```

> 说明：`scripts/test.sh` 内裸调 `pytest`，在 Windows 下会命中系统 Python（缺 annotated_doc）。
> 故用 venv 解释器 + 与脚本完全相同的参数/环境变量执行，语义等价。

## 基线结果（statement coverage，官方口径）

| 指标 | 值 |
|---|---|
| 测试结果 | **1488 passed, 15 skipped, 2 xfailed**（0 failed，exit 0） |
| 耗时 | 66.09 s（xdist 自动并行） |
| 语句覆盖率（typer+tests+docs_src 全仓） | **99%**（15106 语句，177 未覆盖） |
| warnings | 0（pyproject 设 `filterwarnings=error`，警告即失败） |

typer 主包（非 vendored click）statement 覆盖率 **全部 100%**，唯二例外在：
`_completion_classes.py:83`、`_completion_shared.py:106`（branch 模式才可见）。

### vendored click 内的语句缺口（baseline 快照）

| 文件 | 覆盖率 | 缺口行 |
|---|---|---|
| `typer/_click/_termui_impl.py` | 85% | 32-33, 357-367, 398-406, 422, 484-522（进度条终端交互） |
| `typer/_click/utils.py` | 97% | 45, 366-372 |
| `typer/_click/_compat.py` | 98% | 509-515 |

### 15 个 skip 的构成
completion 安装类测试在无权限/非目标 shell 环境下按 `requires_completion_permission` 跳过；2 个 xfail 为已知预期失败（strict_xfail）。明细见 `artifacts/phase1/test_full.log`。

## 分支覆盖率补充测量（阶段 2 选靶用）

因主包语句覆盖已饱和，另做了一次 `--cov-branch --cov=typer` 测量（64s，全绿），
**主要部分分支缺口**（行号 `a->b` 表示该跳转从未发生）：

| 文件 | 分支缺口数 | 代表性缺口 |
|---|---|---|
| `typer/cli.py` | 16 | 35->46, 209->217, 247->258（typer CLI 自身的 `run/docs/completion` 子命令分支） |
| `typer/core.py` | 15 | 335->348, 569->571, 657->660, 877->exit, 1032->1035, 1073->exit |
| `typer/main.py` | 10 | 887->890, 1233->1238, 1817->1820 等 |
| `typer/_click/utils.py` | 8 | 100->108, 256->275, 366-372 |
| `typer/_completion_shared.py` | 6 | 105->107, 127->129, 183->193 等 |
| `typer/rich_utils.py` | 5 | 83->87, 300->320, 383->388, 419->423 |
| `typer/testing.py` | 语句缺口 | **124-125（`Result.stderr` 的空异常分支）** |

完整表：`artifacts/phase1/test_branchcov.log`。

## 踩坑记录（详见 LEARNING_LOG.md 阶段 1）

1. `scripts/test.sh` 裸调 `pytest` 命中系统 Python → 用 `venv/Scripts/python.exe -m pytest` 显式指定。
2. 分支覆盖率 INTERNALERROR（"Can't combine branch coverage data with statement data"）：
   pytest-cov 子进程钩子让测试内 subprocess 以 pyproject 配置（无 branch）写数据，与 CLI `--cov-branch` 冲突。
   临时在 `[tool.coverage.run]` 加 `branch = true` 解决（测完已还原）。
3. `coverage/` 积压 452 个历史并行数据文件，`rm coverage/.coverage*` 因参数超限删不干净 → `find coverage -name ".coverage*" -delete`。
