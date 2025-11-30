-- Migration: Create LLM Request Logs Table
-- Description: Stores comprehensive logs of all LLM API requests (Chat, Embeddings, Transcription)
-- Created: 2025-11-30

CREATE TABLE IF NOT EXISTS llm_request_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Request Classification
    request_type TEXT NOT NULL CHECK (request_type IN ('chat', 'embedding', 'transcription')),
    model TEXT NOT NULL,

    -- User Context
    user_id BIGINT,
    session_id TEXT,

    -- Input Data
    input_text TEXT,
    input_metadata JSONB DEFAULT '{}'::jsonb,

    -- Output Data
    output_text TEXT,
    output_metadata JSONB DEFAULT '{}'::jsonb,

    -- Usage Metrics
    tokens_prompt INTEGER,
    tokens_completion INTEGER,
    tokens_total INTEGER,
    latency_ms INTEGER,
    cost_usd DECIMAL(10, 6),

    -- Status
    success BOOLEAN NOT NULL DEFAULT true,
    error_message TEXT,

    -- Raw Data (for debugging/audit)
    raw_request JSONB,
    raw_response JSONB
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_llm_logs_created_at ON llm_request_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_llm_logs_user_id ON llm_request_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_llm_logs_request_type ON llm_request_logs(request_type);
CREATE INDEX IF NOT EXISTS idx_llm_logs_model ON llm_request_logs(model);
CREATE INDEX IF NOT EXISTS idx_llm_logs_success ON llm_request_logs(success);

-- Composite index for user analytics
CREATE INDEX IF NOT EXISTS idx_llm_logs_user_created ON llm_request_logs(user_id, created_at DESC);

-- Enable Row Level Security (optional - adjust based on your needs)
ALTER TABLE llm_request_logs ENABLE ROW LEVEL SECURITY;

-- Policy: Allow service role full access (for bot operations)
CREATE POLICY "Service role has full access to llm_request_logs"
    ON llm_request_logs
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Comment
COMMENT ON TABLE llm_request_logs IS 'Comprehensive logging of all LLM API requests including chat completions, embeddings, and transcriptions';
