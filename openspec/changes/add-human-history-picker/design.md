## Context

`history` 已有可选的引用参数，当前在没有引用时要求 `--backfill`。历史按 `type/spec-id/contract-id.jsonl` 存放，正式索引只列到 spec 层级。项目配置由 init 和运行期共用入口校验。

## Goals / Non-Goals

提供 `--human` 专属的交互选取和引用补全，支持短输入，在候选较多时限制首屏展示数量，并按项目配置选取后的默认时间线条数。变更范围限于 `history`。

## Decisions

- 在终端执行 `specify history --human` 且省略引用时，进入选择器。终端输入和输出都需要可交互；其他调用继续走现有参数校验。`--backfill` 保留独立入口。
- 交互与 Tab 补全共用候选发现和匹配。候选来自当前正式 spec 的 Contract 和历史目录中的引用，按完整引用去重、排序，遵循 `--root`。历史目录发现只需读取路径，选定后由现有查询读取并判断哪些记录可见。
- 按输入顺序在整条引用中匹配字符，忽略大小写。允许跳过字符并跨越冒号，连续匹配优先。选择器用 Rich 区分引用的三段颜色、标出匹配字符和当前选中项。多项匹配时用方向键选择，Enter 确认，Esc 取消。候选超出可视区域时展示前几项和剩余数量，方向键滚动查看更多，筛选始终覆盖整个候选集。
- 使用 Click 的参数补全入口，并用 `specify history --human <TAB>` 验证 zsh 中整段引用的插入。Tab 只补入完整引用；交互选择器才会应用项目的默认条数。
- `spec/config.yaml` 可配置正整数 `history.defaultLimit`，缺省为 3。仅在交互选取后的时间线查询应用该值。显式 `--limit` 优先，版本 diff 沿用已有规则。已删除 Contract 沿用 `--include-removed` 的展示规则。

## Risks / Trade-offs

- 短输入可能命中多条候选。用户可查看命中位置并确认完整引用。
- 交互需要处理按键、滚动和终端恢复。实现时用 zsh 的真实终端会话验证筛选、取消与 Tab 补全。

## Migration Plan

已有项目可直接使用默认值。需要调整时，在 `spec/config.yaml` 写入以下配置。

```yaml
history:
  defaultLimit: 5
```
