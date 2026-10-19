import random

import pytest

from app.main import AskRequest, IngestRequest, PaymentRequest
from ops.synthetic_corpus import generate_corpus


def test_seeded_corpus_is_repeatable_and_does_not_change_global_rng():
    state = random.getstate()
    first = generate_corpus(44, 2)
    assert first == generate_corpus(44, 2)
    assert first != generate_corpus(45, 2)
    assert state == random.getstate()


def test_exact_utf8_sizes_and_existing_api_contracts():
    corpus = generate_corpus(2026)
    assert [len(doc["text"].encode("utf-8")) for doc in corpus["documents"]] == [1024, 10240, 102400]
    for document, question, payment in zip(corpus["documents"], corpus["questions"], corpus["payments"]):
        IngestRequest(**document)
        AskRequest(**question)
        PaymentRequest(**payment)
        assert document["source"].startswith("synthetic-")
        assert payment["transaction_id"].startswith("synthetic-")
        assert payment["merchant_id"].startswith("synthetic-")
        assert not any(key in payment for key in ("pan", "card_number", "email", "phone", "password"))


def test_positive_count_required():
    with pytest.raises(ValueError, match="count must be positive"):
        generate_corpus(44, 0)
