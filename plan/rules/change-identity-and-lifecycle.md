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

归档时目录名变为 `changes/archived/<kind>/YYYY-MM-DD-<id>/`。日期前缀只表达归档顺序，不参与身份：`meta-data.yaml` 中的 `id` 保持不加前缀的原值，唯一性检查在剥离 `YYYY-MM-DD-` 前缀后进行。这是“目录名等于 ID”的唯一例外，其他任何状态下的目录名都必须与 ID 完全一致。

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

它们由 `<type>:<spec-id>` 区分。Contract 的机器引用再追加其在该 spec 内稳定的显式 ID：

```text
<type>:<spec-id>:<contract-id>
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
- `specify change verify <id>` 必须成功。它是**纯机器判定**：格式、引用、Contract ID 与 title 的存在性和冲突、`affects`/delta/正式 spec 的对应、任务编号与 checkbox 等确定性规则。它不判断“实现是否符合意图”，那是 review 与 agent 的职责。
- `tasks.md` 所有 checkbox 必须完成。
- 只有满足上述条件的 implemented change 可以 archive。含 delta 的 change 还必须先成功 `sync`；archive 核对同步回执后冻结历史，不再次写正式 spec。

## 拒绝与删除

- `specify change reject <id>` 只接受 `proposed/` 的 change，移动到 `rejected/` 并写入一行 `rejectedReason`。
- rejected change 冻结的是提案本身：不要求 tasks 完成、不要求 `verify` 通过、不要求 delta 合并；其 delta 永不进入 `sync` 或 `archive` 的合并路径。
- rejected change 只在它的理由仍能阻止一个可能重犯的错误时保留。
- `specify change remove <id>` 删除整个 change 目录，只接受 `proposed/` 与 `rejected/`。`implemented/` 的结论可能已被 `sync` 写入 `specs/`，`archived/` 是冻结审计，两者都不允许删除。
