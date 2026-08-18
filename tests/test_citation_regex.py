import pytest

from tests.conftest import load_module_standalone

# `graph/schemas.py` has no side effects of its own, but `import graph.schemas`
# would still run `graph/__init__.py` first, which eagerly imports every node
# (including retriever.py's real DB query at import time). Load the file
# directly so this test only depends on what it actually needs: pydantic + re.
schemas = load_module_standalone("regwatch_schemas_under_test", "graph/schemas.py")
VALID_CITATION_RE = schemas.VALID_CITATION_RE


@pytest.mark.parametrize(
    "citation",
    [
        "GDPR Art. 17",
        "GDPR Art. 17(1)",
        "GDPR Art. 5(1)(e)",
        "MiFID II Art. 23",
        "4AMLD Art. 11",
        "5AMLD Art. 3",
        "6AMLD Art. 3(2)(a)",
        "AMLD Art. 8",
    ],
)
def test_accepts_valid_citations(citation):
    assert VALID_CITATION_RE.match(citation), f"expected '{citation}' to be accepted"


@pytest.mark.parametrize(
    "citation",
    [
        "GDPR Art. 5(1)e",  # letter must be its own parenthesized group, not trailing
        "GDPR Art. 5(1)(e)(ii))",  # unbalanced trailing paren
        "",
        "AML Directive Art. 13",  # prefix not in the allowed set
        "EU GDPR Art. 5",  # extra leading token
        "Directive 2015/849 Art. 11",
        "GDPR Article 17",  # wrong keyword ("Article" instead of "Art.")
        "GDPR Art.17",  # missing space after "Art."
    ],
)
def test_rejects_invalid_citations(citation):
    assert not VALID_CITATION_RE.match(citation), f"expected '{citation}' to be rejected"
