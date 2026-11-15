# Change `change.md` 格式

## 位置

```text
spec/changes/<status>/<kind>/<id>/change.md
```

## 原则

`change.md` 合并 proposal 与 design 原先承担的说明职责，记录理解本次变更所需的问题、上下文、目标、范围和技术考虑。它不进入正式 spec，也不传播到 `spec-index.md`。

文件内容没有强制章节、标题或顺序，CLI 只检查 `change.md` 是否存在，不校验 Markdown 格式。作者按变更大小自行取舍：

- 简单 bugfix 可用一段话说明错误和预期结果。
- 跨模块变更可以说明背景、目标、范围、关键决策、风险和迁移。
- 不需要的章节无需写“无”，直接省略。

## 简单修复示例

```markdown
登录接口在凭据过期时仍返回成功。修复为拒绝过期凭据；该行为已由
`capability:user-auth:password-login` Contract 要求，因此不需要 spec delta。
```

## 复杂变更示例

```markdown
# 背景

认证服务目前只接受密码凭据，用户希望使用注册过的通行密钥登录。

# 目标与范围

增加服务端通行密钥验证；注册界面和账户恢复流程不在本次范围内。

# 设计

复用现有会话签发逻辑，在凭据验证层增加通行密钥验证分支。

# 风险

验证库升级可能改变断言格式；在认证服务边界统一解析并覆盖兼容路径。
```

## 相关文件

- `tasks.md` 保存可执行工作和完成状态。
- `meta-data.yaml` 保存机器可读身份、影响目标、正文基线和 sync 回执。
- `deltas/` 只在正式 Contract 语义变化时出现。
