# Change 工作包与 Metadata

## Change 目录

每次工作位于 `changes/{status}/{kind}/{id}/`。`id` 是全局唯一的 kebab-case 目录名；状态由目录表达，不重复存入 metadata。归档时目录名前加 `YYYY-MM-DD-`，metadata 中的 `id` 保持不变。

```text
changes/processing/feat/add-sms-2fa/
├── meta-data.yaml
├── change.md
├── tasks.md
└── deltas/                     # 仅改变正式 Contract 时存在
    ├── capability/user-auth.md
    └── component/auth-service.md
```

## `change.md`

每个 change 使用一个 `change.md` 记录问题、上下文和目标。新 `proposed` 从 `## Requirement` 开始，作者可以在进入 `processing` 后补充设计决策。CLI 只要求文件存在，已有项目可以保留自己的章节结构。

Bugfix 若只是让实现恢复到已有 Contract 的要求，不需要新增或修改 formal spec，也不需要 delta。若修复改变对外行为或 Contract 语义，则必须通过 delta 更新正式 spec。

## `tasks.md`

`tasks.md` 在进入 `processing` 时生成，使用 checkbox 表达完成状态。标记 `implemented` 或归档前要求所有任务完成。

## `meta-data.yaml`

metadata 记录身份、时间、kind、优先级和已声明的影响范围。`proposed` 只需基础元数据。`processing` 可先进入拆解，再确定影响范围。完整验证要求 `affects` 与 `specImpact` 二选一：

- 有正式 Contract 变化时使用 `affects`，每个目标都必须有一个 `deltas/<type>/<spec-id>.md`。
- 不改变正式 Contract 时使用 `specImpact.kind: none` 并写明原因；不得有 delta、baseline 或 sync receipt。

```yaml
id: add-sms-2fa
title: 增加短信二次认证
kind: feat

createdAt: 2026-09-09T10:00:00+08:00
updatedAt: 2026-09-09T10:00:00+08:00

affects:
  - type: capability
    id: user-auth
    change: modify

baseVersions:
  "capability:user-auth:login-methods": "<64 位小写 SHA-256>"
```

`affects.change` 是 spec 级操作：`create` 创建新 spec，`modify` 修改已有 spec，`remove` 删除已通过 delta 移除全部 Contracts 的 spec。Contract 级操作仍由 delta 中的 `ADDED`、`MODIFIED`、`REMOVED`、`RENAMED` 表示。

### 正文基线

`baseVersions` 只记录 `MODIFIED`、`REMOVED`、`RENAMED` 涉及的 Contract，键为 `<type>:<spec-id>:<contract-id>`，值为当前 Contract 正文的 SHA-256。正文先将 CRLF/CR 统一为 LF，只去除边缘空行，保留其余 Markdown 字节内容。

作者完成 delta 后，显式运行 `specify change baseline <id>` 捕获当前基线。校验和 sync 不会隐式刷新 hash。若 sync 发现基线过期，作者先阅读当前 Contract、调整 delta，再显式运行该命令更新基线后重试。`ADDED` 和新建 spec 没有基线。

### Sync 回执

成功同步所有 delta 后，CLI 将回执写入同一份 YAML：

```yaml
sync:
  appliedAt: 2026-11-15T10:00:00+08:00
  deltaHashes:
    "capability/user-auth.md": "<64 位小写 SHA-256>"
```

`deltaHashes` 使用相对 `deltas/` 的路径和原始文件字节 hash。相同 delta 再次 sync 是 no-op；成功 sync 后 delta 固定，之后的语义调整另建 change。归档只核对 receipt 并移动目录，不重放 delta。

正文基线与回执都存放在 change 的 YAML 中；正式 Contract 的权威内容仍只存于 `specs/`。归档完整性清单 `changes/archived/manifest.json` 继续保留，用于检查已封存文件是否被修改。

## 无 Spec 影响示例

```yaml
id: reorganize-auth-files
title: 整理认证模块目录
kind: refactor

createdAt: 2026-09-10T10:00:00+08:00
updatedAt: 2026-09-10T10:00:00+08:00

specImpact:
  kind: none
  reason: 仅调整文件结构，不改变任何 Contract。
```

无 spec 影响的 change 可在任务完成后直接归档，不要求 sync receipt。

## Rejected Change

`rejected/` change 保留 `change.md`、metadata 与当时的其他材料，额外要求 metadata 中有非空 `rejectedReason`。拒绝的 delta 永不进入正式 spec。其余文件按拒绝时状态保存，不要求 tasks 完成或 verify 通过。
