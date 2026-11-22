# Specify

Specify 是一个以 Markdown Contract 为正式规范、以 change 驱动迭代的命令行工具。项目配置、正式 spec 和 change 文件都保存在仓库目录中；不需要数据库或外部 JSON 状态库。

[在线查看 Specify 项目图谱（GitHub Pages）](https://lerr1uqs.github.io/specify/visualized/index.html)。可以展开 spec 和 Contract，查看 change 如何通过 delta 更新规范，以及同步后的版本历史。

## 环境要求

- Python 3.11 或更新版本
- [uv](https://docs.astral.sh/uv/)

## 安装与启动

直接从 GitHub 安装 Specify CLI：

```bash
uv tool install git+https://github.com/Lerr1uqs/specify.git
specify --help
```

如果在本仓库中开发，运行 `uv sync`，并用 `uv run specify` 代替下文的 `specify`。`uv tool install` 会将 CLI 安装到独立环境；如果安装后找不到 `specify` 命令，运行 `uv tool update-shell` 并重新打开终端。

### 安装 AI 工作流 skill

使用 Node.js 22.20 或更新版本。在要使用 Specify 的项目中，一次安装全部工作流 skill：

```bash
npx skills add Lerr1uqs/specify --skill '*'
```

这会安装探索、提案、实施和归档四个专用 skill，以及 `specify-workflow` CLI 参考。只想查阅 CLI 用法时，可以单独安装参考 skill：

```bash
npx skills add Lerr1uqs/specify --skill specify-workflow
```

只给 Codex 安装时，在命令末尾加 `--agent codex`。这些 skill 提供 agent 操作指引，Specify CLI 的安装见上文。

阶段划分借鉴了 [OpenSpec 的开源 skills](https://github.com/Fission-AI/OpenSpec/tree/main/skills)；具体步骤按 Specify 的 Contract、基线、tasks 和同步回执协议编写。

初始化一个 Specify 项目：

```bash
specify init ./my-project
```

初始化会生成 `spec/config.yaml`、`spec/specs/`、change 目录、索引，以及 `spec/template/` 下的内置写作模板。重新初始化会保留已存在的模板文件。后续命令在项目目录中运行即可；默认使用当前工作目录。

## 创建和编写 spec

配置中的每个 `specTypes` 可以通过 `template` 指定写作模板。默认提供 `requirement`、`capability`、`component`、`architecture` 和 `rule` 类型；新增功能使用 `feat` change kind，并通过 delta 更新相应的正式 spec。

```bash
cd ./my-project
specify create requirement password-login
```

命令会把配置引用的模板复制到 `spec/specs/<type>/<id>/spec.md`。需求模板示范 `WHEN / THEN / MUST / SHOULD / MAY` 等表述，组件模板介绍职责、边界和依赖，架构模板提供树形结构示例。模板提供写作指引；`validate` 检查 Markdown 与 Contract 结构，不会自动判定业务语义是否完整。

Contract 标题格式为 `## [<contract-id>] <标题>`。方括号中的 kebab-case ID 是稳定标识；类型、spec ID 和 Contract ID 组合成完整引用，例如 `capability:user-auth:password-login`。

创建和更新 spec 时可以设置一行简介。简介保存在 `spec.md` 同级的 `meta-data.yaml`，命令会同步刷新 `spec/spec-index.md`。`list --spec` 默认用缩进文本按 type 展示 ID、相对项目根的路径和简介，`--human` 切换为 Rich 树，`specify --json list --spec` 返回完整字段。

```bash
specify create capability user-auth --description "登录、认证与会话管理"
specify update capability:user-auth --description "密码登录、通行密钥与会话过期"
specify --root ./my-project list --spec --human
```

## Change 工作流

创建影响正式 spec 的 change，编辑生成的 `change.md`、`tasks.md` 和 delta：

```bash
specify change create feat add-password-login \
  --affect capability:user-auth:modify
```

对于修改、删除或重命名已有 Contract 的 delta，完成 delta 后显式捕获正文基线。新增 Contract 不需要基线。

```bash
specify change baseline add-password-login
specify change verify add-password-login
```

实现并完成 tasks 后，将 change 标记为 implemented，再同步到正式 spec，最后归档：

```bash
specify change implement add-password-login
specify change sync add-password-login
specify change archive add-password-login
```

如果 sync 检测到基线变化，会拒绝整次同步。阅读最新 Contract、调整 delta，并重新运行 `change baseline` 后再验证和同步。成功 sync 后 delta 被回执固定；后续语义调整应另建 change。Archive 只归档已同步 change，不重放 delta。

不影响正式 Contract 的 bugfix 可以不创建 delta：`change create` 不传 `--affect` 时会记录 `specImpact.kind: none`。

## Contract 历史

成功同步的 Contract 变更按完整引用保存在 `spec/.history/contracts/<type>/<spec-id>/<contract-id>.jsonl`。同一个引用删除后重新添加，会沿用原文件并继续递增 `idx`。

```bash
specify history capability:user-auth:session-expiry
specify history capability:user-auth:session-expiry --limit 5 --human
specify history capability:user-auth:session-expiry --include-removed --csv > history.csv
specify history capability:user-auth:session-expiry --diff 1 2 --human
```

默认以 JSON 返回当前生命周期的最新版本。`--limit` 查询最近几条记录，`--include-removed` 展开以前的生命周期和删除记录，`--diff` 按 `idx` 比较标题和正文，支持跨生命周期比较。用 `--human` 在终端浏览，用 `--csv` 导出记录。

升级已有项目时运行 `specify history --backfill`，把还没有历史的 Contract 以当前正文补记为 `add`。补录日期为执行时的日期，同步时也会为首次被修改或删除的已有 Contract 自动补一条起始记录。

## 常用命令

```bash
specify validate
specify list
specify list --human
specify list --spec --human
specify status --human
specify show capability:user-auth
specify index build
```

`list` 默认输出活跃 change 的 JSON，包括 kind、生命周期状态和 tasks 的已完成/总数。`list --human` 用 Rich 树按状态和 kind 分组展示。`list --change` 显式选择 change，`list --spec` 用缩进文本列出正式 spec，`--type` 仅与 `--spec` 搭配。`status` 默认输出整个项目的 JSON，`status --human` 同时显示 spec 和 change。`--human` 与全局 `--json` 互斥。`validate` 可用 `--specs`、`--changes` 或 `--archived` 限定检查范围。

查看本仓库示例项目：

```bash
uv run specify --root example_specs list --human
uv run specify --root example_specs list --spec --human
uv run specify --root example_specs status --human
uv run specify --root example_specs history capability:user-auth:session-expiry --limit 3 --human
uv run specify --root example_specs history capability:user-auth:session-expiry --diff 1 2 --human
```

## 开发检查

```bash
uv run pytest -q
uv run ruff check src/specify tests
uv run ruff format --check src/specify tests
```

`example_specs/` 提供 spec、模板、change delta、基线和归档文件的示例。
