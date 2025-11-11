-- AUTO QUIZ CREATE BOT - PostgreSQL Database Schema
-- Migration from JSON file storage to Neon PostgreSQL

-- Table for tracking quiz ID counter
CREATE TABLE IF NOT EXISTS quiz_id_counter (
    id INTEGER PRIMARY KEY DEFAULT 1,
    counter INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Insert initial counter if not exists
INSERT INTO quiz_id_counter (id, counter) VALUES (1, 0) ON CONFLICT (id) DO NOTHING;

-- Table for storing completed global quiz sessions (1-hour retention)
CREATE TABLE IF NOT EXISTS global_quiz_sessions (
    quiz_id VARCHAR(10) PRIMARY KEY,
    question_count INTEGER NOT NULL,
    time_per_question INTEGER NOT NULL,
    total_participants INTEGER NOT NULL DEFAULT 0,
    quiz_data JSONB NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE DEFAULT (CURRENT_TIMESTAMP + INTERVAL '1 hour')
);

-- Create index on expires_at for cleanup queries
CREATE INDEX IF NOT EXISTS idx_quiz_sessions_expires ON global_quiz_sessions(expires_at);

-- Table for storing quiz participants (for leaderboards)
CREATE TABLE IF NOT EXISTS quiz_participants (
    id SERIAL PRIMARY KEY,
    quiz_id VARCHAR(10) NOT NULL REFERENCES global_quiz_sessions(quiz_id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL,
    user_name VARCHAR(255) NOT NULL,
    score INTEGER NOT NULL DEFAULT 0,
    correct_answers INTEGER NOT NULL DEFAULT 0,
    wrong_answers INTEGER NOT NULL DEFAULT 0,
    unattempted INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for participant queries
CREATE INDEX IF NOT EXISTS idx_participants_quiz ON quiz_participants(quiz_id);
CREATE INDEX IF NOT EXISTS idx_participants_user ON quiz_participants(user_id);

-- Table for storing group-wise quiz results
CREATE TABLE IF NOT EXISTS quiz_group_results (
    id SERIAL PRIMARY KEY,
    quiz_id VARCHAR(10) NOT NULL REFERENCES global_quiz_sessions(quiz_id) ON DELETE CASCADE,
    group_id BIGINT NOT NULL,
    group_name VARCHAR(255) NOT NULL,
    participant_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create index for group result queries
CREATE INDEX IF NOT EXISTS idx_group_results_quiz ON quiz_group_results(quiz_id);

-- Table for bot statistics
CREATE TABLE IF NOT EXISTS bot_stats (
    id INTEGER PRIMARY KEY DEFAULT 1,
    total_users INTEGER NOT NULL DEFAULT 0,
    total_groups INTEGER NOT NULL DEFAULT 0,
    total_quizzes INTEGER NOT NULL DEFAULT 0,
    total_live_quizzes INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Insert initial stats if not exists
INSERT INTO bot_stats (id) VALUES (1) ON CONFLICT (id) DO NOTHING;

-- Table for user statistics
CREATE TABLE IF NOT EXISTS user_stats (
    user_id BIGINT PRIMARY KEY,
    username VARCHAR(255),
    quiz_count INTEGER NOT NULL DEFAULT 0,
    live_quiz_count INTEGER NOT NULL DEFAULT 0,
    first_seen TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table for group statistics
CREATE TABLE IF NOT EXISTS group_stats (
    group_id BIGINT PRIMARY KEY,
    group_name VARCHAR(255),
    quiz_count INTEGER NOT NULL DEFAULT 0,
    live_quiz_count INTEGER NOT NULL DEFAULT 0,
    first_seen TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table for dynamic admin management
CREATE TABLE IF NOT EXISTS bot_admins (
    user_id BIGINT PRIMARY KEY,
    added_by BIGINT NOT NULL,
    added_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table for force join settings
CREATE TABLE IF NOT EXISTS force_join_targets (
    id SERIAL PRIMARY KEY,
    chat_id BIGINT NOT NULL UNIQUE,
    chat_type VARCHAR(50) NOT NULL,
    added_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table for language preferences (per-chat)
CREATE TABLE IF NOT EXISTS language_preferences (
    chat_id BIGINT PRIMARY KEY,
    language VARCHAR(10) NOT NULL DEFAULT 'english',
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table for welcome system settings
CREATE TABLE IF NOT EXISTS welcome_settings (
    group_id BIGINT PRIMARY KEY,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    custom_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table for tagall permissions (per-group)
CREATE TABLE IF NOT EXISTS tagall_permissions (
    group_id BIGINT PRIMARY KEY,
    enabled BOOLEAN NOT NULL DEFAULT FALSE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table for tracked members (for tagall feature)
CREATE TABLE IF NOT EXISTS tracked_members (
    id SERIAL PRIMARY KEY,
    group_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    username VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    is_admin BOOLEAN NOT NULL DEFAULT FALSE,
    last_seen TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(group_id, user_id)
);

-- Create index for member tracking queries
CREATE INDEX IF NOT EXISTS idx_tracked_members_group ON tracked_members(group_id);
CREATE INDEX IF NOT EXISTS idx_tracked_members_admin ON tracked_members(group_id, is_admin);

-- Function to automatically delete expired quiz sessions
CREATE OR REPLACE FUNCTION delete_expired_quiz_sessions()
RETURNS void AS $$
BEGIN
    DELETE FROM global_quiz_sessions WHERE expires_at < CURRENT_TIMESTAMP;
END;
$$ LANGUAGE plpgsql;

-- Comments for documentation
COMMENT ON TABLE global_quiz_sessions IS 'Stores completed global quiz sessions with 1-hour retention for force-send commands';
COMMENT ON TABLE quiz_participants IS 'Stores individual participant results for each quiz';
COMMENT ON TABLE quiz_group_results IS 'Stores group-wise results for each quiz';
COMMENT ON TABLE bot_stats IS 'Global bot statistics';
COMMENT ON TABLE user_stats IS 'Per-user statistics';
COMMENT ON TABLE group_stats IS 'Per-group statistics';
COMMENT ON TABLE bot_admins IS 'Dynamic admin user IDs';
COMMENT ON TABLE force_join_targets IS 'Required channels/groups for force join';
COMMENT ON TABLE language_preferences IS 'Per-chat language settings';
COMMENT ON TABLE welcome_settings IS 'Per-group welcome message settings';
COMMENT ON TABLE tagall_permissions IS 'Per-group tagall feature permissions';
COMMENT ON TABLE tracked_members IS 'Member tracking for tagall feature';
