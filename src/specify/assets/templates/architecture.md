# contract

## [architecture-id1] 系统架构

架构树
```
- 系统
  - 子系统或组件
    - 子组件
```

说明: 解释节点职责、边界和关键依赖。架构树展示结构；本节补充树无法表达的约束。

## [architecture-id2] 事件输出架构

for example： tree展开
```
GuestEvent
├── 人类视图：终端 / 文本文件
│   ├── JNICALL / SYSCALL / SYSPROP / LOGCAT / COMMAND / ERROR / STDIO
│   └── BREAKPOINT / WATCHPOINT（默认不刷终端）
└── agent 视图：.rundroid-tmp/*.jsonl
    └── 与人类视图共用事件顺序和事实字段

EmulatorLog
└── kernel / linker / loader / memory / backend / hook（debug / info / error / fatal）

TelemetryEvent
└── 内部结构化数据：replay / diff / 统计 / UT/IT 断言
```

## [architecture-id3] 业务系统组件架构

可以使用mermaid 也可以使用 obsidian pele
```mermaid
flowchart TB
    subgraph Client["接入层 / Client"]
        direction LR
        Web["Web 前端<br/>(React / Vue)"]
        App["移动端 / 小程序"]
        OpenAPI["开放 API 调用方"]
    end

    subgraph Gateway["网关层 / Gateway"]
        GW["API Gateway<br/>路由 · 鉴权 · 限流"]
        CDN["CDN / 静态资源"]
    end

    subgraph Service["服务层 / Services"]
        direction LR
        Auth["认证服务<br/>Auth Service"]
        User["用户服务<br/>User Service"]
        Order["订单服务<br/>Order Service"]
        Pay["支付服务<br/>Payment Service"]
        Notify["消息通知服务<br/>Notify Service"]
    end

    subgraph Middleware["中间件 / Infrastructure"]
        direction LR
        MQ[["消息队列<br/>Kafka / RabbitMQ"]]
        Cache[("缓存<br/>Redis")]
        Search[("搜索引擎<br/>Elasticsearch")]
    end

    subgraph Data["数据层 / Data"]
        direction LR
        DB1[("用户库<br/>MySQL")]
        DB2[("订单库<br/>MySQL")]
        OSS[("对象存储<br/>OSS / S3")]
    end

    subgraph Ops["可观测 / Observability"]
        direction LR
        Log["日志<br/>ELK"]
        Metric["监控告警<br/>Prometheus + Grafana"]
        Trace["链路追踪<br/>Jaeger"]
    end

    Web --> CDN --> GW
    App --> GW
    OpenAPI --> GW

    GW --> Auth
    GW --> User
    GW --> Order
    GW --> Pay

    Auth -.JWT 校验.-> User
    Order --> Pay
    Order --> MQ
    Pay --> MQ
    MQ --> Notify

    User --> Cache
    User --> DB1
    Order --> DB2
    Order --> Cache
    Order --> Search
    User --> OSS

    Service -.埋点.-> Ops
    Gateway -.埋点.-> Ops
```
