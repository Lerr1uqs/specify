# Change `design.md` 格式

## 位置

```text
spec/changes/<status>/<kind>/<title>/design.md
```

## 格式

```markdown
# design

## Approach

本次实施采用的整体技术路径。

## Decisions

### 验证码存储位置

选择原因、约束和结果。

## Alternatives

### 仅使用密码登录

不采用的原因。

## Risks

- 风险：短信服务不可用。
  缓解：提供重试与明确失败反馈。

## Migration

部署、兼容、回滚或数据迁移策略；无迁移时明确写“无”。
```

## 规则

- 顶层标题必须为 `# design`。
- `## Approach`、`## Decisions`、`## Alternatives`、`## Risks`、`## Migration` 必须存在。
- 每个关键决策必须说明理由；每个有实际竞争关系的替代方案必须说明未采用原因。
- 未发现风险、替代方案或迁移时，保留相应标题并明确写“无”，不要删除标题。
- design 说明本次 change 的技术实现，不复制正式 spec 的 Contract 正文。
