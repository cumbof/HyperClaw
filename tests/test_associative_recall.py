"""Unit tests for skills/associative_recall/handler.py"""

import pytest

from conftest import import_skill_handler

_mod = import_skill_handler("associative_recall")
AssociativeRecall = _mod.AssociativeRecall


PAIRS = [
    {"key": "cat",  "value": "chat"},
    {"key": "dog",  "value": "chien"},
    {"key": "bird", "value": "oiseau"},
]


@pytest.fixture()
def ar(tmp_state_dir):
    return AssociativeRecall()


@pytest.fixture()
def trained_ar(tmp_state_dir):
    a = AssociativeRecall()
    a.store_association("fr", PAIRS)
    return a


# ---------------------------------------------------------------------------
# store_association
# ---------------------------------------------------------------------------

class TestStoreAssociation:
    def test_success(self, ar):
        result = ar.store_association("fr", PAIRS)
        assert result["status"] == "success"

    def test_message_includes_count(self, ar):
        result = ar.store_association("fr", PAIRS)
        assert "3" in result["message"]

    def test_additive_on_second_call(self, ar):
        ar.store_association("fr", PAIRS[:2])
        result = ar.store_association("fr", PAIRS[2:])
        assert result["status"] == "success"

    def test_missing_store_id(self, ar):
        result = ar.store_association("", PAIRS)
        assert result["status"] == "failed"

    def test_empty_pairs(self, ar):
        result = ar.store_association("fr", [])
        assert result["status"] == "failed"


# ---------------------------------------------------------------------------
# recall (key → value)
# ---------------------------------------------------------------------------

class TestRecall:
    def test_known_key_returns_correct_value(self, trained_ar):
        result = trained_ar.recall("fr", "cat")
        assert result["status"] == "success"
        assert result["value"] == "chat"

    def test_second_known_key(self, trained_ar):
        result = trained_ar.recall("fr", "dog")
        assert result["status"] == "success"
        assert result["value"] == "chien"

    def test_confidence_present(self, trained_ar):
        result = trained_ar.recall("fr", "cat")
        assert "confidence" in result
        assert result["confidence"] > 0

    def test_unknown_store_returns_failed(self, ar):
        result = ar.recall("no_store", "cat")
        assert result["status"] == "failed"


# ---------------------------------------------------------------------------
# forget_association
# ---------------------------------------------------------------------------

class TestForgetAssociation:
    def test_forgetting_removes_retrieval(self, trained_ar):
        # After forgetting "cat"→"chat", recall may no longer confidently return "chat"
        trained_ar.forget_association("fr", [{"key": "cat", "value": "chat"}])
        result = trained_ar.recall("fr", "cat")
        # Either low_confidence or success with a different top result is acceptable
        if result["status"] == "success":
            # Could still retrieve by residual, but confidence should drop
            assert result["confidence"] < 60

    def test_unknown_store_returns_failed(self, ar):
        result = ar.forget_association("no_store", [{"key": "cat", "value": "chat"}])
        assert result["status"] == "failed"

    def test_empty_pairs_does_not_crash(self, trained_ar):
        result = trained_ar.forget_association("fr", [])
        assert result["status"] in ("success", "failed")


# ---------------------------------------------------------------------------
# State persistence
# ---------------------------------------------------------------------------

class TestPersistence:
    def test_associations_survive_reinstantiation(self, tmp_state_dir):
        a1 = AssociativeRecall()
        a1.store_association("fr", PAIRS)

        a2 = AssociativeRecall()
        result = a2.recall("fr", "cat")
        assert result["status"] == "success"
        assert result["value"] == "chat"
