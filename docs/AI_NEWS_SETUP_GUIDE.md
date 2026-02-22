# AI News Alerts - Quick Setup Guide

## Step 1: Choose Your AI Provider

You can use either OpenAI (ChatGPT) or xAI (Grok). Both offer free tier options.

### Option A: OpenAI ChatGPT (Recommended)
- **Free Credit**: $5 for new accounts
- **Best For**: Most users, better documentation
- **Sign Up**: https://platform.openai.com/signup

### Option B: xAI Grok
- **Best For**: Users who prefer Grok's real-time capabilities
- **Sign Up**: https://x.ai/api

## Step 2: Get Your API Key

### For OpenAI:
1. Go to https://platform.openai.com/api-keys
2. Click "Create new secret key"
3. Name it "PortAct News Service"
4. Copy the key (starts with `sk-`)

### For Grok:
1. Go to https://x.ai/api
2. Generate an API key
3. Copy the key (starts with `xai-`)

## Step 3: Configure Environment

1. Copy the example environment file:
```bash
cd backend
cp .env.example .env
```

2. Edit `.env` and add your API key:

**For OpenAI:**
```bash
OPENAI_API_KEY=sk-your-actual-key-here
AI_NEWS_PROVIDER=openai
```

**For Grok:**
```bash
GROK_API_KEY=xai-your-actual-key-here
AI_NEWS_PROVIDER=grok
```

## Step 4: Restart the Application

```bash
# Stop the application if running
# Then restart it
cd /Users/debasis/Debasis/personal/Projects/PortAct
./scripts/restart_app.sh
```

## Step 5: Test the System

### Manual Test via API

```bash
# Get your auth token first by logging in
# Then trigger news fetch:

curl -X POST "http://localhost:8000/api/v1/alerts/fetch-news?limit=5" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### Check for Alerts

```bash
curl -X GET "http://localhost:8000/api/v1/alerts" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### View Alert Statistics

```bash
curl -X GET "http://localhost:8000/api/v1/alerts/stats" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

## Step 6: Access in Frontend

1. Navigate to the Alerts page in your web interface
2. Click "Fetch Latest News" button (if available)
3. Wait a few moments for processing
4. Refresh to see new alerts

## Automatic Scheduling

The system automatically runs twice daily:
- **Morning**: 9:00 AM IST
- **Evening**: 6:00 PM IST

No additional configuration needed!

## Verification Checklist

- [ ] API key added to `.env` file
- [ ] AI provider set correctly
- [ ] Application restarted
- [ ] Manual test successful
- [ ] Alerts appearing in frontend
- [ ] No errors in logs

## Troubleshooting

### "No API key configured" Error
- Check `.env` file has the correct key
- Verify no extra spaces or quotes
- Restart the application

### "API Error 401" 
- API key is invalid or expired
- Generate a new key
- Update `.env` file

### No Alerts Generated
- Check if you have active assets in portfolio
- Verify assets have valid symbols
- Try manual trigger first
- Check logs: `tail -f backend/logs/app.log`

### Rate Limit Errors
- Free tier has limited requests
- Reduce the `limit` parameter
- Wait before retrying
- Consider upgrading API plan

## Cost Estimates

### OpenAI (gpt-3.5-turbo)
- **Input**: ~$0.0005 per 1K tokens
- **Output**: ~$0.0015 per 1K tokens
- **Per Asset**: ~$0.002-0.005
- **Daily Cost** (20 assets): ~$0.08-0.20
- **Monthly** (with $5 credit): ~25-60 days free

### Grok
- Check current pricing at https://x.ai/api

## Best Practices

1. **Start Small**: Begin with `limit=5` to test
2. **Monitor Usage**: Check API dashboard regularly
3. **Review Alerts**: Mark as read to keep organized
4. **Adjust Schedule**: Modify if needed in `news_scheduler.py`
5. **Secure Keys**: Never share or commit API keys

## Next Steps

1. ✅ Set up API key
2. ✅ Test manual fetch
3. ✅ Review generated alerts
4. ⏰ Wait for automatic scheduled run
5. 📊 Monitor and optimize

## Support

- Full Documentation: `AI_NEWS_ALERTS_SYSTEM.md`
- API Docs: http://localhost:8000/docs
- Logs: `backend/logs/app.log`

---

**Made with Bob** 🤖