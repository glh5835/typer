# LEARNING_LOG.md — 夜间自主任务学习日志（typer 仓库）

> 记录格式按任务书约定。所有时间均为本机时间（2026-10-09 凌晨开始）。

## 阶段 0：通读仓库
- 开始/结束时间：2026-10-09 02:30 – 02:55
- 目标：理解 typer 架构与核心数据流，产出 ARCHITECTURE.md。
- 我运行的命令：
  - `git remote -v`（确认 origin=我的 fork glh5835/typer，upstream=fastapi/typer）
  - `git checkout -b ai/nightly-typer-20261009-0230`
  - `wc -l typer/*.py typer/_click/*.py`（摸清代码规模：typer 主体 8.3k 行 + vendored click 4.7k 行）
  - `grep -n "^def \|^class \|^    def " typer/main.py typer/core.py typer/models.py`（先看骨架再精读）
  - `cat scripts/test.sh scripts/lint.sh`（官方工作流）
  - `find tests -name "*.py" | wc -l && grep -r "def test_" tests | wc -l`（298 文件 / 965 测试）
- 关键输出：
  - `typer/_click/__init__.py` 开头注释 "Code taken and adapted from Click 8.3.1" —— **click 被 vendored 进了包内**，这是 0.27 版本最大的架构变化，不看这个会完全误解依赖关系。
  - `scripts/test.sh` 设了三个关键环境变量：`TERMINAL_WIDTH=3000`（避免帮助文本换行导致断言不稳定）、`_TYPER_FORCE_DISABLE_TERMINAL=1`、`_TYPER_RUN_INSTALL_COMPLETION_TESTS=1`。**在 Windows Git Bash 里跑测试也必须带这三个变量**，否则输出与 CI 不一致。
- 失败尝试：无（本阶段纯阅读）。
- 为什么这样做：先用 `grep` 抽类/函数骨架而不是逐行通读 2000 行的 main.py——main.py 大部分体积是 `Annotated[..., Doc("...")]` 的文档字符串，真正的逻辑骨架只有几十个函数。定位核心数据流后再精读关键函数（`__call__` → `get_command` → `get_params_from_function` → `get_click_param`）。
- 涉及文件：`typer/main.py`、`typer/core.py`、`typer/utils.py`、`typer/models.py`、`typer/__init__.py`、`typer/_click/__init__.py`、`typer/testing.py`、`tests/conftest.py`、`pyproject.toml`、`scripts/*.sh`。
- 可迁移知识：
  1. 读大型开源库的顺序：pyproject/CI 配置 → 目录树行数分布 → grep 类/函数骨架 → 只精读数据流主路径。
  2. "vendored 依赖"模式：把上游库复制进自己包内魔改，换取不受上游发布节奏约束；识别标志是包内目录名 + 头部 "taken from X" 注释。
  3. `DefaultPlaceholder` 哨兵模式：用 `Default()` 包装默认值来区分"显式设置/未设置"，是多层级配置合并（help 6 级优先级）的基础。
  4. pytest `filterwarnings = ["error"]` 意味着任何新测试都不能触发弃用警告，否则直接失败。
- 我如何复现：`cat ARCHITECTURE.md`；按其 §8 阅读顺序自己走一遍源码。
- 下一步：阶段 1 环境与基线（优先跑 scripts/test.sh）。
