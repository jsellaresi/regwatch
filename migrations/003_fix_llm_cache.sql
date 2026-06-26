-- Safe to drop: full_llm_cache is a pure cache (no source-of-truth data).
-- Recreated on next startup by SQLAlchemyCache with hashed prompt keys.
DROP TABLE IF EXISTS full_llm_cache;
