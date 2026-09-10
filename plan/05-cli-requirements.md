# CLI 需求

## 建议 Action

```text
specify init [path] --config <init.yaml>
specify type list
specify create <type> <id>
specify index build

specify change create <kind> <title>
specify change status <title>
specify change implement <title>
specify change verify <title>
specify change sync <title>
specify change reject <title>
specify change archive <title>

specify validate [--specs|--changes|--archived]
specify show <type>:<spec-id>
specify list [--type <type>]
```

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

## 状态相关 Action

| Action | 目录效果 |
|---|---|
| 创建 change | 创建 `changes/proposed/<kind>/<title>/`。 |
| 标记已实现 | 完成实现、tasks 与 verify 后，移动到 `changes/implemented/<kind>/<title>/`。该状态允许多个 change 并存。 |
| 验证 | 检查正式 Contract、delta、proposal、design、tasks 与实际实现是否一致。 |
| 同步 | 将一个 implemented change 的 delta 合并进当前 `specs/`，change 留在 `implemented/`。重复同步必须安全；已应用的操作应识别为 no-op，而不是重复新增或报错。 |
| 拒绝 | 移动到 `changes/rejected/<kind>/<title>/`。 |
| 归档 | 要求 verify 成功与 tasks 全部完成；确认 delta 已同步（未同步时执行同样的合并）后移动到 `changes/archived/<kind>/YYYY-MM-DD-<title>/`。 |

状态不能从 metadata 推断，也不能由用户手改 metadata 改变；CLI 应检验 metadata 的 kind 与路径中的 kind 一致。

## 必要校验

- `config.yaml` 中声明的 type 与 kind 是唯一合法值。
- change 的 `id` 在所有 kind、状态和 archive 历史中全局唯一；不同 kind 不得复用同一 id。
- 正式 spec 必须位于 `specs/<type>/<id>/spec.md`。
- 正式 spec 必须含非空 `# proposal` 与 `# contract` 区块；每个 Contract 由自然语言 `##` 标题及该标题导出的 hash 标识。
- `affects`、delta 路径和正式 spec 路径必须一一对应。
- `create` 目标不得已存在；`modify` / `remove` 目标必须存在。
- delta 的 Contract title 操作必须满足主 spec 中由 title hash 推导出的存在性与冲突规则。
- task 进度只识别 checkbox；archive 前应报告未完成任务。
- archive 只接受已完成 tasks 且 `specify change verify` 成功的 implemented change。
- archive 后的所有文件必须通过不可变 manifest 校验。
- `specify index build` 必须确定性重建索引，索引文件不得手工编辑。
