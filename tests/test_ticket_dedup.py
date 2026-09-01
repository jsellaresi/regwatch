"""Regression tests for fix 13 (JIRA ticket deduplication against memory).

Before this fix, create_tickets opened a ticket for every HIGH/MEDIUM gap on
every run — re-analyzing the same policy re-opened tickets for gaps that
were already tracked as still-open, even though memory_diff (computed in
format_report.py via diff_with_memory) already has exactly the information
needed to avoid that: memory_diff["new"] is the set of gap keys that weren't
present in the policy's previous analysis.

graph.nodes.memory/create_tickets are inside the `graph` package (heavy
LangChain/torch import chain, ~15-85s depending on system load — this
session observed real variance, not a bug); accepted here since verifying
the actual wired functions matters more than avoiding that cost.
"""

from graph.nodes.create_tickets import select_eligible_gaps
from graph.nodes.memory import gap_key


def _gap(regulation_ref="GDPR Art. 17", risk_level="HIGH", description="Missing retention clause"):
    return {
        "regulation_ref": regulation_ref,
        "gap_description": description,
        "risk_level": risk_level,
        "remediation": "Add a retention clause",
        "confidence": 0.9,
    }


def test_new_high_risk_gap_is_eligible():
    gap = _gap(risk_level="HIGH")
    memory_diff = {"new": [gap_key(gap)], "still_open": [], "resolved": []}
    assert select_eligible_gaps([gap], memory_diff) == [gap]


def test_still_open_gap_is_not_reopened_as_a_duplicate():
    # This is the actual bug: a gap that already had a ticket from a
    # previous analysis (it's in "still_open", not "new") must not get a
    # second ticket just because the policy was re-analyzed.
    gap = _gap(risk_level="HIGH")
    memory_diff = {"new": [], "still_open": [gap_key(gap)], "resolved": []}
    assert select_eligible_gaps([gap], memory_diff) == []


def test_low_risk_gap_is_never_eligible_even_if_new():
    gap = _gap(risk_level="LOW")
    memory_diff = {"new": [gap_key(gap)], "still_open": [], "resolved": []}
    assert select_eligible_gaps([gap], memory_diff) == []


def test_first_ever_analysis_has_no_history_so_everything_new_is_eligible():
    # No prior episode: diff_with_memory sets memory_diff["new"] = every
    # current gap key (nothing to compare against). Nothing should be
    # filtered out relative to the old (pre-fix) behavior in this case.
    high = _gap(regulation_ref="GDPR Art. 17", risk_level="HIGH")
    medium = _gap(regulation_ref="MiFID II Art. 23", risk_level="MEDIUM", description="Conflicts undisclosed")
    gaps = [high, medium]
    memory_diff = {"new": [gap_key(high), gap_key(medium)], "still_open": [], "resolved": []}
    assert select_eligible_gaps(gaps, memory_diff) == gaps


def test_mixed_batch_only_new_high_medium_gaps_pass():
    new_high = _gap(regulation_ref="GDPR Art. 17", risk_level="HIGH")
    still_open_high = _gap(regulation_ref="GDPR Art. 5(1)(e)", risk_level="HIGH", description="Already ticketed")
    new_low = _gap(regulation_ref="4AMLD Art. 11", risk_level="LOW", description="Minor, new")
    gaps = [new_high, still_open_high, new_low]
    memory_diff = {
        "new": [gap_key(new_high), gap_key(new_low)],
        "still_open": [gap_key(still_open_high)],
        "resolved": [],
    }
    assert select_eligible_gaps(gaps, memory_diff) == [new_high]


def test_missing_memory_diff_key_fails_closed_not_open():
    # Defensive default: if memory_diff (or its "new" key) is somehow
    # absent, nothing is eligible rather than falling back to "create a
    # ticket for everything" — under-creating is the safer failure mode
    # than duplicating tickets.
    gap = _gap(risk_level="HIGH")
    assert select_eligible_gaps([gap], {}) == []
