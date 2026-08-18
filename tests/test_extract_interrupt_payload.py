"""Unit tests for api.interrupts.extract_interrupt_payload — the logic that
had to be added to /analyze (fix 2: async-invoke + handle the interrupted
state, since the graph always pauses at human_review on a fresh run and
there is never a `final_report` to return on that path). Also now shared by
/resume and /state, which previously each carried their own copy of this
same interrupt-extraction logic inline.

Plain namespace/dict-like fakes stand in for LangGraph's StateSnapshot /
PregelTask / Interrupt objects — this function only needs `.tasks` and
`.interrupts`/`.value` attributes, so no real graph or checkpointer is needed.
"""

from types import SimpleNamespace

from api.interrupts import extract_interrupt_payload


def _interrupt(value=None):
    return SimpleNamespace(value=value) if value is not None else SimpleNamespace()


def _task(*interrupts):
    return SimpleNamespace(interrupts=list(interrupts))


def _state(tasks):
    return SimpleNamespace(tasks=tasks)


def test_no_tasks_returns_none():
    assert extract_interrupt_payload(_state(tasks=None)) is None
    assert extract_interrupt_payload(_state(tasks=[])) is None


def test_task_with_no_interrupts_returns_none():
    assert extract_interrupt_payload(_state(tasks=[_task()])) is None


def test_single_interrupt_returns_its_value():
    payload = {"gap_report": {"gaps": []}, "reason": "review"}
    state = _state(tasks=[_task(_interrupt(payload))])
    assert extract_interrupt_payload(state) == payload


def test_first_interrupt_wins_when_multiple_present():
    first = {"which": "first"}
    second = {"which": "second"}
    state = _state(tasks=[_task(_interrupt(first), _interrupt(second))])
    assert extract_interrupt_payload(state) == first


def test_interrupt_across_multiple_tasks_finds_first_task_first():
    payload = {"which": "task-1"}
    state = _state(tasks=[_task(_interrupt(payload)), _task(_interrupt({"which": "task-2"}))])
    assert extract_interrupt_payload(state) == payload


def test_interrupt_object_without_value_attribute_yields_empty_dict():
    # Defensive case: an interrupt-like object with no `.value` at all.
    bare_interrupt = object()
    state = _state(tasks=[_task(bare_interrupt)])
    assert extract_interrupt_payload(state) == {}
