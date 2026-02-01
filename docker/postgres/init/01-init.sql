-- OpenClaw VPS - PostgreSQL Initialization Script
-- このスクリプトは初回起動時のみ実行されます

-- ============================================
-- N8N Schema
-- ============================================
CREATE SCHEMA IF NOT EXISTS n8n;

COMMENT ON SCHEMA n8n IS 'N8N workflow automation schema';

-- N8Nは自動的にテーブルを作成するため、ここでは空のスキーマを準備

-- ============================================
-- OpenNotebook Schema
-- ============================================
CREATE SCHEMA IF NOT EXISTS opennotebook;

COMMENT ON SCHEMA opennotebook IS 'OpenNotebook knowledge management schema';

-- Notebooks table
CREATE TABLE IF NOT EXISTS opennotebook.notebooks (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    content TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_notebooks_created_at ON opennotebook.notebooks(created_at DESC);
CREATE INDEX idx_notebooks_deleted_at ON opennotebook.notebooks(deleted_at) WHERE deleted_at IS NULL;

COMMENT ON TABLE opennotebook.notebooks IS 'Notebook entries';

-- Notes table
CREATE TABLE IF NOT EXISTS opennotebook.notes (
    id SERIAL PRIMARY KEY,
    notebook_id INTEGER REFERENCES opennotebook.notebooks(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    content TEXT,
    tags TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_notes_notebook_id ON opennotebook.notes(notebook_id);
CREATE INDEX idx_notes_tags ON opennotebook.notes USING GIN(tags);

COMMENT ON TABLE opennotebook.notes IS 'Individual notes within notebooks';

-- ============================================
-- OpenClaw Schema
-- ============================================
CREATE SCHEMA IF NOT EXISTS openclaw;

COMMENT ON SCHEMA openclaw IS 'OpenClaw AI agent schema';

-- Conversations table
CREATE TABLE IF NOT EXISTS openclaw.conversations (
    id SERIAL PRIMARY KEY,
    telegram_chat_id BIGINT,
    title VARCHAR(255),
    context JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_conversations_telegram_chat_id ON openclaw.conversations(telegram_chat_id);
CREATE INDEX idx_conversations_created_at ON openclaw.conversations(created_at DESC);

COMMENT ON TABLE openclaw.conversations IS 'Conversation history';

-- Messages table
CREATE TABLE IF NOT EXISTS openclaw.messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER REFERENCES openclaw.conversations(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_messages_conversation_id ON openclaw.messages(conversation_id);
CREATE INDEX idx_messages_created_at ON openclaw.messages(created_at DESC);

COMMENT ON TABLE openclaw.messages IS 'Individual messages in conversations';

-- Tasks table
CREATE TABLE IF NOT EXISTS openclaw.tasks (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER REFERENCES openclaw.conversations(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'completed', 'failed')),
    result JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_tasks_conversation_id ON openclaw.tasks(conversation_id);
CREATE INDEX idx_tasks_status ON openclaw.tasks(status);
CREATE INDEX idx_tasks_created_at ON openclaw.tasks(created_at DESC);

COMMENT ON TABLE openclaw.tasks IS 'AI agent tasks and their execution status';

-- ============================================
-- Updated_at Trigger Function
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply triggers
CREATE TRIGGER update_notebooks_updated_at
    BEFORE UPDATE ON opennotebook.notebooks
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_notes_updated_at
    BEFORE UPDATE ON opennotebook.notes
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_conversations_updated_at
    BEFORE UPDATE ON openclaw.conversations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_tasks_updated_at
    BEFORE UPDATE ON openclaw.tasks
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- Sample Data (Optional)
-- ============================================
INSERT INTO opennotebook.notebooks (title, content) VALUES
    ('Welcome to OpenNotebook', 'This is your first notebook. Start adding notes!'),
    ('Getting Started', 'Learn how to use OpenNotebook effectively.')
ON CONFLICT DO NOTHING;

-- ============================================
-- Permissions
-- ============================================
-- Grant schema permissions to the openclaw user
GRANT USAGE ON SCHEMA n8n TO openclaw;
GRANT USAGE ON SCHEMA opennotebook TO openclaw;
GRANT USAGE ON SCHEMA openclaw TO openclaw;

-- Grant table permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA n8n TO openclaw;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA opennotebook TO openclaw;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA openclaw TO openclaw;

-- Grant sequence permissions
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA opennotebook TO openclaw;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA openclaw TO openclaw;

-- Default privileges for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA n8n GRANT ALL ON TABLES TO openclaw;
ALTER DEFAULT PRIVILEGES IN SCHEMA opennotebook GRANT ALL ON TABLES TO openclaw;
ALTER DEFAULT PRIVILEGES IN SCHEMA openclaw GRANT ALL ON TABLES TO openclaw;

ALTER DEFAULT PRIVILEGES IN SCHEMA opennotebook GRANT ALL ON SEQUENCES TO openclaw;
ALTER DEFAULT PRIVILEGES IN SCHEMA openclaw GRANT ALL ON SEQUENCES TO openclaw;

-- ============================================
-- Completion
-- ============================================
\echo 'Database initialization complete!'
\echo 'Schemas created: n8n, opennotebook, openclaw'
\echo 'Tables created and permissions granted'
