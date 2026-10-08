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

## 阶段 1：环境与基线
- 开始/结束时间：2026-10-09 02:55 – 03:05
- 目标：跑通官方测试套件，采集测试数量/通过率/覆盖率/warnings 基线。
- 我运行的命令：
  - `venv/Scripts/python.exe --version && -m pytest --version && -c "import typer; print(typer.__file__)"`（确认 3.10.11 / pytest 9.1.1 / 本地源码导入）
  - `bash scripts/test.sh`（失败，见下）
  - 等价命令（成功）：
    `export TERMINAL_WIDTH=3000 _TYPER_FORCE_DISABLE_TERMINAL=1 _TYPER_RUN_INSTALL_COMPLETION_TESTS=1 && venv/Scripts/python.exe -m pytest --cov --cov-report=term-missing -o console_output_style=progress --showlocals --numprocesses=auto`
  - 补充分支覆盖率：同上 + `--cov=typer --cov-branch`（临时在 pyproject `[tool.coverage.run]` 加 `branch=true`，测完还原）
- 关键输出：
  - 基线：**1488 passed, 15 skipped, 2 xfailed，0 failed，66.09s，总语句覆盖率 99%（15106 语句 / 177 缺口）**；
  - typer 主包 statement 覆盖率全部 100%——这个仓库的测试密度极高，补测试只能从**分支覆盖**和 vendored click 交互层找缺口；
  - warnings=0：`filterwarnings=["error"]` 把任何警告变成失败，这是基线里最严格的隐形约束。
- 失败尝试（3 个，全部定位到根因）：
  1. `bash scripts/test.sh` → `ModuleNotFoundError: annotated_doc`：脚本裸调 `pytest` 命中系统 Python 而非 venv。改用 `venv/Scripts/python.exe -m pytest` + 相同参数。
  2. 分支覆盖率 INTERNALERROR `Can't combine branch coverage data with statement data`：先怀疑 `coverage/` 里 452 个历史数据文件残留，`rm coverage/.coverage*`（glob 参数超限删不净）→ `find coverage -name ".coverage*" -delete` 清空后仍报错；再关 xdist 单进程跑（4 分 20 秒）仍报错 → 定位根因：pytest-cov 子进程钩子让测试内的 subprocess 按 pyproject（无 branch）写语句数据，与 CLI `--cov-branch` 的分支数据冲突。最终方案：临时给 `[tool.coverage.run]` 加 `branch = true`，一次通过，测后还原（`git diff` 确认干净）。
- 为什么这样做：任务书要求优先官方脚本；失败后保持"环境变量+参数逐字对齐"的等价替换，而不是自己发明一套 pytest 参数，这样基线和 CI 可比。
- 涉及文件：`scripts/test.sh`、`pyproject.toml`（临时改后还原）、`coverage/`（清理）、`artifacts/phase1/{test_full.log,test_branchcov.log,summary.txt}`、`BASELINE.md`。
- 可迁移知识：
  1. Windows 下跑 shell 脚本里的裸解释器命令，先确认 PATH 上是谁——`python -m pytest` 永远比 `pytest` 稳；
  2. coverage `parallel=true` 会在 `coverage/` 积数据文件，混合 branch/statement 模式跨次运行必炸，**切换模式前先清数据目录**；
  3. `--cov-branch` CLI 参数不会传播给 subprocess 覆盖（子进程读的是配置文件），要开分支覆盖请在配置文件里设 `branch=true`；
  4. 判定"环境正确"的最快办法：让目标包打印 `__file__`，确认导入的是工作区源码而非 site-packages。
- 我如何复现：见 BASELINE.md「官方测试命令」一节的命令块；分支覆盖率复现需先临时给 pyproject 加 `branch=true`。
- 下一步：阶段 2 按分支缺口清单补测试（`typer/testing.py:124-125`、`_completion_classes.py:83`、`_click/utils.py:366-372`、`core.py`/`cli.py` 部分分支）。

