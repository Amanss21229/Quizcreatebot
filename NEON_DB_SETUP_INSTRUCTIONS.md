# 🗄️ Neon Database Setup Instructions

## Quick Start Guide for NEET Quiz Bot

Your Telegram NEET Quiz Bot is now configured to use **Neon PostgreSQL Database**.

---

## ✅ What's Already Done

1. ✅ **Database Connection Configured**: Your bot is connected to Neon DB via `DATABASE_URL` environment variable
2. ✅ **Complete SQL Schema Created**: All 23 tables, indexes, triggers, and views ready to deploy
3. ✅ **Bot Code Updated**: All database operations use async PostgreSQL queries via `asyncpg`

---

## 📋 Step-by-Step Setup

### Step 1: Open Neon Dashboard

1. Go to [Neon Console](https://console.neon.tech/)
2. Select your project
3. Click on **"SQL Editor"** in the left sidebar

### Step 2: Run the Complete Setup SQL

1. Open the file: **`NEON_DB_COMPLETE_SETUP.sql`**
2. **Copy ALL contents** (from line 1 to the end)
3. **Paste** into Neon SQL Editor
4. Click **"Run"** or **"Execute"** button

### Step 3: Verify Tables Created

After running the SQL, verify setup by running this query in SQL Editor:

```sql
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
ORDER BY table_name;
```

You should see **23 tables** created:
- admins
- bot_admins
- bot_stats
- force_join_settings
- force_join_targets
- global_quiz_sessions
- good_morning_wishes
- group_stats
- language_preferences
- language_settings
- quiz_answers
- quiz_group_results
- quiz_id_counter
- quiz_participants
- quiz_questions
- quiz_sessions
- tagall_history
- tagall_permissions
- tracked_members
- user_stats
- welcome_groups
- welcome_messages
- welcome_settings

---

## 🎯 What Each Table Does

### Core Statistics Tables
- **`user_stats`**: Tracks individual user quiz performance, scores, accuracy
- **`group_stats`**: Tracks group-level quiz activity and participation

### Admin & Permissions
- **`admins`**: Group-specific admin users
- **`bot_admins`**: Bot-level admin users (dynamic)

### Feature Configuration
- **`language_preferences`** / **`language_settings`**: English/Hindi language choices per group
- **`force_join_settings`** / **`force_join_targets`**: Required channel membership settings
- **`welcome_messages`** / **`welcome_groups`** / **`welcome_settings`**: Welcome message configurations
- **`good_morning_wishes`**: Daily good morning message settings
- **`tagall_permissions`** / **`tagall_history`**: Mention all members feature settings
- **`tracked_members`**: Group member tracking database

### Quiz System
- **`quiz_sessions`**: Regular and live quiz session metadata
- **`quiz_participants`**: Participant scores and statistics per quiz
- **`quiz_questions`**: Questions for each quiz with options and correct answers
- **`quiz_answers`**: Individual user answers for detailed analytics
- **`quiz_id_counter`**: Global quiz ID generator (auto-increments)

### Global Live Quiz System
- **`global_quiz_sessions`**: Completed global quizzes (1-hour retention)
- **`quiz_group_results`**: Group-wise results for global quizzes

### Bot Statistics
- **`bot_stats`**: Overall bot usage statistics

---

## 🔧 Features of This Database Setup

### 🛡️ Safety Features
- ✅ **Safe Re-execution**: Uses `IF NOT EXISTS` - won't break if run multiple times
- ✅ **Data Preservation**: Existing data remains intact
- ✅ **No Errors**: Won't fail even if tables already exist

### ⚡ Performance Features
- ✅ **16+ Indexes**: Optimized for fast queries
- ✅ **Automatic Triggers**: Auto-updates `updated_at` timestamps
- ✅ **Helpful Views**: Pre-built queries for common operations

### 🗄️ Data Features
- ✅ **BIGINT for Telegram IDs**: Supports up to 9 quintillion (future-proof)
- ✅ **JSONB Storage**: Efficient storage for complex quiz data
- ✅ **UNIQUE Constraints**: Prevents duplicate data
- ✅ **Auto Timestamps**: Tracks creation and modification times

---

## 🔑 Prerequisites

Before starting, ensure these environment variables are set:

1. **`TELEGRAM_BOT_TOKEN`** - Your Telegram bot token from @BotFather
2. **`GEMINI_API_KEY`** - Your Google Gemini API key for question generation
3. **`DATABASE_URL`** - Your Neon PostgreSQL connection string (already configured ✅)

You can verify these are set:
```bash
python -c "import os; print('TELEGRAM_BOT_TOKEN:', bool(os.getenv('TELEGRAM_BOT_TOKEN'))); print('GEMINI_API_KEY:', bool(os.getenv('GEMINI_API_KEY'))); print('DATABASE_URL:', bool(os.getenv('DATABASE_URL')))"
```

---

## 📦 Migrating from JSON Files (Optional)

**If you have existing data** stored in JSON files (e.g., `bot_stats.json`, `bot_admins.json`, `force_join_data.json`), you can migrate it to Neon DB.

### Option 1: Fresh Start (Recommended)
Simply run the SQL setup and start fresh. Your bot will automatically populate the database with new data as users interact with it.

### Option 2: Migrate Existing Data
If you need to preserve existing statistics and settings:

1. **Keep your JSON files** in the project temporarily
2. **Run the bot** - The database repositories will read from JSON first if tables are empty
3. **Verify data migration** by checking table row counts
4. **Remove JSON files** after confirming data is in database

The bot code includes automatic fallback logic that reads from JSON files if database tables are empty, then migrates data on first use.

---

## 🚀 After Setup

### Test Your Database Connection

Run this in Neon SQL Editor to verify everything works:

```sql
-- Check all table row counts
SELECT 'admins' as table_name, COUNT(*) as row_count FROM admins
UNION ALL SELECT 'user_stats', COUNT(*) FROM user_stats
UNION ALL SELECT 'group_stats', COUNT(*) FROM group_stats
UNION ALL SELECT 'quiz_sessions', COUNT(*) FROM quiz_sessions
UNION ALL SELECT 'global_quiz_sessions', COUNT(*) FROM global_quiz_sessions
ORDER BY table_name;
```

### Start Your Bot

Your bot is already configured! Just run:
```bash
python main.py
```

The bot will:
1. ✅ Auto-connect to Neon DB using `DATABASE_URL`
2. ✅ Create connection pool (2-10 connections)
3. ✅ Start tracking users, groups, and quiz data
4. ✅ Store all quiz results in database

---

## 📊 Useful Database Queries

### View Active Quizzes
```sql
SELECT * FROM active_quiz_sessions;
```

### View Quiz Leaderboard
```sql
SELECT * FROM quiz_leaderboards 
WHERE session_id = 'YOUR_SESSION_ID' 
ORDER BY rank;
```

### View User Quiz History
```sql
SELECT * FROM user_quiz_history 
WHERE user_id = YOUR_USER_ID 
LIMIT 10;
```

### View Top 10 Users by Score
```sql
SELECT user_id, first_name, total_score, best_score, quiz_count
FROM user_stats
ORDER BY total_score DESC
LIMIT 10;
```

### View Most Active Groups
```sql
SELECT group_id, group_name, quiz_count, total_participants
FROM group_stats
ORDER BY quiz_count DESC
LIMIT 10;
```

### Clean Up Expired Quizzes
```sql
SELECT delete_expired_quiz_sessions();
```

---

## 🔍 Database Monitoring

### Check Database Size
```sql
SELECT 
    pg_size_pretty(pg_database_size(current_database())) as database_size;
```

### Check Table Sizes
```sql
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

---

## 🎓 Bot Commands That Use Database

All these commands now use PostgreSQL instead of JSON files:

### Quiz Commands
- `/quiz` - Regular quiz (stores in `quiz_sessions`, `quiz_participants`)
- `/livequiz` - Global live quiz (stores in `global_quiz_sessions`)
- `/leaderboard` - Shows rankings from database

### Admin Commands
- `/fjoin` - Force join settings (stores in `force_join_settings`)
- `/setlang` - Language preference (stores in `language_preferences`)
- `/setwelcome` - Welcome messages (stores in `welcome_messages`)
- `/tagall` - Tag all members (uses `tracked_members`)

### Statistics Commands
- `/stats` - User stats from `user_stats` table
- `/groupstats` - Group stats from `group_stats` table

---

## 🛠️ Troubleshooting

### If bot shows database errors:

1. **Check DATABASE_URL is set:**
   ```bash
   echo $DATABASE_URL
   ```

2. **Verify Neon DB is accessible:**
   - Login to Neon Console
   - Check if your database is active
   - Verify connection string is correct

3. **Re-run setup SQL:**
   - Safe to run multiple times
   - Won't delete existing data

4. **Check bot logs:**
   ```bash
   python main.py
   ```
   Look for messages like:
   - ✅ `Database connection pool initialized successfully`
   - ❌ `Failed to initialize database pool`

---

## 📝 Important Notes

1. **1-Hour Quiz Retention**: Global quiz sessions auto-delete after 1 hour (configurable in code)
2. **Connection Pool**: Bot maintains 2-10 concurrent database connections
3. **Safe Concurrent Access**: Multiple bot instances can share the same database
4. **Automatic Cleanup**: Expired quizzes cleaned via `delete_expired_quiz_sessions()` function

---

## ✅ Setup Complete!

You're all set! Your NEET Quiz Bot now:
- 🗄️ Uses Neon PostgreSQL for all data storage
- ⚡ Fast queries with optimized indexes
- 📊 Rich analytics and leaderboards
- 🔒 Reliable data persistence
- 🚀 Production-ready architecture

**Need help?** Check the SQL comments in `NEON_DB_COMPLETE_SETUP.sql` for detailed table descriptions.
