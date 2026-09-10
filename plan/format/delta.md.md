# Delta Markdown 格式

## 位置

```text
spec/changes/<status>/<kind>/<title>/deltas/<type>/<spec-id>.md
```

metadata 中每个 `affects` 目标必须有且仅有一份对应 delta。

## 格式

```markdown
# delta

## [ADDED] 风险评估职责

认证服务 SHALL 根据风险评估结果决定是否启动二次验证挑战。

## [MODIFIED] 凭据验证的职责

认证服务负责验证凭据并返回认证结果；它不负责发送或投递验证码。

## [REMOVED] 静态令牌职责

**Reason**: 静态令牌不再符合当前安全策略。
**Migration**: 调用方改用一次性验证码挑战。

## [RENAMED] 凭据验证与会话签发 -> 凭据验证的职责
```

## 规则

- 文件首个顶层标题必须为 `# delta`。
- 操作标题必须是 `## [ADDED|MODIFIED|REMOVED] <contract-title>`，或 `## [RENAMED] <old-title> -> <new-title>`。
- 作者只书写 title；CLI 由 title 即时计算 Contract hash 作为内部唯一键。
- `ADDED` title 不得存在于目标正式 spec；`MODIFIED`、`REMOVED` 的 title 必须存在。
- `ADDED` 和 `MODIFIED` 的正文是完整 Contract 正文。
- `REMOVED` 必须包含非空 `**Reason**:` 与 `**Migration**:`。
- `RENAMED` 的旧 title 必须存在，新 title 必须不存在；若还修改正文，应使用新 title 另写 `MODIFIED`。
- `->` 是 `RENAMED` 的唯一旧/新 title 分隔符；Contract title 本身不得包含 `->`，它不是状态迁移语法。
- 同一 delta 不得冲突操作同一个规范化 title/hash。
