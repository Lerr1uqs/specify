---
name: specify-explore
description: 在 Specify 项目中探索需求、Contract 边界和 change 方案。适用于用户还在讨论做什么或如何划分 spec，尚未要求创建 change 或实施代码时。
---

# 探索 Specify 变更

先确认项目存在 `spec/config.yaml`，读取其中的 `specTypes`、`kinds` 和相关模板。根据讨论主题查看 `specify list`、`specify show <type>:<id>`、相关 formal spec，以及现有 change 的 `change.md`、`meta-data.yaml` 和 delta。命令默认作用于当前目录；在本仓库源码中可用 `uv run specify` 替代 `specify`。

帮助用户弄清问题、受影响的 Contract、可观察结果和实现约束。区分“修改正式 Contract”和“仅修复实现”：后者可以使用不带 `--affect` 的 change。若多个 change 涉及同一 spec，重点检查它们实际操作的 Contract ID 与正文，而不是仅凭 spec 路径判定冲突。

讨论尚未定案时，概括已经确认的目标、待决定的问题和可行的下一步。用户要求落盘时，按其意图创建或修改 Specify 文件；仅探索时不要擅自创建 change 或修改 formal spec。
