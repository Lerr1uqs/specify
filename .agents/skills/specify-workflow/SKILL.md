---
name: specify-workflow
description: 查询 Specify CLI 命令和完整 Contract/change 生命周期时使用的简明参考。适用于询问工具用法；具体探索、起草、实施或归档工作分别使用对应的 specify skill。
---

# Specify 工作流

如果还不熟悉这个项目，先在项目根运行 `specify list --spec` 查看全部正式 spec。用输出中的 type、相对路径和简介定位相关 spec，再读取正文。

Specify 项目以 `spec/config.yaml` 为入口。正式规范在 `spec/specs/<type>/<id>/spec.md`，change 在 `spec/changes/`。命令默认作用于当前目录，也可在命令前加 `--root <项目目录>`。以下示例假设 `specify` 已安装；从本仓库源码运行时，用 `uv run specify` 替换。

## 查看与创建

- 先阅读 `spec/config.yaml`、相关 formal spec 和已有 change，再决定目标 type、ID 与操作。
- `specify list` 列出活跃 change；`specify list --spec` 列出 formal spec；`specify show <type>:<id>` 查看内容；`specify validate` 检查项目。
- 新项目用 `specify init <目录>` 初始化。新 formal spec 用 `specify create <type> <id>` 创建，然后填写模板中的 Contract。Contract 标题格式为 `## [<contract-id>] <标题>`。

## 修改 Contract

1. 用 `specify change create <kind> <change-id> --affect <type>:<id>:<create|modify|remove>` 创建 change；多个目标重复传入 `--affect`。不影响 formal spec 的 bugfix 可省略 `--affect`。
2. 编辑生成的 `change.md`、`tasks.md` 和 `deltas/<type>/<id>.md`。写 delta 时查看目标 formal spec 的当前 Contract 内容。
3. 对 `MODIFIED`、`REMOVED`、`RENAMED` 的 Contract，在 delta 写好后运行 `specify change baseline <change-id>`。仅含 `ADDED` 操作时无需基线。
4. **每次开始实现这个 change 前**，先运行 `specify change verify <change-id>`。多个 change 可以基于同一个版本创建；先同步的 change 如果改了后续 change 所依赖的 Contract 正文，后续 change 的 verify 会发现基线已变化。
5. verify 通过后实现代码并完成 `tasks.md`。同步前再运行一次 verify，然后依次运行 `specify change implement <change-id>`、`specify change sync <change-id>`、`specify change archive <change-id>`。

如果 verify 或 sync 报 Contract 正文基线变化，先读最新 formal spec，重新检查这个 change 的意图和 delta，并按新的 Contract 内容调整 delta。然后显式运行 `specify change baseline <change-id>` 和 `specify change verify <change-id>`，通过后再实现或同步。不要仅为消除错误而重捕基线。成功 sync 后不要修改已回执的 delta；后续语义变更应另建 change。

## 当前 CLI 的输出边界

全局 `--json` 放在子命令前，例如 `specify --json list --spec`、`specify --json change verify <change-id>`。`list` 默认输出活跃 change 的 JSON，`list --human` 按状态和 kind 展示变更树及任务进度。`list --spec` 用缩进文本列出正式 spec 的 ID、相对项目根的路径和简介，`--type` 只用于这个视图。`status` 默认输出整个项目的 JSON，`status --human` 同时展示 spec 和 change。`--human` 与 `--json` 互斥。`change status <change-id>` 只查询单个 change；目前没有重叠 change 的预检命令。

当前校验按 Contract 正文 hash 检测已捕获基线的变化。两个 change 修改同一个 spec 中不同的 Contract 时，只要各自依赖的 Contract 正文没有变化，verify 不会因为它们共享 spec 而拒绝。语义是否冲突仍需根据最新规范判断。
