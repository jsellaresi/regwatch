"""Regression test for the import-time-side-effects fix.

Before this fix, `import graph` (transitively, via graph/__init__.py ->
graph/nodes/__init__.py -> retriever.py) ran a live DB query and built a
PGVector store, `config.py` raised RuntimeError unless 5 env vars were set
and built a live Langfuse client + SQLAlchemy engine, rerank.py downloaded a
CrossEncoder model, and 5 node modules (guardrails, analyze_compliance,
enrich_agent, multimodal_extract, agent_judge) each constructed a live LLM
client — all at import time. That made it impossible to unit-test any pure
logic (regex, routing, key derivation) without a reachable Postgres, real
API keys, and a network model download, and was the same root cause behind
the CI eval gate never being able to collect tests.

Each case runs in a fresh subprocess with a controlled environment — this is
the only reliable way to prove "importing X does not need env var Y", since
within a single pytest process module state and monkeypatched env vars can
leak between tests in ways that don't reflect a real fresh import.
"""

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TIMEOUT_SECONDS = 90  # generous headroom over the ~15-20s cold import time.
# Observed flaky at 30s when run as part of the full suite (system under
# load from other tests' own subprocess spawns) rather than in isolation —
# this is still far below what an actual hang (the original bug) would need.

# Vars this test suite cares about isolating per-case. Everything else is
# inherited from the current process (Windows needs SYSTEMROOT etc. for its
# own subsystems — a minimal from-scratch env breaks unrelated stdlib imports
# like asyncio's _overlapped, which has nothing to do with what we're testing).
_ISOLATED_KEYS = ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "DATABASE_URL",
                  "LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY")


def _run(code: str, env: dict) -> subprocess.CompletedProcess:
    full_env = {k: v for k, v in os.environ.items() if k not in _ISOLATED_KEYS}
    full_env.update(env)
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=REPO_ROOT,
        env=full_env,
        capture_output=True,
        text=True,
        timeout=TIMEOUT_SECONDS,
    )


def test_config_import_does_not_require_database_or_langfuse():
    result = _run(
        "import config; print(config.DATABASE_URL)",
        env={"ANTHROPIC_API_KEY": "x", "OPENAI_API_KEY": "x"},
    )
    assert result.returncode == 0, result.stderr


def test_config_validate_required_still_fails_fast_when_missing():
    result = _run(
        "import config; config.validate_required()",
        env={"ANTHROPIC_API_KEY": "x", "OPENAI_API_KEY": "x"},
    )
    assert result.returncode != 0
    assert "DATABASE_URL" in result.stderr


def test_importing_graph_does_not_touch_the_database():
    # DATABASE_URL points at a host that doesn't exist. If anything on the
    # `import graph` path tried to actually connect (the original bug in
    # retriever.py), this would hang or raise a connection error.
    result = _run(
        "import graph; print('ok')",
        env={
            "ANTHROPIC_API_KEY": "x",
            "OPENAI_API_KEY": "x",
            "DATABASE_URL": "postgresql://unreachable-host-for-test:1/db",
        },
    )
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout


def test_importing_graph_needs_no_env_vars_at_all():
    # The strongest guarantee: with every one of the 5 previously-required
    # vars absent, `import graph` still succeeds. This only holds because the
    # 5 node-level LLM clients (guardrails, analyze_compliance, enrich_agent,
    # multimodal_extract, agent_judge) are now lazily constructed on first
    # real use instead of at import time, same as Langfuse/retriever/rerank.
    result = _run("import graph; print('ok')", env={})
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout
