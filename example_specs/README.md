# Specify 示例项目

这个目录是可直接由 CLI 读取的示例项目。从仓库根目录查看：

```bash
uv run specify --root example_specs list --human
uv run specify --root example_specs list --spec --human
uv run specify --root example_specs status --human
```

第一条展示活跃 change 的状态、kind 和 tasks 进度。第二条展示五种正式 spec，包括用户能力、组件职责、业务需求、架构和规则。第三条同时展示正式 spec 和未归档 change，包含 rejected。`list --spec` 默认输出缩进文本。`list` 和 `status` 默认输出 JSON。

## 四种 change 状态

| 状态 | 示例 | 可以看到什么 |
| --- | --- | --- |
| `proposed` | `show-recovery-delivery-state` | 有目标 spec 和 delta，仍在提案阶段 |
| `implemented` | `restore-recovery-attempt-limits` | 同步恢复曾删除的 Contract ID，保留旧历史 |
| `rejected` | `expose-recovery-lookup-result` | 保存提案和未采纳的理由 |
| `archived` | `publish-recovery-controls` | 多份 delta 跨 type 修改规范，归档清单保留文件校验值 |

查看被删除后重新添加的 Contract，以及改标题并更新正文的版本差异：

```bash
uv run specify --root example_specs history rule:recovery-policy:attempt-limits --include-removed --csv
uv run specify --root example_specs history component:auth-service:session-issuance --diff 2 3 --human
uv run specify --root example_specs validate --archived
```

## Web Review：通知回执的三个阶段

```bash
uv run specify --root example_specs web
```

打开 **Changes**，按下表选择 change。点击右侧的 Contract 节点查看逐行 diff。

| Change | 阶段 | 可以看到什么 |
| --- | --- | --- |
| `launch-delivery-receipts` | 已归档 | 新增整份 `capability:delivery-receipts` 和 `rule:receipt-pilot`；同时给现有 `component:notification-service` 新增一条 Contract。 |
| `retire-receipt-pilot` | 已归档 | 删除整份 `rule:receipt-pilot` 及其中两条 Contract，并修改正式回执能力。试点规则已不在正式 Spec 列表，但当时的删除 diff 仍可查。 |
| `explain-delivery-receipt-outcomes` | 已实施，未同步 | 仅重命名一条 Contract、新增一条结果说明、修改通知服务接口，并预览新增保留规则。打开当前正式 Spec，对照仍生效的原名称和正文。 |

前两项通过 CLI 同步并归档，保留真实回执和版本快照；最后一项故意停在 `implemented`，以便检查尚未生效的预览。还可以打开 `publish-recovery-controls` 查看一次 change 如何影响四份不同类型的 Spec。

### Web Review 中的过期基线

`extend-audit-retention-to-60-days` 和 `extend-audit-retention-to-90-days` 都以 `rule:audit-policy:retention` 的 30 天留存期为基线。90 天版本已通过 CLI 同步，60 天版本留在 `proposed`，用于演示过期基线。

- 打开 60 天 change，展开「恢复审计留存周期」。标题栏显示「已落后当前 Spec」，diff 显示 30 → 60 天。点击提示里的 `rule:audit-policy:retention`，弹窗会显示当前 90 天的正式正文。
- 打开 90 天 change，历史 diff 显示 30 → 90 天。点「查看当前 Spec」可以看到当前生效的 90 天留存期。

`change verify extend-audit-retention-to-60-days` 和全量 `validate` 会报该提案的基线已变化。可分别运行 `validate --specs` 和 `validate --archived` 核验正式规范和归档。

## 目录内容

- `spec/config.yaml`：项目允许的 spec type 和 change kind。
- `spec/template/`：不同 spec type 的 Markdown 写作模板；配置中的 `template` 路径指向对应文档。
- `spec/specs/`：当前生效的正式 Contract。Contract ID 写在 `## [id] 标题` 的方括号中。
- `spec/changes/implemented/feat/add-passkey-login/`：已完成并成功同步的 change，包含合并后的 `change.md`、tasks、metadata、正文基线、delta 和 sync 回执。
- `spec/changes/archived/refactor/2026-11-15-reorganize-auth-files/`：一个无 spec 影响的归档 change。
- `spec/changes/archived/manifest.json`：归档文件的 SHA-256 清单。
- `spec/spec-index.md`：按 type 分组的导航索引，包含 spec ID、链接和简介。

`add-passkey-login` 的 delta 已反映在 `spec/specs/` 中。它仍留在 `implemented/`，因为设计要求先 sync，archive 只核对回执并移动目录，不再次应用 delta。

在此示例中，`baseVersions` 是起草时正文的 hash；delta 写完后运行 `specify change baseline <id>` 明确捕获基线。发生基线冲突时，应先阅读最新 Contract、调整 delta 的完整正文，再次显式捕获基线。

> 示例展示当前 Python CLI 目标协议的文件格式。成功 sync 后 delta 固定；之后要继续调整时另建 follow-up change。
