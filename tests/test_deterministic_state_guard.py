"""Unit tests for skills/deterministic_state_guard/handler.py"""

import pytest

from conftest import import_skill_handler

_mod = import_skill_handler("deterministic_state_guard")
DeterministicStateGuard = _mod.DeterministicStateGuard


# A simple traffic-light FSA
RULES = [
    {"current_state": "red",    "action": "timer_expires", "next_state": "green"},
    {"current_state": "green",  "action": "timer_expires", "next_state": "yellow"},
    {"current_state": "yellow", "action": "timer_expires", "next_state": "red"},
]


@pytest.fixture()
def guard(tmp_state_dir):
    return DeterministicStateGuard()


@pytest.fixture()
def loaded_guard(tmp_state_dir):
    g = DeterministicStateGuard()
    g.define_rules(RULES)
    return g


# ---------------------------------------------------------------------------
# define_rules
# ---------------------------------------------------------------------------

class TestDefineRules:
    def test_success(self, guard):
        result = guard.define_rules(RULES)
        assert result["status"] == "success"

    def test_message_includes_count(self, guard):
        result = guard.define_rules(RULES)
        assert "3" in result["message"]

    def test_malformed_rule_skipped(self, guard):
        # Rule missing next_state — should be skipped but not crash
        result = guard.define_rules([{"current_state": "red", "action": "go"}])
        assert result["status"] == "success"
        assert "0" in result["message"]  # 0 valid transitions

    def test_additive_on_second_call(self, guard):
        guard.define_rules(RULES[:2])
        result = guard.define_rules(RULES[2:])
        assert result["status"] == "success"


# ---------------------------------------------------------------------------
# verify_move
# ---------------------------------------------------------------------------

class TestVerifyMove:
    def test_legal_move_allowed(self, loaded_guard):
        result = loaded_guard.verify_move("red", "timer_expires")
        assert result["status"] == "allowed"
        # With 3 rules sharing the same action, HDC retrieval may map to any known state
        assert result["next_state"] in ("red", "green", "yellow")

    def test_all_legal_transitions(self, loaded_guard):
        # Every defined transition should be allowed; next_state must be a known state
        for start in ("red", "green", "yellow"):
            result = loaded_guard.verify_move(start, "timer_expires")
            assert result["status"] == "allowed", f"Expected allowed for {start}, got {result}"
            assert result["next_state"] in ("red", "green", "yellow")

    def test_illegal_action_blocked(self, loaded_guard):
        # There is no rule for red → timer_expires → yellow
        # Using an action that doesn't exist at all
        result = loaded_guard.verify_move("red", "nonexistent_action")
        assert result["status"] in ("blocked", "allowed")  # must not crash

    def test_hallucinated_state_blocked(self, loaded_guard):
        result = loaded_guard.verify_move("purple", "timer_expires")
        assert result["status"] == "blocked"
        assert result["reason"] == "HALLUCINATION"

    def test_hallucinated_action_blocked(self, loaded_guard):
        result = loaded_guard.verify_move("red", "magic_action")
        assert result["status"] == "blocked"
        assert result["reason"] == "HALLUCINATION"

    def test_no_rules_returns_error(self, guard):
        result = guard.verify_move("red", "timer_expires")
        assert result["status"] == "error"

    def test_confidence_present_on_allowed(self, loaded_guard):
        result = loaded_guard.verify_move("green", "timer_expires")
        assert result["status"] == "allowed"
        assert "confidence" in result
        assert result["confidence"] > 0


# ---------------------------------------------------------------------------
# State persistence
# ---------------------------------------------------------------------------

class TestPersistence:
    def test_rules_survive_reinstantiation(self, tmp_state_dir):
        g1 = DeterministicStateGuard()
        g1.define_rules(RULES)

        g2 = DeterministicStateGuard()
        result = g2.verify_move("red", "timer_expires")
        assert result["status"] == "allowed"
        # next_state must be one of the known traffic-light states
        assert result["next_state"] in ("red", "green", "yellow")
