-- ============================================
-- NEET QUIZ BOT - COMPLETE NEON DB SETUP
-- PostgreSQL / Neon DB Compatible
-- ============================================
-- 📋 INSTRUCTIONS FOR USE:
-- 1. Copy this entire file
-- 2. Open Neon DB SQL Editor
-- 3. Paste all contents
-- 4. Click "Run" / "Execute"
-- 5. Done! ✅
--
-- ✅ SAFE TO RUN MULTIPLE TIMES
-- ✅ IF NOT EXISTS prevents errors
-- ✅ Existing data will be preserved
-- ============================================

-- ============================================
-- CORE STATISTICS TABLES
-- ============================================

-- 1. USER STATISTICS TABLE
CREATE TABLE IF NOT EXISTS user_stats (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    username VARCHAR(255),
    first_name VARCHAR(255),
    quiz_count INTEGER DEFAULT 0,
    live_quiz_count INTEGER DEFAULT 0,
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
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id)
);

CREATE INDEX IF NOT EXISTS idx_user_stats_user_id ON user_stats(user_id);
CREATE INDEX IF NOT EXISTS idx_user_stats_total_score ON user_stats(total_score DESC);
CREATE INDEX IF NOT EXISTS idx_user_stats_best_score ON user_stats(best_score DESC);
CREATE INDEX IF NOT EXISTS idx_user_stats_quiz_count ON user_stats(quiz_count DESC);

-- 2. GROUP STATISTICS TABLE
CREATE TABLE IF NOT EXISTS group_stats (
    id SERIAL PRIMARY KEY,
    group_id BIGINT NOT NULL,
    group_name VARCHAR(255),
    quiz_count INTEGER DEFAULT 0,
    live_quiz_count INTEGER DEFAULT 0,
    total_quizzes INTEGER DEFAULT 0,
    total_participants INTEGER DEFAULT 0,
    total_questions_asked INTEGER DEFAULT 0,
    active_users INTEGER DEFAULT 0,
    last_quiz_date TIMESTAMP,
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(group_id)
);

CREATE INDEX IF NOT EXISTS idx_group_stats_group_id ON group_stats(group_id);
CREATE INDEX IF NOT EXISTS idx_group_stats_total_quizzes ON group_stats(total_quizzes DESC);
CREATE INDEX IF NOT EXISTS idx_group_stats_quiz_count ON group_stats(quiz_count DESC);

-- ============================================
-- ADMIN & PERMISSIONS TABLES
-- ============================================

-- 3. ADMINS TABLE
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

