import os
from dotenv import load_dotenv
from langfuse import Langfuse

load_dotenv()


def _required(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise RuntimeError(f"Falta la variable de entorno obligatoria: {key} (revisa tu .env)")
    return value


ANTHROPIC_API_KEY  = _required("ANTHROPIC_API_KEY")
OPENAI_API_KEY     = _required("OPENAI_API_KEY")
_cohere_raw        = os.getenv("COHERE_API_KEY", "").strip()
COHERE_API_KEY     = "" if (not _cohere_raw or _cohere_raw.startswith("#")) else _cohere_raw
DATABASE_URL       = _required("DATABASE_URL")
JIRA_API_TOKEN     = os.getenv("JIRA_API_TOKEN", "")
JIRA_ENABLED       = os.getenv("JIRA_ENABLED", "false").lower() == "true"
EURLEX_BASE_URL    = "https://eur-lex.europa.eu/rest"

# ── Model names ──────────────────────────────────────────────────────────────
MODEL_ANALYZER      = "claude-3-5-haiku-20241022"
MODEL_ENRICH        = "claude-3-5-haiku-20241022"
MODEL_VISION        = "claude-sonnet-4-6"
MODEL_GUARDRAIL     = "claude-haiku-4-5-20251001"
MODEL_JUDGE         = "gpt-4o"
MODEL_CHAT          = "gpt-4o"
MODEL_EMBEDDINGS    = "text-embedding-3-small"
MODEL_RERANK_LOCAL  = "cross-encoder/ms-marco-MiniLM-L-6-v2"
MODEL_RERANK_COHERE = "rerank-multilingual-v3.0"

CACHE_TTL_SECONDS  = 60 * 60 * 24 * 7

langfuse = Langfuse(
    public_key=_required("LANGFUSE_PUBLIC_KEY"),
    secret_key=_required("LANGFUSE_SECRET_KEY"),
    host=(os.getenv("LANGFUSE_HOST") or os.getenv("LANGFUSE_BASE_URL")
          or "https://cloud.langfuse.com"),
)

import hashlib
from langchain_core.globals import set_llm_cache
from langchain_community.cache import SQLAlchemyCache
from sqlalchemy import create_engine


class _HashedPromptCache(SQLAlchemyCache):
    @staticmethod
    def _h(prompt: str) -> str:
        return hashlib.md5(prompt.encode()).hexdigest()

    def lookup(self, prompt, llm_string):
        return super().lookup(self._h(prompt), llm_string)

    def update(self, prompt, llm_string, return_val):
        return super().update(self._h(prompt), llm_string, return_val)


set_llm_cache(_HashedPromptCache(create_engine(DATABASE_URL)))
