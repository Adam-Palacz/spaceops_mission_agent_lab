-- PS7.6: shared daily LLM token ledger (LLM_BUDGET_MODE=postgres).
-- Run once after Postgres starts (same DB as agent/checkpoints).

CREATE TABLE IF NOT EXISTS llm_usage_ledger (
    usage_date DATE NOT NULL PRIMARY KEY,
    tokens_used BIGINT NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE llm_usage_ledger IS
    'PS7.6 UTC-day token totals for shared org cap across API/worker replicas.';
