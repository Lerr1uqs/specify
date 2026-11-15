# Contract 版本检查：防止 Change 覆盖彼此的修改

> 实现状态：当前 Python CLI 已实现正文基线捕获、sync 冲突拒绝和归档回执校验；该文档描述行为边界。

## 要解决的问题

多个 `implemented` change 可以同时存在。它们即使按顺序执行 `sync`，也可能先后修改同一个 Contract。当前 `MODIFIED` 会用 delta 中的完整正文替换正式 spec 的正文；显式 Contract ID 只能确认目标条目，无法判断这份 delta 是基于哪一版正文写成的。

### 例子

正式 spec 起初写着：

```text
spec.md 标题：## [login-methods] 登录方式
正文：用户可以用密码登录。
正文版本：H0
```

A 和 B 都从 H0 开始工作：

```text
A 的目标：用户可以用密码或短信登录。
B 的目标：用户可以用密码或通行密钥登录。
```

A 先同步，正式正文变成 A 的版本 H1。B 随后同步时，若直接执行 `MODIFIED`，会把 A 的短信登录改动覆盖掉。因此 B 必须先看到“当前是 H1，而你基于 H0”，重新阅读 A 的改动，调整自己的完整正文，再以 H1 为基线提交。

## ID 与版本 hash 的职责

| 值 | 回答的问题 | 正文改变时 | 标题改变时 |
|---|---|---|---|
| Contract 显式 ID（目标协议） | 修改的是哪一条 Contract？ | 不变 | 不变，标题仍须使用 `RENAMED` 修改 |
| 正文版本 hash（新增基线） | 起草时看到的是哪一版正文？ | 改变 | 正文不变时不变 |

正文版本使用 SHA-256 计算，但不充当 Contract ID。显式 ID 解决改标题后的身份延续；它不能单独发现上述正文覆盖问题。

## 版本检查规则

1. 对 `MODIFIED`、`REMOVED`、`RENAMED`，作者写完具体 delta 后运行 `specify change baseline <id>`，由 CLI 从当前正式 spec 读取目标 Contract，并将正文 hash 写入该 change 的 `meta-data.yaml`。`change create --affect` 只知道受影响的 spec，不能在创建空骨架时猜测基线；verify 和 sync 也不隐式补录。操作用显式 ID 定位；`RENAMED` 还要核对旧标题，同一 delta 中随后对新标题的 `MODIFIED` 共用一份原始基线。
2. 首次 `sync` 前，工具读取当前正式 spec，计算目标 Contract 的正文版本。只有当前版本等于 `base`，才能应用操作。标题不存在、重命名目标已被占用等现有冲突规则仍须通过。
3. 如果当前版本不同于 `base`，工具报告目标和两个版本，停止本次 change 的同步；不自动选择 A 或 B 的正文，也不自动拼接句子。
4. 作者处理冲突时，先读取当前正文，再修改 delta 中的完整目标正文，显式运行 `specify change baseline <id>` 更新为当前版本。之后重新验证、同步。
5. `ADDED` 没有旧正文基线；首次应用时要求同 ID 和同名 Contract 都不存在。`create` 整份 spec 也没有旧正文基线。

基线在 change 的 `meta-data.yaml` 中按完整 Contract 引用保存，例如：

```yaml
baseVersions:
  "capability:user-auth:login-methods": "<64 位小写 SHA-256>"
```

`baseVersions` 的键必须恰好覆盖 delta 中所有 `MODIFIED`、`REMOVED`、`RENAMED` 触及的不同 Contract；`RENAMED + MODIFIED` 共用一个键。`ADDED` 不需要基线。正式 `spec.md` 不存正文 hash：工具每次读取时从原始 Markdown 正文计算当前版本。

版本 hash 的输入按 [正式 spec 格式](format/spec.md.md)定义：统一换行符、去掉首尾空白行，保留正文内部 Markdown 源码。`REMOVED` 的基线来自正式 Contract 原有正文，不是 delta 中的 Reason/Migration。

## Sync 与 Archive

一次 change 若影响多份 spec，应先检查所有目标的基线并完成内存合并；任何目标冲突时，不写入其中任何一份正式 spec。

成功 `sync` 后，工具在同一份 `meta-data.yaml` 中记录同步时间和每份 delta 的文件 SHA-256，例如：

```yaml
sync:
  appliedAt: 2026-11-15T10:00:00+08:00
  deltaHashes:
    "capability/user-auth.md": "<64 位小写 SHA-256>"
```

`sync` 只有在所有目标和索引成功更新后才能记录此回执。重复 `sync` 若发现回执与当前 delta 文件一致，就直接返回无变化，不重放旧内容。成功 sync 后 delta 固定；修改 delta 会让回执过期，后续语义调整另建 change。含 delta 的 change 必须先成功 `sync` 才能 `archive`。`archive` 只核对回执中的 delta 文件 hash 并封存 change，不再次写正式 spec。无 delta 的 change 可直接归档。

不能仅靠“当前正文恰好等于 delta 正文”推断该 change 已同步：另一个 change 也可能写出相同正文。多目标写入中断后的恢复方式仍需在实施前确定；回执必须反映全部目标已成功应用。

## 边界

本规则只检测正文版本冲突，不判断合并后的业务语义是否正确。不同 change 修改不同 Contract 时，互不阻塞。自动合并同一 Contract 的正文仍留待以后决定。
