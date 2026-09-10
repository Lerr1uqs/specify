# Change `proposal.md` 格式

## 位置

```text
spec/changes/<status>/<kind>/<title>/proposal.md
```

## 格式

```markdown
# proposal

## Context

当前系统状态、触发本次 change 的背景和限制。

## Motivation

要解决的问题、机会或错误，以及为什么现在处理。

## Scope

本次 change 要做什么、明确不做什么。

## Affected Specs

- `capability:user-auth` — 修改高风险登录 Contract。
- `component:auth-service` — 调整认证职责边界。

## Impact

受影响的代码、API、数据、依赖、用户或迁移面。
```

## 规则

- 顶层标题必须为 `# proposal`。
- `## Context`、`## Motivation`、`## Scope`、`## Affected Specs`、`## Impact` 均必须存在且非空。
- `Affected Specs` 中的引用必须对应 `meta-data.yaml` 的 `affects`；它是人类可读说明，不是机器事实来源。
- `Scope` 必须同时说明 in scope 与 out of scope。
