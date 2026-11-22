## ADDED Requirements

### Requirement: Human history Contract selection

当用户在可交互终端运行 `specify history --human` 并省略引用时，CLI MUST 提供交互选择器，列出当前 Contract 和有历史文件的 Contract 引用，并允许在全量候选中实时筛选。候选超过可视区域时，CLI MUST 显示前几项和剩余数量，并支持滚动查看。CLI MUST 在用户确认后查询所选引用，并保留完整引用调用的原有语义。

#### Scenario: Match characters anywhere in the reference

- **WHEN** 用户在选择器中输入 `rbl`、`lts` 或 `kendtouch`
- **THEN** CLI 在每条完整引用中按顺序查找这些字符，找出包括 `requirement:backend-indicators-signals:line-touch-signal` 在内的匹配项
- **AND** 字符可以落在同一段内、单词中间或跨越冒号，连续匹配排在跳字符的匹配前
- **AND** 唯一匹配时按 Enter 即可确认，多项匹配时可用方向键选择后确认

#### Scenario: Distinguish reference segments and matched characters

- **WHEN** 支持颜色的终端展示匹配候选
- **THEN** CLI 使用不同颜色展示 type、spec ID 和 Contract ID，突出命中的字符并标记当前选中项

#### Scenario: Find a candidate below the visible rows

- **WHEN** 候选数量超过可视区域
- **THEN** 首屏仅展示前几项并提示剩余数量
- **AND** 后续候选可滚动查看，也可通过输入筛选后直接显示

#### Scenario: Cancel selection

- **WHEN** 用户按 Esc 取消选择
- **THEN** CLI 退出选择器且不查询历史

#### Scenario: Preserve direct and non-interactive calls

- **WHEN** 调用方传入完整引用或使用 `--backfill`
- **THEN** CLI 沿用相应的参数与输出约定

#### Scenario: Require explicit opt-in and a terminal

- **WHEN** 调用方省略引用与 `--backfill`，并且缺少 `--human` 或终端输入输出不可交互
- **THEN** CLI 返回参数错误

### Requirement: Human history reference completion

当用户在已配置 shell 补全的终端里，为带 `--human` 的 `history` 命令补全引用参数时，CLI MUST 使用交互选择器相同的候选与匹配规则，返回完整的三段式引用。

#### Scenario: Complete a fuzzy match with Tab

- **WHEN** 用户在启用补全的 zsh 中输入 `specify history --human rbl` 并按 Tab
- **THEN** shell 可以将匹配项补全为完整引用

### Requirement: Configurable human history limit

CLI MUST 接受项目配置中可选的正整数 `history.defaultLimit`。交互选取后的时间线查询 MUST 使用显式 `--limit`、项目配置、缺省值 3 的优先级。完整引用查询和版本 diff MUST 沿用现有条数规则。

#### Scenario: Configure the interactive default

- **WHEN** 项目设置 `history.defaultLimit: 5`，用户交互选中引用且未传 `--limit`
- **THEN** 命令最多显示最近 5 条符合查询条件的记录

#### Scenario: Use or override the built-in default

- **WHEN** 项目省略 `history.defaultLimit`
- **THEN** 交互选取后的时间线查询默认显示最近 3 条，显式 `--limit` 可以覆盖这一条数
