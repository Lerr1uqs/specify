# Change 工作包与 Metadata

## Change 目录

每次工作位于 `changes/{status}/{kind}/{id}/`。`id` 是全局唯一的 kebab-case 目录名；状态由目录表达，不重复存入 metadata。归档时目录名前加 `YYYY-MM-DD-`，metadata 中的 `id` 保持不变。

```text
changes/proposed/feat/add-sms-2fa/
├── meta-data.yaml
├── change.md
├── tasks.md
└── deltas/                     # 仅改变正式 Contract 时存在
    ├── capability/user-auth.md
    └── component/auth-service.md
```

## `change.md`

每个 change 使用一个 `change.md` 记录问题、上下文、目标，以及需要的设计说明。它合并原来 proposal 与 design 的说明职责，但**没有强制章节或固定模板**：大 change 可以按背景、范围、决策、风险等分段；小修复可以只写一两句话。CLI 不校验其章节结构，只要求文件存在。该文件随 change 保存，不写入正式 spec 或 `spec-index.md`。

Bugfix 若只是让实现恢复到已有 Contract 的要求，不需要新增或修改 formal spec，也不需要 delta。若修复改变对外行为或 Contract 语义，则必须通过 delta 更新正式 spec。

## `tasks.md`

`tasks.md` 是可执行工作清单，使用 checkbox 表达完成状态：`- [ ]` 为待办，`- [x]` 为完成。实现前应将每项拆到可检查的大小；实现或归档前要求所有任务完成。

## `meta-data.yaml`

metadata 是 change 的机器数据来源。它记录身份、时间、kind 和影响目标。`affects` 与 `specImpact` 必须二选一：

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
