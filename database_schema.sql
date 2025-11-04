-- ============================================
-- NEET Quiz Bot - Complete Database Schema
-- PostgreSQL / Neon DB Compatible
-- ============================================
-- This schema uses IF NOT EXISTS to safely create tables
-- No errors will occur if tables already exist
-- Existing data will be preserved
-- ============================================

-- 1. ADMINS TABLE
-- Stores admin user IDs for each group
CREATE TABLE IF NOT EXISTS admins (
    id SERIAL PRIMARY KEY,
    group_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    added_by BIGINT,
    UNIQUE(group_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_admins_group_id ON admins(group_id);
CREATE INDEX IF NOT EXISTS idx_admins_user_id ON admins(user_id);

-- 2. USER STATISTICS TABLE
-- Tracks individual user quiz performance
CREATE TABLE IF NOT EXISTS user_stats (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    username VARCHAR(255),
    first_name VARCHAR(255),
    total_quizzes INTEGER DEFAULT 0,
    total_questions INTEGER DEFAULT 0,
    correct_answers INTEGER DEFAULT 0,
    wrong_answers INTEGER DEFAULT 0,
    unattempted INTEGER DEFAULT 0,
    total_score INTEGER DEFAULT 0,
    best_score INTEGER DEFAULT 0,
    best_accuracy DECIMAL(5,2) DEFAULT 0.00,
    average_score DECIMAL(10,2) DEFAULT 0.00,
    last_quiz_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id)
);

CREATE INDEX IF NOT EXISTS idx_user_stats_user_id ON user_stats(user_id);
CREATE INDEX IF NOT EXISTS idx_user_stats_total_score ON user_stats(total_score DESC);
CREATE INDEX IF NOT EXISTS idx_user_stats_best_score ON user_stats(best_score DESC);

-- 3. GROUP STATISTICS TABLE
-- Tracks group-level quiz activity
CREATE TABLE IF NOT EXISTS group_stats (
    id SERIAL PRIMARY KEY,
    group_id BIGINT NOT NULL,
    group_name VARCHAR(255),
    total_quizzes INTEGER DEFAULT 0,
    total_participants INTEGER DEFAULT 0,
    total_questions_asked INTEGER DEFAULT 0,
    active_users INTEGER DEFAULT 0,
    last_quiz_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(group_id)
);

CREATE INDEX IF NOT EXISTS idx_group_stats_group_id ON group_stats(group_id);
CREATE INDEX IF NOT EXISTS idx_group_stats_total_quizzes ON group_stats(total_quizzes DESC);

-- 4. LANGUAGE PREFERENCES TABLE
-- Stores language preference for each group
CREATE TABLE IF NOT EXISTS language_preferences (
    id SERIAL PRIMARY KEY,
    group_id BIGINT NOT NULL,
    language VARCHAR(10) NOT NULL DEFAULT 'english',
    set_by BIGINT,
    set_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(group_id)
);

CREATE INDEX IF NOT EXISTS idx_language_prefs_group_id ON language_preferences(group_id);

-- 5. FORCE JOIN SETTINGS TABLE
-- Stores force join channel requirements for groups
CREATE TABLE IF NOT EXISTS force_join_settings (
    id SERIAL PRIMARY KEY,
    group_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    channel_username VARCHAR(255),
    enabled BOOLEAN DEFAULT TRUE,
    set_by BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(group_id)
);

CREATE INDEX IF NOT EXISTS idx_force_join_group_id ON force_join_settings(group_id);

-- 6. WELCOME MESSAGES TABLE
-- Stores custom welcome messages for groups
CREATE TABLE IF NOT EXISTS welcome_messages (
    id SERIAL PRIMARY KEY,
    group_id BIGINT NOT NULL,
    message TEXT NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    set_by BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(group_id)
);

CREATE INDEX IF NOT EXISTS idx_welcome_messages_group_id ON welcome_messages(group_id);

-- 7. TAGALL HISTORY TABLE
-- Tracks tagall command usage and cooldowns
CREATE TABLE IF NOT EXISTS tagall_history (
    id SERIAL PRIMARY KEY,
    group_id BIGINT NOT NULL,
    used_by BIGINT NOT NULL,
    username VARCHAR(255),
    message TEXT,
    tagged_count INTEGER DEFAULT 0,
    used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_tagall_history_group_id ON tagall_history(group_id);
CREATE INDEX IF NOT EXISTS idx_tagall_history_used_at ON tagall_history(used_at DESC);

-- 8. GOOD MORNING WISHES TABLE
-- Stores good morning wish settings for groups
CREATE TABLE IF NOT EXISTS good_morning_wishes (
    id SERIAL PRIMARY KEY,
    group_id BIGINT NOT NULL,
    enabled BOOLEAN DEFAULT FALSE,
    message TEXT,
    send_time TIME DEFAULT '06:00:00',
    timezone VARCHAR(50) DEFAULT 'Asia/Kolkata',
    set_by BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(group_id)
);

CREATE INDEX IF NOT EXISTS idx_good_morning_group_id ON good_morning_wishes(group_id);
CREATE INDEX IF NOT EXISTS idx_good_morning_enabled ON good_morning_wishes(enabled);

-- 9. QUIZ SESSIONS TABLE
-- Stores live and individual quiz session data
CREATE TABLE IF NOT EXISTS quiz_sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL,
    session_type VARCHAR(20) NOT NULL,
    chapter VARCHAR(255) NOT NULL,
    question_count INTEGER NOT NULL,
    language VARCHAR(10) DEFAULT 'english',
    started_by BIGINT,
    group_id BIGINT,
    is_running BOOLEAN DEFAULT FALSE,
    is_completed BOOLEAN DEFAULT FALSE,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(session_id)
);

CREATE INDEX IF NOT EXISTS idx_quiz_sessions_session_id ON quiz_sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_quiz_sessions_group_id ON quiz_sessions(group_id);
CREATE INDEX IF NOT EXISTS idx_quiz_sessions_type ON quiz_sessions(session_type);
CREATE INDEX IF NOT EXISTS idx_quiz_sessions_running ON quiz_sessions(is_running);

-- 10. QUIZ PARTICIPANTS TABLE
-- Stores participant scores and answers for each quiz
CREATE TABLE IF NOT EXISTS quiz_participants (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL,
    user_id BIGINT NOT NULL,
    username VARCHAR(255),
    first_name VARCHAR(255),
    group_id BIGINT,
    score INTEGER DEFAULT 0,
    correct_count INTEGER DEFAULT 0,
    wrong_count INTEGER DEFAULT 0,
    unattempted_count INTEGER DEFAULT 0,
    accuracy DECIMAL(5,2) DEFAULT 0.00,
    rank INTEGER,
    global_rank INTEGER,
    answers JSONB DEFAULT '[]',
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(session_id, user_id, group_id)
);

CREATE INDEX IF NOT EXISTS idx_quiz_participants_session_id ON quiz_participants(session_id);
CREATE INDEX IF NOT EXISTS idx_quiz_participants_user_id ON quiz_participants(user_id);
CREATE INDEX IF NOT EXISTS idx_quiz_participants_score ON quiz_participants(score DESC);
CREATE INDEX IF NOT EXISTS idx_quiz_participants_group_id ON quiz_participants(group_id);

-- 11. QUIZ QUESTIONS TABLE
-- Stores questions for each quiz session
CREATE TABLE IF NOT EXISTS quiz_questions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL,
    question_number INTEGER NOT NULL,
    question_text TEXT NOT NULL,
    option_a TEXT NOT NULL,
    option_b TEXT NOT NULL,
    option_c TEXT NOT NULL,
    option_d TEXT NOT NULL,
    correct_option VARCHAR(1) NOT NULL,
    language VARCHAR(10) DEFAULT 'english',
    explanation TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(session_id, question_number, language)
);

