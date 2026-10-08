# Typer 仓库架构指南（ARCHITECTURE.md）

> 基于本地仓库 `typer 0.27.3`（上游 commit `b15210b`）源码通读整理。
> 目标读者：想给 typer 贡献代码 / 学习 CLI 框架设计的新人。

## 1. 一句话总览

Typer 是"用 Python 类型注解自动生成 CLI 参数"的声明式框架：
**用户函数签名 →（反射 + `Annotated` 元数据）→ 参数模型 → vendored Click 命令树 → 解析 argv → 类型转换 → 调用用户函数**。

## 2. Typer 与 Click 的关系（重点，0.27 起有重大变化）

- 早期版本：typer 依赖 PyPI 上的 `click` 包，在其上做薄封装。
- **现在（0.27.x）**：click 的源码被 **vendored（内嵌复制并适配）** 到 `typer/_click/`，取自 Click 8.3.1（见 `typer/_click/__init__.py` 的模块 docstring）。typer 不再依赖外部 click。
- 这样做的动机：typer 需要修改 click 的内部行为（帮助文本渲染、错误信息、参数处理），又不想 fork 整个 click 项目或受上游发布节奏约束。
- `typer/__init__.py` 把 `_click` 里的 `echo/secho/prompt/confirm/style/progressbar/getchar` 等终端工具函数直接 re-export 为公共 API——用户代码 `typer.echo(...)` 实际执行的是 vendored click 的实现。
- 兼容层亮点：`_click/_compat.py`（Windows 控制台适配）、`_click/_winconsole.py`（Windows ANSI/UTF-8 处理）、`_click/_termui_impl.py`（进度条底层）。

**给贡献者的影响**：修 bug 时要分清问题出在 `typer/*.py`（typer 逻辑）还是 `typer/_click/*.py`（vendored click）。后者改动要谨慎，尽量保持与上游 click 可比对。

## 3. 核心数据流（从 `@app.command()` 到程序运行）

### 3.1 注册阶段（用户代码执行时）

```
app = typer.Typer()                      # main.Typer 实例，保存元信息到 self.info (TyperInfo)
@app.command()                           # main.Typer.command() 装饰器
def create(name: str): ...               # → CommandInfo(callback=...) 存入 app.registered_commands

app.add_typer(sub_app, name="sub")       # → TyperInfo(sub_app) 存入 app.registered_groups
```

- `main.Typer.__init__` 的每个参数都是 `Annotated[T, Doc("...")] = Default(...)` 风格：
  `Default()` 返回 `DefaultPlaceholder`（models.py），用于区分"用户显式设置"和"用了默认值"——这是后面 help 优先级合并的基础。
- `models.py` 的 `CommandInfo / TyperInfo / ParameterInfo / OptionInfo / ArgumentInfo` 是纯数据类，`Option()/Argument()` 本质是构造 `OptionInfo/ArgumentInfo`。

### 3.2 编译阶段（`app()` 被调用 / 测试 invoke 时）

入口：`main.Typer.__call__`（main.py:1133）→ `get_command(app)`（main.py:1173）

```
Typer.__call__
 ├─ 安装全局 excepthook（pretty exceptions，见 §3.4）
 └─ get_command(app)
     ├─ 有 callback / 子组 / 多个命令 → get_group_from_info() → TyperGroup（core.py）
     ├─ 只有一个命令且无 callback   → get_command_from_info() → TyperCommand
     └─ _add_completion 时附加 --install-completion/--show-completion 参数
```

`get_command_from_info()`（main.py:1392）内部：

1. `solve_typer_info_defaults()` / `solve_typer_info_help()`（main.py:1211-1280）：
   按 6 级优先级合并 help（`add_typer(help=)` > `@subapp.callback()` > `typer.Typer(help=)` > 各自 docstring）。
