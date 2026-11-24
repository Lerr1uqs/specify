- [ ] spec 有过时有冲突如何调整？skill？
- [ ] rule应该是必须遵守的规定
- [ ] archive之前应该强制一次 sync的检查？
- [ ] 有问题怎么抛出给前端展示呢？sync检查？
- [ ]  specify history requirement:backend-indicators-signals:line-touch-signal --limit 3 --human 每次都要好长一段 补全+交互式的方式最好 比如我 可以看到全部候选的折叠 但是我选择 r就能筛选出来一部分 rbl 就能选择这个了？

## 待做

- [ ] **Change 交接**：让 `specify change status` 输出当前阶段、缺失项、相关文件和建议的下一步，方便人或 agent 接手。
- [ ] **Contract Audit**：用同一次审查检查当前代码是否满足 Contract，以及相关 Contract 之间是否存在矛盾。统一报告涉及的 Contract、代码或测试证据，以及发现的缺口和冲突。
- [ ] **并行 Change 预检**：在 sync 前列出哪些活跃 Change 改动了同一个 Contract、各自基于哪个版本，以及先同步谁会让哪些基线过期。
