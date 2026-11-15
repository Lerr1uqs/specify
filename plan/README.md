# 自定义 Spec CLI 设计草案

本目录记录当前讨论已达成的设计结论，供后续实现 CLI、模板和校验器时使用。

> Python CLI 已按 OpenSpec change `refine-specify-contracts-and-change-workflow` 实现显式 Contract ID、正文基线、sync 回执和单一 `change.md`；本目录的格式文件描述当前协议。

## 核心结论

- `specs/` 是当前生效的事实来源，只按可配置的 `type` 分类；不放 `proposed`、`rejected` 或 `archived` 状态。
- 一次工作是一个 change，路径为 `changes/{status}/{kind}/{title}/`；状态由目录唯一表达，不在 metadata 中重复维护。
- `kind` 描述为什么改（例如 `feat`、`bugfix`、`refactor`）；`type` 描述被管理的 spec 是什么（例如 `capability`、`component`、`rule`）。
- 每个 type 的 spec 都由可定位的 **Contract** 条目组成。Contract 取代 OpenSpec 的 capability/requirement 作为统一的内部变更单位。
- 每个 Contract 在所属 spec 内有显式、稳定的 kebab-case ID；标题可改，ID 不随标题或正文变化。
- change 仅在改变正式 spec 时拥有 `deltas/`；delta 对 Contract 执行 `ADDED`、`MODIFIED`、`REMOVED`、`RENAMED`。
- `implemented` 是已完成但未归档的状态；`specify change sync` 可提前更新 `specs/`，不改变 change 状态。
- `rejected` 冻结 change 本身，只要求 metadata（含一行 `rejectedReason`）与 `change.md`；不再有价值的 proposed/rejected change 用 `specify change remove` 移入 `.trash/`。
- 一个 change 只使用 `change.md` 记录上下文与设计；没有固定章节，小修复可写简短说明。若 bugfix 只恢复已有 Contract 行为，不需要 formal spec delta。

## 延后决策

- [并行 change 合并](todo/parallel-change-merge.md)：V1 不做同一 Contract 的自动并行合并。
- 含 delta 的 change 先 `sync` 到 `specs/`，再 archive；archive 只封存 change，不重放 delta。

## 文档导航

- [01-layout-and-lifecycle.md](01-layout-and-lifecycle.md)：目录、状态与归档流程。
- [02-spec-types-and-contracts.md](02-spec-types-and-contracts.md)：type 与 Contract 模型、正式 spec 格式。
- [03-change-artifacts-and-metadata.md](03-change-artifacts-and-metadata.md)：change 内容、`meta-data.yaml` 和 `affects`。
- [04-delta-and-archive-protocol.md](04-delta-and-archive-protocol.md)：delta 语法、合并和归档不可变性。
- [05-cli-requirements.md](05-cli-requirements.md)：建议的 CLI action 与校验要求。
- [06-implementation-plan.md](06-implementation-plan.md)：Python 实现的技术栈、模块划分、测试策略与里程碑。
- [07-contract-version-check.md](07-contract-version-check.md)：多个 change 修改同一 Contract 时的正文版本检查与冲突处理（设计补充，尚未实现）。
- [format/](format/README.md)：所有 Markdown、YAML 与生成文件的具体协议格式。
- [rules/change-identity-and-lifecycle.md](rules/change-identity-and-lifecycle.md)：change 命名、type 同名、状态迁移和完成条件的硬规则。
