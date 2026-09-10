# Change 工作包与 Metadata

## Change 目录

每次工作位于：

```text
changes/{status}/{kind}/{title}/
```

其中 `<title>` 是稳定的 kebab-case ID；可读标题保存在 metadata，修改人类标题不应移动目录。

```text
changes/proposed/feat/add-sms-2fa/
├── meta-data.yaml
├── proposal.md
├── design.md
├── tasks.md
└── deltas/                     # 仅发生正式 spec 改动时存在
    ├── capability/user-auth.md
    └── component/auth-service.md
```

## `meta-data.yaml`

metadata 记录稳定身份、时间、kind，以及这次 change 触及的正式 spec。它不重复记录状态：状态来自目录。

```yaml
id: add-sms-2fa
title: 增加短信二次认证
kind: feat

createdAt: 2026-09-09T10:00:00+08:00
updatedAt: 2026-09-09T10:00:00+08:00

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

`change` 的语义是正式 spec 实体级别的操作：

| 值 | 前置条件 | archive 后结果 |
|---|---|---|
| `create` | `specs/<type>/<id>/spec.md` 不存在 | 创建该正式 spec。 |
| `modify` | 正式 spec 已存在 | 合并该 spec 内的 Contract 变动。 |
| `remove` | 正式 spec 已存在 | 在明确的删除规则满足时移除该正式 spec。 |

它不是 Contract 级别的 `ADDED`、`MODIFIED` 等操作；后者只存在于 delta 文件。

## 无 Spec 影响的 Change

并非所有 change 都有 delta。纯测试、文档、CI、工具、或不改变责任/边界/行为的内部重构，可明确声明：

```yaml
specImpact:
  kind: none
  reason: 仅调整认证模块内部文件结构，不改变 Contract。
```

校验器要求二选一：

```text
affects 非空  <=> 每个目标都有对应 deltas/<type>/<id>.md
affects 为空  <=> 必须声明 specImpact.kind: none 和 reason
```

## `proposal.md`、`design.md` 与 `tasks.md`

- `proposal.md` 描述一次 change 的问题、动机、范围和受影响的正式 spec；它不同于正式 spec 内的 `# proposal` 区块：前者描述一次 change，后者描述某个当前 spec 的上下文、目的和动机。
- `design.md` 描述本次实施的技术方案、决策、备选方案、风险与迁移。
- `tasks.md` 采用 checkbox 作为机器接口：`- [ ]` 为待办，`- [x]` 为完成。每项应写明验证方式。
- 这三个文件解释为什么和如何做；它们不替代正式 spec 或 delta。
