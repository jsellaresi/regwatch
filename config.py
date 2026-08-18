import os
from dotenv import load_dotenv

load_dotenv()

# Vars actually required to run the app for real (API startup, scripts, evals).
# Read plainly here (no raise) so importing this module — and anything that
# transitively imports it — never requires live credentials just to exist.
# Call validate_required() once, at a real entry point, to fail fast instead.
_REQUIRED_KEYS = (
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "DATABASE_URL",
    "LANGFUSE_PUBLIC_KEY",
    "LANGFUSE_SECRET_KEY",
)


def validate_required() -> None:
    missing = [key for key in _REQUIRED_KEYS if not os.getenv(key)]
    if missing:
        raise RuntimeError(
            f"Faltan variables de entorno obligatorias: {', '.join(missing)} (revisa tu .env)"
        )


ANTHROPIC_API_KEY  = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY     = os.getenv("OPENAI_API_KEY", "")
_cohere_raw        = os.getenv("COHERE_API_KEY", "").strip()
COHERE_API_KEY     = "" if (not _cohere_raw or _cohere_raw.startswith("#")) else _cohere_raw
DATABASE_URL       = os.getenv("DATABASE_URL", "")
JIRA_API_TOKEN     = os.getenv("JIRA_API_TOKEN", "")
JIRA_ENABLED       = os.getenv("JIRA_ENABLED", "false").lower() == "true"
JIRA_BASE_URL      = os.getenv("JIRA_BASE_URL", "https://your-org.atlassian.net")
EURLEX_BASE_URL    = "https://eur-lex.europa.eu/rest"

# ── Model names ──────────────────────────────────────────────────────────────
MODEL_ANALYZER      = "claude-haiku-4-5"
MODEL_ENRICH        = "claude-haiku-4-5"
MODEL_VISION        = "claude-sonnet-4-6"
MODEL_GUARDRAIL     = "claude-haiku-4-5"
MODEL_JUDGE         = "gpt-4o"
MODEL_CHAT          = "gpt-4o"
MODEL_EMBEDDINGS    = "text-embedding-3-small"
MODEL_RERANK_LOCAL  = "BAAI/bge-reranker-v2-m3"
MODEL_RERANK_COHERE = "rerank-multilingual-v3.0"

CACHE_TTL_SECONDS  = 60 * 60 * 24 * 7

_langfuse_client = None


def get_langfuse():
    """Lazily construct the Langfuse client on first real use, instead of at
    import time. Importing `config` (directly or transitively via `graph`)
    must not require live Langfuse credentials or a network round-trip."""
    global _langfuse_client
    if _langfuse_client is None:
        from langfuse import Langfuse

        _langfuse_client = Langfuse(
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY", ""),
            secret_key=os.getenv("LANGFUSE_SECRET_KEY", ""),
            host=(os.getenv("LANGFUSE_HOST") or os.getenv("LANGFUSE_BASE_URL")
                  or "https://cloud.langfuse.com"),
        )
    return _langfuse_client


import hashlib


def _make_hashed_prompt_cache(engine):
    from langchain_community.cache import SQLAlchemyCache

    class HashedPromptCache(SQLAlchemyCache):
        @staticmethod
        def _h(prompt: str) -> str:
            return hashlib.md5(prompt.encode()).hexdigest()

        def lookup(self, prompt, llm_string):
            return super().lookup(self._h(prompt), llm_string)

        def update(self, prompt, llm_string, return_val):
            return super().update(self._h(prompt), llm_string, return_val)

    return HashedPromptCache(engine)


_llm_cache_initialized = False


def init_llm_cache() -> None:
    """Build the SQLAlchemy-backed LLM cache and register it globally. Must be
    called explicitly once, by a real entry point (API startup, scripts,
    evals) — never at import time, since it needs a reachable DATABASE_URL."""
    global _llm_cache_initialized
    if _llm_cache_initialized:
        return
    from langchain_core.globals import set_llm_cache
    from sqlalchemy import create_engine

    set_llm_cache(_make_hashed_prompt_cache(create_engine(DATABASE_URL)))
    _llm_cache_initialized = True
