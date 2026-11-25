# Specify

Specify 是一个以 Markdown Contract 为正式规范、以 change 驱动迭代的命令行工具。项目配置、正式 spec 和 change 文件都保存在仓库目录中；不需要数据库或外部 JSON 状态库。

[在线查看项目图谱示例（GitHub Pages）](https://lerr1uqs.github.io/specify/visualized/index.html)。这是静态示例；要查看手头项目，请运行 `specify web`。

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

技能包包含 [`specify` 主技能](skills/specify/SKILL.md)、探索、提案、实施、审查和归档专用 skill，以及 `specify-workflow` CLI 参考。初次接触 Specify 可从主技能了解概念、基本命令和各技能的入口。只想查阅 CLI 用法时，可以单独安装参考 skill：

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

## 在浏览器中 Review

在包含 `spec/config.yaml` 的项目根目录运行：

```bash
specify web
```

从其他目录启动时，可以用 `specify --root ./my-project web` 指定项目。命令会尝试打开默认浏览器，并在终端打印本机地址。浏览器没有自动打开时，复制这个地址即可。试用本仓库示例：

```bash
uv run specify --root example_specs web
```

- **正式 Spec**：按 type 浏览当前规范，点击 Spec 查看简介和 Contract 正文。
- **Contract 引用**：悬停或聚焦引用可预览当前正式正文，点击跳到具体 Contract。
- **Spec 图**：顶部独立视图，展示所有正式 Spec 和它们之间的实际引用。悬停节点高亮相邻连线，并显示完整的 `type:spec:contract` 引用。支持点击节点打开 Spec、拖动平移、滚轮缩放和筛选孤立节点。
- **查找栏**：标题栏右侧的查找栏像 `rg` 一样搜索 Contract 的 ID、标题和正文；命中后左栏只保留命中 Contract 所属的 Spec，右侧只显示命中的 Contract 并高亮关键词。支持区分大小写（`Aa`）、全字匹配（`wd`）、正则（`.*`）和按 type 限定范围；`‹ ›` 或 Enter / Shift+Enter 在命中处之间移动，按 `/` 聚焦，Esc 清空并退出搜索。
- **图表**：Contract 正文中语言标记为 `pele` 或 `mermaid` 的代码围栏会渲染为 [Pele](https://pele.run) 图表，源码保留在「查看图表源码」中。Pele 以 MIT 许可证内置，不依赖外部 CDN。
- **Changes**：左侧 Change 通过曲线连到右侧各个 Spec；每个 Spec 用树形折线展开到 Contract。点击 Contract 查看逐行 diff，或用「展开全部」查看当前 Change 的所有差异。点击 Spec 名称可在修改列表旁边打开正式正文，此时 Change 根节点和连线让出空间，收起正文即可恢复影响树。
- **待拆解需求**：`proposed` 详情在可滚动的正文框中渲染 `change.md`。进入 `processing` 后可以查看任务进度、影响范围和 diff。
- **优先级**：左栏在各状态分组内按 P0 到 P4 排序，同级保留原顺序。选择「P2 及以上」可查看 P0、P1 和 P2。色块随档位依次使用红、蓝、紫、绿、黄。
- **时间与任务进度**：Change 标题下方显示已有的创建、更新、同步和归档时间，保留原始时区。任务进度与变更说明一同展示，可直接查看完成数、总数和任务清单。
- **差异来源**：未同步的 change 按捕获的基线正文预览。已同步的 change 比较当次同步前后的历史快照。当草稿基线或同步结果落后于当前 Contract 时，标题栏会标出「已落后当前 Spec」。缺少匹配的历史正文时，页面显示 delta 声明。
- **查看当前正文**：基线过期时，点击提示中的 Contract 引用，弹窗会显示当前正式 Contract 的标题与正文。逐行 diff 保留在变更详情中。

Web Review 以只读方式监听本机。保存 Markdown 后，前台页面会自动更新并恢复展开项和阅读位置。在启动命令的终端按 `Ctrl+C` 停止。

在示例项目的 **Changes** 中打开 `extend-audit-retention-to-60-days`，展开「恢复审计留存周期」，可同时查看提案的 30 → 60 天 diff 和当前正式规范的 90 天正文。更多用例见 [示例项目 README](example_specs/README.md)。

## 创建和编写 spec

配置中的每个 `specTypes` 可以通过 `template` 指定写作模板。默认提供 `requirement`、`capability`、`component`、`architecture`、`rule` 和 `test` 类型；新增功能使用 `feat` change kind，并通过 delta 更新相应的正式 spec。

```bash
cd ./my-project
specify create requirement password-login
```

命令会把配置引用的模板复制到 `spec/specs/<type>/<id>/spec.md`。需求模板示范 `WHEN / THEN / MUST / SHOULD / MAY` 等表述，组件模板介绍职责、边界和依赖，架构模板提供树形结构示例。模板提供写作指引；`validate` 检查 Markdown 与 Contract 结构，不会自动判定业务语义是否完整。

Contract 标题格式为 `## [<contract-id>] <标题>`。方括号中的 kebab-case ID 是稳定标识；类型、spec ID 和 Contract ID 组合成完整引用，例如 `capability:user-auth:password-login`。

在 Contract 的普通 Markdown 正文里写 `@[rule:recovery-policy:challenge-expiry]`，可引用另一条 Contract。行内代码、围栏代码、HTML 注释、普通 Markdown 链接的标签及转义写法 `\@[...]` 保持字面内容。标题重命名保留 ID，因此引用地址不变。要移动 Spec 或更换 ID，在同一个 Change 里显式更新引用来源。

`validate --specs` 检查当前正式引用。`change verify` 和 `change sync` 检查同一次 Change 所有 delta 合并后的正式结果。删除目标前可在同一个 Change 中移除或改写指向它的引用，悬挂引用会在落盘前被拦截，并报告来源和目标。

`test` 类型把每个必须通过的验收场景写成一条 Contract，记录关联 Contract、前置条件、验收步骤和可观察的通过标准。例如 `specify create test account-recovery-acceptance` 会生成验收模板。[查看示例](example_specs/spec/specs/test/account-recovery-acceptance/spec.md)

已有项目可把下列条目加入 `spec/config.yaml` 的 `specTypes`，再从项目根运行 `specify init . --config spec/config.yaml`，补装缺失的内置模板并保留项目配置。

```yaml
test:
  label: 测试验收
  description: 必须通过的验收场景、验证步骤和通过标准
  template: template/test.md
```

创建和更新 spec 时可以设置一行简介。简介保存在 `spec.md` 同级的 `meta-data.yaml`，命令会同步刷新 `spec/spec-index.md`。`list --spec` 默认用缩进文本按 type 展示 ID、相对项目根的路径和简介，`--human` 切换为 Rich 树，`specify --json list --spec` 返回完整字段。

```bash
specify create capability user-auth --description "登录、认证与会话管理"
specify update capability:user-auth --description "密码登录、通行密钥与会话过期"
specify --root ./my-project list --spec --human
```

## Change 工作流

创建 change 并在 `change.md` 记录背景、动机和需求。可按内容使用 `## Background`、`## Why`、`## Requirement` 等标题。此时状态为 `proposed`：

```bash
specify change create feat add-password-login --priority P1
```

优先级保存在 Change 的 `meta-data.yaml` 中。创建时省略 `--priority` 默认为 `P2`，老 Change 缺少字段时也按 `P2` 读取。

```bash
specify change priority add-password-login P0
```

归档后优先级固定。调整未归档 Change 的优先级只更新元数据和更新时间。

**后续计划**：支持在项目配置中定义有序档位和默认值，让团队可以把 `P00` 排在 `P0` 之前。CLI 校验、Web 排序和筛选届时共用同一套档位配置。当前内置档位为 `P0` 到 `P4`。

开始拆解时进入 `processing`，在同一份 `change.md` 补充设计和实现方案，再把实施与验证工作拆进 `tasks.md`。影响范围明确时可在同一条命令里声明：

```bash
specify change process add-password-login --affect capability:user-auth:modify
```

可以先运行不带选项的 `change process <id>`，等影响范围明确后再通过同一命令补充 `--affect`，或用 `--no-spec-impact "原因"` 明确无 Spec 影响。范围已知时，也可以在 `change create` 上直接使用这两个选项之一创建 `processing`。旧版已写好 tasks 和 delta 的 `proposed` 可运行 `change process <id>` 原样迁移，保留现有影响范围和基线。

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

未声明影响范围的 `processing` 在 `verify` 时会提示补充。明确无正式 Spec 影响的 change 完成任务后可直接从 `implemented` 归档。

## Contract 历史

成功同步的 Contract 变更按完整引用保存在 `spec/.history/contracts/<type>/<spec-id>/<contract-id>.jsonl`。同一个引用删除后重新添加，会沿用原文件并继续递增 `idx`。

```bash
specify history capability:user-auth:session-expiry
specify history capability:user-auth:session-expiry --limit 5 --human
specify history capability:user-auth:session-expiry --include-removed --csv > history.csv
specify history capability:user-auth:session-expiry --diff 1 2 --human
specify history --human
```

默认以 JSON 返回当前生命周期的最新版本。`--limit` 查询最近几条记录，`--include-removed` 展开以前的生命周期和删除记录，`--diff` 按 `idx` 比较标题和正文，支持跨生命周期比较。用 `--human` 在终端浏览，用 `--csv` 导出记录。

升级已有项目时运行 `specify history --backfill`，把还没有历史的 Contract 以当前正文补记为 `add`。捕获基线时会保存当时的正式版本。如果同步前的正文或标题与最近一条历史记录不同，同步也会补存修改前的实际版本。

在 POSIX 终端运行 `specify history --human` 可打开选择器。输入的字符按顺序在整条引用中匹配，可以在同一段内跳着选字，也可以跨段。例如 `touch`、`lts` 和 `kendtouch` 都能找到 `requirement:backend-indicators-signals:line-touch-signal`。列表用颜色区分引用的三段，并突出命中的字符。首屏只显示终端能容纳的条目，按方向键可以滚动，Enter 确认，Esc 取消。

交互选中后默认显示最近 3 条。可在 `spec/config.yaml` 修改默认值，显式传入的 `--limit` 优先。

```yaml
history:
  defaultLimit: 5
```

在 `~/.zshrc` 启用 Click 补全后，输入 `specify history --human rbl` 并按 Tab，即可补入匹配的完整引用。补全也支持全局 `--root`。

```zsh
autoload -Uz compinit
compinit
source <(_SPECIFY_COMPLETE=zsh_source specify)
```

## 常用命令

```bash
specify validate
specify list
specify list --human
specify list --spec --human
specify status --human
specify change status add-password-login
specify --json change status add-password-login
specify show capability:user-auth
specify index build
```

`list` 默认输出活跃 change 的 JSON，包括 kind、生命周期状态和 tasks 的已完成/总数。`list --human` 用 Rich 树按状态和 kind 分组展示。`list --change` 显式选择 change，`list --spec` 用缩进文本列出正式 spec，`--type` 仅与 `--spec` 搭配。`status` 默认输出整个项目的 JSON，`status --human` 同时显示 spec 和 change。`--human` 与全局 `--json` 互斥。`validate` 可用 `--specs`、`--changes` 或 `--archived` 限定检查范围。

交接单个 Change 时，用 `change status <id>` 查看阶段、相关文件、未完成任务、缺失项和建议的下一步。`--json` 提供 `files`、`tasks`、`missing`、`nextStep` 和校验问题，存在校验问题时仍输出报告并返回退出码 1。

用 [`specify-audit` 技能](skills/specify-audit/SKILL.md) 审查代码是否兑现正式 Contract，并在同一份报告里检查相关 Contract 是否冲突。技能会列出代码、测试和规范证据。`change verify` 负责 CLI 的结构与基线检查。

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
