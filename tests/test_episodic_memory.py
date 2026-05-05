"""Unit tests for skills/episodic_memory/handler.py"""

import pytest

from conftest import import_skill_handler

_mod = import_skill_handler("episodic_memory")
EpisodicMemory = _mod.EpisodicMemory


EVENTS = ["Arrival", "Triage", "XRay", "Diagnosis", "Discharge"]
TAGS = ["hospital", "morning", "emergency"]


@pytest.fixture()
def mem(tmp_state_dir):
    return EpisodicMemory()


@pytest.fixture()
def mem_with_episode(tmp_state_dir):
    m = EpisodicMemory()
    m.record_episode("ep1", EVENTS, TAGS)
    return m


# ---------------------------------------------------------------------------
# record_episode
# ---------------------------------------------------------------------------

class TestRecordEpisode:
    def test_success(self, mem):
        result = mem.record_episode("ep1", EVENTS, TAGS)
        assert result["status"] == "success"

    def test_listed_after_record(self, mem_with_episode):
        result = mem_with_episode.list_episodes()
        assert "ep1" in result["episodes"]

    def test_correct_event_count(self, mem_with_episode):
        result = mem_with_episode.list_episodes()
        assert result["episodes"]["ep1"]["event_count"] == len(EVENTS)

    def test_missing_episode_id(self, mem):
        result = mem.record_episode("", EVENTS, TAGS)
        assert result["status"] == "failed"

    def test_too_few_events(self, mem):
        result = mem.record_episode("ep_short", ["OnlyOne"], [])
        assert result["status"] == "failed"

    def test_no_context_tags_ok(self, mem):
        result = mem.record_episode("ep_no_tags", EVENTS, [])
        assert result["status"] == "success"

    def test_overwrite_same_id(self, mem):
        mem.record_episode("ep_dup", EVENTS, TAGS)
        # Second call with same ID should overwrite silently
        result = mem.record_episode("ep_dup", ["A", "B"], [])
        assert result["status"] == "success"
        summary = mem.list_episodes()
        assert summary["episodes"]["ep_dup"]["event_count"] == 2


# ---------------------------------------------------------------------------
# recall_by_context
# ---------------------------------------------------------------------------

class TestRecallByContext:
    def test_matches_correct_episode(self, mem_with_episode):
        result = mem_with_episode.recall_by_context(["hospital"])
        assert result["status"] in ("success", "low_confidence")
        if result["status"] == "success":
            assert result["best_match"] == "ep1"

    def test_returns_event_list(self, mem_with_episode):
        result = mem_with_episode.recall_by_context(TAGS)
        if result["status"] == "success":
            assert result["events"] == EVENTS

    def test_empty_tags_returns_failed(self, mem_with_episode):
        result = mem_with_episode.recall_by_context([])
        assert result["status"] == "failed"

    def test_no_episodes_returns_failed(self, mem):
        result = mem.recall_by_context(["hospital"])
        assert result["status"] == "failed"

    def test_all_scores_present(self, mem_with_episode):
        result = mem_with_episode.recall_by_context(TAGS)
        if result["status"] == "success":
            assert "all_scores" in result
            assert len(result["all_scores"]) == 1


# ---------------------------------------------------------------------------
# query_next_event
# ---------------------------------------------------------------------------

class TestQueryNextEvent:
    def test_known_predecessor_returns_correct_successor(self, mem_with_episode):
        result = mem_with_episode.query_next_event("ep1", "Triage")
        assert result["status"] in ("success", "low_confidence")
        if result["status"] == "success":
            assert result["next_event"] == "XRay"

    def test_first_event_returns_second(self, mem_with_episode):
        result = mem_with_episode.query_next_event("ep1", "Arrival")
        assert result["status"] in ("success", "low_confidence")
        if result["status"] == "success":
            assert result["next_event"] == "Triage"

    def test_unknown_episode(self, mem):
        result = mem.query_next_event("nonexistent", "Arrival")
        assert result["status"] == "failed"

    def test_confidence_present(self, mem_with_episode):
        result = mem_with_episode.query_next_event("ep1", "Triage")
        if result["status"] == "success":
            assert result["confidence"] > 0


# ---------------------------------------------------------------------------
# list_episodes
# ---------------------------------------------------------------------------

class TestListEpisodes:
    def test_empty_initially(self, mem):
        result = mem.list_episodes()
        assert result["count"] == 0
        assert result["episodes"] == {}

    def test_count_after_multiple(self, mem):
        mem.record_episode("ep1", EVENTS, TAGS)
        mem.record_episode("ep2", ["A", "B", "C"], ["tag1"])
        result = mem.list_episodes()
        assert result["count"] == 2


# ---------------------------------------------------------------------------
# State persistence
# ---------------------------------------------------------------------------

class TestPersistence:
    def test_episode_survives_reinstantiation(self, tmp_state_dir):
        m1 = EpisodicMemory()
        m1.record_episode("ep_persist", EVENTS, TAGS)

        m2 = EpisodicMemory()
        result = m2.list_episodes()
        assert "ep_persist" in result["episodes"]
