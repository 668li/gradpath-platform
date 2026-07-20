# GradPath n8n Setup Guide

## 1. Install n8n

### Option A: Docker (Recommended)

```bash
# Pull and run n8n
docker run -it --rm \
  --name n8n \
  -p 5678:5678 \
  -v ~/.n8n:/home/node/.n8n \
  -e GRADPATH_API_URL=http://host.docker.internal:8000 \
  -e GRADPATH_ADMIN_TOKEN=<your-admin-jwt> \
  n8nio/n8n

# Or with docker-compose
version: '3'
services:
  n8n:
    image: n8nio/n8n
    ports:
      - "5678:5678"
    volumes:
      - ~/.n8n:/home/node/.n8n
    environment:
      - GRADPATH_API_URL=http://host.docker.internal:8000
      - GRADPATH_ADMIN_TOKEN=<your-admin-jwt>
```

### Option B: npm (Local)

```bash
# Install globally
npm install n8n -g

# Start n8n
n8n start

# Or with environment variables
GRADPATH_API_URL=http://localhost:8000 GRADPATH_ADMIN_TOKEN=<token> n8n start
```

## 2. Configure Credentials

### In n8n UI

1. Open n8n at `http://localhost:5678`
2. Go to **Credentials** → **Add Credential**
3. Select **HTTP Header Auth**
4. Configure:

| Field | Value |
|-------|-------|
| Name | `GradPath API` |
| Header Name | `Authorization` |
| Header Value | `Bearer <your-admin-jwt>` |

### Environment Variables

Set these in your environment or in n8n settings:

```bash
# Required
GRADPATH_API_URL=http://localhost:8000
GRADPATH_ADMIN_TOKEN=<your-admin-jwt>

# Optional
N8N_BASIC_AUTH_ACTIVE=true
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=<secure-password>
```

## 3. Import Workflow Templates

### Via UI

1. Open n8n at `http://localhost:5678`
2. Go to **Workflows**
3. Click **Import from File**
4. Select workflow JSON from `n8n/workflows/`:
   - `grad-crawler-scheduler.json`
   - `data-update-notification.json`
   - `auto-crawl-schedule.json`
   - `data-quality-monitor.json`
   - `community-digest.json`

### Via CLI

```bash
# Import all workflows
for file in n8n/workflows/*.json; do
  n8n import:workflow --input="$file"
done
```

## 4. Configure Workflows

### auto-crawl-schedule.json

**Purpose**: Automatically run yanzhao crawler daily at 2:00 AM UTC

**Configuration**:
- Edit cron expression in "Daily 02:00 UTC" node to change schedule
- Verify `GRADPATH_API_URL` environment variable is set
- Test with "Execute Workflow" button

### data-quality-monitor.json

**Purpose**: Monitor dark knowledge data quality weekly

**Configuration**:
- Runs every Sunday at 8:00 AM UTC
- Alert threshold: 1000 items (configurable in "Count Below 1000?" node)
- Webhook notification on data quality issues

### community-digest.json

**Purpose**: Send daily community digest with top 5 experience posts

**Configuration**:
- Runs daily at 8:00 AM UTC
- Adjust `limit=5` parameter to change number of posts
- Customize message template in "Format Digest" node

## 5. Test Workflows

### Manual Trigger

1. Open workflow in n8n
2. Click **Execute Workflow**
3. Check execution results in **Executions** tab

### Test Credentials

```bash
# Test API connection
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/crawlers

# Test webhook
curl -X POST http://localhost:5678/webhook/data-update \
  -H "Content-Type: application/json" \
  -d '{"source_name":"test","items_stored":1}'
```

## 6. Monitor Executions

- **Executions**: View all workflow runs in n8n UI
- **Error Handling**: Workflows include error notifications
- **Logs**: Check n8n logs for debugging

```bash
# View n8n logs (Docker)
docker logs n8n

# View n8n logs (npm)
# Logs are in ~/.n8n/logs/
```

## 7. Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| n8n won't start | Check port 5678 is available |
| HTTP requests fail | Verify GradPath backend is running |
| Credentials error | Re-create HTTP Header Auth credential |
| Cron not triggering | Check timezone settings in n8n |

### Debug Mode

```bash
# Start n8n with debug logging
DEBUG=n8n:* n8n start

# Or Docker
docker run -e DEBUG=n8n:* n8nio/n8n
```

## 8. Advanced Configuration

### Custom Webhooks

To receive data from GradPath backend:

1. Import `data-update-notification.json`
2. Activate workflow
3. Webhook URL will be: `http://localhost:5678/webhook/data-update`
4. Configure GradPath backend to send webhooks to this URL

### Scheduled Exports

To export data on schedule:

1. Create new workflow
2. Add Cron trigger
3. Add HTTP Request node to fetch data
4. Add email/file nodes to export

## 9. Security Notes

- Never commit `GRADPATH_ADMIN_TOKEN` to version control
- Use n8n's built-in credential encryption
- Enable basic auth for production
- Restrict webhook access with firewall rules

## 10. Next Steps

- [ ] Set up email notifications
- [ ] Configure Slack/WeChat integrations
- [ ] Add error alerting
- [ ] Set up workflow versioning
- [ ] Create custom nodes for GradPath-specific logic