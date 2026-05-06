"""Unit tests for skills/deduplication_cache/handler.py"""

import pytest

from conftest import import_skill_handler

_mod = import_skill_handler("deduplication_cache")
DeduplicationCache = _mod.DeduplicationCache


@pytest.fixture()
def cache(tmp_state_dir):
    return DeduplicationCache()


# ---------------------------------------------------------------------------
# check_and_add
# ---------------------------------------------------------------------------

class TestCheckAndAdd:
    def test_new_item_not_duplicate(self, cache):
        result = cache.check_and_add("urls", "page1")
        assert result["status"] == "success"
        assert result["is_duplicate"] is False
        assert result["was_added"] is True
        assert result["cache_size"] == 1

    def test_same_item_detected_as_duplicate(self, cache):
        cache.check_and_add("urls", "page1")
        result = cache.check_and_add("urls", "page1")
        assert result["is_duplicate"] is True
        assert result["was_added"] is False
        assert result["cache_size"] == 1  # was NOT re-added

    def test_different_items_not_duplicate(self, cache):
        cache.check_and_add("urls", "page1")
        result = cache.check_and_add("urls", "page2")
        assert result["is_duplicate"] is False
        assert result["cache_size"] == 2

    def test_cache_grows_monotonically(self, cache):
        for i in range(5):
            cache.check_and_add("urls", f"page{i}")
        result = cache.cache_stats("urls")
        assert result["item_count"] == 5

    def test_custom_threshold_stored(self, cache):
        cache.check_and_add("urls", "page1", threshold=0.8)
        result = cache.cache_stats("urls")
        assert result["threshold"] == 0.8

    def test_missing_cache_id(self, cache):
        result = cache.check_and_add("", "page1")
        assert result["status"] == "failed"

    def test_missing_item(self, cache):
        result = cache.check_and_add("urls", "")
        assert result["status"] == "failed"

    def test_first_item_has_no_distance(self, cache):
        result = cache.check_and_add("urls", "page1")
        assert result["distance"] is None


# ---------------------------------------------------------------------------
# check_only
# ---------------------------------------------------------------------------

class TestCheckOnly:
    def test_empty_cache_not_duplicate(self, cache):
        result = cache.check_only("urls", "page1")
        assert result["status"] == "success"
        assert result["is_duplicate"] is False

    def test_known_item_is_duplicate(self, cache):
        cache.check_and_add("urls", "page1")
        result = cache.check_only("urls", "page1")
        assert result["is_duplicate"] is True

    def test_check_only_does_not_modify_cache(self, cache):
        cache.check_and_add("urls", "page1")
        cache.check_only("urls", "page_new")
        stats = cache.cache_stats("urls")
        assert stats["item_count"] == 1  # unchanged

    def test_nonexistent_cache_returns_not_duplicate(self, cache):
        result = cache.check_only("never_created", "page1")
        assert result["is_duplicate"] is False


# ---------------------------------------------------------------------------
# clear_cache
# ---------------------------------------------------------------------------

class TestClearCache:
    def test_clears_all_items(self, cache):
        for i in range(3):
            cache.check_and_add("urls", f"page{i}")
        cache.clear_cache("urls")
        stats = cache.cache_stats("urls")
        assert stats["item_count"] == 0

    def test_preserves_threshold_after_clear(self, cache):
        cache.check_and_add("urls", "page1", threshold=0.9)
        cache.clear_cache("urls")
        stats = cache.cache_stats("urls")
        assert stats["threshold"] == 0.9

    def test_unknown_cache_returns_failed(self, cache):
        result = cache.clear_cache("no_such_cache")
        assert result["status"] == "failed"

    def test_can_add_after_clear(self, cache):
        cache.check_and_add("urls", "page1")
        cache.clear_cache("urls")
        result = cache.check_and_add("urls", "page1")
        assert result["is_duplicate"] is False  # fresh cache


# ---------------------------------------------------------------------------
# cache_stats
# ---------------------------------------------------------------------------

class TestCacheStats:
    def test_returns_correct_count(self, cache):
        cache.check_and_add("urls", "p1")
        cache.check_and_add("urls", "p2")
        result = cache.cache_stats("urls")
        assert result["item_count"] == 2

    def test_unknown_cache_returns_failed(self, cache):
        result = cache.cache_stats("no_cache")
        assert result["status"] == "failed"


# ---------------------------------------------------------------------------
# State persistence
# ---------------------------------------------------------------------------

class TestPersistence:
    def test_cache_survives_reinstantiation(self, tmp_state_dir):
        c1 = DeduplicationCache()
        c1.check_and_add("urls", "page1")

        c2 = DeduplicationCache()
        result = c2.check_only("urls", "page1")
        assert result["is_duplicate"] is True
