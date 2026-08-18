import importlib.util
import os
import sys
from pathlib import Path

# `config.py` requires several env vars AND opens live clients (Langfuse over
# HTTP, a SQLAlchemy engine for the LLM cache) at import time. Worse,
# `graph/__init__.py` eagerly imports every node, including `retriever.py`,
# which runs a real DB query and constructs `PGVector` at import time too.
# Importing `graph.<anything>` therefore triggers live network/DB calls that
# have nothing to do with most unit tests and will hang/fail without a real
# backend. Seed harmless env var defaults for tests that only need `config`
# to import without raising (real env/.env values always win over setdefault).
os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic-key")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("LANGFUSE_PUBLIC_KEY", "test-public-key")
os.environ.setdefault("LANGFUSE_SECRET_KEY", "test-secret-key")

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def load_module_standalone(dotted_name: str, relative_path: str):
    """Import a single project module by file path, bypassing its package's
    __init__.py (and therefore any heavy/network side effects triggered by
    sibling modules in that package, e.g. graph/__init__.py -> retriever.py).
    Only safe for modules whose own top-level code has no such side effects.
    """
    spec = importlib.util.spec_from_file_location(dotted_name, _REPO_ROOT / relative_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[dotted_name] = module
    spec.loader.exec_module(module)
    return module
