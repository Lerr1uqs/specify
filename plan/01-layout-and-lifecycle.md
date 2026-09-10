# 目录与生命周期

## 术语

| 概念 | 含义 |
|---|---|
| `type` | 正式 spec 的类别，例如 `capability`、`component`、`rule`。由项目配置定义。 |
| `kind` | 本次 change 的性质，例如 `feat`、`bugfix`、`simplify`、`refactor`、`arch`、`test`。由项目配置定义。 |
| `status` | change 的生命周期：`proposed`、`implemented`、`rejected`、`archived`。状态只由 change 目录表达。 |
| Contract | 一份 type spec 内可独立定位、变更和校验的最小条目。 |

## 推荐目录

```text
spec/
├── config.yaml
├── spec-index.md
├── specs/                                      # 当前事实来源
│   ├── capability/
│   │   └── user-auth/spec.md
│   ├── component/
│   │   └── auth-service/spec.md
│   └── rule/
│       └── password-policy/spec.md
└── changes/
    ├── proposed/
    │   └── feat/
    │       └── add-sms-2fa/
    │           ├── meta-data.yaml
    │           ├── proposal.md
    │           ├── design.md
    │           ├── tasks.md
    │           └── deltas/
    ├── implemented/
    ├── rejected/
    └── archived/
        └── feat/
            └── 2026-09-09-add-sms-2fa/
```

## 状态转换

```text
proposed ──验证成功且 tasks 全部完成──> implemented ──归档──> archived
    │
    └──不采纳──────────────────────────> rejected
```

- 迁移状态就是移动目录；`meta-data.yaml` 不保存第二份 `status`。
- 状态迁移是固定单向规则：只允许 `proposed → implemented → archived` 或 `proposed → rejected`。
- `implemented` 表示 change 的实现和验证已完成，但尚未归档；它不是“正在实施”的互斥锁，允许有多个 implemented change 长期并存。
- `specify change sync` 可在不归档的前提下把一个 implemented change 的 delta 合并到当前 `specs/`；状态保持为 `implemented`。
- `archived` 的目录名由 CLI 加上归档日期：`YYYY-MM-DD-<title>`。
- `rejected` 是保留“不做”的理由，不进入 `archived`。
- `specs/` 永远只包含当前生效的内容；归档不改变其目录结构。
