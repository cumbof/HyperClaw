"""Unit tests for skills/attribute_filter/handler.py"""

import pytest

from conftest import import_skill_handler

_mod = import_skill_handler("attribute_filter")
AttributeFilter = _mod.AttributeFilter


ENTITIES = [
    ("Alice", {"dept": "Eng",   "city": "NYC", "level": "Senior"}),
    ("Bob",   {"dept": "Sales", "city": "LA",  "level": "Junior"}),
    ("Carol", {"dept": "Eng",   "city": "NYC", "level": "Lead"}),
    ("Dave",  {"dept": "HR",    "city": "LA",  "level": "Senior"}),
]


@pytest.fixture()
def af(tmp_state_dir):
    return AttributeFilter()


@pytest.fixture()
def populated_af(tmp_state_dir):
    a = AttributeFilter()
    for name, attrs in ENTITIES:
        a.store_entity("emp", name, attrs)
    return a


# ---------------------------------------------------------------------------
# store_entity
# ---------------------------------------------------------------------------

class TestStoreEntity:
    def test_success(self, af):
        result = af.store_entity("emp", "Alice", {"dept": "Eng"})
        assert result["status"] == "success"

    def test_missing_store_id(self, af):
        result = af.store_entity("", "Alice", {"dept": "Eng"})
        assert result["status"] == "failed"

    def test_missing_entity_name(self, af):
        result = af.store_entity("emp", "", {"dept": "Eng"})
        assert result["status"] == "failed"

    def test_empty_attributes_ok(self, af):
        result = af.store_entity("emp", "Alice", {})
        assert result["status"] == "success"

    def test_entity_exists_after_store(self, af):
        af.store_entity("emp", "Alice", {"dept": "Eng"})
        result = af.get_entity("emp", "Alice")
        assert result["exists"] is True

    def test_overwrite_updates_vector(self, af):
        af.store_entity("emp", "Alice", {"dept": "Eng"})
        af.store_entity("emp", "Alice", {"dept": "Sales"})
        result = af.get_entity("emp", "Alice")
        assert result["exists"] is True


# ---------------------------------------------------------------------------
# filter_entities
# ---------------------------------------------------------------------------

class TestFilterEntities:
    def test_single_attribute_filter(self, populated_af):
        result = populated_af.filter_entities("emp", {"city": "NYC"})
        assert result["status"] == "success"
        names = [m["entity"] for m in result["matches"]]
        assert "Alice" in names
        assert "Carol" in names
        assert "Bob" not in names
        assert "Dave" not in names

    def test_multi_attribute_filter_narrows_results(self, populated_af):
        result = populated_af.filter_entities("emp", {"dept": "Eng", "city": "NYC"})
        assert result["status"] == "success"
        names = [m["entity"] for m in result["matches"]]
        # Both Alice and Carol match; Bob/Dave should not
        assert "Bob" not in names
        assert "Dave" not in names

    def test_results_sorted_by_score(self, populated_af):
        result = populated_af.filter_entities("emp", {"city": "NYC"})
        scores = [m["score"] for m in result["matches"]]
        assert scores == sorted(scores, reverse=True)

    def test_missing_store_id(self, af):
        result = af.filter_entities("", {"city": "NYC"})
        assert result["status"] == "failed"

    def test_unknown_store(self, af):
        result = af.filter_entities("no_store", {"city": "NYC"})
        assert result["status"] == "failed"

    def test_empty_filters(self, populated_af):
        result = populated_af.filter_entities("emp", {})
        assert result["status"] == "failed"


# ---------------------------------------------------------------------------
# get_entity / list_entities
# ---------------------------------------------------------------------------

class TestGetAndList:
    def test_get_existing(self, populated_af):
        result = populated_af.get_entity("emp", "Alice")
        assert result["exists"] is True

    def test_get_nonexistent(self, populated_af):
        result = populated_af.get_entity("emp", "Zara")
        assert result["exists"] is False

    def test_list_returns_all(self, populated_af):
        result = populated_af.list_entities("emp")
        assert result["status"] == "success"
        assert result["count"] == len(ENTITIES)
        for name, _ in ENTITIES:
            assert name in result["entities"]

    def test_list_unknown_store(self, af):
        result = af.list_entities("no_store")
        assert result["status"] == "failed"


# ---------------------------------------------------------------------------
# State persistence
# ---------------------------------------------------------------------------

class TestPersistence:
    def test_entity_survives_reinstantiation(self, tmp_state_dir):
        a1 = AttributeFilter()
        a1.store_entity("emp", "Alice", {"dept": "Eng", "city": "NYC"})

        a2 = AttributeFilter()
        result = a2.get_entity("emp", "Alice")
        assert result["exists"] is True
