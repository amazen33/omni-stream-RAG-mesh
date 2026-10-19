import pytest

from ops.helm_contract import approved_lab_changes


@pytest.mark.parametrize("quote", [b'', b'"'])
def test_d_o13_only_allows_the_model_scalar_change(quote):
    old = b'  OLLAMA_MODEL: ' + quote + b'previous-model:tag' + quote + b'\n  KEEP: value\n'
    new = old.replace(b'previous-model:tag', b'phi4-mini:3.8b')
    assert approved_lab_changes(old, new) == ['D-O13: OLLAMA_MODEL default -> phi4-mini:3.8b (MIT)']
    assert approved_lab_changes(old, new.replace(b'KEEP: value', b'KEEP: changed')) == []
    assert approved_lab_changes(old, new.replace(b'phi4-mini:3.8b', b'other-model:tag')) == []


def test_d_o13_can_follow_the_original_amendment_4_baseline():
    old = b'  ENABLE_VECTOR_STORE: "true"\n  OLLAMA_MODEL: previous-model:tag\n'
    new = old.replace(b'"true"', b'"false"').replace(b'previous-model:tag', b'phi4-mini:3.8b')
    assert len(approved_lab_changes(old, new)) == 2
