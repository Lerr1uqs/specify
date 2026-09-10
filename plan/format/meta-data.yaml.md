# `meta-data.yaml` 格式

## 位置

```text
spec/changes/<status>/<kind>/<title>/meta-data.yaml
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

- `id` 必须与路径中的 `<title>` 相同，且为 kebab-case。
- change `id` 在整个 `changes/` 树中全局唯一；不同 `kind`、不同状态与 archive 历史均不得复用它。
- `title` 是可读标题，可修改而不移动目录。
- `kind` 必须与路径中的 `<kind>` 相同，并存在于 `config.yaml`。
- 时间必须为带时区的 RFC 3339 timestamp；`updatedAt` 不早于 `createdAt`。
- `affects` 与 `specImpact` 必须二选一。
- 每个 `affects` 条目包含已声明的 `type`、kebab-case `id`，以及 `create`、`modify`、`remove` 之一。
- `affects` 不得包含重复的 `<type>:<id>`。
- 有 `affects` 时，每个目标必须有 `deltas/<type>/<id>.md`；没有 `affects` 时不得存在 `deltas/`。
