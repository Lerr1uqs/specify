# Delta 与 Archive 协议

## Delta 定位

metadata 的每个 `affects` 目标必须有一个对应 delta：

```text
affects: component:auth-service
        ↓
deltas/component/auth-service.md
        ↓ change sync
specs/component/auth-service/spec.md
```

type 由 `meta-data.yaml` 与 delta 路径决定；delta 标题中的显式 ID 定位该 spec 内的 Contract。一个被修改的 Contract 的全局引用是 `<type>:<spec-id>:<contract-id>`，例如 `component:auth-service:credential-validation`。

## Delta Markdown 格式

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

语法要求：

- 标题必须是精确的 `## [ADDED|MODIFIED|REMOVED] [<contract-id>] <contract-title>` 或 `## [RENAMED] [<contract-id>] <old-title> -> <new-title>`。操作、ID、title 之间各用一个空格分隔。
- Contract ID 为 kebab-case，在目标 spec 内唯一。修改正文或用 `RENAMED` 改标题，都不能改变 ID。
- `ADDED` 的 ID 与规范化 title 在主 spec 中都不得存在；`MODIFIED` 与 `REMOVED` 的 ID 必须存在，title 必须匹配当前标题。
- `ADDED` / `MODIFIED` 标题后的正文是该 Contract 的完整新版本，不是补丁描述。
- `RENAMED` 的 ID 必须存在，旧 title 必须匹配当前标题，新 title 不得与其他 Contract 重复；合并后只改 title，不改 ID。若还要改变正文，另用相同 ID 和新 title 写 `MODIFIED`。
- 同一 delta 内同时出现 `RENAMED [<id>] <old> -> <new>` 和 `MODIFIED [<id>] <new>` 是合法写法。校验与合并按 `RENAMED` → `MODIFIED` 的顺序、对重命名**之后**的状态求值。
- 同一 delta 内不得冲突操作同一 ID；`RENAMED` 后针对同一 ID 的 `MODIFIED` 是唯一允许的组合。不同 ID 的规范化 title 不得重复。
- `REMOVED` 必须给出原因和迁移说明。
- `->` 只保留给 `RENAMED` 标题的旧/新 title 分隔符；Contract title 本身不得包含该字符序列。它与 change 状态迁移无关。

CLI 用显式 ID 定位 Contract，用 title 帮助作者核对目标：

```text
"[credential-validation] 凭据验证的职责"
  -> 用 credential-validation 在目标 spec 中定位
  -> 核对可读标题，再应用操作
```

## Archive 流程

```text
1. 校验 change、metadata、change.md、tasks 与 delta
2. 确认所有 tasks 都完成，并执行 `specify change verify <id>` 成功
3. 含 delta 的 change 必须已有成功 `sync` 回执，且回执中的每份 delta hash 与当前文件一致
4. 将 change 移至 changes/archived/{kind}/YYYY-MM-DD-{id}/，不再次写入正式 spec
5. 写入 archive manifest 并冻结目录
```

无 delta 的 change 不要求 `sync` 回执。正式 spec 和索引由 `sync` 更新；archive 只封存已应用的结果，避免旧 delta 在其他 change 更新后再次覆盖正式 spec。

正文基线与同步回执的字段、冲突处理见 [07-contract-version-check.md](07-contract-version-check.md)。

## Sync 流程

`specify change sync <id>` 允许已完成、但暂不 archive 的 change 提前更新正式 spec：

1. 要求目标 change 位于 `implemented/`，并通过 `verify`；
2. 若已有与当前 delta 文件一致的成功回执，直接返回无变化；
3. 否则读取所有 delta，核对 `MODIFIED`、`REMOVED`、`RENAMED` 的起草基线并在内存中完成所有目标的合并；任一冲突都停止，不写正式 spec；
4. 写入正式 specs，校验结果，重建 `spec-index.md`，最后在 change 的 metadata 中写入同步回执；change 保持在 `implemented/`。

sync 不自动合并两个 change 对同一 Contract 的不同正文；基线冲突时由作者阅读最新正文、调整 delta，运行 `specify change baseline <id>` 明确更新基线后再 verify 和重试。成功 sync 后 delta 固定，进一步调整另建 change。自动语义合并仍见 [parallel-change-merge.md](todo/parallel-change-merge.md)。

`rejected/` 的 delta 永不进入 `sync` 或 `archive` 的合并路径。

## Archive 冻结

`changes/archived/` 是审计历史，不是当前权威。实现方式采用 DS Note 的 append-only 思路：

- `changes/archived/manifest.json` 保存每个归档文件的 SHA-256；
- `specify archive` 只允许为新归档目录追加清单记录；
- `specify validate --archived` 比对既有清单，拒绝已封存文件的修改、删除或改名；
- 将该验证放入 pre-commit 与 CI；
- 正式 spec 有错时，创建一个新的 change 修正，不能修改 archive。
