# AI-Powered News & Alerts System

## Overview

The AI-Powered News & Alerts System uses free-tier APIs from OpenAI (ChatGPT) or xAI (Grok) to fetch relevant, actionable information about your portfolio assets. The system automatically analyzes your holdings and creates alerts for significant events that could impact your investments.

## Features

- **AI-Powered Analysis**: Uses ChatGPT or Grok to analyze and filter relevant news
- **Smart Filtering**: Only reports significant, actionable information
- **Automatic Scheduling**: Runs twice daily (9 AM and 6 PM IST)
- **Manual Triggers**: On-demand news fetching via API
- **Multi-Asset Support**: Works with stocks, mutual funds, commodities, crypto, and more
- **Severity Levels**: Categorizes alerts as INFO, WARNING, or CRITICAL
- **Action Suggestions**: Provides recommended actions for each alert

## Supported AI Providers

### 1. OpenAI ChatGPT (Recommended for Free Tier)
- **Model**: gpt-3.5-turbo
- **Free Tier**: $5 credit for new accounts
- **API Endpoint**: https://api.openai.com/v1/chat/completions
- **Setup**: Get API key from https://platform.openai.com/api-keys

### 2. xAI Grok
- **Model**: grok-beta
- **API Endpoint**: https://api.x.ai/v1/chat/completions
- **Setup**: Get API key from https://x.ai/api

## Configuration

### Environment Variables

Add these to your `.env` file:

```bash
# AI News Configuration
OPENAI_API_KEY=sk-your-openai-api-key-here
GROK_API_KEY=xai-your-grok-api-key-here
AI_NEWS_PROVIDER=openai  # Options: "openai" or "grok"
```

### Getting API Keys

#### OpenAI (ChatGPT)
1. Go to https://platform.openai.com/signup
2. Create an account (free $5 credit for new users)
3. Navigate to https://platform.openai.com/api-keys
4. Click "Create new secret key"
5. Copy the key and add to `.env` file

#### xAI (Grok)
1. Go to https://x.ai/api
2. Sign up for API access
3. Generate an API key
4. Copy the key and add to `.env` file

## How It Works

### 1. Asset Analysis
The system analyzes each asset in your portfolio and builds a context-aware prompt:
- Asset name and symbol
- Asset type (stock, mutual fund, etc.)
- Current price and holdings

### 2. AI Query
The AI is asked to find:
- **Major News Events**: Breaking news, announcements, M&A activity
- **Policy Changes**: Regulatory changes, tax implications
- **Financial Performance**: Earnings surprises, dividend announcements
- **Market Impact**: Significant market movements, sector trends
- **Risk Alerts**: Credit rating changes, fraud alerts

### 3. Smart Filtering
The AI only reports information that:
- Is from the last 7 days
- Has material impact on the investment
- Requires investor attention or action
- Is significant (ignores minor price fluctuations)

### 4. Alert Creation
If significant news is found, an alert is created with:
- **Title**: Brief headline
- **Summary**: Detailed information
- **Impact**: How it affects your investment
- **Suggested Action**: What you should consider doing
- **Severity**: INFO, WARNING, or CRITICAL
- **Category**: Type of event (news, regulatory, earnings, etc.)

## API Endpoints

### 1. Fetch News for Portfolio
```http
POST /api/v1/alerts/fetch-news?limit=10
Authorization: Bearer <token>
```

**Description**: Triggers AI-powered news fetching for your portfolio assets.

**Parameters**:
- `limit` (optional): Maximum number of assets to process (default: 10, max: 50)

**Response**:
```json
{
  "message": "News fetching started in background",
  "status": "processing",
  "max_assets": 10
}
```

### 2. Get Alerts
```http
GET /api/v1/alerts?is_read=false&severity=critical
Authorization: Bearer <token>
```

**Parameters**:
- `is_read` (optional): Filter by read status
- `is_dismissed` (optional): Filter by dismissed status
- `severity` (optional): Filter by severity (info, warning, critical)
- `skip` (optional): Pagination offset
- `limit` (optional): Number of results (max: 1000)

### 3. Get Alert Statistics
```http
GET /api/v1/alerts/stats
Authorization: Bearer <token>
```

**Response**:
```json
{
  "total": 25,
  "unread": 5,
  "critical": 2
}
```

### 4. Mark Alert as Read
```http
PATCH /api/v1/alerts/{alert_id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "is_read": true
}
```

