# Delta 与 Archive 协议

## Delta 定位

metadata 的每个 `affects` 目标必须有一个对应 delta：

```text
affects: component:auth-service
        ↓
deltas/component/auth-service.md
        ↓ archive merge
specs/component/auth-service/spec.md
```

type 由 `meta-data.yaml` 与 delta 路径决定；delta 内部的标题只定位该 spec 内的 Contract。一个被修改的 Contract 的全局引用是 `<type>:<spec-id>:<contract-hash>`，例如 `component:auth-service:9aa30d42`。

## Delta Markdown 格式

```markdown
# Auth Service Delta

## [ADDED] 风险评估职责

认证服务 SHALL 根据风险评估结果决定是否启动二次验证挑战。

## [MODIFIED] 凭据验证的职责

认证服务负责验证凭据并返回认证结果；它不负责发送或投递验证码。

## [REMOVED] 静态令牌职责

**Reason**: 静态令牌不再符合当前安全策略。
**Migration**: 调用方改用一次性验证码挑战。

## [RENAMED] 凭据验证与会话签发 -> 凭据验证的职责
```

语法要求：

- 标题必须是精确的 `## [ADDED|MODIFIED|REMOVED] <contract-title>` 或 `## [RENAMED] <old-title> -> <new-title>`。作者永远书写 title，不书写 hash。
- Contract hash 只由自然语言 title 计算，正文不参与；CLI 每次解析文档时即时计算，不存储或缓存 hash。hash 仅用于内部唯一性、比较和合并，不是 Markdown 协议的书写内容。
- `ADDED` title 的 hash 在主 spec 中不得存在；`MODIFIED` 与 `REMOVED` 的 title hash 必须存在。
- `ADDED` / `MODIFIED` 标题后的正文是该 Contract 的完整新版本，不是补丁描述。`MODIFIED` title 必须与主 spec 的现有 title 严格一致（按标题规范化规则比较）。
- `RENAMED` 的旧 title hash 必须存在，新 title hash 必须不存在；合并后以新 title 替换旧 title。若还要改变正文，另用新 title 写 `MODIFIED`。
- 同一 delta 内不得以不同操作处理同一个 title/hash；不得出现规范化后相同、但表面写法不同的重复标题。
- `REMOVED` 必须给出原因和迁移说明。
- `->` 只保留给 `RENAMED` 标题的旧/新 title 分隔符；Contract title 本身不得包含该字符序列。它与 change 状态迁移无关。

这套格式让 review 只面对业务语言；CLI 在后台执行以下映射：

```text
"凭据验证的职责"
  -> normalize(title)
  -> SHA-256(title)
  -> 用 hash 与目标 spec 的 Contract 建立唯一对应
```

## Archive 流程

```text
1. 校验 change、metadata、proposal、design、tasks 与 delta
2. 确认所有 tasks 都完成，并执行 `specify change verify <id>` 成功
3. 为每个 affects 读取主 spec 和 delta
4. 若 delta 尚未同步，以 Contract hash 执行 create/modify/remove/rename 合并；若已经同步，确认当前 formal spec 与 delta 的预期结果一致
5. 校验写入后的正式 specs
6. 将 change 移至 changes/archived/{kind}/YYYY-MM-DD-{title}/
7. 写入 archive manifest 并冻结目录
8. 重建 spec-index.md
```

没有 `deltas/` 的 change 跳过第 2–4 步，仍可 archive。

## Sync 流程

`specify change sync <id>` 允许已完成、但暂不 archive 的 change 提前更新正式 spec：

1. 要求目标 change 位于 `implemented/`，并通过 `verify`；
2. 读取 `deltas/` 并合并到 `specs/`；
3. 校验写入后的正式 specs，并重建 `spec-index.md`；
4. change 保持在 `implemented/`，供后续审计、补充验证或 archive。

sync 必须幂等：若其 delta 的预期结果已存在，重复执行不应改变 formal spec。并行 change 修改同一 Contract 时的基线检测与三方合并不在 V1 范围，见 `todo/parallel-change-merge.md`。

## Archive 冻结

`changes/archived/` 是审计历史，不是当前权威。实现方式采用 DS Note 的 append-only 思路：

- `changes/archived/manifest.json` 保存每个归档文件的 SHA-256；
- `specify archive` 只允许为新归档目录追加清单记录；
- `specify validate --archived` 比对既有清单，拒绝已封存文件的修改、删除或改名；
- 将该验证放入 pre-commit 与 CI；
- 正式 spec 有错时，创建一个新的 change 修正，不能修改 archive。
