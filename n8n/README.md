# GradPath n8n Workflow Templates

## Overview

[n8n](https://n8n.io) is a workflow automation tool. These templates integrate with GradPath's crawler system for scheduled data collection and user notifications.

## Setup

### 1. Install n8n

```bash
# Docker (recommended)
docker run -it --rm \
  --name n8n \
  -p 5678:5678 \
  -v ~/.n8n:/home/node/.n8n \
  n8nio/n8n

# Or npm
npm install n8n -g
n8n start
```

### 2. Configure Credentials

In n8n UI, add credentials:

| Name | Type | Fields |
|------|------|--------|
| GradPath API | HTTP Header Auth | `Authorization: Bearer <admin_token>` |
| GradPath WS | WebSocket | `ws://backend:8000/ws/{user_id}?token=<token>` |

### 3. Import Workflows

1. Open n8n at `http://localhost:5678`
2. Go to **Workflows** → **Import from File**
3. Select workflow JSON from `n8n/workflows/`

## Workflows

### grad-crawler-scheduler.json

**Trigger**: Cron schedule (default: daily at 02:00 UTC)

**Flow**:
1. Cron trigger fires
2. HTTP Request: GET `/api/crawlers` (list available crawlers)
3. Split In Batches: Process each crawler
4. HTTP Request: POST `/api/crawlers/run` (trigger crawl)
5. Wait: Poll `/api/crawlers/status/{task_id}` until complete
6. Aggregate results
7. IF errors > 0 → Send alert notification

**Customization**:
- Edit cron expression in trigger node
- Modify crawler list in filter node
- Configure notification webhook URL

### data-update-notification.json

**Trigger**: Webhook from GradPath backend

**Flow**:
1. Webhook receives `POST /webhook/data-update`
2. Extract: `source_name`, `items_stored`, `timestamp`
3. HTTP Request: GET `/api/crawlers/runs?source_name={name}&limit=1` (get stats)
4. Template: Format notification message
5. Switch: Route by notification type (email/push/webhook)
6. Send notifications to subscribed users

**Webhook Payload**:
```json
{
  "source_name": "kaoyan_news",
  "items_stored": 15,
  "timestamp": "2026-07-11T02:30:00Z"
}
```

## Environment Variables

Set in n8n or via environment:

```bash
GRADPATH_API_URL=http://localhost:8000
GRADPATH_ADMIN_TOKEN=<your-admin-jwt>
```

## Troubleshooting

- **Workflow won't start**: Check n8n logs, verify cron timezone
- **HTTP requests fail**: Verify GradPath backend is running, check CORS
- **Notifications not sent**: Check webhook URL, verify user subscriptions