### 5. Delete Alert
```http
DELETE /api/v1/alerts/{alert_id}
Authorization: Bearer <token>
```

## Automatic Scheduling

The system automatically fetches news twice daily:

- **Morning**: 9:00 AM IST
- **Evening**: 6:00 PM IST

Each scheduled run processes up to 10 assets per user to stay within API rate limits.

## Alert Types

| Type | Description |
|------|-------------|
| `news_event` | General news and announcements |
| `regulatory_change` | Policy or regulatory changes |
| `earnings_report` | Earnings announcements and surprises |
| `dividend_announcement` | Dividend declarations |
| `market_volatility` | Significant market movements |

## Severity Levels

| Severity | Description | Use Case |
|----------|-------------|----------|
| `INFO` | Informational | General updates, minor news |
| `WARNING` | Attention needed | Moderate impact, review recommended |
| `CRITICAL` | Urgent action | High impact, immediate attention required |

## Usage Examples

### Example 1: Manual News Fetch
```bash
curl -X POST "http://localhost:8000/api/v1/alerts/fetch-news?limit=5" \
  -H "Authorization: Bearer your-token-here"
```

### Example 2: Get Unread Critical Alerts
```bash
curl -X GET "http://localhost:8000/api/v1/alerts?is_read=false&severity=critical" \
  -H "Authorization: Bearer your-token-here"
```

### Example 3: Mark Alert as Read
```bash
curl -X PATCH "http://localhost:8000/api/v1/alerts/123" \
  -H "Authorization: Bearer your-token-here" \
  -H "Content-Type: application/json" \
  -d '{"is_read": true}'
```

## Sample Alert

```json
{
  "id": 123,
  "user_id": 1,
  "asset_id": 456,
  "alert_type": "earnings_report",
  "severity": "warning",
  "title": "Infosys Q4 Earnings Beat Expectations",
  "message": "Infosys reported Q4 earnings with revenue growth of 15% YoY, beating analyst estimates. The company also announced a special dividend of ₹20 per share.\n\nImpact: Positive earnings surprise may lead to stock price appreciation. Special dividend provides additional returns.",
  "suggested_action": "Consider holding the position. Monitor for any guidance changes in the earnings call.",
  "is_read": false,
  "is_dismissed": false,
  "is_actionable": true,
  "alert_date": "2026-02-17T10:30:00Z",
  "created_at": "2026-02-17T10:30:00Z"
}
```

## Best Practices

### 1. API Key Management
- Never commit API keys to version control
- Use environment variables
- Rotate keys periodically
- Monitor API usage

### 2. Rate Limiting
- Free tier has limited requests
- System processes top 10 assets per user
- Scheduled runs are spaced 9 hours apart
- Manual triggers should be used sparingly

### 3. Alert Management
- Review alerts regularly
- Mark as read after reviewing
- Dismiss non-actionable alerts
- Use severity filters for prioritization

### 4. Cost Optimization
- Start with OpenAI's free $5 credit
- Monitor token usage
- Adjust asset limit based on portfolio size
- Consider upgrading if needed

## Troubleshooting

### No Alerts Generated
- Check if API key is configured correctly
- Verify AI provider is set in `.env`
- Check logs for API errors
- Ensure assets have valid symbols

### API Errors
- Verify API key is valid and not expired
- Check API rate limits
- Review error logs in `logs/app.log`
- Test API key with curl

### Scheduler Not Running
- Check if scheduler started in logs
- Verify timezone settings
- Restart application
- Check for scheduler errors

## Monitoring

### Logs
Check application logs for news fetching activity:
```bash
tail -f logs/app.log | grep "news"
```

### Database
Query alerts table to see generated alerts:
```sql
SELECT COUNT(*), severity, alert_type 
FROM alerts 
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY severity, alert_type;
```

## Future Enhancements

- [ ] Email notifications for critical alerts
- [ ] Webhook support for external integrations
- [ ] Custom alert rules and filters
- [ ] Historical news archive
- [ ] Sentiment analysis
- [ ] Multi-language support
- [ ] Mobile push notifications

## Support

For issues or questions:
1. Check logs in `logs/app.log`
2. Review API documentation
3. Test API keys manually
4. Check GitHub issues

## License

This feature is part of PortAct and follows the same license.

---

**Made with Bob** 🤖