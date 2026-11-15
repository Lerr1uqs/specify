# TODO：并行 Change 的 Contract 合并

正文版本检查与人工处理冲突的规则见 [07-contract-version-check.md](../07-contract-version-check.md)。本文保留自动合并的后续问题；版本检查目前尚未实现。

## 当前决定

V1 支持多个 `implemented` change 并存，也支持 `specify change sync <id>` 在 archive 前更新正式 `specs/`。

V1 **不**自动合并两个 change 对同一个 `<type>:<spec-id>:<contract-id>` 的不同正文。sync 发现基线冲突时由作者依据当前正式 spec 手动调整 delta 与基线后重试。

V1 假定写入 `specs/` 的 sync 操作串行执行。含 delta 的 change 必须先成功 sync；archive 只核对回执并封存，不重放 delta。

这与 OpenSpec 当前的风险相同：`MODIFIED` 是完整 Contract 替换，两个 change 都基于旧正文写作时，后同步者可能覆盖先同步者新增的内容。

## 后续要解决的问题

1. 是否在 change 内保存原始正文用于三方合并？正文基线 SHA-256 的检查规则已在 [07-contract-version-check.md](../07-contract-version-check.md) 确定；它与显式 Contract ID 的定位职责不同。
2. 将来是否提供带冲突标记的辅助合并，而不只报告基线冲突？
3. Contract 内部是否需要进一步稳定的子条目 ID，来减少不同段落/规则彼此独立修改时的冲突？
4. Git 分支、PR 与 CI 如何保证两个同步操作在共享主分支上的顺序一致？

## 非目标

- 不以 `implemented/` 的数量限制并行；它代表“已完成未归档”，不是锁。
- 不在 V1 引入 CRDT、操作转换或自动语义合并。
- 不以正文版本 hash 充当 Contract ID；定位始终使用正式 spec 与 delta 中的显式 ID。
