# Render Deployment Guide (Free Web Service)

## Steps to Deploy on Render

### 1. Create PostgreSQL Database
1. Render Dashboard pe jao
2. **New +** → **PostgreSQL** select karo
3. Free plan select karo
4. Database create karo
5. **Internal Database URL** copy karo (ye `DATABASE_URL` ke liye chahiye)

### 2. Create Web Service
1. Render Dashboard pe jao
2. **New +** → **Web Service** select karo
3. GitHub repository connect karo
4. Settings:
   - **Name**: drquiz-telegram-bot (ya koi bhi naam)
   - **Environment**: Python
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python run.py`
   - **Plan**: Free

### 3. Add Environment Variables
Environment Variables section me ye add karo:

```
TELEGRAM_BOT_TOKEN = <your_telegram_bot_token>
GEMINI_API_KEY = <your_gemini_api_key>
DATABASE_URL = <internal_database_url_from_step_1>
```

**Important**: Render automatically `PORT` environment variable provide karta hai, manually add karne ki zarurat nahi hai.

### 4. Deploy
- **Create Web Service** button click karo
- Deployment start hogi
- Logs me ye dikhna chahiye:
  ```
  ✅ Database connection pool initialized successfully
  Starting web server on port 10000...
  Web server started!
  Application started
  ```

### 5. Health Check
Deploy hone ke baad browser me apne app ka URL kholo:
- `https://your-app-name.onrender.com/` → "Bot is running!" dikhna chahiye
- `https://your-app-name.onrender.com/health` → "Bot is running!" dikhna chahiye

## How It Works

Bot **polling mode** me run hota hai aur saath me ek **web server** bhi chalta hai:
- Web server Render ko batata hai ki service alive hai (health check)
- Bot Telegram se messages receive karta hai (polling)
- Dono ek saath chalte hain background me

## Features That Work
✅ All commands (`/start`, `/cquiz`, `/jeequiz`, etc.)
✅ Conversational AI (natural language)
✅ Group chat support (mention bot with @)
✅ Leaderboards
✅ Admin features
✅ Quiz sessions
✅ Database storage

## Troubleshooting

### Bot not responding?
1. Render logs check karo: "Application started" dikhna chahiye
2. Health check endpoint test karo
3. Environment variables verify karo

### Database errors?
1. `DATABASE_URL` correctly set hai?
2. PostgreSQL database running hai?
3. Database same region me hai?

### Deployment fails?
1. Build logs dekho kaunsa package install nahi ho raha
2. `requirements.txt` me sab dependencies hain?

## Cost
- **Web Service (Free)**: Bot running
- **PostgreSQL (Free)**: Database (90 days free, then $7/month)
- **Total**: First 90 days FREE, then $7/month for database

## Notes
- Free web services sleep after 15 minutes of inactivity
- First request ke baad bot 30-50 seconds me wake up hota hai
- Conversation feature work karega but thoda delay ho sakta hai first request me