2. `get_params_convertors_ctx_param_name_from_function(callback)`（main.py:1373）
   → 调 `utils.get_params_from_function()`（utils.py:107）：
   - `inspect.signature()` + `get_type_hints()` 解析函数签名；
   - 拆 `Annotated[T, Option(...)]`：`_split_annotation_from_typer_annotations()`；
   - 禁止混合风格并抛 `MixedAnnotatedAndDefaultStyleError` / `AnnotatedParamWithDefaultValueError` / `MultipleTyperAnnotationsError` / `DefaultFactoryAndDefaultValueError`（都在 utils.py）；
   - 产出 `dict[str, ParamMeta(name, default, annotation)]`。
3. `get_click_param(param_meta)`（main.py:1632）：`ParamMeta` → `TyperOption` / `TyperArgument`（core.py，继承 `_click.core.Parameter`）。
   Python 类型 → click 类型的映射在 `get_click_type()`（main.py:1530）：Enum→Choice、bool→Bool、list/set/tuple→multiple、Path→TyperPath、UUID 等。
4. `get_callback()`（main.py:1496）把用户函数包成 `wrapper(**kwargs)`：运行时对 list/tuple/enum/path 参数应用 convertor 再调用原函数。

### 3.3 运行阶段（解析 argv 并回调）

- `TyperCommand.main()` / `TyperGroup.main()`（core.py）覆写 vendored click 的入口，
  处理 rich 格式的 Usage/Error 输出（`_main()`，core.py:158）。
- `TyperGroup.resolve_command()` / `suggest_commands`：命令打错时给出"你是不是想输入 …"建议。
- 解析完成后由 vendored click 的 parser（`_click/parser.py`）分派到各 `TyperOption.add_to_parser` 注册的回调，最终 `get_callback` 的 wrapper 以 kwargs 调用用户函数。

### 3.4 漂亮的异常（pretty exceptions）

`main.Typer.__call__` 安装 `except_hook`（main.py:61）：用户函数抛异常时，
- 有 rich：`rich_utils.get_traceback()` 生成精简 traceback（隐藏 typer/_click 内部帧，显示用户代码局部变量）；
- 无 rich：手工过滤 `TracebackException` 的栈帧。
- 环境变量 `TYPER_STANDARD_TRACEBACK` 可关闭。

## 4. 目录导览（按重要性排序）

| 路径 | 行数 | 职责 |
|---|---|---|
| `typer/main.py` | 2022 | `Typer` 类、命令注册、`get_command*` 编译管线、`get_click_type` 类型映射、except_hook |
| `typer/core.py` | 1221 | `TyperCommand` / `TyperGroup` / `TyperOption` / `TyperArgument`（对 vendored click 的四个核心覆写） |
| `typer/params.py` | 1833 | `Option()` / `Argument()` 全部参数定义（几乎全是 docstring） |
| `typer/models.py` | 743 | `TyperInfo` / `CommandInfo` / `ParameterInfo` 数据类、文件类型、`DefaultPlaceholder` |
| `typer/_click/` | ~4700 | vendored Click 8.3.1（core/termui/types/parser/shell_completion…） |
| `typer/rich_utils.py` | 776 | rich 控制台/帮助/错误输出（`rich_markup_mode` 支持） |
| `typer/testing.py` | 342 | `CliRunner` / `Result`：测试用 CLI 调用器（捕获 stdout/stderr/exit_code） |
| `typer/completion.py` + `_completion_classes.py` + `_completion_shared.py` | ~630 | shell 补全：安装、卸载、每 shell（bash/zsh/fish/powershell）的补全脚本生成 |
| `typer/cli.py` | 317 | `typer` 命令本身（`typer run file.py`、`typer docs`、补全管理） |
| `typer/utils.py` | 197 | `get_params_from_function`（签名→参数模型）+ 4 个风格混用异常类 |
| `typer/_typing.py` | 73 | typing 兼容小工具（`is_union`/`literal_values` 等），coverage omit |

## 5. 测试结构