## 阶段 2：补全测试（覆盖率缺口）
- 开始/结束时间：2026-10-09 03:05 – 03:35
- 目标：只针对覆盖缺口补测试，禁止重写/碰现有测试。
- 我运行的命令：
  - `pytest --cov=typer --cov-branch --cov-report=term-missing`（定位缺口，方法见阶段 1 踩坑）
  - 目标测试：`pytest tests/test_result_repr.py tests/test_completion/test_bash_version.py tests/test_get_app_dir_paths.py tests/test_optional_enum_default.py -q`
  - 全量：官方等价命令（1488 → **1503 passed**，0 failed）
  - `ruff check --fix` + `ruff format`（新文件过 lint）
- 关键输出 / 覆盖率变化：
  | 文件 | 前 | 后 |
  |---|---|---|
  | `typer/testing.py` | 99%（124-125 缺） | **100%** |
  | `typer/_completion_classes.py` | 99%（83 行缺） | **100%** |
  | `typer/_click/utils.py` | 97%（45, 366-372 缺；8 个部分分支） | 语句缺口清零，部分分支 8→6 |
  | `typer/main.py` | 10 个部分分支 | 9（1458->exit 被枚举 None 测试覆盖） |
  | 全仓（官方口径） | 1488 passed / 177 语句缺 | **1503 passed / 168 语句缺** |
- 新增文件（4 个，共 15 个测试）：
  - `tests/test_result_repr.py`：`Result.__repr__` 成功态 `<Result okay>` 与异常态包含异常类名（typer.testing 公共行为，全仓此前从未调用过 repr）。
  - `tests/test_completion/test_bash_version.py`：`BashComplete._check_version` 对 bash<4.4 打印 stderr 警告、bash≥5 无输出、版本串不可解析时提示检测失败（文档"Shell completion is not supported for Bash versions older than 4.4"的行为）。
  - `tests/test_get_app_dir_paths.py`：`get_app_dir` 各平台目录布局（docstring 明文承诺的 roaming/LOCALAPPDATA/darwin/XDG 布局）+ `_posixify`。
  - `tests/test_optional_enum_default.py`：`Optional[Enum]` 选项默认 None 时保持 None、传值时正确转枚举、非法值报错。
- 失败尝试：
  1. 首版 `test_get_app_dir_force_posix` 在真 Windows 上断言失败——**发现 vendored 代码里 `if WIN:` 分支先于 `force_posix` 判断提前 return，即 Windows 上 force_posix 参数实际不可达**（与上游 click 8.3.1 一致的结构）。判定为"上游设计如此"而非 typer bug：修正测试为 patch `WIN=False` 覆盖 posix 分支，另保留真实 Windows 行为断言（roaming 路径）。
  2. 3 个断言用 `str(Path.home()/".x")` 比较失败：Windows 下 `expanduser("~/.x")` 产生混合分隔符 `C:\Users\L/.x`。改用 `Path(a) == Path(b)` 归一化比较。**教训：Windows 上断言路径永远用 Path 比较，别用字符串。**
  3. 分支覆盖测量第二次踩 combine 坑（忘开 `branch=true`），重做一次。
- 为什么选这些缺口：typer 主包语句覆盖已 100%，值得补的只剩三类——(a) typer 自身代码的分支缺口（testing/completion）；(b) vendored click 里 docstring 明文承诺但 Windows 跑不到的跨平台行为（get_app_dir）；(c) 数据转换边界（枚举 None）。跳过的：`_compat.py:509-515`（非 Windows 平台的 `else:` 分支，Windows 上物理不可达，伪造覆盖无意义）、`_termui_impl.py` 进度条终端交互（需要真 TTY）、import 期模块级代码（`rich_utils.py:83`）。
- 如何读 coverage：先 `--cov-report=term-missing` 拿语句缺口；语句饱和后加 `--cov-branch` 看 `a->b` 部分分支（a 行的某条跳转路径从未发生）；对每个缺口先读源码判断"这是行为分支还是死代码/平台分支"，只给行为分支写测试。
- 涉及文件：新增 4 个测试文件；`artifacts/phase2/{test_full_after.log,test_branchcov_after.log}`。
- 可迁移知识：
  1. 语句覆盖 100% ≠ 分支覆盖 100%，成熟项目要靠 `--cov-branch` 找剩余价值；
  2. 跨平台库在单一平台上必有"物理不可达"分支（如 WIN 常量提前 return），正确做法是 monkeypatch 模块常量模拟平台 + 断言文档承诺的布局，而不是伪造；
  3. 测试写完必须 `ruff check`（本项目 isort 把 `typer` 当第三方包排序、强制 `X | None` 语法）；
  4. 断言路径用 `Path` 对象比较避免分隔符陷阱。