-- 4. BOT ADMINS TABLE (Dynamic)
CREATE TABLE IF NOT EXISTS bot_admins (
    user_id BIGINT PRIMARY KEY,
    added_by BIGINT NOT NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- FEATURE CONFIGURATION TABLES
-- ============================================

-- 5. LANGUAGE PREFERENCES TABLE
CREATE TABLE IF NOT EXISTS language_preferences (
    id SERIAL PRIMARY KEY,
    group_id BIGINT NOT NULL,
    language VARCHAR(10) NOT NULL DEFAULT 'english',
    set_by BIGINT,
    set_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(group_id)
);

CREATE INDEX IF NOT EXISTS idx_language_prefs_group_id ON language_preferences(group_id);

-- 6. LANGUAGE SETTINGS TABLE (Alternative name used in code)
CREATE TABLE IF NOT EXISTS language_settings (
    id SERIAL PRIMARY KEY,
    chat_id BIGINT NOT NULL UNIQUE,
    language VARCHAR(10) NOT NULL DEFAULT 'english',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_language_settings_chat_id ON language_settings(chat_id);

-- 7. FORCE JOIN SETTINGS TABLE
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

-- 8. FORCE JOIN TARGETS TABLE (Alternative)
CREATE TABLE IF NOT EXISTS force_join_targets (
    id SERIAL PRIMARY KEY,
    chat_id BIGINT NOT NULL UNIQUE,
    chat_type VARCHAR(50) NOT NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 9. WELCOME MESSAGES TABLE
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

-- 10. WELCOME GROUPS TABLE (Alternative)
CREATE TABLE IF NOT EXISTS welcome_groups (
    id SERIAL PRIMARY KEY,
    group_id BIGINT NOT NULL UNIQUE,
    welcome_message TEXT,
    enabled BOOLEAN DEFAULT TRUE,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_welcome_groups_group_id ON welcome_groups(group_id);

-- 11. WELCOME SETTINGS TABLE (Alternative)
CREATE TABLE IF NOT EXISTS welcome_settings (
    group_id BIGINT PRIMARY KEY,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    custom_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 12. GOOD MORNING WISHES TABLE
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

-- 13. TAGALL PERMISSIONS TABLE
CREATE TABLE IF NOT EXISTS tagall_permissions (
    id SERIAL PRIMARY KEY,
    group_id BIGINT NOT NULL UNIQUE,
    permission_level VARCHAR(20) DEFAULT 'admins',
    enabled BOOLEAN DEFAULT FALSE,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_tagall_permissions_group_id ON tagall_permissions(group_id);

-- 14. TAGALL HISTORY TABLE
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

-- 15. TRACKED MEMBERS TABLE
CREATE TABLE IF NOT EXISTS tracked_members (
    id SERIAL PRIMARY KEY,
    group_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    first_name VARCHAR(255),
    username VARCHAR(255),
    last_name VARCHAR(255),
    is_admin BOOLEAN DEFAULT FALSE,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(group_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_tracked_members_group ON tracked_members(group_id);
CREATE INDEX IF NOT EXISTS idx_tracked_members_user ON tracked_members(user_id);
CREATE INDEX IF NOT EXISTS idx_tracked_members_admin ON tracked_members(group_id, is_admin);

-- ============================================
-- QUIZ SYSTEM TABLES
-- ============================================

-- 16. QUIZ SESSIONS TABLE
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

-- 17. QUIZ PARTICIPANTS TABLE
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

-- 18. QUIZ QUESTIONS TABLE
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

-- 19. QUIZ ANSWERS TABLE
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

-- ============================================
-- GLOBAL LIVE QUIZ TABLES
-- ============================================

-- 20. QUIZ ID COUNTER TABLE
CREATE TABLE IF NOT EXISTS quiz_id_counter (
    id INTEGER PRIMARY KEY DEFAULT 1,
    counter INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CHECK (id = 1)
);

-- Initialize quiz_id_counter with default row
INSERT INTO quiz_id_counter (id, counter, updated_at)
VALUES (1, 0, CURRENT_TIMESTAMP)
ON CONFLICT (id) DO NOTHING;

-- 21. GLOBAL QUIZ SESSIONS TABLE (1-hour retention)
CREATE TABLE IF NOT EXISTS global_quiz_sessions (
    id SERIAL PRIMARY KEY,
    quiz_id VARCHAR(20) NOT NULL UNIQUE,
    question_count INTEGER NOT NULL,
    time_per_question INTEGER NOT NULL,
    total_participants INTEGER DEFAULT 0,
    quiz_data JSONB NOT NULL,
    completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_global_quiz_sessions_quiz_id ON global_quiz_sessions(quiz_id);
CREATE INDEX IF NOT EXISTS idx_global_quiz_sessions_expires_at ON global_quiz_sessions(expires_at);
CREATE INDEX IF NOT EXISTS idx_global_quiz_sessions_completed_at ON global_quiz_sessions(completed_at DESC);

-- 22. QUIZ GROUP RESULTS TABLE
CREATE TABLE IF NOT EXISTS quiz_group_results (
    id SERIAL PRIMARY KEY,
    quiz_id VARCHAR(20) NOT NULL,
    group_id BIGINT NOT NULL,
    group_title VARCHAR(255),
    participant_count INTEGER DEFAULT 0,
    group_data JSONB NOT NULL,
    UNIQUE(quiz_id, group_id)
);

CREATE INDEX IF NOT EXISTS idx_quiz_group_results_quiz_id ON quiz_group_results(quiz_id);
CREATE INDEX IF NOT EXISTS idx_quiz_group_results_group_id ON quiz_group_results(group_id);

-- 23. BOT STATS TABLE
CREATE TABLE IF NOT EXISTS bot_stats (
    id INTEGER PRIMARY KEY DEFAULT 1,
    total_users INTEGER NOT NULL DEFAULT 0,
    total_groups INTEGER NOT NULL DEFAULT 0,
    total_quizzes INTEGER NOT NULL DEFAULT 0,
    total_live_quizzes INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert initial bot stats
INSERT INTO bot_stats (id) VALUES (1) ON CONFLICT (id) DO NOTHING;

-- ============================================
-- HELPER FUNCTIONS & TRIGGERS
-- ============================================

-- Function to update updated_at timestamp automatically
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers for automatic updated_at timestamp
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

DROP TRIGGER IF EXISTS update_language_settings_updated_at ON language_settings;
CREATE TRIGGER update_language_settings_updated_at
    BEFORE UPDATE ON language_settings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_tagall_permissions_updated_at ON tagall_permissions;
CREATE TRIGGER update_tagall_permissions_updated_at
    BEFORE UPDATE ON tagall_permissions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Function to automatically delete expired quiz sessions
CREATE OR REPLACE FUNCTION delete_expired_quiz_sessions()
RETURNS void AS $$
BEGIN
    DELETE FROM global_quiz_sessions WHERE expires_at < CURRENT_TIMESTAMP;
END;
$$ LANGUAGE plpgsql;

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
-- VERIFICATION QUERIES (Uncomment to run)
-- ============================================

-- List all tables
-- SELECT table_name FROM information_schema.tables 
-- WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
-- ORDER BY table_name;

-- Count rows in each table
-- SELECT 'admins' as table_name, COUNT(*) as row_count FROM admins
-- UNION ALL SELECT 'user_stats', COUNT(*) FROM user_stats
-- UNION ALL SELECT 'group_stats', COUNT(*) FROM group_stats
-- UNION ALL SELECT 'language_preferences', COUNT(*) FROM language_preferences
-- UNION ALL SELECT 'language_settings', COUNT(*) FROM language_settings
-- UNION ALL SELECT 'force_join_settings', COUNT(*) FROM force_join_settings
-- UNION ALL SELECT 'force_join_targets', COUNT(*) FROM force_join_targets
-- UNION ALL SELECT 'welcome_messages', COUNT(*) FROM welcome_messages
-- UNION ALL SELECT 'welcome_groups', COUNT(*) FROM welcome_groups
-- UNION ALL SELECT 'tagall_permissions', COUNT(*) FROM tagall_permissions
-- UNION ALL SELECT 'tagall_history', COUNT(*) FROM tagall_history
-- UNION ALL SELECT 'tracked_members', COUNT(*) FROM tracked_members
-- UNION ALL SELECT 'quiz_sessions', COUNT(*) FROM quiz_sessions
-- UNION ALL SELECT 'quiz_participants', COUNT(*) FROM quiz_participants
-- UNION ALL SELECT 'quiz_questions', COUNT(*) FROM quiz_questions
-- UNION ALL SELECT 'quiz_answers', COUNT(*) FROM quiz_answers
-- UNION ALL SELECT 'global_quiz_sessions', COUNT(*) FROM global_quiz_sessions
-- UNION ALL SELECT 'quiz_group_results', COUNT(*) FROM quiz_group_results
-- UNION ALL SELECT 'bot_stats', COUNT(*) FROM bot_stats;

-- ============================================
-- ✅ SETUP COMPLETE!
-- ============================================
-- All 23 tables created successfully
-- All indexes created
-- All triggers configured
-- All views created
-- Your Neon DB is now ready for NEET Quiz Bot!
-- ============================================
