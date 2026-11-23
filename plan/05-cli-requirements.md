# CLI 需求

## 建议 Action

```text
specify init [path] --config <init.yaml>
specify create <type> <id>
specify index build

specify change create <kind> <id>
specify change baseline <id>
specify change status <id>
specify change implement <id>
specify change verify <id>
specify change sync <id>
specify change reject <id>
specify change remove <id>
specify change archive <id>

specify validate [--specs|--changes|--archived]
specify show <type>:<spec-id>
specify list [--change|--spec] [--type <type>] [--human]
```

`specify list` 默认以 JSON 列出活跃 change 及 tasks 进度；`--change` 显式选择 change，`--spec` 切换为正式 spec（可用 `--type` 过滤）。`--human` 才使用 Rich 表格。V1 不提供 `type list`。所有 change 命令都以全局唯一的 `<id>` 定位，不接收状态或 kind 作为参数——CLI 自行在 `changes/` 树中查找，归档目录先剥离 `YYYY-MM-DD-` 前缀再匹配。

`specify init . --config init.yaml` 读取调用前已存在的 YAML，验证 `specTypes`、`kinds` 等内容，然后创建：

```text
./spec/
├── config.yaml                  # 从 init.yaml 写入的项目配置
├── specs/
└── changes/
```

`--config` 应接受相对调用目录的路径；没有 `--config` 时才进入交互式 type/kind 配置。初始化不得要求用户预先创建 `./spec/`。

实现时可以为 change create 提供显式目标参数：

```text
specify change create feat add-sms-2fa \
  --affect capability:user-auth:modify \
  --affect component:auth-service:modify \
  --affect component:sms-gateway:create
```

CLI 根据 targets 创建 `meta-data.yaml` 与对应 delta 骨架；无 `--affect` 时要求写入 `specImpact.kind: none` 与原因。

`--affect` 的三段是 **spec 级**定位与操作：`<type>:<spec-id>:<create|modify|remove>`。它不表达 Contract 操作；三级 Contract 引用为 `<type>:<spec-id>:<contract-id>`，第三段的语义由使用位置明确区分（见 [02-spec-types-and-contracts.md](02-spec-types-and-contracts.md)）。

## 状态相关 Action

| Action | 目录效果 |
|---|---|
| 创建 change | 默认创建只含需求和基础元数据的 `proposed`。明确传入 `--affect` 或 `--no-spec-impact` 时直接创建 `processing`。 |
| 开始拆解 | `change process <id>` 移入 `processing` 并补齐任务骨架，可以声明影响范围。旧方案的已有材料随目录移动。 |
| 标记已实现 | `processing` 的 tasks 完成并通过 verify 后，移动到 `changes/implemented/<kind>/<id>/`。 |
| 验证 | 纯机器判定：格式、引用、Contract ID 与 title 的存在性和冲突、`affects`/delta/正式 spec 的对应、checkbox 编号等确定性规则。它不判断“实现是否符合意图”，那是 review 与 agent 的工作。 |
| 同步 | 用起草基线校验并合并一个 implemented change 的 delta，更新当前 `specs/`，成功后在 change 的 metadata 中记录回执；相同 delta 重复同步为 no-op。 |
| 拒绝 | 将 `proposed` 或 `processing` 移入 `rejected` 并写入 `rejectedReason`。 |
| 删除 | 将 `proposed`、`processing` 或 `rejected` 移入项目根 `.trash/`。默认交互确认。 |
| 归档 | 要求 verify 成功与 tasks 全部完成；含 delta 时还要求同步回执与当前 delta 一致，然后移动到 `changes/archived/<kind>/YYYY-MM-DD-<id>/`，不重放 delta。 |

状态不能从 metadata 推断，也不能由用户手改 metadata 改变；CLI 应检验 metadata 的 kind 与路径中的 kind 一致。

## 必要校验

- `config.yaml` 中声明的 type 与 kind 是唯一合法值。
- change 的 `id` 在所有 kind、状态和 archive 历史中全局唯一；不同 kind 不得复用同一 id。归档目录的 `YYYY-MM-DD-` 前缀在比较前剥离。
- 正式 spec 必须位于 `specs/<type>/<id>/spec.md`。
- 正式 spec 只含一个 `# contract` 顶层区块；每个 Contract 使用 `## [<contract-id>] <contract-title>`，ID 在所属 spec 内唯一且保持稳定。
- `affects` 的每个目标必须有且仅有一份 delta，且 delta 路径必须与目标 `<type>:<id>` 一致。
- `affects` 条目的 `<type>:<id>` 必须指向已声明的 type 与合法 id；`create` 目标不得已存在，`modify` / `remove` 目标必须已存在。因此 `create` 的目标路径没有对应的现有正式 spec，这是“路径一一对应”规则的唯一例外。
- `create` 目标的 delta 只允许 `ADDED`；`remove` 目标的 delta 必须把目标 spec 现有 Contract 全部 `REMOVED`。
- delta 的 Contract ID 与 title 必须满足主 spec 中的存在性、标题匹配与冲突规则。
- `MODIFIED`、`REMOVED`、`RENAMED` 的正文基线写在 change metadata 中；`sync` 对照当前正式 Contract，冲突时停止并要求作者调整 delta 与基线。
- task 进度只识别 checkbox；archive 前应报告未完成任务。
- archive 只接受已完成 tasks 且 `specify change verify` 成功的 implemented change。
- archive 后的所有文件必须通过不可变 manifest 校验。
- `specify index build` 必须确定性重建索引，索引文件不得手工编辑。