- 我如何复现：`venv/Scripts/python.exe -m pytest tests/test_result_repr.py tests/test_completion/test_bash_version.py tests/test_get_app_dir_paths.py tests/test_optional_enum_default.py -v`；覆盖率对比看 `artifacts/phase1/test_branchcov.log` vs `artifacts/phase2/test_branchcov_after.log`。
- 下一步：阶段 3 从 GitHub Issues 找 1-3 个可复现 bug，先写复现测试再修。

## 阶段 3：测试驱动修 bug（结论：无合格 issue，转为修复验证）
- 开始/结束时间：2026-10-09 03:35 – 03:55
- 目标：挑 1-3 个开放 bug issue，先写复现测试再修复。
- 我运行的命令（寻issue 的 4 种方式）：
  1. `gh issue list --repo fastapi/typer --label bug --state open` → **空**
  2. `gh label list` + 按各标签（investigate/confirmed/good first issue/help wanted）逐一查开放 issue → 全空
  3. `gh api search/issues?q=repo:fastapi/typer+state:open+type:issue` → **总数 1，仅 #678 Roadmap**
  4. 转而验证"最近关闭的 bug 是否修干净"（修复不完整 = 真 bug）
- 关键输出：typer 上游 triage 极快，**当前零个开放 bug issue**。对 3 个最近关闭的 bug 在 0.27.3 上跑复现（`artifacts/phase3/repro_closed_bugs.log`）：
  | issue | 现象 | 0.27.3 验证结果 | 树内回归测试 |
  |---|---|---|---|
  | #1787 envvar 在 Option 上失效（0.26.0 回归） | `ME=bar` 不被读取 | **已修复**（读到 envvar，exit 0） | `tests/test_others.py:328` `test_option_envvar` |
  | #1353 default_factory 返回空列表报错 | 空 list 工厂崩 | **已修复**（`items=[]`） | `tests/test_others.py:320` |
  | #1156 Argument(metavar) 面板与 usage 不一致 | 两处显示不同 | **已修复**（usage `{MY_ARG}` 与面板一致） | `tests/test_rich_utils.py` 等 metavar 用例 |
- 另一个自查发现（阶段 2 顺带）：`get_app_dir(force_posix=True)` 在 Windows 上不可达（`if WIN:` 提前 return）。核对 docstring：只为 Mac/Unix 列了 POSIX 变体、未承诺 Windows；且结构与上游 click 8.3.1 一致（vendored 头注释可证）。**定性：上游怪癖，文档行为自洽，不修**（改它反而会偏离 click 语义）。
- 失败尝试：`git fetch upstream` 与 WebFetch raw.githubusercontent 均被网络重置（ECONNRESET），但 `gh api` 正常，足以完成 issue 调查。
- 为什么这样做：任务书要求"只修有测试证据的问题"。在零开放 bug 的前提下，任何"修 bug"都只能是无依据的改动；把调查过程和修复验证做实，是本阶段能交付的最大真实价值。
- 涉及文件：`artifacts/phase3/{gh_evidence.txt,repro_closed_bugs.log}`（无源码改动，无 fix commit——如实记录）。
- 可迁移知识：
  1. 活跃上游（fastapi 系）的 issue 池常被清空，贡献 bug fix 的窗口期很短；`gh api search/issues` 是绕过标签漏标的最终确认手段；
  2. "验证已关闭 bug 是否修干净"是接手旧代码库时建立信心的手段：复现脚本 + 树内测试对照；
  3. 判定"是不是 bug"的标准是"文档承诺 vs 实际行为"，而不是直觉——force_posix 看着像 bug，但 docstring 没承诺 Windows 行为。
- 我如何复现：`cat artifacts/phase3/gh_evidence.txt`；复现脚本思路见 `repro_closed_bugs.log`（envvar/default_factory/metavar 三个最小用例）。
- 下一步：阶段 4 保守重构（tests/ 内部去重、统一风格，不动核心源码）。

