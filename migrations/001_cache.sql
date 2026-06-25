CREATE TABLE IF NOT EXISTS analysis_cache (
    doc_hash    TEXT PRIMARY KEY,
    final_report JSONB NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