- `tests/conftest.py`：唯一 fixture `app_dir`（把 `typer.get_app_dir` 重定向到 tmp_path）。
- `tests/utils.py`：辅助（如 `requires_completion_permission` 跳过标记）。
- 298 个测试文件 / **965 个测试函数**，组织方式：
  - `tests/test_tutorial/**`：**镜像 `docs_src/` 教程示例**（每个文档示例文件一个测试），量大，保证文档可运行；
  - 功能专题文件：`test_rich_markup_mode.py`、`test_annotated.py`、`test_completion/`、`test_win_console.py`、`test_types.py`…
- **断言风格**：模块级 `runner = CliRunner()`；`result = runner.invoke(app, [...])`；
  `assert result.exit_code == 0` / `assert "xxx" in result.stdout`；
  错误路径用 `runner.invoke(app, input=...)` 检查非零退出码 + stderr 内容。
- pytest 配置（pyproject.toml `[tool.pytest.ini_options]`）：`filterwarnings = ["error"]`（警告即失败！）、`--strict-markers`、`strict_xfail`。
- 覆盖率配置：source = `typer` + `tests` + `docs_src`，omit `typer/_typing.py`；`exclude_lines` 含 `@overload` / `if TYPE_CHECKING:` / `pragma: no cover`。

## 6. 官方工作流（scripts/）

```bash
bash scripts/test.sh        # 官方测试：pytest --cov --cov-report=term-missing -n auto
                            # 环境变量: TERMINAL_WIDTH=3000, _TYPER_FORCE_DISABLE_TERMINAL=1,
                            #          _TYPER_RUN_INSTALL_COMPLETION_TESTS=1
bash scripts/lint.sh        # mypy typer && ty check typer && ruff check/format
bash scripts/test-cov-html.sh  # HTML 覆盖率报告
```

依赖组（pyproject `[dependency-groups]`）：`tests`（pytest≥9、coverage、mypy、ty、ruff、xdist、sugar）、`docs`、`github-actions`。
Python 要求 **>=3.10**。运行时依赖：`shellingham`、`rich>=13.8`、`annotated-doc`、`colorama`(Windows)。

CI（`.github/workflows/test.yml`）：pytest 矩阵（3 个 OS × 多 Python 版本，含 nightly）、coverage 合并、smokeshow。

## 7. 文档体系

- `docs/`（mkdocs，`mkdocs.yml` + `mkdocs.env.yml`）：教程页几乎全部引用 `docs_src/` 的示例代码片段（动态 include），所以 **改文档示例 = 改 `docs_src/*.py`，其正确性由 `tests/test_tutorial/**` 保证**。
- `docs/release-notes.md`：每版变更记录。
- 贡献入口：仓库根无 CONTRIBUTING.md，实际指引在 https://typer.tiangolo.com/contribute/ （docs/en/contribute.md？本地 docs 下未包含，见遗留说明）。

## 8. 推荐阅读顺序（新人上手路径）

1. `README.md` → `docs/tutorial/first-stsps` 系列（跑 `docs_src/first_steps/` 例子）；
2. `typer/main.py` 的 `Typer.command()` + `Typer.__call__` + `get_command()`（注册与编译主干）；
3. `typer/utils.py::get_params_from_function`（签名解析——typer 的灵魂）；
4. `typer/core.py` 的 `TyperCommand` / `TyperGroup`（与 click 的接缝）;
5. `typer/testing.py` + 任一 `tests/test_tutorial/**`（学会怎么测）；
6. 需要时再深入 `typer/_click/`、`completion` 三件套、`rich_utils.py`。

## 9. 关键设计模式速记

- **DefaultPlaceholder 哨兵**：区分"默认值"与"未设置"，支撑多层 help 合并优先级。
- **Annotated 元数据驱动**：参数配置既可 `Annotated[str, Option(...)]` 也可默认值风格 `= Option(...)`，`get_params_from_function` 统一归一化并校验冲突。
- **vendored 依赖**：`typer/_click` 整树复制 + 按需魔改，公共 API 面向用户保持稳定。
- **文档即测试**：docs_src 示例被 tutorial 测试逐个执行，防文档腐化。
