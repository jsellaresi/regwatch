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
COHERE_API_KEY     = os.getenv("COHERE_API_KEY", "")
DATABASE_URL       = _required("DATABASE_URL")
JIRA_API_TOKEN     = _required("JIRA_API_TOKEN")
EURLEX_BASE_URL    = "https://eur-lex.europa.eu/rest"

CACHE_TTL_SECONDS  = 60 * 60 * 24 * 7

langfuse = Langfuse(
    public_key=_required("LANGFUSE_PUBLIC_KEY"),
    secret_key=_required("LANGFUSE_SECRET_KEY"),
    host=(os.getenv("LANGFUSE_HOST") or os.getenv("LANGFUSE_BASE_URL")
          or "https://cloud.langfuse.com"),
)

from langchain_core.globals import set_llm_cache
from langchain_community.cache import SQLAlchemyCache
from sqlalchemy import create_engine
set_llm_cache(SQLAlchemyCache(create_engine(DATABASE_URL)))
