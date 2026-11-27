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
TIMEOUT_SECONDS = 90  # see test_import_side_effects.py for why 90 and not 30-60:
# observed flaky under full-suite system load, not in isolation.

# Mirrors the `env:` block in .github/workflows/eval_gate.yml.
CI_ENV = {
    "ANTHROPIC_API_KEY": "ci-placeholder",
    "OPENAI_API_KEY": "ci-placeholder",
    "DATABASE_URL": "postgresql://ci:ci@localhost:5432/ci_placeholder_unused",
    "LANGFUSE_PUBLIC_KEY": "ci-placeholder",
    "LANGFUSE_SECRET_KEY": "ci-placeholder",
}
_ISOLATED_KEYS = tuple(CI_ENV)


def _collect(env_overrides: dict, target: str = "evals/eval_suite.py") -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k not in _ISOLATED_KEYS}
    env["PYTHON_DOTENV_DISABLED"] = "1"  # a local .env must not refill the variables removed above
    env.update(env_overrides)
    return subprocess.run(
        [sys.executable, "-m", "pytest", target, "--collect-only", "-q"],
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


def test_workflow_file_is_at_the_repo_root():
    # GitHub Actions only reads <repo-root>/.github/workflows/.
    assert (REPO_ROOT / ".git").exists(), "test assumption: this directory is the repo root"
    assert (REPO_ROOT / ".github" / "workflows" / "eval_gate.yml").exists()


def test_eval_gate_push_trigger_is_limited_to_main():
    # The workflow's last step promotes staging -> production on any `push`
    # event; without a branch filter a feature-branch push would promote.
    import yaml

    workflow = yaml.safe_load((REPO_ROOT / ".github" / "workflows" / "eval_gate.yml").read_text(encoding="utf-8"))
    triggers = workflow.get("on", workflow.get(True))
    assert triggers["push"]["branches"] == ["main"]


def _workflow(name):
    import yaml

    return yaml.safe_load((REPO_ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8"))


def _triggers(workflow):
    return workflow.get("on", workflow.get(True))


def test_workflows_never_use_triggers_that_expose_secrets_to_outsiders():
    for path in (REPO_ROOT / ".github" / "workflows").glob("*.yml"):
        triggers = _triggers(_workflow(path.name))
        assert "pull_request_target" not in triggers, path.name
        assert "issue_comment" not in triggers, path.name


def test_workflows_declare_read_only_token_permissions():
    for path in (REPO_ROOT / ".github" / "workflows").glob("*.yml"):
        assert _workflow(path.name)["permissions"] == {"contents": "read"}, path.name


def test_eval_gate_spends_credits_only_for_the_owner_on_main_via_the_evals_environment():
    workflow = _workflow("eval_gate.yml")
    triggers = _triggers(workflow)
    assert "pull_request" not in triggers
    job = workflow["jobs"]["eval-gate"]
    assert job["environment"] == "evals"
    assert job["if"] == "github.actor == github.repository_owner"


def test_retrieval_suite_collects_with_ci_env_vars():
    result = _collect(CI_ENV, target="evals/retrieval_suite.py")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "3 tests collected" in result.stdout


def test_eval_gate_runs_both_suites_against_a_real_pgvector_database():
    workflow = _workflow("eval_gate.yml")
    job = workflow["jobs"]["eval-gate"]
    assert job["services"]["postgres"]["image"].startswith("pgvector/pgvector")
    assert "localhost:5432/regwatch" in job["env"]["DATABASE_URL"]
    assert "placeholder" not in job["env"]["DATABASE_URL"]
    commands = " ".join(step.get("run", "") for step in job["steps"])
    assert "evals/eval_suite.py" in commands and "evals/retrieval_suite.py" in commands
    assert "scripts.ingest_regulations" in commands


def test_register_prompt_workflow_is_manual_owner_only_and_uses_the_evals_environment():
    workflow = _workflow("register-prompt.yml")
    assert set(_triggers(workflow)) == {"workflow_dispatch"}
    job = workflow["jobs"]["register"]
    assert job["environment"] == "evals"
    assert job["if"] == "github.actor == github.repository_owner"
    commands = " ".join(step.get("run", "") for step in job["steps"])
    assert "scripts.register_prompts" in commands


def test_eval_gate_applies_every_migration_before_ingesting_the_corpus():
    # Ingestion invalidates analysis_cache after each regulation; without the
    # migrations that table does not exist and the ingestion step crashes.
    steps = _workflow("eval_gate.yml")["jobs"]["eval-gate"]["steps"]
    runs = [step.get("run", "") for step in steps]
    migrate = next(i for i, run in enumerate(runs) if "migrations/*.sql" in run)
    ingest = next(i for i, run in enumerate(runs) if "scripts.ingest_regulations" in run)
    assert migrate < ingest
    assert "docker/init-db.sql" in runs[migrate]


def test_cached_corpus_is_loaded_without_settings_newer_than_the_postgres_service():
    # The runner's pg_dump can be newer than the Postgres 16 service and emit
    # `SET transaction_timeout`, which the server rejects; the cached dump is reused across runs.
    steps = _workflow("eval_gate.yml")["jobs"]["eval-gate"]["steps"]
    load = next(step for step in steps if step.get("name") == "Load cached corpus")
    assert "transaction_timeout" in load["run"] and "ON_ERROR_STOP=1" in load["run"]
