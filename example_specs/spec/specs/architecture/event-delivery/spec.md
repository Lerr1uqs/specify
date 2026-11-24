# contract

## [event-routing] 恢复通知的事件路由

```pele
flowchart LR
  auth[认证服务] -->|创建通知任务| task[通知任务]
  task --> notify[通知服务]
  notify -->|投递| mail[邮件服务]
  notify -.->|投递结果| auth
```

一条通知任务对应单次恢复通知。任务标识贯穿请求、重试和终态回执。

## [dependency-direction] 通知服务的依赖方向

认证服务通过任务接口发起投递，并通过投递结果接口读取状态。通知服务依赖邮件服务，不读取账号或会话存储。
