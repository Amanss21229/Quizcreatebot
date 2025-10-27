# Database Setup Guide

## Overview
Your Telegram Quiz Bot now has a PostgreSQL (Neon) database configured for persistent data storage.

## Database Connection
The database is already connected and available through environment variables:
- `DATABASE_URL` - Full connection string
- `PGHOST` - Database host
- `PGPORT` - Database port (5432)
- `PGUSER` - Database username
- `PGPASSWORD` - Database password
- `PGDATABASE` - Database name

## Running the Schema

### Option 1: Using the SQL Editor in Replit
1. Open the **Database** tab in the left sidebar
2. Click on **SQL Editor**
3. Copy the contents of `database_schema.sql`
4. Paste and run the SQL commands

### Option 2: Using psql Command Line
```bash
psql $DATABASE_URL -f database_schema.sql
```

### Option 3: Using Python (psycopg2)
```python
import psycopg2
import os

conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

with open('database_schema.sql', 'r') as f:
    cur.execute(f.read())

conn.commit()
cur.close()
conn.close()
```

## Database Tables Created

The schema creates the following tables:

### 1. **bot_stats** - Global bot statistics
- Total users, groups, quizzes generated, questions sent
- Bot start time and last updated timestamp

### 2. **bot_users** - User tracking
- User ID, name, username
- First and last seen timestamps

### 3. **bot_groups** - Group tracking
- Group ID, name
- First added and last active timestamps

### 4. **bot_admins** - Admin management
- Dynamic admin user IDs
- Added by and added at information

### 5. **force_join_groups** - Force join requirements
- Required groups/channels users must join
- Chat ID, invite link, title

### 6. **language_settings** - Language preferences
- Per-chat language settings (Hindi/English)

### 7. **tagall_permissions** - Tagall settings
- Permission level per group (user/admin)

### 8. **tracked_members** - Group member tracking
- Members in each group for tagall functionality
- User info, admin status, last seen

### 9. **welcome_groups** - Welcome messages
- Groups with welcome messages enabled
- Custom welcome message text

### 10. **quiz_sessions** - Quiz tracking
- Active and historical quiz sessions
- Chapter, questions, current progress

### 11. **quiz_participants** - Quiz participant data
- Scores, correct/wrong answers, time taken
- Rankings and accuracy

### 12. **quiz_answers** - Individual answers
- Each answer for each question
- Correctness and time taken

### 13. **good_morning_groups** - Good morning messages
- Groups with scheduled good morning messages
- Schedule time and timezone

## Useful Views

### active_quiz_sessions
Shows all active quiz sessions with participant counts

### quiz_leaderboards
Generates leaderboards for all quiz sessions with rankings

## Next Steps

After running the schema:

1. **Update your Python code** to use PostgreSQL instead of JSON files
2. Install the PostgreSQL adapter:
   ```bash
   pip install psycopg2-binary
   ```
   Or use SQLAlchemy for ORM:
   ```bash
   pip install sqlalchemy
   ```

3. **Example connection code**:
   ```python
   import psycopg2
   import os
   
   def get_db_connection():
       return psycopg2.connect(os.environ['DATABASE_URL'])
   ```

4. **Migrate existing JSON data** to the database (if needed)

## Database Management

- **View data**: Use the Replit Database tab with SQL Editor
- **Backup**: Neon provides automatic backups
- **Monitor**: Check the Database tab for connection status and usage

## Sample Queries

```sql
-- Get all bot statistics
SELECT * FROM bot_stats;

-- Get active quiz sessions
SELECT * FROM active_quiz_sessions;

-- Get leaderboard for a quiz
SELECT * FROM quiz_leaderboards WHERE session_id = 1;

-- Get user's quiz history
SELECT qs.chapter, qs.start_time, qp.total_score, qp.rank
FROM quiz_participants qp
JOIN quiz_sessions qs ON qp.session_id = qs.id
WHERE qp.user_id = 123456789
ORDER BY qs.start_time DESC;
```

## Important Notes

- The schema includes automatic timestamps with triggers
- Foreign keys ensure data integrity
- Indexes optimize common queries
- Views simplify complex queries
- All existing JSON files can remain as backup during migration
