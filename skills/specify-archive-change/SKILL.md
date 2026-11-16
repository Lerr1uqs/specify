---
name: specify-archive-change
description: 完成 Specify implemented change 的同步与归档。适用于用户要求将已实施的 change 写入正式 Contract 并归档时。
---

# 同步并归档 Specify change

根据用户给出的 ID 或上下文定位 implemented change；目标不明确时先查看 `spec/changes/implemented/` 并确认目标。读取 `change.md`、`tasks.md`、`meta-data.yaml`、delta 与受影响的 formal spec。命令默认作用于当前目录；在本仓库源码中可用 `uv run specify` 替代 `specify`。

1. 确认 tasks 已完成，运行 `specify change verify <change-id>`。若基线变化，先按最新 Contract 审查并调整 delta，必要时同步修正实现，再显式运行 `specify change baseline <change-id>` 和 verify。不要只刷新基线 hash。
2. 对 `meta-data.yaml` 中有 `affects` 的 change，执行 `specify change sync <change-id>`。CLI 会校验并合并 delta，写入 sync 回执；失败时根据错误修正，不手工移动目录或修改回执。`specImpact.kind: none` 的 change 无需同步 formal spec。
3. 运行 `specify change archive <change-id>`。CLI 将 change 移到带日期的归档目录并更新 manifest；不要手工移动文件代替这个命令。

完成后报告归档路径和正式 spec 的同步结果。已成功 sync 的 delta 不再修改；后续语义变更另建 change。
