# 文件格式协议

本目录定义 Specify V1 的文件级格式。格式文件是实现 CLI parser、validator、scaffold 和 archive 的依据。

| 文件 | 路径 | 作用 | 协议 |
|---|---|---|---|
| 项目配置 | `spec/config.yaml` | type、kind 等项目级定义 | [config.yaml.md](config.yaml.md) |
| 正式 spec | `spec/specs/<type>/<spec-id>/spec.md` | 当前生效的事实 | [spec.md.md](spec.md.md) |
| Change metadata | `spec/changes/<status>/<kind>/<title>/meta-data.yaml` | change 身份、时间、影响目标 | [meta-data.yaml.md](meta-data.yaml.md) |
| Change proposal | `.../proposal.md` | 为什么改、改什么 | [proposal.md.md](proposal.md.md) |
| Change design | `.../design.md` | 本次如何实现 | [design.md.md](design.md.md) |
| Change tasks | `.../tasks.md` | 可执行、可跟踪的实施工作 | [tasks.md.md](tasks.md.md) |
| Delta | `.../deltas/<type>/<spec-id>.md` | 对正式 spec 中 Contract 的增量 | [delta.md.md](delta.md.md) |
| 规格索引 | `spec/spec-index.md` | 当前正式 spec 的自动导航 | [spec-index.md.md](spec-index.md.md) |

`init.yaml` 与最终写入项目的 `spec/config.yaml` 使用同一格式；前者是 `specify init . --config init.yaml` 的输入，后者是初始化输出。

`changes/archived/manifest.json` 是不可变 archive 的机器清单，属于实现细节；其格式在 archive 实现阶段另行定义。
