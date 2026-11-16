---
name: specify-apply-change
description: 实施 Specify proposed change 中的 tasks，并在开始实施前核对 Contract 基线。适用于用户要求开始或继续实现一个已有 change 时。
---

# 实施 Specify change

根据用户给出的 ID 或上下文定位 `spec/changes/proposed/<kind>/<change-id>/`。若有多个可能目标且无法判断，先列出候选 change 并请用户选择。读取 `change.md`、`tasks.md`、`meta-data.yaml`、所有 delta 与相关 formal spec。命令默认作用于当前目录；在本仓库源码中可用 `uv run specify` 替代 `specify`。

**每次开始实施前**运行 `specify change verify <change-id>`。若报告 Contract 正文基线变化，先阅读最新 formal spec，重新审查 change 的目标和 delta，按新正文调整 delta，再显式运行 `specify change baseline <change-id>` 和 `specify change verify <change-id>`。不要只重捕 hash 来消除错误；必要时同步调整 tasks 和已经写好的实现。

校验通过后按 `tasks.md` 实施、验证，并在对应任务实际完成时将 `- [ ]` 改为 `- [x]`。用户中途要求修改方案时，先更新 change 文件和 delta，再继续实施。完成所有 tasks 后再次运行 `specify change verify <change-id>`，再执行 `specify change implement <change-id>`；该命令会检查任务完成状态并将目录移到 implemented。

报告已完成的工作、验证结果和 change 状态。正式 Contract 的更新交给 `specify change sync`，不要手工套用 delta。
