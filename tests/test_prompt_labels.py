import types

from langfuse.api import NotFoundError

from scripts import promote_prompt as promote
from scripts import register_prompts as register


class _FakeLangfuse:
    def __init__(self, production_exists):
        self.production_exists = production_exists
        self.created = []
        self.updated = []

    def get_prompt(self, name, label=None, **kwargs):
        if label == "production" and not self.production_exists:
            raise NotFoundError(body={})
        return types.SimpleNamespace(version=7, prompt="p", config={})

    def create_prompt(self, **kwargs):
        self.created.append(kwargs)

    def update_prompt(self, **kwargs):
        self.updated.append(kwargs)


def test_first_registration_in_a_new_environment_also_gets_production(monkeypatch):
    fake = _FakeLangfuse(production_exists=False)
    monkeypatch.setattr(register, "get_langfuse", lambda: fake)
    register.ensure_prompts()
    assert fake.created[0]["labels"] == ["staging", "production"]


def test_later_registrations_are_staging_only_so_the_gate_compares_something(monkeypatch):
    fake = _FakeLangfuse(production_exists=True)
    monkeypatch.setattr(register, "get_langfuse", lambda: fake)
    register.ensure_prompts()
    assert fake.created[0]["labels"] == ["staging"]


def test_promote_relabels_the_evaluated_version_instead_of_creating_a_new_one(monkeypatch):
    fake = _FakeLangfuse(production_exists=True)
    invalidated = []
    monkeypatch.setattr(promote, "get_langfuse", lambda: fake)
    monkeypatch.setattr(promote, "invalidate_analysis_cache", lambda reason: invalidated.append(reason))
    promote.promote_prompt("staging", "production")
    assert fake.created == []
    assert fake.updated == [{"name": "compliance-analyzer", "version": 7, "new_labels": ["production"]}]
    assert len(invalidated) == 1


def test_promote_to_a_non_production_label_does_not_invalidate_the_cache(monkeypatch):
    fake = _FakeLangfuse(production_exists=True)
    invalidated = []
    monkeypatch.setattr(promote, "get_langfuse", lambda: fake)
    monkeypatch.setattr(promote, "invalidate_analysis_cache", lambda reason: invalidated.append(reason))
    promote.promote_prompt("staging", "candidate")
    assert fake.updated[0]["new_labels"] == ["candidate"]
    assert invalidated == []
