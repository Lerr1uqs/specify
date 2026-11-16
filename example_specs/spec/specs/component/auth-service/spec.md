# contract

## [credential-validation] 凭据验证职责

认证服务验证密码或通行密钥凭据，并返回认证结果。它不负责发送验证码或管理客户端密钥。

## [session-issuance] 会话签发职责

认证服务仅在凭据验证成功后签发会话，并设置会话过期时间。
