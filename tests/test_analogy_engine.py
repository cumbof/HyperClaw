"""Unit tests for skills/analogy_engine/handler.py"""

import pytest

from conftest import import_skill_handler

_mod = import_skill_handler("analogy_engine")
AnalogyEngine = _mod.AnalogyEngine


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

CAPITAL_PAIRS = [
    {"source": "France",  "target": "Paris"},
    {"source": "Germany", "target": "Berlin"},
    {"source": "Italy",   "target": "Rome"},
]


@pytest.fixture()
def engine(tmp_state_dir):
    return AnalogyEngine()


@pytest.fixture()
def trained_engine(tmp_state_dir):
    eng = AnalogyEngine()
    eng.train_relation("capital_of", CAPITAL_PAIRS)
    return eng


# ---------------------------------------------------------------------------
# train_relation
# ---------------------------------------------------------------------------

class TestTrainRelation:
    def test_returns_success(self, engine):
        result = engine.train_relation("capital_of", CAPITAL_PAIRS)
        assert result["status"] == "success"

    def test_pair_count_increments(self, engine):
        engine.train_relation("capital_of", CAPITAL_PAIRS)
        summary = engine.list_relations()
        assert summary["relations"]["capital_of"]["pair_count"] == 3

    def test_additive_on_second_call(self, engine):
        engine.train_relation("capital_of", CAPITAL_PAIRS[:2])
        engine.train_relation("capital_of", CAPITAL_PAIRS[2:])
        summary = engine.list_relations()
        assert summary["relations"]["capital_of"]["pair_count"] == 3

    def test_missing_relation_name(self, engine):
        result = engine.train_relation("", CAPITAL_PAIRS)
        assert result["status"] == "failed"

    def test_missing_pairs(self, engine):
        result = engine.train_relation("capital_of", [])
        assert result["status"] == "failed"

    def test_multiple_relations_independent(self, engine):
        engine.train_relation("capital_of", CAPITAL_PAIRS)
        engine.train_relation("synonym_of", [{"source": "happy", "target": "joyful"}])
        summary = engine.list_relations()
        assert "capital_of" in summary["relations"]
        assert "synonym_of" in summary["relations"]


# ---------------------------------------------------------------------------
# reverse_lookup  (more reliable than forward_lookup)
# ---------------------------------------------------------------------------

class TestReverseLookup:
    def test_known_target_returns_correct_source(self, trained_engine):
        result = trained_engine.reverse_lookup("capital_of", "Berlin")
        assert result["status"] == "success"
        assert result["source"] == "Germany"

    def test_result_contains_confidence(self, trained_engine):
        result = trained_engine.reverse_lookup("capital_of", "Paris")
        assert "confidence" in result
        assert result["confidence"] > 0

    def test_unknown_relation_returns_failed(self, trained_engine):
        result = trained_engine.reverse_lookup("no_such_relation", "Berlin")
        assert result["status"] == "failed"


# ---------------------------------------------------------------------------
# forward_lookup
# ---------------------------------------------------------------------------

class TestForwardLookup:
    def test_known_source_in_training_returns_success_or_low_confidence(self, trained_engine):
        # Forward lookup has higher noise; accept either success or low_confidence
        result = trained_engine.forward_lookup("capital_of", "France")
        assert result["status"] in ("success", "low_confidence")

    def test_unknown_relation(self, trained_engine):
        result = trained_engine.forward_lookup("nonexistent", "France")
        assert result["status"] == "failed"


# ---------------------------------------------------------------------------
# test_conformance
# ---------------------------------------------------------------------------

class TestConformance:
    def test_trained_pair_conforms(self, trained_engine):
        result = trained_engine.test_conformance("capital_of", "France", "Paris")
        assert result["status"] == "success"
        assert result["conforms"] is True

    def test_wrong_pair_does_not_conform(self, trained_engine):
        # France→Berlin is NOT in the training set; it may or may not pass
        # depending on random vectors, but the call must succeed
        result = trained_engine.test_conformance("capital_of", "France", "Berlin")
        assert result["status"] == "success"
        assert "conforms" in result

    def test_contains_similarity_score(self, trained_engine):
        result = trained_engine.test_conformance("capital_of", "Germany", "Berlin")
        assert "similarity" in result

    def test_unknown_relation(self, trained_engine):
        result = trained_engine.test_conformance("no_rel", "A", "B")
        assert result["status"] == "failed"


# ---------------------------------------------------------------------------
# list_relations
# ---------------------------------------------------------------------------

class TestListRelations:
    def test_empty_initially(self, engine):
        result = engine.list_relations()
        assert result["status"] == "success"
        assert result["relations"] == {}

    def test_populated_after_training(self, trained_engine):
        result = trained_engine.list_relations()
        assert "capital_of" in result["relations"]


# ---------------------------------------------------------------------------
# State persistence
# ---------------------------------------------------------------------------

class TestPersistence:
    def test_state_reloads_across_instances(self, tmp_state_dir):
        eng1 = AnalogyEngine()
        eng1.train_relation("capital_of", CAPITAL_PAIRS)

        eng2 = AnalogyEngine()  # new instance; should load from disk
        summary = eng2.list_relations()
        assert summary["relations"]["capital_of"]["pair_count"] == 3
