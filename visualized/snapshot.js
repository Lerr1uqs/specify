// 来源为 example_specs 的 history JSON 和归档 metadata，页面本地读取快照。
const exampleSnapshot = {
  "contracts": {
    "expiry": {
      "ref": "capability:user-auth:session-expiry",
      "status": "active",
      "records": [
        {
          "idx": 1,
          "action": "add",
          "date": "2026-11-22 14:24:26+08:00",
          "changeId": null,
          "source": "backfill",
          "title": "会话过期",
          "content": "会话在过期时间到达后失效，后续请求必须重新认证。"
        },
        {
          "idx": 2,
          "action": "modify",
          "date": "2026-11-22 14:27:44+08:00",
          "changeId": "define-session-lifetime",
          "source": "sync",
          "title": "会话过期",
          "content": "会话自签发起最多有效 30 分钟。达到有效期后，后续请求必须重新认证。"
        },
        {
          "idx": 3,
          "action": "modify",
          "date": "2026-11-22 14:28:01+08:00",
          "changeId": "expire-idle-sessions",
          "source": "sync",
          "title": "会话过期",
          "content": "会话自签发起最多有效 30 分钟。自上次通过认证的请求起连续空闲满 10 分钟时，会话提前失效。尚未使用的会话从签发时开始计算空闲时间。会话失效后，后续请求必须重新认证。"
        }
      ]
    },
    "issuance": {
      "ref": "component:auth-service:session-issuance",
      "status": "active",
      "records": [
        {
          "idx": 1,
          "action": "add",
          "date": "2026-11-22 14:24:26+08:00",
          "changeId": null,
          "source": "backfill",
          "title": "会话签发职责",
          "content": "认证服务仅在凭据验证成功后签发会话，并设置会话过期时间。"
        },
        {
          "idx": 2,
          "action": "modify",
          "date": "2026-11-22 14:27:44+08:00",
          "changeId": "define-session-lifetime",
          "source": "sync",
          "title": "会话签发职责",
          "content": "认证服务仅在凭据验证成功后签发会话，并将会话过期时间设为签发时间加 30 分钟。"
        },
        {
          "idx": 3,
          "action": "modify",
          "date": "2026-11-22 14:28:01+08:00",
          "changeId": "expire-idle-sessions",
          "source": "sync",
          "title": "会话签发与过期职责",
          "content": "认证服务仅在凭据验证成功后签发会话。签发时设置 30 分钟的绝对有效期和 10 分钟的初始空闲期限。验证会话时，任一期限到达即拒绝请求；通过认证的请求只刷新空闲期限。"
        }
      ]
    }
  },
  "changes": {
    "define-session-lifetime": {
      "id": "define-session-lifetime",
      "title": "明确会话最长有效期",
      "kind": "feat",
      "status": "archived",
      "path": "spec/changes/archived/feat/2026-11-22-define-session-lifetime"
    },
    "expire-idle-sessions": {
      "id": "expire-idle-sessions",
      "title": "增加会话空闲超时",
      "kind": "feat",
      "status": "archived",
      "path": "spec/changes/archived/feat/2026-11-22-expire-idle-sessions"
    }
  }
};
