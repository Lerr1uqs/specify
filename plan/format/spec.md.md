# 正式 `spec.md` 格式

## 位置

```text
spec/specs/<type>/<spec-id>/spec.md
```

`<type>` 必须存在于 `config.yaml` 的 `specTypes`；`<spec-id>` 为 kebab-case 目录标识。

## 格式

```markdown
# contract

## [credential-validation] 凭据验证的职责

认证服务负责验证凭据并返回认证结果。

## [memory-responsibilities] bytes/int/deref 的职责拆分

明确 bytes、int 和 deref 各自的职责与边界。

## [string-decoder-reuse] 字符串命令复用 MemoryInspector decoder

字符串命令通过 MemoryInspector decoder 复用既有解码逻辑。
```

## 规则

- 文档必须恰好包含一个 `# contract` 顶层区块；change 的 `change.md` 留在 change 目录，不写入正式 spec。
- `# contract` 之前和第一条 Contract 之前不得有正文；HTML 注释与空白不算正文。
- `# contract` 下必须至少有一个 `## [<contract-id>] <contract-title>`；方括号内是稳定 ID，后面是可读标题。ID 后必须有一个空格分隔标题。
- Contract ID 为 kebab-case，在所属 spec 内唯一；创建后不得因标题或正文变化而修改。Contract title 可以使用汉字、空格、标点和专业术语。
- 新增 Contract 时由作者或 Agent 选定 ID 并写入标题；CLI 只校验，不根据标题自动生成或在重命名时重算。
- Contract title 不得包含 `->`，该字符序列保留给 delta 的 `RENAMED` 分隔符。
- 同一 spec 内的 Contract title 经 `NFKC(trim(collapse-whitespace(title)))` 规范化后也必须唯一；标题用于阅读和核对，不作为身份键。
- Contract 正文是该 `##` 标题之后、下一个顶层 `##` 或 `#` 之前的**原始 Markdown 源码**；文件结束也能终止正文。`###`、列表、引用和代码块保留在正文中，正文不得为空。
- 只有文档顶层的 Markdown 标题参与分块：围栏代码块、缩进代码块、引用块或列表内部看起来像 `#`、`##` 的内容都属于正文。围栏按 CommonMark 的配对规则处理。
- 计算正文版本 hash 时，先统一 `CRLF`/`CR` 为 `LF`，再去掉首尾空白行；保留内部空白、Markdown 标记与代码块内容，最后计算 UTF-8 字节的 SHA-256。标题和 ID 不参与正文 hash。
- 除 `# contract` 外，文档不允许出现其他顶层标题；遇到即报错（顶层标题同时结束当前 Contract 正文）。
- Contract 的全局机器引用为 `<type>:<spec-id>:<contract-id>`；作者在 Markdown 中明写 ID 与 title。
