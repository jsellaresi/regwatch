import importlib

rerank_mod = importlib.import_module("graph.nodes.rerank")


def _reg(content, articles=None, regulation="4AMLD"):
    reg = {"regulation": regulation, "content": content}
    if articles is not None:
        reg["articles"] = articles
    return reg


class _FakeCrossEncoder:
    """Scores a chunk by the number written in its content, so the test controls the order."""

    def predict(self, pairs):
        return [float(content.split(":")[0]) for _, content in pairs]


def _rerank(monkeypatch, regs):
    monkeypatch.setattr(rerank_mod, "COHERE_API_KEY", "")
    monkeypatch.setattr(rerank_mod, "_get_local_ce", lambda: _FakeCrossEncoder())
    out = rerank_mod.rerank({"extracted_text": "política", "retrieved_regulations": regs})
    return [r["content"] for r in out["retrieved_regulations"]]


def test_chunks_that_belong_to_no_article_never_take_a_slot_from_an_article(monkeypatch):
    regs = [
        _reg("9: anexo de riesgos", articles=[]),
        _reg("8: considerando", articles=[]),
        _reg("5: Artículo 14", articles=[14]),
        _reg("4: Artículo 11", articles=[11]),
    ]
    assert _rerank(monkeypatch, regs) == ["5: Artículo 14", "4: Artículo 11"]


def test_chunks_without_the_articles_tag_are_kept_for_a_corpus_ingested_before_tagging(monkeypatch):
    regs = [_reg("3: sin etiqueta"), _reg("2: otra sin etiqueta")]
    assert _rerank(monkeypatch, regs) == ["3: sin etiqueta", "2: otra sin etiqueta"]


def test_if_nothing_citable_was_retrieved_the_untagged_chunks_are_still_ranked(monkeypatch):
    regs = [_reg("1: considerando", articles=[]), _reg("2: anexo", articles=[])]
    assert _rerank(monkeypatch, regs) == ["2: anexo", "1: considerando"]


def test_at_most_top_n_chunks_are_returned_best_first(monkeypatch):
    regs = [_reg(f"{n}: texto", articles=[n]) for n in range(1, 13)]
    result = _rerank(monkeypatch, regs)
    assert len(result) == rerank_mod.TOP_N == 8
    assert result[0] == "12: texto" and result[-1] == "5: texto"


def test_the_filter_is_what_lets_article_11_into_the_final_selection():
    # Mirrors the offline probe on the real 4AMLD: with the recital and the annex out of the
    # way, the chunk that opens Article 11 moves from 7th to 5th place.
    ranked = [
        _reg("annex", articles=[]), _reg("art 13", articles=[13]), _reg("recital", articles=[]),
        _reg("art 14", articles=[14]), _reg("art 16-17", articles=[16, 17]), _reg("art 14b", articles=[14]),
        _reg("art 11", articles=[11]),
    ]
    kept = [r["content"] for r in rerank_mod._citable(ranked)]
    assert len(kept) == 5 and kept.index("art 11") == 4
