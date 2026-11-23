# 目录与生命周期

## 术语

| 概念 | 含义 |
|---|---|
| `type` | 正式 spec 的类别，例如 `capability`、`component`、`rule`。由项目配置定义。 |
| `kind` | 本次 change 的性质，例如 `feat`、`bugfix`、`simplify`、`refactor`、`arch`、`test`。由项目配置定义。 |
| `status` | change 的生命周期为 `proposed`、`processing`、`implemented`、`rejected`、`archived`，状态由目录表达。 |
| `id` | change 的稳定 kebab-case 目录名，也是它在整个 `changes/` 树中全局唯一的机器标识。可读标题另存 metadata，不是路径。归档时目录名会加上日期前缀，`id` 本身不变。 |
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
    │       └── preview-audit-export/
    │           ├── meta-data.yaml
    │           └── change.md
    ├── processing/
    │   └── feat/
    │       └── add-sms-2fa/
    │           ├── meta-data.yaml
    │           ├── change.md
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
proposed ──process──> processing ──implement──> implemented ──archive──> archived
    │                      │
    └──reject──────────────┴──────────────────> rejected
```

- 迁移状态就是移动目录；`meta-data.yaml` 不保存第二份 `status`。
- `proposed` 用于记录需求，只需 `change.md` 和基础元数据。`processing` 覆盖拆解和实施，在标记完成前需声明 Spec 影响并通过完整校验。
- 旧 `proposed` 可用 `specify change process <id>` 迁移，沿用已有 tasks、delta 和基线。
- `implemented` 表示 change 的实现和验证已完成，但尚未归档；它不是“正在实施”的互斥锁，允许有多个 implemented change 长期并存。
- `specify change sync` 可在不归档的前提下把一个 implemented change 的 delta 合并到当前 `specs/`；状态保持为 `implemented`。
- 含 delta 的 implemented change 必须先成功 `sync` 才能 archive；archive 核对同步回执后只封存 change，不再次修改 `specs/`。
- `archived` 的目录名由 CLI 加上归档日期：`YYYY-MM-DD-<id>`。这是“目录名等于 `id`”的唯一例外：日期前缀只表达归档顺序，不参与身份，`meta-data.yaml` 中的 `id` 保持不含前缀的原值；全局唯一性检查必须先剥离 `YYYY-MM-DD-` 前缀再比较。
- `rejected` 冻结的是提案本身：保留“不做”的理由，不进入 `archived`，也不要求 tasks 完成、delta 合并或 `verify` 成立。
- `rejected` 只在它的理由仍能阻止一个可能重犯的错误时保留；理由不再有价值时用 `specify change remove` 删除。
- `specify change remove` 可将 `proposed/`、`processing/` 或 `rejected/` 移入项目根的 `.trash/`。
- `specs/` 永远只包含当前生效的内容；归档不改变其目录结构。
