"""Unit tests for skills/event_counter/handler.py"""

import pytest

from conftest import import_skill_handler

_mod = import_skill_handler("event_counter")
EventCounter = _mod.EventCounter


EVENTS = ["404", "500", "404", "404", "403", "500"]
# Expected: 404 x3, 500 x2, 403 x1


@pytest.fixture()
def ec(tmp_state_dir):
    return EventCounter()


@pytest.fixture()
def loaded_ec(tmp_state_dir):
    e = EventCounter()
    e.observe("errors", EVENTS)
    return e


# ---------------------------------------------------------------------------
# observe
# ---------------------------------------------------------------------------

class TestObserve:
    def test_success(self, ec):
        result = ec.observe("errors", EVENTS)
        assert result["status"] == "success"

    def test_total_observations_correct(self, loaded_ec):
        result = loaded_ec.estimate_count("errors", "404")
        assert result["total_observations"] == len(EVENTS)

    def test_additive(self, ec):
        ec.observe("errors", ["404", "404"])
        ec.observe("errors", ["404"])
        result = ec.estimate_count("errors", "404")
        assert result["estimated_count"] == pytest.approx(3.0, abs=0.5)

    def test_missing_counter_id(self, ec):
        result = ec.observe("", EVENTS)
        assert result["status"] == "failed"

    def test_empty_events_list(self, ec):
        result = ec.observe("errors", [])
        assert result["status"] == "failed"


# ---------------------------------------------------------------------------
# estimate_count
# ---------------------------------------------------------------------------

class TestEstimateCount:
    def test_most_frequent_has_highest_estimate(self, loaded_ec):
        count_404 = loaded_ec.estimate_count("errors", "404")["estimated_count"]
        count_500 = loaded_ec.estimate_count("errors", "500")["estimated_count"]
        count_403 = loaded_ec.estimate_count("errors", "403")["estimated_count"]
        assert count_404 > count_500
        assert count_500 > count_403

    def test_approx_correct_for_most_frequent(self, loaded_ec):
        result = loaded_ec.estimate_count("errors", "404")
        assert result["estimated_count"] == pytest.approx(3.0, abs=0.5)

    def test_unknown_counter_returns_failed(self, ec):
        result = ec.estimate_count("no_counter", "404")
        assert result["status"] == "failed"

    def test_total_observations_returned(self, loaded_ec):
        result = loaded_ec.estimate_count("errors", "404")
        assert result["total_observations"] == len(EVENTS)

    def test_unseen_item_estimate_near_zero(self, loaded_ec):
        result = loaded_ec.estimate_count("errors", "418")  # never observed
        # May be slightly off zero due to random cross-talk; should be close
        assert result["estimated_count"] < 1.0


# ---------------------------------------------------------------------------
# top_items
# ---------------------------------------------------------------------------

class TestTopItems:
    def test_returns_requested_n(self, loaded_ec):
        result = loaded_ec.top_items("errors", n=3)
        assert result["status"] == "success"
        assert len(result["top_items"]) <= 3

    def test_most_frequent_is_first(self, loaded_ec):
        result = loaded_ec.top_items("errors", n=3)
        assert result["top_items"][0]["item"] == "404"

    def test_ranking_correct(self, loaded_ec):
        result = loaded_ec.top_items("errors", n=3)
        items = result["top_items"]
        counts = [i["estimated_count"] for i in items]
        assert counts == sorted(counts, reverse=True)

    def test_unknown_counter_returns_failed(self, ec):
        result = ec.top_items("no_counter")
        assert result["status"] == "failed"

    def test_default_n_is_five(self, loaded_ec):
        result = loaded_ec.top_items("errors")
        assert len(result["top_items"]) <= 5


# ---------------------------------------------------------------------------
# reset_counter
# ---------------------------------------------------------------------------

class TestResetCounter:
    def test_clears_all_observations(self, loaded_ec):
        loaded_ec.reset_counter("errors")
        result = loaded_ec.estimate_count("errors", "404")
        assert result["total_observations"] == 0

    def test_unknown_counter_returns_failed(self, ec):
        result = ec.reset_counter("no_counter")
        assert result["status"] == "failed"

    def test_can_observe_after_reset(self, loaded_ec):
        loaded_ec.reset_counter("errors")
        loaded_ec.observe("errors", ["404"])
        result = loaded_ec.estimate_count("errors", "404")
        assert result["estimated_count"] == pytest.approx(1.0, abs=0.5)


# ---------------------------------------------------------------------------
# State persistence
# ---------------------------------------------------------------------------

class TestPersistence:
    def test_counter_survives_reinstantiation(self, tmp_state_dir):
        e1 = EventCounter()
        e1.observe("errors", EVENTS)

        e2 = EventCounter()
        result = e2.estimate_count("errors", "404")
        assert result["status"] == "success"
        assert result["estimated_count"] == pytest.approx(3.0, abs=0.5)
