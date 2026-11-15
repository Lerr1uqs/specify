# Specify 示例项目

这个目录演示当前设计中的文件布局和内容。它不是 CLI 的测试 fixture，也不会被根目录的 `specify` 命令自动扫描。

## 目录内容

- `config.yaml`：项目允许的 spec type 和 change kind。
- `template/`：不同 spec type 的 Markdown 写作模板；配置中的 `template` 路径指向对应文档。
- `specs/`：当前生效的正式 Contract。Contract ID 写在 `## [id] 标题` 的方括号中。
- `changes/implemented/feat/add-passkey-login/`：已完成并成功同步的 change，包含合并后的 `change.md`、tasks、metadata、正文基线、delta 和 sync 回执。
- `changes/archived/refactor/2026-11-15-reorganize-auth-files/`：一个无 spec 影响的归档 change。
- `changes/archived/manifest.json`：归档文件的 SHA-256 清单。
- `spec-index.md`：由 type 和 spec ID 构成的导航索引。

`add-passkey-login` 的 delta 已反映在 `specs/` 中。它仍留在 `implemented/`，因为设计要求先 sync，archive 只核对回执并移动目录，不再次应用 delta。

在此示例中，`baseVersions` 是起草时正文的 hash；delta 写完后运行 `specify change baseline <id>` 明确捕获基线。发生基线冲突时，应先阅读最新 Contract、调整 delta 的完整正文，再次显式捕获基线。

> 示例展示当前 Python CLI 目标协议的文件格式。成功 sync 后 delta 固定；之后要继续调整时另建 follow-up change。
