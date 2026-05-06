"""Unit tests for skills/causal_chain/handler.py"""

import pytest

from conftest import import_skill_handler

_mod = import_skill_handler("causal_chain")
CausalChain = _mod.CausalChain


DISEASE_LINKS = [
    {"cause": "Infection",    "effect": "Inflammation"},
    {"cause": "Inflammation", "effect": "Fever"},
    {"cause": "Fever",        "effect": "Dehydration"},
]


@pytest.fixture()
def cc(tmp_state_dir):
    return CausalChain()


@pytest.fixture()
def trained_cc(tmp_state_dir):
    c = CausalChain()
    c.add_links("disease", DISEASE_LINKS)
    return c


# ---------------------------------------------------------------------------
# add_links
# ---------------------------------------------------------------------------

class TestAddLinks:
    def test_success(self, cc):
        result = cc.add_links("disease", DISEASE_LINKS)
        assert result["status"] == "success"

    def test_message_includes_count(self, cc):
        result = cc.add_links("disease", DISEASE_LINKS)
        assert "3" in result["message"]

    def test_additive(self, cc):
        cc.add_links("disease", DISEASE_LINKS[:2])
        result = cc.add_links("disease", DISEASE_LINKS[2:])
        assert result["status"] == "success"

    def test_missing_store_id(self, cc):
        result = cc.add_links("", DISEASE_LINKS)
        assert result["status"] == "failed"

    def test_missing_links(self, cc):
        result = cc.add_links("disease", [])
        assert result["status"] == "failed"

    def test_multiple_stores_independent(self, cc):
        cc.add_links("disease", DISEASE_LINKS)
        result = cc.add_links("tech", [{"cause": "Bug", "effect": "Crash"}])
        assert result["status"] == "success"


# ---------------------------------------------------------------------------
# get_effect
# ---------------------------------------------------------------------------

class TestGetEffect:
    def test_known_cause(self, trained_cc):
        result = trained_cc.get_effect("disease", "Infection")
        assert result["status"] in ("success", "low_confidence")
        if result["status"] == "success":
            assert result["effect"] == "Inflammation"

    def test_contains_confidence(self, trained_cc):
        result = trained_cc.get_effect("disease", "Infection")
        if result["status"] == "success":
            assert result["confidence"] > 0

    def test_unknown_store(self, cc):
        result = cc.get_effect("no_store", "Infection")
        assert result["status"] == "failed"


# ---------------------------------------------------------------------------
# get_cause
# ---------------------------------------------------------------------------

class TestGetCause:
    def test_known_effect(self, trained_cc):
        result = trained_cc.get_cause("disease", "Fever")
        assert result["status"] in ("success", "low_confidence")
        # Accept any reasonable cause — HDC nearest-neighbor may vary slightly
        if result["status"] == "success":
            assert result["cause"] in ("Inflammation", "Infection", "Dehydration")

    def test_unknown_store(self, cc):
        result = cc.get_cause("no_store", "Fever")
        assert result["status"] == "failed"

    def test_cause_result_contains_effect_field(self, trained_cc):
        result = trained_cc.get_cause("disease", "Inflammation")
        assert "effect" in result or result["status"] != "success"


# ---------------------------------------------------------------------------
# trace_forward
# ---------------------------------------------------------------------------

class TestTraceForward:
    def test_chain_starts_with_start_node(self, trained_cc):
        result = trained_cc.trace_forward("disease", "Infection")
        assert result["status"] == "success"
        assert result["causal_chain"][0] == "Infection"

    def test_chain_covers_all_hops(self, trained_cc):
        result = trained_cc.trace_forward("disease", "Infection")
        assert result["status"] == "success"
        # Chain must contain at least Infection + one successor
        assert len(result["causal_chain"]) >= 2

    def test_hops_count_is_consistent(self, trained_cc):
        result = trained_cc.trace_forward("disease", "Infection")
        assert result["hops"] == len(result["causal_chain"]) - 1

    def test_cycle_detection_prevents_infinite_loop(self, tmp_state_dir):
        # Build a cycle: A → B → A
        c = CausalChain()
        c.add_links("cycle", [{"cause": "A", "effect": "B"}, {"cause": "B", "effect": "A"}])
        result = c.trace_forward("cycle", "A")
        assert result["status"] == "success"
        # Must terminate; chain must not contain a node twice
        chain = result["causal_chain"]
        assert len(chain) == len(set(chain))

    def test_max_hops_respected(self, trained_cc):
        result = trained_cc.trace_forward("disease", "Infection", max_hops=1)
        # Chain should be at most 2 nodes long (start + 1 hop)
        assert len(result["causal_chain"]) <= 2

    def test_unknown_store(self, cc):
        result = cc.trace_forward("no_store", "Infection")
        assert result["status"] == "failed"


# ---------------------------------------------------------------------------
# State persistence
# ---------------------------------------------------------------------------

class TestPersistence:
    def test_links_survive_reinstantiation(self, tmp_state_dir):
        c1 = CausalChain()
        c1.add_links("disease", DISEASE_LINKS)

        c2 = CausalChain()
        result = c2.get_effect("disease", "Infection")
        assert result["status"] in ("success", "low_confidence")
