#!/usr/bin/env bash
# 统一推送适配层（2026-09-25）：主通道 WxPusher（500条/天），失败兜底 Server酱（5条/天）
# 用法: send_notify.sh "标题" "正文"
# 输出: 单行结果（wxpusher:ok / wxpusher:fail <resp> / serverchan:ok / serverchan:ok(fallback) / serverchan:fail <resp>）
#       退出码 0=至少一个通道成功，1=全部失败
# 凭据: /home/ubuntu/.wxpusher.json（600，appToken+uid）与 /home/ubuntu/.sec_webhook_url（600）
#       两文件绝不入库。WxPusher 判定必须看 data[].code——顶层 code:1000 只代表 API 收到，
#       用户未订阅应用时内层 code:1001（2026-09-25 实测假阳性）。
set -u
TITLE="${1:-GradPath 通知}"
BODY="${2:-（空）}"
WXP_FILE="/home/ubuntu/.wxpusher.json"
SEC_FILE="/home/ubuntu/.sec_webhook_url"

# ---- 主通道 WxPusher ----
if [ -f "$WXP_FILE" ]; then
  APP_TOKEN=$(python3 -c 'import json;print(json.load(open("'"$WXP_FILE"'"))["appToken"])' 2>/dev/null || true)
  WXP_UID=$(python3 -c 'import json;print(json.load(open("'"$WXP_FILE"'"))["uid"])' 2>/dev/null || true)
fi
if [ -n "${APP_TOKEN:-}" ] && [ -n "${WXP_UID:-}" ]; then
  # summary=微信通知栏摘要(≤99字)；content=标题+正文
  JSON=$(python3 -c '
import json,sys
body={
  "appToken": sys.argv[1],
  "uids": [sys.argv[2]],
  "summary": sys.argv[3][:99],
  "content": sys.argv[3] + "\n\n" + sys.argv[4],
  "contentType": 1,
}
print(json.dumps(body, ensure_ascii=False))
' "$APP_TOKEN" "$WXP_UID" "$TITLE" "$BODY")
  RESP=$(curl -s -m 15 -X POST -H "Content-Type: application/json" \
    -d "$JSON" "https://wxpusher.zjiecode.com/api/send/message" 2>&1)
  VERDICT=$(printf '%s' "$RESP" | python3 -c '
import json,sys
try:
    d=json.load(sys.stdin)
    data=d.get("data") or []
    if d.get("code")==1000 and data and all(x.get("code")==1000 for x in data):
        print("ok")
    else:
        print("fail:" + json.dumps(d,ensure_ascii=False)[:300])
except Exception as e:
    print("fail:" + str(e))
' 2>/dev/null)
  if [ "$VERDICT" = "ok" ]; then
    echo "wxpusher:ok"
    exit 0
  fi
  echo "wxpusher:fail $VERDICT"
else
  echo "wxpusher:skip (credential missing)"
fi

# ---- 兜底通道 Server酱 ----
if [ -f "$SEC_FILE" ]; then
  RESP2=$(curl -s -m 10 \
    --data-urlencode "title=$TITLE" \
    --data-urlencode "content=$BODY" \
    "$(cat "$SEC_FILE")" 2>&1)
  if printf '%s' "$RESP2" | grep -q '"errno":0'; then
    echo "serverchan:ok(fallback)"
    exit 0
  fi
  echo "serverchan:fail $(printf '%s' "$RESP2" | tr -d '\n' | cut -c1-200)"
  exit 1
fi
exit 1
