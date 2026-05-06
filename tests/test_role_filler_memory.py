"""Unit tests for skills/role_filler_memory/handler.py"""

import pytest

from conftest import import_skill_handler

_mod = import_skill_handler("role_filler_memory")
RoleFillerMemory = _mod.RoleFillerMemory


FRAME1 = {"agent": "Alice", "action": "Bought",  "object": "Laptop",  "location": "Online"}
FRAME2 = {"agent": "Bob",   "action": "Sold",    "object": "Tablet",  "location": "Store"}
FRAME3 = {"agent": "Alice", "action": "Returned", "object": "Monitor", "location": "Store"}


@pytest.fixture()
def rfm(tmp_state_dir):
    return RoleFillerMemory()


@pytest.fixture()
def loaded_rfm(tmp_state_dir):
    r = RoleFillerMemory()
    r.store_frame("f1", FRAME1)
    r.store_frame("f2", FRAME2)
    r.store_frame("f3", FRAME3)
    return r


# ---------------------------------------------------------------------------
# store_frame
# ---------------------------------------------------------------------------

class TestStoreFrame:
    def test_success(self, rfm):
        result = rfm.store_frame("f1", FRAME1)
        assert result["status"] == "success"

    def test_message_includes_binding_count(self, rfm):
        result = rfm.store_frame("f1", FRAME1)
        assert str(len(FRAME1)) in result["message"]

    def test_missing_frame_id(self, rfm):
        result = rfm.store_frame("", FRAME1)
        assert result["status"] == "failed"

    def test_empty_bindings(self, rfm):
        result = rfm.store_frame("f_empty", {})
        assert result["status"] == "failed"

    def test_overwrite_same_id(self, rfm):
        rfm.store_frame("f1", FRAME1)
        result = rfm.store_frame("f1", FRAME2)
        assert result["status"] == "success"


# ---------------------------------------------------------------------------
# query_role
# ---------------------------------------------------------------------------

class TestQueryRole:
    def test_known_role_returns_correct_filler(self, loaded_rfm):
        result = loaded_rfm.query_role("f1", "agent")
        assert result["status"] == "success"
        assert result["filler"] == "Alice"

    def test_second_role(self, loaded_rfm):
        result = loaded_rfm.query_role("f1", "action")
        assert result["status"] == "success"
        assert result["filler"] == "Bought"

    def test_confidence_present(self, loaded_rfm):
        result = loaded_rfm.query_role("f1", "agent")
        assert "confidence" in result
        assert result["confidence"] > 0

    def test_unknown_frame_returns_failed(self, rfm):
        result = rfm.query_role("no_frame", "agent")
        assert result["status"] == "failed"

    def test_unknown_role_returns_low_confidence_or_success(self, loaded_rfm):
        # Querying a role that doesn't exist is not a hard error — result will
        # be uncertain.  The handler should not crash.
        result = loaded_rfm.query_role("f1", "nonexistent_role")
        assert result["status"] in ("success", "low_confidence", "failed")


# ---------------------------------------------------------------------------
# find_similar_frame
# ---------------------------------------------------------------------------

class TestFindSimilarFrame:
    def test_finds_frame_with_matching_agent(self, loaded_rfm):
        result = loaded_rfm.find_similar_frame({"agent": "Alice"})
        assert result["status"] == "success"
        # At least one frame where agent=Alice should be in the top results
        top_ids = [r["frame_id"] for r in result["all_scores"][:2]]
        assert "f1" in top_ids or "f3" in top_ids

    def test_best_match_field_present(self, loaded_rfm):
        result = loaded_rfm.find_similar_frame({"agent": "Alice"})
        assert "best_match" in result

    def test_all_scores_present(self, loaded_rfm):
        result = loaded_rfm.find_similar_frame({"agent": "Alice"})
        assert "all_scores" in result
        assert len(result["all_scores"]) == 3  # f1, f2, f3

    def test_no_frames_returns_failed(self, rfm):
        result = rfm.find_similar_frame({"agent": "Alice"})
        assert result["status"] == "failed"

    def test_empty_bindings_returns_failed(self, loaded_rfm):
        result = loaded_rfm.find_similar_frame({})
        assert result["status"] == "failed"


# ---------------------------------------------------------------------------
# State persistence
# ---------------------------------------------------------------------------

class TestPersistence:
    def test_frame_survives_reinstantiation(self, tmp_state_dir):
        r1 = RoleFillerMemory()
        r1.store_frame("f1", FRAME1)

        r2 = RoleFillerMemory()
        result = r2.query_role("f1", "agent")
        assert result["status"] == "success"
        assert result["filler"] == "Alice"
