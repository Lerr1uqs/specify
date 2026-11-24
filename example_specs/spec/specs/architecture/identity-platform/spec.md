# contract

## [service-boundaries] 身份平台服务边界

```pele
flowchart LR
  auth[认证服务：登录、会话、恢复凭证、密码更新]
  notify[通知服务：恢复通知投递与重试]
  auth -->|恢复通知请求| notify
  notify -->|投递状态| auth
```

认证服务掌握账号凭据和认证结果。通知服务只处理投递所需的信息。

## [data-flow] 恢复校验与通知数据流

```pele
flowchart LR
  browser[浏览器] -->|发起恢复| auth[认证服务]
  auth -->|恢复通知| notify[通知服务]
  notify -->|投递| mail[邮件服务]
  notify -.->|投递状态| auth
  auth -->|凭证校验| verify[凭证验证]
  verify -->|通过| reset[密码更新]
```

恢复通知和状态通过通知编号关联。认证服务统一验证凭证和有效期，并在同一凭证累计五次失败后拒绝后续验证。
