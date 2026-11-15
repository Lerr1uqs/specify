# Python 实现边界

本文档说明实现模块怎样对应协议，不增加新的用户行为。实现目标是让每个模块只承担一类工作：CLI 解析参数和展示结果，服务对象编排文件流程，解析器负责 Markdown 结构，模型保存业务数据。

## 技术栈

- Python ≥ 3.11，`src/` 布局，`click` 命令行。
- `markdown-it-py` 读取 Markdown token 与源码行号；正文必须从原始 Markdown 行切片，不能重渲染 inline token。
- `ruamel.yaml` 读写项目与 change metadata。
- `pytest` 覆盖 parser、sync 冲突、所有 CLI action 与状态迁移。

## 模块职责

```text
src/specify/
├── cli.py              # Click 参数适配、输出、调用服务
├── models.py           # Contract、Delta、Change、Issue 等类型化对象
├── paths.py            # RepoPaths 与 ChangeTree
├── config.py           # 配置和 metadata YAML 文件操作
├── contract.py         # 显式 ID、标题规范化、正文版本 hash
├── parse/
│   ├── document.py     # 顶层 Markdown 标题与原始正文边界
│   ├── spec.py         # SpecParser
│   ├── delta.py        # DeltaParser
│   └── tasks.py        # TaskParser
├── validate/
│   ├── specs.py        # SpecTreeValidator
│   └── changes.py      # ChangeValidator
├── baseline.py        # BaselineCapture
├── merge.py           # DeltaMerger，纯内存操作
├── sync.py            # SpecSynchronizer，预检、多目标写入和回执
├── archive.py         # ArchiveService 与 ArchiveValidator
├── index.py            # SpecIndex
├── scaffold.py         # 初始化与文件骨架
└── io.py               # 原子写入、hash、.trash 移动
```

## 调用边界

1. CLI 在入口读取项目配置、定位 change，并把业务工作交给服务对象；Click handler 不实现解析或 delta 规则。
2. Parser 把 Markdown 转成类型化对象并指出路径/行范围；校验器在边界检查用户文件一次。
3. `DeltaMerger` 只操作内存对象，不读写文件。`SpecSynchronizer` 先校验所有基线和目标，内存中准备全部结果，再写正式 specs、重建索引，最后记录 YAML 回执。
4. `ArchiveService` 核对已同步 delta 的 hash，只移动 change 并追加 manifest，不调用 sync 或 merge。
5. Contract ID 与正文 hash 分开处理：ID 定位对象，正文 hash 检测起草基线是否过期。

## 验证范围

- Markdown：显式 ID、唯一性、围栏/引用/列表/嵌套标题边界、正文 hash 规范化。
- Merge：`RENAMED → MODIFIED → ADDED → REMOVED`，重复 ID、标题冲突和全 spec remove。
- Change lifecycle：所有 CLI action、合法与非法状态转移、拒绝与回收站移动。
- Sync：多目标预检；任意基线冲突时不写任何 spec、索引或 receipt；成功回执幂等；成功后 delta 固定。
- Archive：缺失/过期回执被拒绝；archive 不重放 delta；manifest 可检测篡改。
