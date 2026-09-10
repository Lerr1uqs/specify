# 正式 `spec.md` 格式

## 位置

```text
spec/specs/<type>/<spec-id>/spec.md
```

`<type>` 必须存在于 `config.yaml` 的 `specTypes`；`<spec-id>` 为 kebab-case 目录标识。

## 格式

```markdown
# proposal

简要叙述当前 spec 的上下文、目的和动机。

# contract

## 凭据验证的职责

认证服务负责验证凭据并返回认证结果。

## bytes/int/deref 的职责拆分

明确 bytes、int 和 deref 各自的职责与边界。

## 字符串命令复用 MemoryInspector decoder

字符串命令通过 MemoryInspector decoder 复用既有解码逻辑。
```

## 规则

- 文档必须恰好包含一个非空 `# proposal` 区块和一个 `# contract` 区块，二者按此顺序出现。
- `# proposal` 是索引提取的唯一来源，必须简要写清当前 spec 的上下文、目的和动机。
- `# contract` 下必须至少有一个 `## <contract-title>`；`##` 标题就是 Contract 的可读名称。
- Contract title 可以使用汉字、空格、标点和专业术语；不要求 kebab-case。
- Contract title 不得包含 `->`，该字符序列保留给 delta 的 `RENAMED` 分隔符。
- Contract 的内部唯一键是 `SHA-256(normalize(title))`，其中 `normalize` 为 `NFKC(trim(collapse-whitespace(title)))`。hash 不写入 Markdown、YAML、缓存或本地数据库；CLI 每次解析时计算。
- Contract 正文从该 `##` 标题之后开始，直到下一个同级 `##`、`#` 或文件结束。正文不得为空。
- 同一 spec 中不允许出现规范化后相同的 Contract title。
- Contract 的全局机器引用为 `<type>:<spec-id>:<contract-hash>`；作者在 Markdown 中只书写 title。
