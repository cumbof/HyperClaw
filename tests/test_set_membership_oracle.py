"""Unit tests for skills/set_membership_oracle/handler.py"""

import pytest

from conftest import import_skill_handler

_mod = import_skill_handler("set_membership_oracle")
SetMembershipOracle = _mod.SetMembershipOracle


@pytest.fixture()
def oracle(tmp_state_dir):
    return SetMembershipOracle()


@pytest.fixture()
def loaded_oracle(tmp_state_dir):
    o = SetMembershipOracle()
    o.add_elements("fruits", ["apple", "banana", "cherry", "date"])
    o.add_elements("veggies", ["carrot", "broccoli", "spinach", "kale"])
    return o


# ---------------------------------------------------------------------------
# add_elements
# ---------------------------------------------------------------------------

class TestAddElements:
    def test_success(self, oracle):
        result = oracle.add_elements("fruits", ["apple", "banana"])
        assert result["status"] == "success"

    def test_element_count_in_message(self, oracle):
        result = oracle.add_elements("fruits", ["apple", "banana"])
        assert "2" in result["message"]

    def test_additive(self, oracle):
        oracle.add_elements("fruits", ["apple"])
        oracle.add_elements("fruits", ["banana"])
        # Both should be members
        r1 = oracle.test_membership("fruits", "apple")
        r2 = oracle.test_membership("fruits", "banana")
        assert r1["is_member"] is True
        assert r2["is_member"] is True

    def test_missing_set_id(self, oracle):
        result = oracle.add_elements("", ["apple"])
        assert result["status"] == "failed"

    def test_empty_elements(self, oracle):
        result = oracle.add_elements("fruits", [])
        assert result["status"] == "failed"

    def test_multiple_sets_independent(self, loaded_oracle):
        # apple is in fruits, not veggies
        r1 = loaded_oracle.test_membership("fruits",  "apple")
        r2 = loaded_oracle.test_membership("veggies", "apple")
        assert r1["is_member"] is True
        assert r2["is_member"] is False


# ---------------------------------------------------------------------------
# test_membership
# ---------------------------------------------------------------------------

class TestMembership:
    def test_member_is_detected(self, loaded_oracle):
        result = loaded_oracle.test_membership("fruits", "apple")
        assert result["status"] == "success"
        assert result["is_member"] is True

    def test_non_member_is_rejected(self, loaded_oracle):
        result = loaded_oracle.test_membership("fruits", "carrot")
        assert result["is_member"] is False

    def test_confidence_present(self, loaded_oracle):
        result = loaded_oracle.test_membership("fruits", "apple")
        assert "confidence" in result
        assert result["confidence"] > 0

    def test_unknown_set_returns_failed(self, oracle):
        result = oracle.test_membership("no_set", "apple")
        assert result["status"] == "failed"


# ---------------------------------------------------------------------------
# remove_elements
# ---------------------------------------------------------------------------

class TestRemoveElements:
    def test_removed_element_no_longer_member(self, loaded_oracle):
        loaded_oracle.remove_elements("fruits", ["apple"])
        result = loaded_oracle.test_membership("fruits", "apple")
        assert result["is_member"] is False

    def test_other_members_unaffected_after_removal(self, loaded_oracle):
        loaded_oracle.remove_elements("fruits", ["apple"])
        result = loaded_oracle.test_membership("fruits", "banana")
        assert result["is_member"] is True

    def test_unknown_set_returns_failed(self, oracle):
        result = oracle.remove_elements("no_set", ["apple"])
        assert result["status"] == "failed"

    def test_empty_elements_returns_success_with_zero(self, loaded_oracle):
        # Handler iterates over empty list — no error, just removes 0 elements
        result = loaded_oracle.remove_elements("fruits", [])
        assert result["status"] == "success"
        assert "0" in result["message"]


# ---------------------------------------------------------------------------
# set_similarity
# ---------------------------------------------------------------------------

class TestSetSimilarity:
    def test_self_similarity_high(self, loaded_oracle):
        result = loaded_oracle.set_similarity("fruits", "fruits")
        assert result["status"] == "success"
        assert result["similarity"] > 80  # near-identical

    def test_disjoint_sets_low_similarity(self, loaded_oracle):
        result = loaded_oracle.set_similarity("fruits", "veggies")
        assert result["similarity"] < 50

    def test_unknown_set_a_returns_failed(self, loaded_oracle):
        result = loaded_oracle.set_similarity("no_set", "fruits")
        assert result["status"] == "failed"

    def test_unknown_set_b_returns_failed(self, loaded_oracle):
        result = loaded_oracle.set_similarity("fruits", "no_set")
        assert result["status"] == "failed"


# ---------------------------------------------------------------------------
# State persistence
# ---------------------------------------------------------------------------

class TestPersistence:
    def test_set_survives_reinstantiation(self, tmp_state_dir):
        o1 = SetMembershipOracle()
        o1.add_elements("fruits", ["apple", "banana"])

        o2 = SetMembershipOracle()
        result = o2.test_membership("fruits", "apple")
        assert result["is_member"] is True
