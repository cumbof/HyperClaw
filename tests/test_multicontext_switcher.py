"""Unit tests for skills/multicontext_switcher/handler.py"""

import pytest

from conftest import import_skill_handler

_mod = import_skill_handler("multicontext_switcher")
MulticontextSwitcher = _mod.MulticontextSwitcher


ALPHA_FACTS = ["PostgreSQL database migration", "JWT authentication RS256"]
BETA_FACTS  = ["React CDN deployment caching", "Webpack bundle optimisation"]


@pytest.fixture()
def sw(tmp_state_dir):
    return MulticontextSwitcher()


@pytest.fixture()
def populated_sw(tmp_state_dir):
    s = MulticontextSwitcher()
    s.create_context("alpha", tags=["backend"])
    s.add_facts(ALPHA_FACTS, context_id="alpha")
    s.create_context("beta", tags=["frontend"])
    s.add_facts(BETA_FACTS, context_id="beta")
    return s


# ---------------------------------------------------------------------------
# create_context
# ---------------------------------------------------------------------------

class TestCreateContext:
    def test_success(self, sw):
        result = sw.create_context("alpha")
        assert result["status"] == "success"

    def test_idempotent_second_call(self, sw):
        sw.create_context("alpha")
        result = sw.create_context("alpha")
        assert result["status"] == "success"

    def test_missing_context_id(self, sw):
        result = sw.create_context("")
        assert result["status"] == "failed"

    def test_tags_stored(self, sw):
        sw.create_context("alpha", tags=["backend", "auth"])
        result = sw.list_contexts()
        assert "backend" in result["contexts"]["alpha"]["tags"]


# ---------------------------------------------------------------------------
# switch_to
# ---------------------------------------------------------------------------

class TestSwitchTo:
    def test_active_context_changes(self, sw):
        sw.create_context("alpha")
        sw.switch_to("alpha")
        result = sw.list_contexts()
        assert result["active_context"] == "alpha"

    def test_auto_creates_if_not_existing(self, sw):
        result = sw.switch_to("new_ctx")
        assert result["status"] == "success"
        listed = sw.list_contexts()
        assert "new_ctx" in listed["contexts"]

    def test_previous_context_marked_inactive(self, sw):
        sw.create_context("alpha")
        sw.create_context("beta")
        sw.switch_to("alpha")
        sw.switch_to("beta")
        result = sw.list_contexts()
        assert result["contexts"]["alpha"]["active"] is False
        assert result["contexts"]["beta"]["active"] is True


# ---------------------------------------------------------------------------
# add_facts
# ---------------------------------------------------------------------------

class TestAddFacts:
    def test_adds_to_active_context(self, sw):
        sw.switch_to("alpha")
        result = sw.add_facts(["some fact"])
        assert result["status"] == "success"
        assert result["context_id"] == "alpha"

    def test_adds_to_explicit_context(self, sw):
        sw.create_context("beta")
        result = sw.add_facts(["another fact"], context_id="beta")
        assert result["context_id"] == "beta"

    def test_fact_count_increments(self, sw):
        sw.switch_to("alpha")
        sw.add_facts(["fact1", "fact2", "fact3"])
        listed = sw.list_contexts()
        assert listed["contexts"]["alpha"]["fact_count"] == 3

    def test_no_active_context_returns_failed(self, sw):
        result = sw.add_facts(["some fact"])
        assert result["status"] == "failed"

    def test_empty_facts_list_adds_zero(self, sw):
        sw.switch_to("alpha")
        result = sw.add_facts([])
        assert result["status"] == "success"
        listed = sw.list_contexts()
        assert listed["contexts"]["alpha"]["fact_count"] == 0


# ---------------------------------------------------------------------------
# query_context
# ---------------------------------------------------------------------------

class TestQueryContext:
    def test_relevant_terms_score_higher(self, populated_sw):
        alpha_result = populated_sw.query_context(["PostgreSQL", "database"], context_id="alpha")
        beta_result  = populated_sw.query_context(["PostgreSQL", "database"], context_id="beta")
        assert alpha_result["relevance"] > beta_result["relevance"]

    def test_returns_distance_and_relevance(self, populated_sw):
        result = populated_sw.query_context(["React"], context_id="beta")
        assert "relevance" in result
        assert "distance" in result

    def test_empty_context_returns_failed(self, sw):
        sw.create_context("empty_ctx")
        result = sw.query_context(["term"], context_id="empty_ctx")
        assert result["status"] == "failed"

    def test_missing_query_terms(self, populated_sw):
        result = populated_sw.query_context([], context_id="alpha")
        assert result["status"] == "failed"


# ---------------------------------------------------------------------------
# find_relevant_context
# ---------------------------------------------------------------------------

class TestFindRelevantContext:
    def test_database_query_finds_alpha(self, populated_sw):
        result = populated_sw.find_relevant_context(["database", "PostgreSQL"])
        assert result["status"] == "success"
        assert result["best_context"] == "alpha"

    def test_frontend_query_finds_beta(self, populated_sw):
        result = populated_sw.find_relevant_context(["React", "CDN"])
        assert result["status"] == "success"
        assert result["best_context"] == "beta"

    def test_all_scores_present(self, populated_sw):
        result = populated_sw.find_relevant_context(["anything"])
        assert "all_scores" in result
        assert len(result["all_scores"]) == 2

    def test_no_contexts_returns_failed(self, sw):
        result = sw.find_relevant_context(["term"])
        assert result["status"] == "failed"


# ---------------------------------------------------------------------------
# list_contexts
# ---------------------------------------------------------------------------

class TestListContexts:
    def test_empty_initially(self, sw):
        result = sw.list_contexts()
        assert result["contexts"] == {}
        assert result["active_context"] is None

    def test_shows_all_contexts(self, populated_sw):
        result = populated_sw.list_contexts()
        assert "alpha" in result["contexts"]
        assert "beta" in result["contexts"]


# ---------------------------------------------------------------------------
# State persistence
# ---------------------------------------------------------------------------

class TestPersistence:
    def test_context_survives_reinstantiation(self, tmp_state_dir):
        s1 = MulticontextSwitcher()
        s1.create_context("alpha")
        s1.add_facts(ALPHA_FACTS, context_id="alpha")

        s2 = MulticontextSwitcher()
        result = s2.query_context(["PostgreSQL"], context_id="alpha")
        assert result["status"] == "success"
