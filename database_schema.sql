-- =============================================
-- NEET Quiz Bot - PostgreSQL Database Schema
-- =============================================
-- This file contains all SQL commands to create
-- the required tables for the Telegram Quiz Bot
-- =============================================

-- Drop existing tables if they exist (in reverse dependency order)
DROP TABLE IF EXISTS quiz_answers CASCADE;
DROP TABLE IF EXISTS quiz_participants CASCADE;
DROP TABLE IF EXISTS quiz_sessions CASCADE;
DROP TABLE IF EXISTS tracked_members CASCADE;
DROP TABLE IF EXISTS tagall_permissions CASCADE;
DROP TABLE IF EXISTS language_settings CASCADE;
DROP TABLE IF EXISTS welcome_groups CASCADE;
DROP TABLE IF EXISTS force_join_groups CASCADE;
DROP TABLE IF EXISTS bot_admins CASCADE;
DROP TABLE IF EXISTS bot_stats CASCADE;

-- =============================================
-- 1. BOT STATISTICS TABLE
-- =============================================
-- Stores global bot statistics
CREATE TABLE bot_stats (
    id SERIAL PRIMARY KEY,
    total_users BIGINT DEFAULT 0,
    total_groups BIGINT DEFAULT 0,
    total_quizzes_generated BIGINT DEFAULT 0,
    total_questions_sent BIGINT DEFAULT 0,
    start_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert initial record
INSERT INTO bot_stats (total_users, total_groups, total_quizzes_generated, total_questions_sent)
VALUES (0, 0, 0, 0);

-- =============================================
-- 2. BOT USERS TABLE
-- =============================================
-- Tracks all users who have interacted with the bot
CREATE TABLE bot_users (
    user_id BIGINT PRIMARY KEY,
    first_name VARCHAR(255),
    username VARCHAR(255),
    first_seen TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_seen TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

-- =============================================
-- 3. BOT GROUPS TABLE
-- =============================================
-- Tracks all groups where the bot is active
CREATE TABLE bot_groups (
    group_id BIGINT PRIMARY KEY,
    group_name VARCHAR(255),
    first_added TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_active TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

-- =============================================
-- 4. BOT ADMINS TABLE
-- =============================================
-- Stores dynamic admin user IDs
CREATE TABLE bot_admins (
    user_id BIGINT PRIMARY KEY,
    added_by BIGINT,
    added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

-- =============================================
-- 5. FORCE JOIN GROUPS TABLE
-- =============================================
-- Stores groups/channels users must join to use the bot
CREATE TABLE force_join_groups (
    id SERIAL PRIMARY KEY,
    chat_id BIGINT NOT NULL UNIQUE,
    invite_link TEXT,
    title VARCHAR(255),
    added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

-- =============================================
-- 6. LANGUAGE SETTINGS TABLE
-- =============================================
-- Stores language preferences for each chat
CREATE TABLE language_settings (
    chat_id BIGINT PRIMARY KEY,
    language VARCHAR(10) DEFAULT 'english',
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =============================================
-- 7. TAGALL PERMISSIONS TABLE
-- =============================================
-- Stores tagall permission settings for groups
CREATE TABLE tagall_permissions (
    group_id BIGINT PRIMARY KEY,
    permission_level VARCHAR(20) DEFAULT 'admin',
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT check_permission_level CHECK (permission_level IN ('user', 'admin'))
);

-- =============================================
-- 8. TRACKED MEMBERS TABLE
-- =============================================
-- Tracks members in groups for tagall functionality
CREATE TABLE tracked_members (
    id SERIAL PRIMARY KEY,
    group_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    first_name VARCHAR(255),
    username VARCHAR(255),
    is_admin BOOLEAN DEFAULT FALSE,
    last_seen TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(group_id, user_id)
);

CREATE INDEX idx_tracked_members_group ON tracked_members(group_id);
CREATE INDEX idx_tracked_members_user ON tracked_members(user_id);

-- =============================================
-- 9. WELCOME GROUPS TABLE
-- =============================================
-- Stores groups with welcome message enabled
CREATE TABLE welcome_groups (
    group_id BIGINT PRIMARY KEY,
    welcome_message TEXT,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =============================================
-- 10. QUIZ SESSIONS TABLE
-- =============================================
-- Stores active and historical quiz sessions
CREATE TABLE quiz_sessions (
    id SERIAL PRIMARY KEY,
    chat_id BIGINT NOT NULL,
    chapter VARCHAR(255),
    total_questions INTEGER NOT NULL,
    current_question_index INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    is_private_chat BOOLEAN DEFAULT FALSE,
    start_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    end_time TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_quiz_sessions_chat ON quiz_sessions(chat_id);
CREATE INDEX idx_quiz_sessions_active ON quiz_sessions(is_active);

-- =============================================
-- 11. QUIZ PARTICIPANTS TABLE
-- =============================================
-- Stores participant data for each quiz session
CREATE TABLE quiz_participants (
    id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES quiz_sessions(id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL,
    user_name VARCHAR(255),
    total_score INTEGER DEFAULT 0,
    correct_answers INTEGER DEFAULT 0,
    wrong_answers INTEGER DEFAULT 0,
    unattempted INTEGER DEFAULT 0,
    total_time DECIMAL(10, 2) DEFAULT 0,
    rank INTEGER,
    accuracy DECIMAL(5, 2) DEFAULT 0,
    UNIQUE(session_id, user_id)
);

CREATE INDEX idx_quiz_participants_session ON quiz_participants(session_id);
CREATE INDEX idx_quiz_participants_user ON quiz_participants(user_id);

-- =============================================
-- 12. QUIZ ANSWERS TABLE
-- =============================================
-- Stores individual answers for each question
CREATE TABLE quiz_answers (
    id SERIAL PRIMARY KEY,
    participant_id INTEGER NOT NULL REFERENCES quiz_participants(id) ON DELETE CASCADE,
    question_index INTEGER NOT NULL,
    option_id INTEGER NOT NULL,
    is_correct BOOLEAN NOT NULL,
    time_taken DECIMAL(10, 2) NOT NULL,
    answered_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(participant_id, question_index)
);

CREATE INDEX idx_quiz_answers_participant ON quiz_answers(participant_id);

-- =============================================
-- 13. GOOD MORNING GROUPS TABLE
-- =============================================
-- Stores groups with good morning messages enabled
CREATE TABLE good_morning_groups (
    group_id BIGINT PRIMARY KEY,
    enabled BOOLEAN DEFAULT TRUE,
    scheduled_time TIME DEFAULT '06:00:00',
    timezone VARCHAR(50) DEFAULT 'Asia/Kolkata',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =============================================
-- USEFUL QUERIES AND VIEWS
-- =============================================

-- View to get active quiz sessions with participant count
CREATE VIEW active_quiz_sessions AS
SELECT 
    qs.id,
    qs.chat_id,
    qs.chapter,
    qs.total_questions,
    qs.current_question_index,
    qs.start_time,
    COUNT(DISTINCT qp.user_id) as participant_count
FROM quiz_sessions qs
LEFT JOIN quiz_participants qp ON qs.id = qp.session_id
WHERE qs.is_active = TRUE
GROUP BY qs.id;

-- View to get leaderboard for a quiz session
CREATE VIEW quiz_leaderboards AS
SELECT 
    qp.session_id,
    qp.user_id,
    qp.user_name,
    qp.total_score,
    qp.correct_answers,
    qp.wrong_answers,
    qp.unattempted,
    qp.total_time,
    qp.accuracy,
    RANK() OVER (PARTITION BY qp.session_id ORDER BY qp.total_score DESC, qp.total_time ASC) as rank
FROM quiz_participants qp
ORDER BY qp.session_id, rank;

-- =============================================
-- HELPER FUNCTIONS
-- =============================================

-- Function to update last_updated timestamp
CREATE OR REPLACE FUNCTION update_last_updated()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_updated = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for bot_stats
CREATE TRIGGER update_bot_stats_timestamp
BEFORE UPDATE ON bot_stats
FOR EACH ROW
EXECUTE FUNCTION update_last_updated();

-- Trigger for language_settings
CREATE TRIGGER update_language_settings_timestamp
BEFORE UPDATE ON language_settings
FOR EACH ROW
EXECUTE FUNCTION update_last_updated();

-- Trigger for tagall_permissions
CREATE TRIGGER update_tagall_permissions_timestamp
BEFORE UPDATE ON tagall_permissions
FOR EACH ROW
EXECUTE FUNCTION update_last_updated();

-- =============================================
-- SAMPLE QUERIES FOR REFERENCE
-- =============================================

-- Get total bot statistics:
-- SELECT * FROM bot_stats;

-- Get all active admins:
-- SELECT * FROM bot_admins WHERE is_active = TRUE;

-- Get language preference for a chat:
-- SELECT language FROM language_settings WHERE chat_id = ?;

-- Get all force join groups:
-- SELECT * FROM force_join_groups WHERE is_active = TRUE;

-- Get tracked members for a group:
-- SELECT * FROM tracked_members WHERE group_id = ? ORDER BY last_seen DESC;

-- Get active quiz sessions:
-- SELECT * FROM active_quiz_sessions;

-- Get leaderboard for a specific quiz:
-- SELECT * FROM quiz_leaderboards WHERE session_id = ? ORDER BY rank;

-- Get user quiz history:
-- SELECT qs.chapter, qs.start_time, qp.total_score, qp.rank
-- FROM quiz_participants qp
-- JOIN quiz_sessions qs ON qp.session_id = qs.id
-- WHERE qp.user_id = ?
-- ORDER BY qs.start_time DESC;

-- =============================================
-- END OF SCHEMA
-- =============================================
