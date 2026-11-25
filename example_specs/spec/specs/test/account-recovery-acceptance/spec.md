# contract

## [expired-challenge-rejected] 过期恢复凭证无法重置密码

### 关联 Contract

- @[rule:recovery-policy:challenge-expiry]
- @[capability:account-recovery:reset-password]

### 前置条件

准备一个可登录的测试账号，并签发一份未使用的恢复凭证。测试环境支持推进时钟。

### 验收步骤

1. 将测试时钟推进到签发后 11 分钟。
2. 使用这份凭证提交密码重置，再分别尝试用原密码和本次提交的新密码登录。

### 通过标准

- 重置请求被拒绝。
- 原密码仍能登录，本次提交的新密码无法登录。

## [used-challenge-rejected] 已成功用过的恢复凭证无法再次使用

### 关联 Contract

- @[rule:recovery-policy:challenge-expiry]
- @[capability:account-recovery:reset-password]

### 前置条件

准备一个测试账号和一份新签发的恢复凭证，整个场景在凭证有效期内完成。

### 验收步骤

1. 使用凭证把账号密码改成密码 A，并确认 A 可以登录。
2. 用同一份凭证尝试把密码改成密码 B，再分别用 A 和 B 登录。

### 通过标准

- 第一次重置成功，第二次重置被拒绝。
- 密码 A 仍能登录，密码 B 无法登录。
