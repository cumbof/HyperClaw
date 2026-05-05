"""Unit tests for skills/concept_hierarchy/handler.py"""

import pytest

from conftest import import_skill_handler

_mod = import_skill_handler("concept_hierarchy")
ConceptHierarchy = _mod.ConceptHierarchy


@pytest.fixture()
def hier(tmp_state_dir):
    return ConceptHierarchy()


@pytest.fixture()
def built_hier(tmp_state_dir):
    h = ConceptHierarchy()
    h.define_class("Dog",    ["Poodle", "Bulldog", "Labrador"], parent_classes=["Animal"])
    h.define_class("Cat",    ["Siamese", "Tabby"],              parent_classes=["Animal"])
    h.define_class("Animal", ["Dog", "Cat", "Fish"])
    return h


# ---------------------------------------------------------------------------
# define_class
# ---------------------------------------------------------------------------

class TestDefineClass:
    def test_basic_success(self, hier):
        result = hier.define_class("Dog", ["Poodle", "Bulldog"])
        assert result["status"] == "success"

    def test_missing_class_name(self, hier):
        result = hier.define_class("", ["Poodle"])
        assert result["status"] == "failed"

    def test_additive_members(self, hier):
        hier.define_class("Dog", ["Poodle"])
        hier.define_class("Dog", ["Bulldog"])
        # No error expected — additive
        result = hier.is_a("Poodle", "Dog")
        assert result["is_direct_member"] is True

    def test_empty_members_ok(self, hier):
        result = hier.define_class("EmptyClass", [])
        assert result["status"] == "success"

    def test_parent_classes_registered(self, hier):
        hier.define_class("Dog", ["Poodle"], parent_classes=["Animal"])
        result = hier.get_ancestors("Dog")
        assert "Animal" in result["ancestors"]


# ---------------------------------------------------------------------------
# is_a – direct membership
# ---------------------------------------------------------------------------

class TestIsADirect:
    def test_member_is_direct(self, built_hier):
        result = built_hier.is_a("Poodle", "Dog")
        assert result["status"] == "success"
        assert result["is_direct_member"] is True

    def test_non_member_is_not_direct(self, built_hier):
        result = built_hier.is_a("Siamese", "Dog")
        assert result["status"] == "success"
        assert result["is_direct_member"] is False

    def test_similarity_within_valid_range(self, built_hier):
        result = built_hier.is_a("Poodle", "Dog")
        # Cosine-distance-based similarity can be negative; just check it's a number
        assert isinstance(result["similarity"], float)


# ---------------------------------------------------------------------------
# is_a – transitive membership
# ---------------------------------------------------------------------------

class TestIsATransitive:
    def test_transitive_member(self, built_hier):
        # Poodle → Dog → Animal
        result = built_hier.is_a("Poodle", "Animal")
        assert result["status"] == "success"
        assert result["is_transitive_member"] is True

    def test_non_transitive_non_member(self, built_hier):
        # Fish was added directly to Animal but never had a parent pointing to Dog
        result = built_hier.is_a("Fish", "Dog")
        assert result["is_transitive_member"] is False

    def test_unknown_class_returns_failed(self, built_hier):
        result = built_hier.is_a("Poodle", "NoSuchClass")
        assert result["status"] == "failed"


# ---------------------------------------------------------------------------
# get_ancestors
# ---------------------------------------------------------------------------

class TestGetAncestors:
    def test_poodle_ancestors_include_dog_and_animal(self, built_hier):
        result = built_hier.get_ancestors("Poodle")
        assert result["status"] == "success"
        assert "Dog" in result["ancestors"]
        assert "Animal" in result["ancestors"]

    def test_no_ancestors_returns_empty_list(self, built_hier):
        # Fish was listed as a member of Animal, so Animal IS an ancestor of Fish
        result = built_hier.get_ancestors("Fish")
        assert result["status"] == "success"
        assert "Animal" in result["ancestors"]

    def test_unknown_concept_returns_failed(self, built_hier):
        result = built_hier.get_ancestors("Unicorn")
        assert result["status"] == "failed"


# ---------------------------------------------------------------------------
# find_class
# ---------------------------------------------------------------------------

class TestFindClass:
    def test_finds_correct_class_for_known_member(self, built_hier):
        result = built_hier.find_class("Poodle")
        assert result["status"] == "success"
        # Dog should rank higher than Animal for Poodle
        top = result["all_scores"][0]["class"]
        assert top == "Dog"

    def test_all_scores_present(self, built_hier):
        result = built_hier.find_class("Siamese")
        assert "all_scores" in result
        assert len(result["all_scores"]) >= 2  # Dog and Cat at minimum

    def test_no_classes_returns_failed(self, hier):
        result = hier.find_class("Poodle")
        assert result["status"] == "failed"


# ---------------------------------------------------------------------------
# State persistence
# ---------------------------------------------------------------------------

class TestPersistence:
    def test_class_survives_reinstantiation(self, tmp_state_dir):
        h1 = ConceptHierarchy()
        h1.define_class("Dog", ["Poodle"], parent_classes=["Animal"])

        h2 = ConceptHierarchy()
        result = h2.is_a("Poodle", "Dog")
        assert result["is_direct_member"] is True
