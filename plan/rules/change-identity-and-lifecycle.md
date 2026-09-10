# Rule：Change Identity 与 Lifecycle

## Change ID 全局唯一

change 的路径是：

```text
changes/<status>/<kind>/<id>/
```

`id` 是 kebab-case 稳定目录名，也是 change 的唯一机器标识。它在整个 `changes/` 树中全局唯一：不同 kind、不同状态与 archive 历史都不能复用。

因此以下结构非法：

```text
changes/proposed/feat/add-login/
changes/proposed/bugfix/add-login/
```

同一主题后续工作必须使用新 ID，例如 `add-login-v2` 或 `fix-login-validation`。

## Spec ID 只在 Type 内唯一

正式 spec 的路径是：

```text
specs/<type>/<spec-id>/spec.md
```

不同 type 可以拥有相同的 `<spec-id>`，例如：

```text
specs/capability/auth/spec.md
specs/component/auth/spec.md
```

它们由 `<type>:<spec-id>` 区分。Contract 的内部机器引用再追加从 title 即时计算的 hash：

```text
<type>:<spec-id>:<contract-hash>
```

## 固定状态迁移

```text
proposed ──> implemented ──> archived
    │
    └──> rejected
```

- 禁止 `proposed → archived`、`implemented → rejected`、任何 archived/rejected 回退。
- 状态只能由 `specify change implement`、`specify change reject`、`specify change archive` 执行的目录移动改变；不从 metadata 读取，也不允许手改 metadata 改变。
- `implemented` 表示实现已完成、等待或已经同步、但尚未归档的 change；多个 implemented change 可以并存，不表示互斥的“实施中”。
- `specify change sync <id>` 不改变状态：它只将一个 implemented change 的 delta 提前合并到正式 spec，供后续 change 和当前事实来源使用。

## 完成与归档

- 进入 `implemented/` 前，proposal、design、tasks、metadata 和 delta 必须通过格式与引用校验。
- `specify change verify <id>` 必须成功，确认实现与正式 Contract、delta、proposal、design、tasks 一致。
- `tasks.md` 所有 checkbox 必须完成。
- 只有满足上述条件的 implemented change 可以 archive。archive 合并 delta、冻结历史并更新 `spec-index.md`。
