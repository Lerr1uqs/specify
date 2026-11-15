# `config.yaml` 格式

## 用途与位置

- 初始化前：任意位置的 `init.yaml`。
- 初始化后：`spec/config.yaml`。
- 两者结构完全相同。

## 格式

```yaml
specTypes:
  requirement:
    label: 需求
    description: 业务目标、触发条件和必须达到的结果
    template: template/requirement.md
  capability:
    label: 能力
    description: 面向用户或外部系统的可观察行为
    template: template/capability.md
  feature:
    label: 特性
    description: 一组面向用户的新功能和预期行为
    template: template/feature.md
  component:
    label: 组件
    description: 模块职责、边界、接口与依赖
    template: template/component.md
  architecture:
    label: 架构
    description: 系统、子系统和组件的结构关系
    template: template/architecture.md
  rule:
    label: 规则
    description: 跨能力或组件适用的稳定约束
    template: template/rule.md
  rule:
    label: 规则
    description: 跨能力或组件适用的稳定约束

kinds:
  feat:
    label: 功能
    description: 新增或扩展正式能力、组件或规则
  bugfix:
    label: 修复
    description: 修复实现或正式 spec 的错误
  simplify:
    label: 简化
    description: 降低复杂度而不增加能力
  refactor:
    label: 重构
    description: 改善内部结构
  arch:
    label: 架构
    description: 调整组件边界、依赖或架构决策
  test:
    label: 测试
    description: 补充或调整验证覆盖
```

## 规则

- `specTypes` 与 `kinds` 都必须是非空对象。
- key 必须是唯一 kebab-case 标识；它们用于目录名与 CLI 参数。
- 每项必须有非空 `label` 与 `description`。
- `specTypes` 条目可选 `template`，路径相对于 `spec/`，指向 `spec/template/` 下的 Markdown 文档。`specify create` 使用该文档作为新 spec 的初始内容。
- `kinds` 不支持 `template` 字段；遇到未知字段应报错，不应静默忽略。
- `specify init` 要求输入同时含非空 `specTypes` 与 `kinds`，缺一即失败。
- 初始化会在 `spec/template/` 安装内置模板；若目标文件已存在则保留用户版本。模板表达写作约定，不替代 parser 对 Markdown 结构和 Contract ID 的校验。
- CLI 随发行提供一份默认初始化文件（结构与上例同构），用户复制后即可作为 `--config` 的起点；该文件是 CLI 资产，不是项目内的固定路径。
