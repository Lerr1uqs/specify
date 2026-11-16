---
name: specify-propose
description: 根据需求在 Specify 项目中创建并写好 proposed change，包括 change.md、tasks.md 和必要的 Contract delta。适用于用户要起草新变更或把已讨论方案落实为 change 时。
---

# 起草 Specify change

先读取 `spec/config.yaml`、目标 formal spec 和相关模板，确认 change kind、kebab-case ID，以及每个目标的 `<type>:<spec-id>:<create|modify|remove>` 操作。命令默认作用于当前目录；在本仓库源码中可用 `uv run specify` 替代 `specify`。

1. 用 `specify change create <kind> <change-id> --affect <type>:<spec-id>:<operation>` 建立骨架；多个目标重复传入 `--affect`。若不改变正式 Contract，省略 `--affect`，并在 `meta-data.yaml` 的 `specImpact.reason` 解释原因。
2. 写清 `change.md` 中的问题、目的与预期结果；按实际工作拆分 `tasks.md`。Specify 不要求另建 proposal.md 或 design.md。
3. 对每个受影响 spec，填写生成的 `deltas/<type>/<spec-id>.md`。delta 标题使用 `## [操作] [contract-id] 标题`，其中操作为 `ADDED`、`MODIFIED`、`REMOVED` 或 `RENAMED`；`MODIFIED` 提供变更后的完整正文，`REMOVED` 提供 `**Reason**:` 和 `**Migration**:` 两行，`RENAMED` 的标题使用 `旧标题 -> 新标题` 且不写正文。依照项目模板和既有 Contract 表达需求。
4. 对涉及 `MODIFIED`、`REMOVED`、`RENAMED` 的 delta，完成编辑后运行 `specify change baseline <change-id>`；仅新增 Contract 无需基线。运行 `specify change verify <change-id>` 并修正报告的问题。

交付时说明 change 目录、影响的 formal spec 和剩余 tasks。此阶段不把 delta 直接写进 formal spec，也不标记 implemented。
