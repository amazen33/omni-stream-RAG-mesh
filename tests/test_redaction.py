from app.redaction import redact

def test_redacts_common_pii_deterministically():
    text, counts = redact("Email A@Example.com, SSN 123-45-6789, card 4111 1111 1111 1111", "salt")
    assert "A@Example.com" not in text
    assert "123-45-6789" not in text
    assert counts == {"ssn": 1, "card": 1, "email": 1}
    assert redact("A@Example.com", "salt")[0] == redact("A@Example.com", "salt")[0]
