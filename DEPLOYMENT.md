# Deployment Guide for AUTO QUIZ CREATE BOT

## Overview
This guide covers how to deploy your Telegram bot to Render.com or any other Python hosting platform.

## Prerequisites
- A Telegram Bot Token (from [@BotFather](https://t.me/botfather))
- A Google Gemini API Key (from [Google AI Studio](https://makersuite.google.com/app/apikey))
- A GitHub account (to push your code)
- A Render account (free tier available at [render.com](https://render.com))

---

## Step 1: Push Code to GitHub

1. Create a new repository on GitHub
2. Push your bot code to the repository:

```bash
git init
git add .
git commit -m "Initial commit - AUTO QUIZ CREATE BOT"
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

---

## Step 2: Deploy on Render

### Option A: Automatic Deployment (Using render.yaml)

1. **Sign up/Login to Render**: Go to [render.com](https://render.com) and create an account

2. **Create New Background Worker**:
   - Click "New +" → "Background Worker"
   - Connect your GitHub repository
   - Render will automatically detect the `render.yaml` file
   
   **Note**: Use "Background Worker" not "Web Service" because Telegram bots using polling don't need to expose any ports.

3. **Configure Environment Variables**:
   - In the Render dashboard, go to your service's "Environment" section
   - Add the following secrets:
     ```
     TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
     GOOGLE_API_KEY=your_google_gemini_api_key_here
     ```

4. **Deploy**:
   - Click "Create Background Worker"
   - Render will automatically build and deploy your bot
   - Wait for the deployment to complete (usually 2-5 minutes)

### Option B: Manual Deployment

1. **Create New Background Worker** on Render (NOT Web Service)

2. **Configure Build Settings**:
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python -m bot.main`
   - **Plan**: Free

3. **Add Environment Variables**:
   ```
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
   GOOGLE_API_KEY=your_google_gemini_api_key_here
   ```

4. **Deploy**: Click "Create Background Worker"

---

## Step 3: Verify Deployment

1. **Check Logs**:
   - Go to your service's "Logs" tab on Render
   - You should see: `Bot is starting...`
   - No errors should appear

2. **Test the Bot**:
   - Open Telegram
   - Search for your bot (the name you gave it in BotFather)
   - Send `/start` command
   - Try generating a quiz: `/cquiz Cell Biology 3`

---

## Alternative Deployment Options

### Deploy on Railway.app

1. Install Railway CLI or use their web interface
2. Create new project from GitHub
3. Add environment variables:
   ```
   TELEGRAM_BOT_TOKEN=your_token
   GOOGLE_API_KEY=your_key
   ```
4. Deploy with: `railway up`

### Deploy on Heroku

1. Install Heroku CLI
2. Create `Procfile`:
   ```
   worker: python -m bot.main
   ```
3. Deploy:
   ```bash
   heroku create your-bot-name
   heroku config:set TELEGRAM_BOT_TOKEN=your_token
   heroku config:set GOOGLE_API_KEY=your_key
   git push heroku main
   heroku ps:scale worker=1
   ```

### Deploy on PythonAnywhere

1. Upload files via their web interface
2. Create a new task (scheduled or always-on)
3. Set environment variables in .env file
4. Run: `python -m bot.main`

### Deploy on Google Cloud Run

Use the included `render.yaml` as reference and adapt for Cloud Run configuration.

---

## Troubleshooting

### Bot doesn't respond
- Check that environment variables are set correctly
- Verify the bot token is valid (test with BotFather)
- Check service logs for errors

### "Model not found" error
- Ensure your Google API key is valid
- Check that you have access to Gemini models
- Verify the model name in `bot/quiz_generator.py`

### Questions not generating
- Check API quota limits on Google AI Studio
- Verify internet connectivity from your deployment
- Review error messages in logs

### Deployment fails
- Ensure `requirements.txt` is present
- Check Python version compatibility (3.11+)
- Review build logs for specific errors

---

## Monitoring

### Check Bot Health
- Monitor logs regularly on your hosting platform
- Set up alerts for crashes/errors
- Track API usage on Google AI Studio

### Performance Metrics
- Response time for quiz generation
- API call success rate
- Number of users/requests

---

## Updating the Bot

When you make changes to the code:

1. Commit and push changes to GitHub:
   ```bash
   git add .
   git commit -m "Update: description of changes"
   git push
   ```

2. Render will automatically detect changes and redeploy
   - Or manually trigger deployment from Render dashboard

---

## Cost Considerations

### Free Tier Limits
- **Render**: 750 hours/month (enough for one always-on service)
- **Google Gemini**: Generous free tier (check current limits)
- **Telegram**: Free, no limits

### Optimization Tips
- Cache common responses if needed
- Implement rate limiting for users
- Monitor API usage to stay within free tier

---

## Security Best Practices

1. **Never commit API keys** to GitHub
2. **Use environment variables** for all secrets
3. **Enable 2FA** on all services
4. **Regularly rotate** API keys
5. **Monitor** for unusual activity

---

## Support

For issues:
1. Check logs first
2. Review error messages
3. Consult platform documentation
4. Open an issue on your GitHub repository

---

## Next Steps

After successful deployment:
1. ✅ Share your bot with users
2. ✅ Gather feedback
3. ✅ Add new features (chapter validation, difficulty levels, etc.)
4. ✅ Monitor performance and optimize

**Your bot is now live! 🎉**
