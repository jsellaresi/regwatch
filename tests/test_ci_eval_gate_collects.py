"""Regression test for fix 4 (CI eval gate).

Before this fix, the workflow only exported ANTHROPIC_API_KEY and the 3
Langfuse vars, but evals/eval_suite.py imports config, which required
OPENAI_API_KEY and DATABASE_URL at import time too — so the gate raised a
RuntimeError before pytest could even collect a single test, and (separately)
the workflow file lived at regwatch/.github/workflows/, one level below the
actual repo root (Block 20/.git), so GitHub Actions never ran it at all.

This test can't verify "does GitHub Actions discover the file" (that's a
property of the file's path in the repo, not something Python can assert),
but it does verify the part that actually matters for correctness: given
exactly the env vars the fixed workflow now provides — real-looking but
fake placeholder values, since collection must not require live
credentials or a live Postgres — pytest can collect evals/eval_suite.py
without error. This is the exact failure mode from the PDF finding.
"""

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TIMEOUT_SECONDS = 60

# Mirrors the `env:` block in Block 20/.github/workflows/eval_gate.yml.
CI_ENV = {
    "ANTHROPIC_API_KEY": "ci-placeholder",
    "OPENAI_API_KEY": "ci-placeholder",
    "DATABASE_URL": "postgresql://ci:ci@localhost:5432/ci_placeholder_unused",
    "LANGFUSE_PUBLIC_KEY": "ci-placeholder",
    "LANGFUSE_SECRET_KEY": "ci-placeholder",
}
_ISOLATED_KEYS = tuple(CI_ENV)


def _collect(env_overrides: dict) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k not in _ISOLATED_KEYS}
    env.update(env_overrides)
    return subprocess.run(
        [sys.executable, "-m", "pytest", "evals/eval_suite.py", "--collect-only", "-q"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=TIMEOUT_SECONDS,
    )


def test_eval_suite_collects_with_ci_env_vars():
    result = _collect(CI_ENV)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "3 tests collected" in result.stdout


def test_eval_suite_collection_fails_clearly_when_a_var_is_missing():
    # Reproduces the original bug: without OPENAI_API_KEY/DATABASE_URL (the
    # two the old workflow never exported), collection must fail — and fail
    # with a clear message naming the missing vars, not an opaque traceback.
    incomplete_env = {k: v for k, v in CI_ENV.items()
                       if k not in ("OPENAI_API_KEY", "DATABASE_URL")}
    result = _collect(incomplete_env)
    assert result.returncode != 0
    assert "OPENAI_API_KEY" in result.stdout + result.stderr
    assert "DATABASE_URL" in result.stdout + result.stderr


def test_workflow_file_is_at_the_real_repo_root_not_inside_the_subproject():
    # The other half of finding 4: the workflow must live where GitHub
    # Actions actually looks — <repo-root>/.github/workflows/ — not inside
    # the regwatch/ subproject that this repo's real root (Block 20) contains.
    repo_root = REPO_ROOT.parent
    assert (repo_root / ".git").exists(), "test assumption: repo root is one level above regwatch/"
    assert (repo_root / ".github" / "workflows" / "eval_gate.yml").exists()
    assert not (REPO_ROOT / ".github").exists()
