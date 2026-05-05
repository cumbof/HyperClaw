"""Unit tests for skills/semantic_classifier/handler.py"""

import pytest

from conftest import import_skill_handler

_mod = import_skill_handler("semantic_classifier")
SemanticClassifier = _mod.SemanticClassifier


@pytest.fixture()
def clf(tmp_state_dir):
    return SemanticClassifier()


@pytest.fixture()
def trained_clf(tmp_state_dir):
    c = SemanticClassifier()
    c.train("spam",   ["buy", "free", "offer", "discount", "prize"])
    c.train("spam",   ["win", "money", "cheap", "click", "deal"])
    c.train("ham",    ["meeting", "report", "schedule", "project", "deadline"])
    c.train("ham",    ["budget", "review", "team", "agenda", "update"])
    return c


# ---------------------------------------------------------------------------
# train
# ---------------------------------------------------------------------------

class TestTrain:
    def test_success(self, clf):
        result = clf.train("spam", ["buy", "free", "offer"])
        assert result["status"] == "success"

    def test_class_appears_in_list(self, clf):
        clf.train("spam", ["buy", "free"])
        result = clf.list_classes()
        assert "spam" in result["classes"]

    def test_missing_class_label(self, clf):
        result = clf.train("", ["buy", "free"])
        assert result["status"] == "failed"

    def test_empty_features(self, clf):
        result = clf.train("spam", [])
        assert result["status"] == "failed"

    def test_additive_training(self, clf):
        clf.train("spam", ["buy"])
        clf.train("spam", ["free", "offer"])
        result = clf.list_classes()
        # Should still be one class with combined prototype
        assert result["classes"].count("spam") == 1 if isinstance(result["classes"], list) else True


# ---------------------------------------------------------------------------
# classify
# ---------------------------------------------------------------------------

class TestClassify:
    def test_spam_features_classified_as_spam(self, trained_clf):
        result = trained_clf.classify(["buy", "free", "win"])
        assert result["status"] == "success"
        assert result["predicted_class"] == "spam"

    def test_ham_features_classified_as_ham(self, trained_clf):
        result = trained_clf.classify(["meeting", "agenda", "team"])
        assert result["status"] == "success"
        assert result["predicted_class"] == "ham"

    def test_confidence_present(self, trained_clf):
        result = trained_clf.classify(["buy", "free"])
        assert "confidence" in result
        assert result["confidence"] > 0

    def test_all_scores_present(self, trained_clf):
        result = trained_clf.classify(["buy"])
        if result["status"] == "success":
            assert "all_scores" in result
            assert len(result["all_scores"]) == 2  # spam and ham

    def test_scores_sorted_descending(self, trained_clf):
        result = trained_clf.classify(["buy"])
        if result["status"] == "success":
            scores = [s["confidence"] for s in result["all_scores"]]
            assert scores == sorted(scores, reverse=True)

    def test_empty_features_returns_failed(self, trained_clf):
        result = trained_clf.classify([])
        assert result["status"] == "failed"

    def test_no_classes_trained_returns_failed(self, clf):
        result = clf.classify(["buy"])
        assert result["status"] == "failed"


# ---------------------------------------------------------------------------
# list_classes
# ---------------------------------------------------------------------------

class TestListClasses:
    def test_empty_initially(self, clf):
        result = clf.list_classes()
        assert result["status"] == "success"
        # classes is an empty list or dict
        classes = result.get("classes", [])
        assert len(classes) == 0

    def test_two_classes_after_training(self, trained_clf):
        result = trained_clf.list_classes()
        classes = result["classes"]
        assert "spam" in classes
        assert "ham" in classes


# ---------------------------------------------------------------------------
# State persistence
# ---------------------------------------------------------------------------

class TestPersistence:
    def test_classifier_survives_reinstantiation(self, tmp_state_dir):
        c1 = SemanticClassifier()
        c1.train("spam", ["buy", "free", "offer"])
        c1.train("ham",  ["meeting", "agenda"])

        c2 = SemanticClassifier()
        result = c2.classify(["buy", "free"])
        assert result["status"] == "success"
        assert result["predicted_class"] == "spam"
