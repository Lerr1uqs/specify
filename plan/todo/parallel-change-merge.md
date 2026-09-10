# TODO：并行 Change 的 Contract 合并

## 当前决定

V1 支持多个 `implemented` change 并存，也支持 `specify change sync <id>` 在 archive 前更新正式 `specs/`。

V1 **不**自动处理两个 change 并行修改同一个 `<type>:<spec-id>:<contract-hash>` 的语义冲突。sync 与 archive 只应用经作者 review 的 delta；发生冲突时由作者依据当前正式 spec 手动调整 delta 后重试。

这与 OpenSpec 当前的风险相同：`MODIFIED` 是完整 Contract 替换，两个 change 都基于旧正文写作时，后同步者可能覆盖先同步者新增的内容。

## 后续要解决的问题

1. 在何时记录一个 `MODIFIED`、`REMOVED` 或 `RENAMED` Contract 所基于的正文版本：创建 delta、首次 validate，还是首次 sync？
2. 是否在 change 内保存基线正文 SHA-256 和原始正文，用于 stale 检测与三方合并？这与即时计算的 Contract title hash 不同：前者是临时并行控制数据，后者是由标题推导的定位键。
3. `sync` 发现基线已变化时，是直接拒绝，还是生成带冲突标记的 delta 供作者解决？
4. Contract 内部是否需要进一步稳定的子条目 ID，来减少不同段落/规则彼此独立修改时的冲突？
5. Git 分支、PR 与 CI 如何保证两个同步/归档操作在共享主分支上的顺序一致？

## 非目标

- 不以 `implemented/` 的数量限制并行；它代表“已完成未归档”，不是锁。
- 不在 V1 引入 CRDT、操作转换或自动语义合并。
- 不改变 Contract hash 的规则：它仍只由标题即时计算，不落盘，也不取决于正文。
