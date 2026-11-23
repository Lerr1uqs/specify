---
name: specify-propose
description: 根据需求创建 Specify proposed change，或按用户要求进入 processing 起草 tasks 和 Contract delta。
---

# 起草 Specify change

如果还不熟悉这个项目，先运行 `specify list --spec` 查看全部正式 spec，再用相对路径和简介定位相关正文。

先读取 `spec/config.yaml`、目标 formal spec 和相关模板，确认 change kind、kebab-case ID，以及每个目标的 `<type>:<spec-id>:<create|modify|remove>` 操作。命令默认作用于当前目录；在本仓库源码中可用 `uv run specify` 替代 `specify`。

1. 用 `specify change create <kind> <change-id>` 录入 proposed。在 `change.md` 写清背景、动机和需求。可用 `## Background`、`## Why`、`## Requirement` 分段，也可以把简短需求写成几段。如果用户只要求记录需求，保存正文后即可交付。
2. 用户要求拆解时，用 `specify change process <change-id>` 进入 processing。在同一份 `change.md` 保留需求，经讨论后补充设计、实现方案及验证思路。通过 `--affect <type>:<spec-id>:<operation>` 声明影响，或用 `--no-spec-impact "原因"` 明确无影响。把已确定的实施和验证工作拆进 `tasks.md`；影响未确定时可稍后补充。
3. 对每个受影响 spec，填写生成的 `deltas/<type>/<spec-id>.md`。delta 标题使用 `## [操作] [contract-id] 标题`，其中操作为 `ADDED`、`MODIFIED`、`REMOVED` 或 `RENAMED`；`MODIFIED` 提供变更后的完整正文，`REMOVED` 提供 `**Reason**:` 和 `**Migration**:` 两行，`RENAMED` 的标题使用 `旧标题 -> 新标题` 且不写正文。依照项目模板和既有 Contract 表达需求。
4. 对涉及 `MODIFIED`、`REMOVED`、`RENAMED` 的 delta，完成编辑后运行 `specify change baseline <change-id>`；仅新增 Contract 无需基线。运行 `specify change verify <change-id>` 并修正报告的问题。

交付时说明 change 的目录和阶段。若已进入 processing，再说明影响的正式 Spec、剩余 tasks 和 verify 结果。

## 输入与目标选择

用户可能只说想做什么，没有提供 ID。先从描述推导 kebab-case ID 和 `spec/config.yaml` 允许的 kind；若目标 Contract 不明确，查 `specify list --spec` 与 `specify show <type>:<id>`。阅读相关的 proposed、processing 和 implemented change，确认不会重复建同一个变更。若 ID 已存在，检查已有 change 是否就是用户想继续的对象；不要覆盖目录。

判断正式规范影响时逐个回答：

| 事实 | 选择 |
| --- | --- |
| 新建一份 formal spec | `--affect type:id:create`，delta 只含 `ADDED` |
| 修改已有 spec 的一个或多个 Contract | `--affect type:id:modify`，按 Contract ID 写操作 |
| 删除整份 spec 的全部 Contract | `--affect type:id:remove`，delta 只含 `REMOVED` |
| 只改实现，不改变 Contract | 用 `--no-spec-impact "原因"` 声明 |

若问题、预期结果或删除范围缺少关键事实，指出缺口并询问；其余材料可先继续完成。不要把实现细节冒充可观察的业务行为，也不要因为用户说“bugfix”就自动认定没有 spec 影响。

## 按依赖顺序完成材料

1. **按阶段扩展 `change.md`**：proposed 说明现在发生了什么、为什么值得做、希望达到什么结果。processing 再写选定的设计、涉及的模块或接口、实现步骤和验证方式。方案存在取舍时，记录会影响实施的理由。标题按内容组织，小变更可以合并章节。
2. **再写 delta**：以当前 formal spec 为输入，保留已有 Contract 的稳定 ID。`MODIFIED` 要写新的完整正文；`REMOVED` 要有非空 `**Reason**:` 和 `**Migration**:`；`RENAMED` 标题使用 `旧标题 -> 新标题` 且不带正文。新增 Contract 要有新的 kebab-case ID。创建整份 spec 时只用 `ADDED`；删除整份 spec 时要移除其中所有 Contract。
3. **再写 tasks**：把目标拆成编号复选框，包含必要的实现和验证；每项应能判断是否完成。保持 `- [ ] 1.1 任务描述` 这样的可解析格式，别提前勾选。
4. **最后做基线与校验**：只有 delta 写好后才运行 `change baseline`，随后运行 `change verify`。先阅读校验错误并修正文档；不要手工填写 `baseVersions`，也不要通过重捕基线掩盖语义变化。

每完成一个材料就检查文件内容是否符合上一项的意图。模板提供写作引导，CLI 的 verify 只证明结构、目标和基线有效，不证明业务语义正确。

## 完成时的报告

用简短清单说明 change ID 与路径、kind、影响的 spec/Contract、写好的材料、tasks 数量和 verify 结果。若有待用户决定的语义问题，指出对应 Contract 和可选处理方式，不宣称“已可实施”。可告诉用户下一步是实施这个 change；不要在提案阶段运行 implement、sync 或 archive。

## 常见阻碍

- **项目未初始化**：确认目标项目根目录；若任务是新建 Specify 项目，先运行 `specify init <目录>`，否则说明缺少 `spec/config.yaml` 并继续能做的分析。
- **已有同 ID change**：展示其状态与路径。继续编辑它或另取 ID，不能覆盖。
- **目标 Contract 已变**：先读最新正文并重审 delta，显式重捕基线；不自动合并语义。
- **verify 失败**：保留实际错误与当前文件位置，修正后重试；问题未解决时报告尚缺什么。

## 命令与文件示例

例如用户要调整已有 `capability:user-auth` 的登录规则，可在确认配置允许 `feat` 且目标 spec 存在后运行：

```bash
specify change create feat adjust-login-rule
specify change process adjust-login-rule \
  --affect capability:user-auth:modify
```

在 `spec/changes/processing/feat/adjust-login-rule/deltas/capability/user-auth.md` 中使用完整操作，而不是把一句“增加登录限制”当作可同步的 delta：

```markdown
# delta

## [MODIFIED] [password-login] 密码登录

这里写修改后完整、可验证的 Contract 正文。
```

随后填写 `change.md` 与编号 tasks，运行 `specify change baseline adjust-login-rule` 和 `specify change verify adjust-login-rule`。若只修复实现使其符合现有 Contract，拆解时用 `--no-spec-impact "原因"`。

交付示例：`adjust-login-rule` 已创建于 `spec/changes/processing/feat/adjust-login-rule/`，影响 `capability:user-auth` 的 `password-login`，计划 3 项任务，verify 通过；可以开始实施。实际回复应使用真实 ID、目标和进度。
