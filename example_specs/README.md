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
