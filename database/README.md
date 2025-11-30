# Database Migrations

This directory contains SQL migration files for the database schema.

## LLM Request Logging Migration

### Overview

The `create_llm_logs_table.sql` migration creates a comprehensive logging system for all LLM API requests (chat completions, embeddings, and transcriptions).

### What This Migration Creates

1. **Table: `llm_request_logs`**
   - Stores all LLM API requests with detailed metadata
   - Tracks tokens, costs, latency, and success/failure status
   - Supports three request types: `chat`, `embedding`, `transcription`

2. **Indexes** for efficient querying:
   - `created_at` (for time-based queries)
   - `user_id` (for per-user analytics)
   - `request_type` (for filtering by type)
   - `model` (for model-specific analytics)
   - `success` (for error analysis)
   - Composite index on `(user_id, created_at)` for user analytics

3. **Row Level Security (RLS)** with service role access policy

### How to Apply the Migration

#### Option 1: Supabase Dashboard (Recommended)

1. Log in to your [Supabase Dashboard](https://app.supabase.com)
2. Select your project
3. Go to **SQL Editor** (left sidebar)
4. Click **New Query**
5. Copy the contents of `database/migrations/create_llm_logs_table.sql`
6. Paste into the SQL Editor
7. Click **Run** (or press Ctrl+Enter / Cmd+Enter)
8. Verify the table was created:
   ```sql
   SELECT * FROM llm_request_logs LIMIT 1;
   ```

#### Option 2: Using Supabase CLI

If you have the Supabase CLI installed:

```bash
# Make sure you're logged in
supabase login

# Link your project (if not already linked)
supabase link --project-ref your-project-ref

# Run the migration
supabase db push --include-all
```

#### Option 3: Using psql

If you have direct PostgreSQL access:

```bash
psql "postgresql://postgres:[YOUR-PASSWORD]@[YOUR-HOST]:5432/postgres" \
  -f database/migrations/create_llm_logs_table.sql
```

### Verification

After running the migration, verify it was successful:

```sql
-- Check if table exists
SELECT table_name
FROM information_schema.tables
WHERE table_name = 'llm_request_logs';

-- Check table structure
\d llm_request_logs

-- Check indexes
SELECT indexname
FROM pg_indexes
WHERE tablename = 'llm_request_logs';

-- Check RLS is enabled
SELECT tablename, rowsecurity
FROM pg_tables
WHERE tablename = 'llm_request_logs';
```

### Usage

The logging system is automatically integrated into:

1. **RAG Pipeline** (`bot/services/rag_pipeline.py`)
   - Logs all embedding requests
   - Logs all chat completion requests
   - Captures token usage, latency, and costs

2. **Transcription Services**
   - `bot/services/transcription.py` - Standalone transcription functions
   - `bot/handlers/handlers.py` - Voice message transcriptions
   - Captures audio metadata and transcription results

3. **Automatic Logging**
   - All successful and failed requests are logged
   - No manual intervention required
   - Logging errors are suppressed to avoid breaking main functionality

### Example Queries

#### Total API costs by user

```sql
SELECT
  user_id,
  COUNT(*) as total_requests,
  SUM(cost_usd) as total_cost_usd,
  SUM(tokens_total) as total_tokens
FROM llm_request_logs
GROUP BY user_id
ORDER BY total_cost_usd DESC;
```

#### Error rate by model

```sql
SELECT
  model,
  request_type,
  COUNT(*) as total_requests,
  SUM(CASE WHEN success = false THEN 1 ELSE 0 END) as failed_requests,
  ROUND(100.0 * SUM(CASE WHEN success = false THEN 1 ELSE 0 END) / COUNT(*), 2) as error_rate_pct
FROM llm_request_logs
GROUP BY model, request_type
ORDER BY error_rate_pct DESC;
```

#### Average latency by request type

```sql
SELECT
  request_type,
  model,
  COUNT(*) as request_count,
  ROUND(AVG(latency_ms), 2) as avg_latency_ms,
  ROUND(AVG(tokens_total), 2) as avg_tokens
FROM llm_request_logs
WHERE success = true
GROUP BY request_type, model
ORDER BY request_type, avg_latency_ms DESC;
```

#### Daily usage and costs

```sql
SELECT
  DATE(created_at) as date,
  COUNT(*) as total_requests,
  SUM(cost_usd) as total_cost_usd,
  SUM(tokens_total) as total_tokens
FROM llm_request_logs
GROUP BY DATE(created_at)
ORDER BY date DESC;
```

### Rollback

If you need to remove the table and all related objects:

```sql
-- Drop the table (cascades to indexes and policies)
DROP TABLE IF EXISTS llm_request_logs CASCADE;
```

### Notes

- The logging system is designed to be non-intrusive - if logging fails, it won't break your main application
- All costs are estimates in USD - adjust pricing calculations if needed
- Token counts are captured from API responses when available
- Raw request/response data is stored as JSONB for debugging purposes
