---
name: specify
description: 介绍 Specify 的 Spec、Contract、Change 与生命周期，提供 CLI 入门和专用技能导航。适用于刚接触 Specify、需要理解概念或判断该用哪段工作流时。
---

# Specify

Specify 用 Markdown 维护当前生效的规范，并通过 Change 推进修改。项目以 `spec/config.yaml` 为入口。

- **Spec** 按项目配置中的 type 组织，正文位于 `spec/specs/<type>/<id>/spec.md`。
- **Contract** 是 Spec 里可独立修改的条目。它有稳定 ID，完整引用为 `<type>:<spec-id>:<contract-id>`。在另一条 Contract 正文中写 `@[<type>:<spec-id>:<contract-id>]` 可建立可验证、可导航的引用。
- **Change** 位于 `spec/changes/` 下，记录一次工作的意图和进展。影响正式 Contract 时，用 delta 描述修改，并按需记录正文基线。

用 `specify init <目录>` 初始化项目。在项目根目录运行 `specify list --spec` 查看正式规范，运行 `specify list --human` 查看活跃 Change，或运行 `specify web` 在浏览器里查看。可用 `specify --root <目录> ...` 指定项目。从 Specify 源码仓库运行时，使用 `uv run specify`。

`change create` 录入 `proposed` 需求，`change process` 进入 `processing` 拆解和实施，`change implement` 标记已完成。涉及 Contract 的变更经 `change sync` 写入正式 Spec，再用 `change archive` 归档。

按当前任务使用对应的专用技能：

| 当前任务 | 专用技能 |
| --- | --- |
| 讨论需求、查 Contract 或比较方案 | [specify-explore](../specify-explore/SKILL.md) |
| 录入需求，或进入 processing 起草方案和任务 | [specify-propose](../specify-propose/SKILL.md) |
| 继续实施已有 Change 并核对基线 | [specify-apply-change](../specify-apply-change/SKILL.md) |
| 审查代码是否满足 Contract，以及 Contract 之间是否冲突 | [specify-audit](../specify-audit/SKILL.md) |
| 同步和归档已实施的 Change | [specify-archive-change](../specify-archive-change/SKILL.md) |
| 查询具体 CLI 命令或生命周期细节 | [specify-workflow](../specify-workflow/SKILL.md) |

这些技能随完整技能包安装。如果当前只安装了主技能，可用 `specify --help` 和 `specify change --help` 查看命令入口。
