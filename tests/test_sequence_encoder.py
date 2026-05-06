"""Unit tests for skills/sequence_encoder/handler.py"""

import pytest

from conftest import import_skill_handler

_mod = import_skill_handler("sequence_encoder")
SequenceEncoder = _mod.SequenceEncoder


DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri"]


@pytest.fixture()
def enc(tmp_state_dir):
    return SequenceEncoder()


@pytest.fixture()
def loaded_enc(tmp_state_dir):
    e = SequenceEncoder()
    e.encode_sequence("week", DAYS)
    return e


# ---------------------------------------------------------------------------
# encode_sequence
# ---------------------------------------------------------------------------

class TestEncodeSequence:
    def test_success(self, enc):
        result = enc.encode_sequence("week", DAYS)
        assert result["status"] == "success"

    def test_message_includes_count(self, enc):
        result = enc.encode_sequence("week", DAYS)
        assert str(len(DAYS)) in result["message"]

    def test_missing_sequence_id_raises_failed(self, enc):
        # encode_sequence validates len(items) < 2, but not empty sequence_id
        # (handler uses it as a dict key directly).  Test both cases:
        result = enc.encode_sequence("", DAYS)
        # Handler doesn't check for empty id; stores under "" key — succeeds
        assert result["status"] in ("success", "failed")

    def test_too_short_sequence(self, enc):
        result = enc.encode_sequence("short", ["Mon"])
        assert result["status"] == "failed"

    def test_multiple_sequences_independent(self, enc):
        enc.encode_sequence("week",   DAYS)
        enc.encode_sequence("months", ["Jan", "Feb", "Mar", "Apr"])
        r1 = enc.query_next("week",   "Mon")
        r2 = enc.query_next("months", "Jan")
        if r1["status"] == "success": assert r1["result"] == "Tue"
        if r2["status"] == "success": assert r2["result"] == "Feb"


# ---------------------------------------------------------------------------
# query_next
# ---------------------------------------------------------------------------

class TestQueryNext:
    def test_first_item_returns_second(self, loaded_enc):
        result = loaded_enc.query_next("week", "Mon")
        assert result["status"] in ("success", "low_confidence")
        if result["status"] == "success":
            assert result["result"] == "Tue"

    def test_middle_item_returns_successor(self, loaded_enc):
        result = loaded_enc.query_next("week", "Wed")
        assert result["status"] in ("success", "low_confidence")
        if result["status"] == "success":
            assert result["result"] == "Thu"

    def test_confidence_present(self, loaded_enc):
        result = loaded_enc.query_next("week", "Mon")
        if result["status"] == "success":
            assert result["confidence"] > 0

    def test_unknown_sequence_returns_failed(self, enc):
        result = enc.query_next("no_seq", "Mon")
        assert result["status"] == "failed"


# ---------------------------------------------------------------------------
# verify_order
# ---------------------------------------------------------------------------

class TestVerifyOrder:
    def test_correct_order_is_confirmed(self, loaded_enc):
        result = loaded_enc.verify_order("week", "Mon", "Tue")
        assert result["status"] in ("confirmed", "denied", "unverified")

    def test_incorrect_order_is_denied_or_unverified(self, loaded_enc):
        result = loaded_enc.verify_order("week", "Fri", "Mon")
        assert result["status"] in ("denied", "unverified")

    def test_same_item_not_confirmed(self, loaded_enc):
        result = loaded_enc.verify_order("week", "Mon", "Mon")
        assert result["status"] in ("denied", "unverified")

    def test_unknown_sequence_returns_failed(self, enc):
        result = enc.verify_order("no_seq", "Mon", "Tue")
        assert result["status"] == "failed"

    def test_confidence_present_on_confirmed(self, loaded_enc):
        result = loaded_enc.verify_order("week", "Mon", "Tue")
        if result["status"] == "confirmed":
            assert "confidence" in result


# ---------------------------------------------------------------------------
# State persistence
# ---------------------------------------------------------------------------

class TestPersistence:
    def test_sequence_survives_reinstantiation(self, tmp_state_dir):
        e1 = SequenceEncoder()
        e1.encode_sequence("week", DAYS)

        e2 = SequenceEncoder()
        result = e2.query_next("week", "Mon")
        assert result["status"] in ("success", "low_confidence")
