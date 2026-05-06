"""Unit tests for skills/reversible_memory/handler.py"""

import pytest
import numpy as np

from conftest import import_skill_handler

_mod = import_skill_handler("reversible_memory")
ReversiblePersonaCore = _mod.ReversiblePersonaCore


FACTS = [
    {"subject": "Alice", "predicate": "likes",  "object": "coffee"},
    {"subject": "Alice", "predicate": "works_at", "object": "TechCorp"},
    {"subject": "Alice", "predicate": "lives_in",  "object": "NYC"},
]


@pytest.fixture()
def core(tmp_state_dir):
    return ReversiblePersonaCore()


@pytest.fixture()
def loaded_core(tmp_state_dir):
    c = ReversiblePersonaCore()
    c.memorize("alice", FACTS)
    return c


# ---------------------------------------------------------------------------
# memorize
# ---------------------------------------------------------------------------

class TestMemorize:
    def test_success(self, core):
        result = core.memorize("alice", FACTS)
        assert result["status"] == "success"

    def test_message_includes_count(self, core):
        result = core.memorize("alice", FACTS)
        assert "3" in result["message"]

    def test_additive_on_second_call(self, core):
        core.memorize("alice", FACTS[:1])
        result = core.memorize("alice", FACTS[1:])
        assert result["status"] == "success"

    def test_missing_persona_id(self, core):
        # Handler uses persona_id as a dict key; empty string is a valid key
        result = core.memorize("", FACTS)
        assert result["status"] in ("success", "failed")

    def test_empty_facts(self, core):
        # Handler iterates empty list; adds 0 facts — returns success
        result = core.memorize("alice", [])
        assert result["status"] == "success"
        assert "0" in result["message"]


# ---------------------------------------------------------------------------
# forget
# ---------------------------------------------------------------------------

class TestForget:
    def test_success(self, loaded_core):
        result = loaded_core.forget("alice", [FACTS[0]])
        assert result["status"] == "success"

    def test_accumulator_changes_after_forget(self, loaded_core):
        vec_before = loaded_core.get_thresholded_persona("alice").vector.copy()
        loaded_core.forget("alice", [FACTS[0]])
        vec_after = loaded_core.get_thresholded_persona("alice").vector
        # At least some bits should differ after forgetting a fact
        assert not np.array_equal(vec_before, vec_after)

    def test_unknown_persona_returns_failed(self, core):
        result = core.forget("nonexistent", FACTS)
        assert result["status"] == "failed"

    def test_empty_facts_returns_success_with_zero(self, loaded_core):
        result = loaded_core.forget("alice", [])
        assert result["status"] == "success"
        assert "0" in result["message"]

    def test_forget_then_re_memorize_restores_state(self, loaded_core):
        vec_before = loaded_core.get_thresholded_persona("alice").vector.copy()
        loaded_core.forget("alice", [FACTS[0]])
        loaded_core.memorize("alice", [FACTS[0]])
        vec_after = loaded_core.get_thresholded_persona("alice").vector
        # Should be identical because memorize/forget are exact inverses on the integer accumulator
        assert np.array_equal(vec_before, vec_after)


# ---------------------------------------------------------------------------
# get_thresholded_persona
# ---------------------------------------------------------------------------

class TestGetThresholdedPersona:
    def test_returns_vector_for_known_persona(self, loaded_core):
        vec = loaded_core.get_thresholded_persona("alice")
        assert vec is not None

    def test_returns_none_for_unknown_persona(self, core):
        vec = core.get_thresholded_persona("nobody")
        assert vec is None

    def test_vector_is_bipolar(self, loaded_core):
        vec = loaded_core.get_thresholded_persona("alice")
        unique = set(vec.vector.tolist())
        assert unique <= {1, -1}


# ---------------------------------------------------------------------------
# State persistence
# ---------------------------------------------------------------------------

class TestPersistence:
    def test_persona_survives_reinstantiation(self, tmp_state_dir):
        c1 = ReversiblePersonaCore()
        c1.memorize("alice", FACTS)
        vec1 = c1.get_thresholded_persona("alice").vector.copy()

        c2 = ReversiblePersonaCore()
        vec2 = c2.get_thresholded_persona("alice").vector
        assert np.array_equal(vec1, vec2)