CREATE INDEX IF NOT EXISTS idx_quiz_questions_session_id ON quiz_questions(session_id);
CREATE INDEX IF NOT EXISTS idx_quiz_questions_number ON quiz_questions(question_number);

-- 12. QUIZ ANSWERS TABLE
-- Stores individual user answers for detailed analytics
CREATE TABLE IF NOT EXISTS quiz_answers (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL,
    user_id BIGINT NOT NULL,
    question_number INTEGER NOT NULL,
    selected_option VARCHAR(1),
    correct_option VARCHAR(1) NOT NULL,
    is_correct BOOLEAN DEFAULT FALSE,
    time_taken INTEGER,
    answered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(session_id, user_id, question_number)
);

CREATE INDEX IF NOT EXISTS idx_quiz_answers_session_id ON quiz_answers(session_id);
CREATE INDEX IF NOT EXISTS idx_quiz_answers_user_id ON quiz_answers(user_id);
CREATE INDEX IF NOT EXISTS idx_quiz_answers_question ON quiz_answers(question_number);

-- 13. TRACKED MEMBERS TABLE
-- Tracks members in groups for tagall functionality
CREATE TABLE IF NOT EXISTS tracked_members (
    id SERIAL PRIMARY KEY,
    group_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    first_name VARCHAR(255),
    username VARCHAR(255),
    is_admin BOOLEAN DEFAULT FALSE,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(group_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_tracked_members_group ON tracked_members(group_id);
CREATE INDEX IF NOT EXISTS idx_tracked_members_user ON tracked_members(user_id);

-- ============================================
-- HELPER FUNCTIONS
-- ============================================

-- Function to update updated_at timestamp automatically
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Add triggers for automatic updated_at timestamp
DROP TRIGGER IF EXISTS update_user_stats_updated_at ON user_stats;
CREATE TRIGGER update_user_stats_updated_at
    BEFORE UPDATE ON user_stats
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_group_stats_updated_at ON group_stats;
CREATE TRIGGER update_group_stats_updated_at
    BEFORE UPDATE ON group_stats
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_force_join_updated_at ON force_join_settings;
CREATE TRIGGER update_force_join_updated_at
    BEFORE UPDATE ON force_join_settings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_welcome_messages_updated_at ON welcome_messages;
CREATE TRIGGER update_welcome_messages_updated_at
    BEFORE UPDATE ON welcome_messages
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_good_morning_updated_at ON good_morning_wishes;
CREATE TRIGGER update_good_morning_updated_at
    BEFORE UPDATE ON good_morning_wishes
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- VERIFICATION QUERIES
-- ============================================
-- Uncomment and run these queries after executing the schema to verify table creation:

-- List all tables
-- SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;

-- Count rows in each table
-- SELECT 'admins' as table_name, COUNT(*) as row_count FROM admins
-- UNION ALL SELECT 'user_stats', COUNT(*) FROM user_stats
-- UNION ALL SELECT 'group_stats', COUNT(*) FROM group_stats
-- UNION ALL SELECT 'language_preferences', COUNT(*) FROM language_preferences
-- UNION ALL SELECT 'force_join_settings', COUNT(*) FROM force_join_settings
-- UNION ALL SELECT 'welcome_messages', COUNT(*) FROM welcome_messages
-- UNION ALL SELECT 'tagall_history', COUNT(*) FROM tagall_history
-- UNION ALL SELECT 'good_morning_wishes', COUNT(*) FROM good_morning_wishes
-- UNION ALL SELECT 'quiz_sessions', COUNT(*) FROM quiz_sessions
-- UNION ALL SELECT 'quiz_participants', COUNT(*) FROM quiz_participants
-- UNION ALL SELECT 'quiz_questions', COUNT(*) FROM quiz_questions
-- UNION ALL SELECT 'quiz_answers', COUNT(*) FROM quiz_answers
-- UNION ALL SELECT 'tracked_members', COUNT(*) FROM tracked_members;

-- ============================================
-- USEFUL VIEWS
-- ============================================

-- View for active quiz sessions with participant count
CREATE OR REPLACE VIEW active_quiz_sessions AS
SELECT 
    qs.session_id,
    qs.chapter,
    qs.question_count,
    qs.session_type,
    qs.start_time,
    COUNT(DISTINCT qp.user_id) as participant_count
FROM quiz_sessions qs
LEFT JOIN quiz_participants qp ON qs.session_id = qp.session_id
WHERE qs.is_running = TRUE
GROUP BY qs.session_id, qs.chapter, qs.question_count, qs.session_type, qs.start_time;

-- View for quiz leaderboards
CREATE OR REPLACE VIEW quiz_leaderboards AS
SELECT 
    qp.session_id,
    qp.user_id,
    qp.first_name,
    qp.username,
    qp.score,
    qp.correct_count,
    qp.wrong_count,
    qp.unattempted_count,
    qp.accuracy,
    RANK() OVER (PARTITION BY qp.session_id ORDER BY qp.score DESC) as rank
FROM quiz_participants qp
ORDER BY qp.session_id, rank;

-- View for user quiz history
CREATE OR REPLACE VIEW user_quiz_history AS
SELECT 
    qp.user_id,
    qp.first_name,
    qp.username,
    qs.chapter,
    qs.start_time,
    qp.score,
    qp.correct_count,
    qp.wrong_count,
    qp.accuracy,
    qp.rank
FROM quiz_participants qp
JOIN quiz_sessions qs ON qp.session_id = qs.session_id
WHERE qs.is_completed = TRUE
ORDER BY qs.start_time DESC;

-- ============================================
-- SAMPLE QUERIES FOR REFERENCE
-- ============================================

-- Get all admins for a specific group:
-- SELECT * FROM admins WHERE group_id = YOUR_GROUP_ID;

-- Get language preference for a group:
-- SELECT language FROM language_preferences WHERE group_id = YOUR_GROUP_ID;

-- Get user statistics:
-- SELECT * FROM user_stats WHERE user_id = YOUR_USER_ID;

-- Get group statistics:
-- SELECT * FROM group_stats WHERE group_id = YOUR_GROUP_ID;

-- Get active quiz sessions:
-- SELECT * FROM active_quiz_sessions;

-- Get leaderboard for a specific quiz:
-- SELECT * FROM quiz_leaderboards WHERE session_id = 'YOUR_SESSION_ID' ORDER BY rank;

-- Get user quiz history:
-- SELECT * FROM user_quiz_history WHERE user_id = YOUR_USER_ID LIMIT 10;

-- Get all groups with good morning wishes enabled:
-- SELECT * FROM good_morning_wishes WHERE enabled = TRUE;

-- Get tracked members for a group:
-- SELECT * FROM tracked_members WHERE group_id = YOUR_GROUP_ID ORDER BY last_seen DESC;

-- ============================================
-- TABLE DESCRIPTIONS
-- ============================================

-- 1. admins: Stores admin users per group
-- 2. user_stats: Individual user statistics and quiz performance
-- 3. group_stats: Group-level statistics
-- 4. language_preferences: Language settings (English/Hindi) per group
-- 5. force_join_settings: Required channel join settings per group
-- 6. welcome_messages: Custom welcome messages for groups
-- 7. tagall_history: History of tagall command usage
-- 8. good_morning_wishes: Good morning message settings per group
-- 9. quiz_sessions: All quiz sessions (live, individual, group)
-- 10. quiz_participants: Participant scores and stats per quiz
-- 11. quiz_questions: Questions for each quiz session
-- 12. quiz_answers: Individual user answers for detailed analytics
-- 13. tracked_members: Group member tracking for tagall functionality

-- ============================================
-- NOTES FOR USAGE
-- ============================================
-- ✅ This schema is 100% safe to run multiple times
-- ✅ IF NOT EXISTS prevents errors on re-execution
-- ✅ All indexes use IF NOT EXISTS
-- ✅ Triggers are recreated safely (DROP IF EXISTS first)
-- ✅ JSONB type stores complex data (answers array)
-- ✅ Automatic triggers update 'updated_at' timestamps
-- ✅ Views are created with OR REPLACE for safety
-- ✅ BIGINT supports Telegram IDs (up to 9 quintillion)
-- ✅ UNIQUE constraints prevent duplicate data
-- ✅ Indexes optimize query performance

-- ============================================
-- HOW TO USE IN NEON DB
-- ============================================
-- 1. Copy this entire file
-- 2. Go to your Neon DB SQL Editor
-- 3. Paste the contents
-- 4. Click "Run" or "Execute"
-- 5. No errors will occur even if tables exist!
-- 6. Your existing data will be preserved

-- ✅ SCHEMA CREATION COMPLETE
-- ✅ Safe for production use
-- ✅ Compatible with PostgreSQL 12+
-- ✅ Optimized for Neon DB
