"""Regression test for fix 6.

Before this fix, api/main.py's lifespan called ensure_prompts() on every
startup, which unconditionally creates a new Langfuse prompt version and
labels it BOTH staging and production (register_prompts.py has no gating
condition). That breaks the two things ADR-0009 wants: controlled promotion
(nothing goes through the eval gate) and informe-version traceability (the
version number tracks container restarts, not actual prompt changes).

api/main.py is deliberately NOT imported here: its own top-level imports
(langchain_openai, scripts.ingest_regulations -> PDFPlumberLoader) take
40-80s to import, and this check doesn't need a live module — it just needs
to confirm the source no longer wires ensure_prompts() into the app.
"""

import inspect
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_api_main_source_no_longer_references_ensure_prompts():
    source = (REPO_ROOT / "api" / "main.py").read_text(encoding="utf-8")
    assert "ensure_prompts" not in source


def test_api_main_lifespan_still_validates_config_and_initializes_llm_cache():
    # Make sure removing ensure_prompts() didn't also strip the two calls
    # from an earlier fix (fix "part 1") that must still run at startup.
    source = (REPO_ROOT / "api" / "main.py").read_text(encoding="utf-8")
    lifespan_start = source.index("async def lifespan")
    lifespan_body = source[lifespan_start:source.index("yield", lifespan_start)]
    assert "config.validate_required()" in lifespan_body
    assert "config.init_llm_cache()" in lifespan_body


def test_manual_bootstrap_path_still_registers_prompts():
    # The documented manual step (README.md / GETTING-STARTED.md:
    # `docker compose exec api python -m scripts.register_prompts`) must
    # still work — this is now the *only* place prompts get registered.
    # scripts.register_prompts has no heavy imports, safe to import directly.
    #
    # Note: register_prompts.py has no `main()` function — its CLI behavior
    # lives directly under `if __name__ == "__main__":`, unlike
    # promote_prompt.py's `main()`. pyproject.toml's console-script entry
    # (`regwatch-register-prompts = "scripts.register_prompts:main"`) is
    # therefore broken (AttributeError) — a separate, pre-existing bug this
    # test doesn't attempt to fix, just doesn't assume away.
    from scripts.register_prompts import ensure_prompts

    assert callable(ensure_prompts)
    source = inspect.getsource(__import__("scripts.register_prompts", fromlist=["_"]))
    assert '__name__ == "__main__"' in source
    assert "ensure_prompts()" in source
    assert "validate_required()" in source


def test_readme_documents_the_manual_registration_step():
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "scripts.register_prompts" in readme
