from app.redaction import redact, token_for

def test_redacts_common_pii_deterministically():
    text, counts = redact("Email A@Example.com, SSN 123-45-6789, card 4111 1111 1111 1111", "salt")
    assert "A@Example.com" not in text
    assert "123-45-6789" not in text
    assert counts == {"ssn": 1, "card": 1, "email": 1}
    assert redact("A@Example.com", "salt")[0] == redact("A@Example.com", "salt")[0]
    assert redact("A@Example.com", "salt")[0] == redact("a@example.com", "salt")[0]


def test_card_detection_requires_luhn_and_tokens_are_keyed() -> None:
    output, counts = redact("reference 4111 1111 1111 1112", "salt")
    assert "4111 1111 1111 1112" not in output
    assert counts == {"numeric_identifier": 1}
    assert token_for("email", "a@example.com", "key-a") != token_for("email", "a@example.com", "key-b")


def test_does_not_misclassify_iso_timestamps_as_phone_numbers() -> None:
    timestamp = "2024-01-15 10:30"
    output, counts = redact(f"created {timestamp}", "salt")
    assert timestamp in output
    assert counts == {}
