# Delta Markdown 格式

## 位置

```text
spec/changes/<status>/<kind>/<id>/deltas/<type>/<spec-id>.md
```

metadata 中每个 `affects` 目标必须有且仅有一份对应 delta。

## 格式

```markdown
# delta

## [ADDED] [risk-assessment] 风险评估职责

认证服务 SHALL 根据风险评估结果决定是否启动二次验证挑战。

## [MODIFIED] [credential-validation] 凭据验证的职责

认证服务负责验证凭据并返回认证结果；它不负责发送或投递验证码。

## [REMOVED] [static-token] 静态令牌职责

**Reason**: 静态令牌不再符合当前安全策略。
**Migration**: 调用方改用一次性验证码挑战。

## [RENAMED] [credential-validation] 凭据验证与会话签发 -> 凭据验证的职责
```

## 规则

- 文件首个顶层标题必须为 `# delta`。
- 操作标题必须是 `## [ADDED|MODIFIED|REMOVED] [<contract-id>] <contract-title>`，或 `## [RENAMED] [<contract-id>] <old-title> -> <new-title>`。操作、ID、title 之间各用一个空格分隔。
- Contract ID 为 kebab-case，必须在所属 spec 内唯一；同一 Contract 的每个操作沿用同一个 ID。
- `ADDED` 的 ID 由作者或 Agent 在起草 delta 时选定；sync 后原样进入正式 spec。其余操作复制目标 Contract 的现有 ID。
- `ADDED` ID 与规范化 title 都不得存在于目标正式 spec；`MODIFIED`、`REMOVED` 的 ID 必须存在，所写 title 必须与当前 title 一致。
- `MODIFIED`、`REMOVED`、`RENAMED` 对应的起草正文 hash 存在 change 的 `meta-data.yaml` 中；sync 时与当前正式 Contract 正文比较。不同则停止，由作者调整完整正文与基线。
- `ADDED` 和 `MODIFIED` 的正文是完整 Contract 正文。
- `REMOVED` 必须包含非空 `**Reason**:` 与 `**Migration**:`。
- `RENAMED` 的 ID 必须存在，旧 title 必须与当前 title 一致，新 title 不得与其他 Contract 重复；合并后 ID 保持不变。若还修改正文，另用相同 ID 和新 title 写 `MODIFIED`。校验与合并按 `RENAMED` → `MODIFIED` 的顺序求值。
- `affects` 中标记为 `create` 的目标，其 delta 只允许 `ADDED`；标记为 `remove` 的目标，其 delta 必须把目标 spec 现有的每个 Contract 都 `REMOVED`。
- `->` 是 `RENAMED` 的唯一旧/新 title 分隔符；Contract title 本身不得包含 `->`，它不是状态迁移语法。
- 同一 delta 不得冲突操作同一 ID；`RENAMED` 后针对同一 ID 的 `MODIFIED` 是唯一允许的组合。不同 ID 的规范化 title 不得重复。
