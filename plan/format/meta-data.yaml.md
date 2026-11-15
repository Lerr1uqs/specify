# `meta-data.yaml` 格式

## 位置

```text
spec/changes/<status>/<kind>/<id>/meta-data.yaml
```

`status` 由路径表达，不能写入此文件。

## 格式

```yaml
id: add-sms-2fa
title: 增加短信二次认证
kind: feat

createdAt: 2026-09-10T10:00:00+08:00
updatedAt: 2026-09-10T10:00:00+08:00

affects:
  - type: capability
    id: user-auth
    change: modify
  - type: component
    id: auth-service
    change: modify
  - type: component
    id: sms-gateway
    change: create

baseVersions:
  "capability:user-auth:login-methods": "<64 位小写 SHA-256>"
  "component:auth-service:credential-validation": "<64 位小写 SHA-256>"
```

完成具体 delta 后，作者显式运行 `specify change baseline <id>`，由 CLI 读取正式 Contract 正文并生成 `baseVersions`；verify 和 sync 不会隐式刷新基线。上例假定两个 `modify` 目标各修改一条 Contract。成功 `sync` 后，CLI 追加回执：

```yaml
sync:
  appliedAt: 2026-11-15T10:00:00+08:00
  deltaHashes:
    "capability/user-auth.md": "<64 位小写 SHA-256>"
    "component/auth-service.md": "<64 位小写 SHA-256>"
    "component/sms-gateway.md": "<64 位小写 SHA-256>"
```

无正式 spec 影响时：

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

## 规则

- `id` 必须与路径中的目录名相同，且为 kebab-case。**唯一例外**：`archived/` 下的目录名是 `YYYY-MM-DD-<id>`，此时 `id` 仍是去掉日期前缀后的原值。
- change `id` 在整个 `changes/` 树中全局唯一；不同 `kind`、不同状态与 archive 历史均不得复用它。比较归档 change 时先剥离 `YYYY-MM-DD-` 前缀。
- `title` 是可读标题，可修改而不移动目录。它是人类标题，与 `id`、与 Contract title 都不是一回事。
- `kind` 必须与路径中的 `<kind>` 相同，并存在于 `config.yaml`。
- 时间必须为带时区的 RFC 3339 timestamp；`updatedAt` 不早于 `createdAt`。
- `affects` 与 `specImpact` 必须二选一。
- 每个 `affects` 条目包含已声明的 `type`、kebab-case `id`，以及 `create`、`modify`、`remove` 之一。
- `affects` 不得包含重复的 `<type>:<id>`。
- 有 `affects` 时，每个目标必须有 `deltas/<type>/<id>.md`；没有 `affects` 时不得存在 `deltas/`。
- `baseVersions` 的键为 `<type>:<spec-id>:<contract-id>`，值为该 Contract 起草时正文的 64 位小写 SHA-256；键集合必须恰好等于所有 `MODIFIED`、`REMOVED`、`RENAMED` 操作涉及的不同 Contract。`ADDED` 与新建 spec 不记录基线。
- 没有需要旧正文的操作时省略 `baseVersions`；`specImpact.kind: none` 的 change 也不使用 `baseVersions` 或 `sync`。
- `sync` 只由 CLI 在成功写入全部目标后生成；`deltaHashes` 的键是相对 `deltas/` 的文件路径，值为原始文件字节的 SHA-256。回执必须覆盖全部 delta，`archive` 核对后才封存。
- 位于 `rejected/` 的 change 必须额外带一行 `rejectedReason`，写清“为什么不做”；其他状态不得出现该字段。

```yaml
id: add-oauth-login
title: 增加 OAuth 登录
kind: feat

createdAt: 2026-09-11T09:00:00+08:00
updatedAt: 2026-09-11T09:00:00+08:00

rejectedReason: 现有 SSO 已覆盖该场景，新增一套凭据来源不划算。

affects:
  - type: capability
    id: user-auth
    change: modify
```
