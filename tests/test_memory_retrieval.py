import pytest

from app.storage import RetrievalStore


@pytest.fixture
def store(monkeypatch):
    monkeypatch.setenv("ENABLE_VECTOR_STORE", "false")
    monkeypatch.setenv("ENABLE_SEARCH_STORE", "false")
    return RetrievalStore()


@pytest.mark.parametrize(
    ("question", "document", "score"),
    [
        ("marker,", "marker.", 1),
        ("ALPHA", "alpha", 1),
        ("STRASSE", "Straße", 1),
        ("CAFÉ", "café.", 1),
        ("route42, 123", "ROUTE42; 123.", 2),
        ("alpha_beta", "alpha/beta", 2),
    ],
)
def test_memory_query_normalizes_questions_and_documents(store, question, document, score):
    store.add(["document"], [document])

    assert store.query(question, 1) == [
        {"text": document, "index": 0, "backend": "memory", "score": score}
    ]


def test_memory_query_ranks_by_shared_distinct_tokens(store):
    store.add(["repeated", "best"], ["violet violet violet", "Violet parcel marker."])

    results = store.query("marker, violet parcel parcel", 2)

    assert [result["text"] for result in results] == ["Violet parcel marker.", "violet violet violet"]
    assert [result["score"] for result in results] == [3, 1]
    assert store.query("marker, violet parcel parcel", 1) == results[:1]


@pytest.mark.parametrize("question", ["unrelated galaxy", "!?", ""])
def test_memory_query_without_shared_words_returns_no_results(store, question):
    store.add(["document"], ["The sample parcel is violet."])

    assert store.query(question, 4) == []


def test_memory_query_preserves_complete_privacy_tokens(store):
    token = "<PII_EMAIL_V1_0123456789abcdef0123456789abcdef>"
    other_token = "<PII_EMAIL_V1_fedcba9876543210fedcba9876543210>"
    store.add(["other", "matching"], [other_token + ".", token + "."])

    assert store.query(token + ",", 4) == [
        {"text": token + ".", "index": 0, "backend": "memory", "score": 1}
    ]
    assert store.query("PII EMAIL V1", 4) == []


def test_memory_limit_and_oldest_entry_eviction_are_preserved(monkeypatch):
    monkeypatch.setenv("MEMORY_STORE_MAX_DOCUMENTS", "2")
    store = RetrievalStore()
    store.add(["oldest", "middle", "newest"], ["alpha", "beta", "gamma"])

    assert store.query("alpha", 4) == []
    assert [result["text"] for result in store.query("beta gamma", 4)] == ["beta", "gamma"]
