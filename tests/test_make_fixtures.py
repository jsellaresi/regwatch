import importlib

import fitz
import pytest

from graph.nodes.guardrails import find_injection, redact_pii
from scripts.make_fixtures import BANNER, _render, build_fixtures

retrieve_mod = importlib.import_module("graph.nodes.retrieve_regulations")

DIGITAL = ["policy_retencion", "policy_retencion_v2", "policy_limpia", "policy_mixta", "policy_injection", "policy_pii"]


@pytest.fixture(scope="module")
def fixtures():
    return build_fixtures()


def _text(pdf: bytes) -> str:
    return " ".join(page.get_text() for page in fitz.open(stream=pdf, filetype="pdf"))


def test_every_expected_fixture_is_generated_as_a_valid_pdf(fixtures):
    assert set(fixtures) == set(DIGITAL) | {"policy_escaneada"}
    assert all(data.startswith(b"%PDF-") for data in fixtures.values())


def test_digital_fixtures_have_extractable_text_and_say_they_are_synthetic(fixtures):
    for name in DIGITAL:
        assert BANNER in " ".join(_text(fixtures[name]).split()), name


def test_the_scanned_fixture_has_no_text_layer_so_extraction_must_use_vision(fixtures):
    pages = list(fitz.open(stream=fixtures["policy_escaneada"], filetype="pdf"))
    assert pages and all(not page.get_text().strip() and page.get_images() for page in pages)


def test_the_scanned_fixture_is_the_image_twin_of_policy_retencion(fixtures):
    original = fitz.open(stream=fixtures["policy_retencion"], filetype="pdf")
    scanned = fitz.open(stream=fixtures["policy_escaneada"], filetype="pdf")
    assert len(original) == len(scanned)


def test_the_injection_fixture_is_blocked_by_the_input_guardrail(fixtures):
    assert find_injection(_text(fixtures["policy_injection"])) is not None


def test_the_pii_fixture_is_redacted_not_blocked(fixtures):
    text = _text(fixtures["policy_pii"])
    assert find_injection(text) is None
    _, counts = redact_pii(text)
    assert {"DNI", "IBAN", "CARD"} <= set(counts)


@pytest.mark.parametrize("name", ["policy_retencion", "policy_retencion_v2", "policy_limpia", "policy_mixta"])
def test_the_ordinary_fixtures_pass_the_input_guardrail_untouched(fixtures, name):
    text = _text(fixtures[name])
    assert find_injection(text) is None
    assert redact_pii(text)[1] == {}


def test_retention_v1_has_the_gaps_v2_partly_fixes_and_the_clean_policy_has_none(fixtures):
    v1, v2, clean = (" ".join(_text(fixtures[n]).split()) for n in ("policy_retencion", "policy_retencion_v2", "policy_limpia"))
    assert "de forma indefinida" in v1 and "no ha designado" not in v1 and "decidido no designar" in v1
    assert "de forma indefinida" not in v2 and "ha designado un delegado" in v2
    assert "semanas después" in v1 and "semanas después" in v2  # the breach-notification gap stays open
    assert "72 horas" in clean and "semanas después" not in clean


def test_the_mixed_policy_is_long_enough_to_be_split_into_several_retrieval_queries(fixtures):
    assert len(retrieve_mod._split_into_queries(_text(fixtures["policy_mixta"]))) > 1


def test_extracted_text_has_no_ligature_glyphs_that_would_break_phrase_matching(fixtures):
    for name in DIGITAL:
        assert not any(0xFB00 <= ord(ch) <= 0xFB06 for ch in _text(fixtures[name])), name  # fi, fl, ff...
    assert "de forma indefinida" in " ".join(_text(fixtures["policy_retencion"]).split())


def test_a_long_document_flows_onto_further_pages_without_losing_text():
    sections = [(f"{n}. Sección {n}", f"Párrafo número {n}. " + "texto de relleno " * 60) for n in range(1, 31)]
    pages = list(fitz.open(stream=_render("Documento largo", sections), filetype="pdf"))
    text = " ".join(" ".join(page.get_text().split()) for page in pages)
    assert len(pages) > 1
    assert all(f"Párrafo número {n}." in text for n in (1, 15, 30))
    assert text.count("texto de relleno") == 30 * 60
