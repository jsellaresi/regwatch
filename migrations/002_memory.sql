CREATE TABLE IF NOT EXISTS policy_episodes (
    id          SERIAL PRIMARY KEY,
    policy_id   TEXT NOT NULL,
    gap_report  JSONB NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_policy ON policy_episodes (policy_id, created_at DESC);
