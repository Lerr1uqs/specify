## Why

人工查询 Contract 历史时，每次都要输入三段完整引用和常用显示参数。将交互入口放在 `--human` 下，可以按短输入选取 Contract，并让每个项目配置常用的显示条数。

## What Changes

- 在终端运行 `specify history --human` 时打开候选选择器，首屏只展示前几个候选，其余可滚动查看。输入会实时筛选全部候选，支持键盘确认。
- 支持在完整引用里按字符顺序模糊匹配，例如用 `rbl` 或 `kendtouch` 找到 `requirement:backend-indicators-signals:line-touch-signal`。使用 Rich 区分三段并突出匹配字符，`--human` 的 Tab 补全复用匹配规则。
- 在项目配置中提供可选的 `history.defaultLimit`，交互查询默认展示最近 3 条，显式 `--limit` 优先。
- AI 和脚本继续传入完整引用，沿用现有的非交互调用与输出约定。

## Capabilities

### New Capabilities

### Modified Capabilities

- `specify-cli-v1` — 增加人工历史选择、引用补全与可配置的交互查询条数。

## Impact

影响 history CLI、Contract 候选发现、项目配置校验和 CLI 使用文档。交互查询选定引用后复用现有的历史读取和展示。
