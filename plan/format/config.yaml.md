# `config.yaml` 格式

## 用途与位置

- 初始化前：任意位置的 `init.yaml`。
- 初始化后：`spec/config.yaml`。
- 两者结构完全相同。

## 格式

```yaml
specTypes:
  capability:
    label: 能力
    description: 面向用户或外部系统的可观察行为
  component:
    label: 组件
    description: 模块职责、边界、接口与依赖
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
- V1 不支持 `template` 字段；遇到未知字段应报错，不应静默忽略。