## 阶段 4：重构（保守模式）
- 开始/结束时间：2026-10-09 03:55 – 04:10
- 目标：仅消除 tests/ 内重复，统一断言风格；核心源码零改动。
- 我运行的命令：
  - `pytest tests/test_rich_markup_mode.py -q`（重构后目标文件：28 passed + 2 xfailed，与重构前完全一致）
  - 官方全量：**1503 passed, 15 skipped, 2 xfailed**（与重构前一致，`artifacts/phase4/test_full_after.log`）
  - `ruff check` + `ruff format --check` 通过
- 关键输出：`tests/test_rich_markup_mode.py` 净变化 **+26/-65**。5 个测试（`test_markup_mode_newline_pr815/issue447/mixed`、`test_markup_mode_bullets_single/double_newline`）各自复制了一段 13 行的"跑命令→取 help→定位首行→比对行块"断言，提取为文件内辅助函数 `_assert_markup_mode_help(app, mode, help_first_line, lines)`。唯一语义微调：`result_lines.index("First line")`（精确匹配）统一为子串匹配 `[i for i,row in enumerate(...) if marker in row][0]`——对这 5 个用例等价（原精确匹配能命中的行，子串匹配命中同一行）。
- 为什么值得消除：同一断言块 5 份拷贝，新增 markup mode 用例时改一处漏四处；提取后每个测试只剩"app 定义 + 期望行列表"，测试意图更清晰。
- 哪些"看起来能重构"但**没有动**（及理由）：
  1. 298 个测试文件各自的模块级 `runner = CliRunner()`——这是上游的显式风格（每文件自包含、可独立阅读），改成 conftest fixture 会触碰全部测试文件，与上游合并必冲突；
  2. `tests/test_tutorial/**` 里大量结构相似的 tutorial 测试——它们逐个镜像 `docs_src/` 文件，重复是"文档即测试"模式的本质，合并会破坏一一对应关系；
  3. `typer/params.py` 中 Argument/Option 各约 1800 行的参数定义"重复"——那是公共 API 的 docstring（文档源），不是代码重复；
  4. vendored `typer/_click/**` 里与 click 相似的结构——保持与上游可 diff 是 vendoring 的前提。
- 失败尝试：无（本步骤一次通过）。
- 涉及文件：`tests/test_rich_markup_mode.py`、`artifacts/phase4/test_full_after.log`。
- 可迁移知识：
  1. 重构测试的安全网是"重构前后测试结果逐字相同"（本例 28 passed + 2 xfailed → 相同）；
  2. 给活跃上游贡献时，重构的合并冲突成本 ≈ 重构收益 × 未来 diff 概率，只动"纯新增辅助函数 + 局部调用点"这种低冲突面；
  3. "重复"要区分三种：意外复制（值得消除）、模式性重复（每文件 runner，是风格）、本质性重复（tutorial 镜像，是设计）。
- 我如何复现：`git show <本次commit>` 看 diff；`pytest tests/test_rich_markup_mode.py -v` 看 30 个用例全部按原名通过。
- 下一步：阶段 5 补公开 API docstring 与 CONTRIBUTING 新人指南。

## 阶段 5：文档
- 开始/结束时间：2026-10-09 04:10 – 04:45
- 目标：公开 API 补 Google 风格 docstring；新增 CONTRIBUTING.md 新人指南；增量、不改官方文档风格。
- 我运行的命令：
  - AST 扫描找缺 docstring 的公开对象（`ast.get_docstring` 遍历 `typer/{__init__,main,models,params,utils,testing,completion,cli}.py` 的顶层类/函数）
  - `ruff check typer tests docs_src scripts` + `ruff format --check` → **全部通过**
  - `mypy typer` → 3 个错误（`colorama` stubs 缺失 ×1、vendored `_termui_impl.py` redundant-cast ×2）
  - `ty check typer` → 16 个诊断
  - 全量测试：**1503 passed, 15 skipped, 2 xfailed**（`artifacts/phase5/test_full.log`）
