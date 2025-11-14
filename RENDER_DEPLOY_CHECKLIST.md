# 🚀 Render Deployment - Step-by-Step Checklist

## ⚠️ **CRITICAL FIX APPLIED!**
**Problem:** Render was getting confused between `pyproject.toml` and `requirements.txt`

**Solution:** `pyproject.toml` has been renamed to `pyproject.toml.backup` so Render will ONLY use `requirements.txt` (which has all dependencies including asyncpg).

## ✅ Pre-Deployment Checklist

### 1. Files to Commit to GitHub
Make sure these files are in your repository root:
- [x] `requirements.txt` (all dependencies including asyncpg) ✅ **CRITICAL**
- [x] `runtime.txt` (python-3.11.9) ✅
- [x] `render.yaml` (updated build command) ✅
- [x] `.renderignore` (ignores pyproject.toml.backup) ✅
- [x] `run.py` ✅
- [x] All `bot/` folder files ✅

**NOTE:** `pyproject.toml` renamed to `pyproject.toml.backup` to avoid conflicts!

### 2. Verify Files on GitHub
```bash
# Push all changes to GitHub:
git add .
git commit -m "Fix Render deployment - clean requirements.txt"
git push origin main
```

**IMPORTANT**: Go to your GitHub repository in browser and verify these files are there!

---

## 🔧 Render Deployment Steps

### Step 1: Clear Build Cache (CRITICAL!)
1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click on your bot service
3. Click **"Manual Deploy"** button (top right)
4. Select **"Clear build cache & deploy"**
5. Click **"Deploy"**

### Step 2: Verify Environment Variables
Make sure these are set in Render Environment section:
```
TELEGRAM_BOT_TOKEN = <your_bot_token>
GEMINI_API_KEY = <your_api_key>
GOOGLE_API_KEY = <your_api_key>  (same as GEMINI_API_KEY)
DATABASE_URL = <your_postgres_url>
```

### Step 3: Watch Build Logs
In the logs, you should see:
```
✅ Collecting asyncpg>=0.29.0
✅ Successfully installed asyncpg-0.x.x
✅ Successfully installed python-telegram-bot-22.x
```

If you DON'T see "Successfully installed asyncpg", the build cache wasn't cleared!

### Step 4: Verify Deployment
After deployment completes:
1. Check logs for: "Application started"
2. Visit: `https://your-app.onrender.com/health`
3. Should show: "Bot is running!"

---

## 🐛 Still Getting "Module not found" Error?

### Fix #1: Force Fresh Install
1. In Render dashboard → Settings
2. Change Build Command to:
   ```bash
   pip install --upgrade pip && pip cache purge && pip install --no-cache-dir -r requirements.txt
   ```
3. Save changes
4. Clear build cache & deploy again

### Fix #2: Verify Python Version
1. In Render dashboard → Environment
2. Add/Update: `PYTHON_VERSION` = `3.11.0`
3. Save and redeploy

### Fix #3: Check File Paths
Run this locally to verify structure:
```bash
ls -la
# Should show:
# requirements.txt
# runtime.txt
# render.yaml
# run.py
# bot/
```

---

## 📝 What Was Fixed

1. **Cleaned requirements.txt** - Removed duplicate entries
2. **Added runtime.txt** - Specifies Python 3.11.9
3. **Updated render.yaml** - Added `--no-cache-dir` flag
4. **Updated build command** - Forces fresh package installation

---

## 🎯 Expected Build Output

```
==> Installing dependencies
Collecting google-generativeai>=0.8.5
Collecting python-dotenv>=1.1.1
Collecting python-telegram-bot[job-queue]>=22.5
Collecting aiohttp>=3.9.0
Collecting psycopg2-binary>=2.9.9
Collecting asyncpg>=0.29.0          ← This MUST appear!
Collecting APScheduler>=3.10.0
...
Successfully installed asyncpg-0.30.0 ...
==> Build successful

==> Running 'python run.py'
Bot is starting...
Database connection pool initialized successfully
Application started
```

---

## 💡 Pro Tips

1. **Always clear build cache** when deployment fails
2. **Check GitHub** - Make sure all files are committed
3. **Read build logs** - Look for "Successfully installed asyncpg"
4. **Database URL** - Must start with `postgresql://` or `postgres://`

---

## ✅ Success Indicators

- ✅ Build logs show "Successfully installed asyncpg"
- ✅ No "ModuleNotFoundError" in logs
- ✅ Logs show "Application started"
- ✅ `/health` endpoint returns "Bot is running!"
- ✅ Bot responds to Telegram messages

---

**If still failing after all steps, share the FULL build logs from Render!**
