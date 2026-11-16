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

## 选择目标与核对状态

用户指定 ID 时按 ID 定位；未指定时用 `specify status` 的 `changes` 列表和当前对话判断。多个可能的 implemented change 需要用户选择；不要猜测要归档哪一个。开始时说明 ID、kind、当前状态和 tasks 进度。

只有 implemented change 能归档。读取 `meta-data.yaml`、`tasks.md`、delta、`change.md` 与受影响的正式 Contract；检查以下事实：

| 条件 | 处理 |
| --- | --- |
| 还有未完成 tasks | 完成并验证相应工作；CLI 不允许跳过 |
| `specImpact.kind: none` | 不需要正式 spec 同步，可直接进入归档校验 |
| 有 `affects`，尚无有效 sync 回执 | verify 后运行 `change sync` |
| 已有有效 sync 回执 | 不重复应用 delta，进入 archive |
| 已 archived | 报告现有归档位置，不再移动 |

与 OpenSpec 的归档流程不同，Specify 不允许“带着未完成任务继续归档”，有 delta 的 change 也不能选择“跳过同步直接归档”。不要提出 CLI 实际不支持的选项。

## 同步前的复核

执行 `specify change verify <change-id>`，确认 delta、基线与现有正式 spec 一致。若 verify 报基线已变化：

1. 读最新 Contract 正文及本 change 的 delta，解释发生了什么变化。
2. 根据最新正文调整 delta，并检查已实施代码与 tasks 是否仍符合新的语义。
3. 显式运行 `specify change baseline <change-id>`，再次 verify。只刷新 hash 不算解决冲突。

如果 delta 已成功 sync 且回执有效，verify 仅用于确认回执与当前 delta 未分叉。此时不要修改 delta 或重捕基线；新的语义调整另建 change。

## 执行与结果

有 `affects` 且尚未 sync 时，先运行 `specify change sync <change-id>`。它会校验并合并 delta、更新 formal spec 与索引、写入回执；失败时保留原始错误并修正问题，不手动编辑回执或手工移动 change。无正式 spec 影响时跳过 sync。

之后运行 `specify change archive <change-id>`。CLI 会将目录移至 `spec/changes/archived/<kind>/<日期>-<change-id>/`，并登记 `manifest.json`；不要用文件移动命令代替。若归档失败，按 CLI 报错处理，不宣称已归档。

交付时报告 change ID、归档位置、正式 spec 是否同步、验证结果。若停在 sync 或 archive 之前，报告当前状态和下一步，不把未完成过程写成成功。

## 命令顺序示例

有正式 spec 影响且未同步的 implemented change：

```bash
specify change verify add-passkey-login
specify change sync add-passkey-login
specify change archive add-passkey-login
```

若 `meta-data.yaml` 是 `specImpact.kind: none`，省去 sync：

```bash
specify change verify fix-internal-cache
specify change archive fix-internal-cache
```

若已有有效 sync 回执，直接 verify 后 archive；不要因为想“确认一下”就手动重放 delta。若 CLI 报回执与 delta 不一致，报告该错误，先调查已同步后的文件改动；不能通过修改回执绕过。

成功回复应包含实际的归档路径、是否同步 formal spec、校验结果。例如：`add-passkey-login 已同步到正式 spec，归档于 spec/changes/archived/feat/<日期>-add-passkey-login/，verify 通过。` 不要猜日期或路径，以 CLI 返回为准。