- 关键输出：mypy 3 错误与 ty 16 诊断经 `git stash` 对照验证，**在未改动的原树上完全相同**——全部为存量问题（colorama 类型存根是本机环境差异；redundant-cast 与 contextmanager 风格告警在 vendored click 代码里，属 ty/mypy 版本与 CI 固定版本的漂移）。本次改动零新增 lint 问题。
- 改动内容：
  1. `typer/models.py`：8 个数据类补一句话 docstring（CommandInfo/TyperInfo/ParameterInfo/OptionInfo/ArgumentInfo/ParamMeta/DeveloperExceptionConfig/TyperPath），说明其在管线中的角色；
  2. `typer/utils.py`：4 个用户可见异常类 + `get_params_from_function` / `parse_boolean_env_var`（后者用 Args/Returns 段）；
  3. `typer/main.py`：22 个管线函数补简洁 docstring（except_hook、get_command/get_group、solve_*、get_click_type/get_click_param、convertor 工厂等）；
  4. 新增根级 `CONTRIBUTING.md`：GitHub 自动展示；链接官方指南 + 基于 tonight 实操的"新人上手补充指南"（环境搭建、Windows 下 pytest 陷阱、三个测试环境变量含义、目录导览、测试风格、分支覆盖率技巧、提交前检查单）。
- 失败尝试：
  1. 给 `params.py` 的 Option 实现加 docstring 时两次 Edit 贴错内容（一次误删 assert 消息、一次误加 type: ignore）——**都立即用反向 Edit 恢复并 `git diff` 验证归零**。随后核实：缺 docstring 的只是两个 `@overload` 变体，实现本身有完整 docstring，params.py 根本无需改动；
  2. 结论：长匹配串 Edit 有粘贴错位风险，改错后必须立即用 diff 验证。
- 如何判断"公开 API"：以 `typer/__init__.py` 的 re-export 为准（用户直接 `import typer` 可见），加上用户会直接读到其报错信息的异常类；`cli.py`/`completion.py` 的内部回调和 `@overload` 存根不算（后者按惯例不带 docstring）。
- 如何写可维护的 docstring：一句话说"它在管线中的角色"而不是重复函数名；只在参数含义非显然时写 Args/Returns；与相邻代码的详略程度保持一致（内部函数一句话，面向用户的加示例——本仓库后者已由 `Doc()` 注解承担）。
- 涉及文件：`typer/main.py`、`typer/models.py`、`typer/utils.py`、`CONTRIBUTING.md`（新增）、`artifacts/phase5/test_full.log`。
- 可迁移知识：
  1. 验证"不是我引入的 lint 错误"的标准手法：`git stash` 改动 → 重跑 → 对照 → `git stash pop`；
  2. docstring 改动也要跑全量测试与 lint（CI 对文档型 PR 同样跑检查）；
  3. 仓库没有根级 CONTRIBUTING.md 时，GitHub 新人第一站是空的——建一个链接官方指南 + 实操补充的文件是零冲突的增量贡献。
- 我如何复现：`python -c "import typer.utils; print(typer.utils.get_params_from_function.__doc__[:60])"`；CONTRIBUTING.md 按章节从上到下执行即可复现整个环境搭建流程。
- 下一步：阶段 6 收尾报告 REPORT.md 与 PR_DRAFT.md。

## 阶段 6：收尾报告
- 开始/结束时间：2026-10-09 04:45 – 05:00
- 目标：REPORT.md（耗时/覆盖率对比/issue 结果/遗留问题/合规声明）+ PR_DRAFT.md（草稿，不提交）。
- 我运行的命令：从 `artifacts/phase{1,2,5}/` 留档日志提取分模块覆盖率对比；`git log --oneline` 汇总各阶段 commit。
- 关键输出：见 REPORT.md §2 的前后对比表与 §0 的合规声明。
- 失败尝试：无。
- 为什么这样做：报告里所有数字都从留档日志原样提取（而非凭记忆），保证"第二天照着学"时每个数字可复核。
- 涉及文件：REPORT.md、PR_DRAFT.md。
- 可迁移知识：收尾报告的核心是"可复核性"——每个结论都能指到一个 artifact 文件或一条可重跑的命令。
- 我如何复现：按 REPORT.md §7 的命令清单逐条执行。
- 下一步：无（任务收尾）。给仓库主人的后续建议见 REPORT.md §6。