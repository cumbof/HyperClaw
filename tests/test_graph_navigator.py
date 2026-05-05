"""Unit tests for skills/graph_navigator/handler.py"""

import pytest

from conftest import import_skill_handler

_mod = import_skill_handler("graph_navigator")
GraphNavigator = _mod.GraphNavigator


@pytest.fixture()
def nav(tmp_state_dir):
    return GraphNavigator()


@pytest.fixture()
def undirected_nav(tmp_state_dir):
    n = GraphNavigator()
    n.add_edges("g", [
        {"from": "A", "to": "B"},
        {"from": "A", "to": "C"},
        {"from": "B", "to": "D"},
        {"from": "C", "to": "D"},
    ], directed=False)
    return n


@pytest.fixture()
def directed_nav(tmp_state_dir):
    n = GraphNavigator()
    n.add_edges("dg", [
        {"from": "X", "to": "Y"},
        {"from": "Y", "to": "Z"},
    ], directed=True)
    return n


# ---------------------------------------------------------------------------
# add_edges
# ---------------------------------------------------------------------------

class TestAddEdges:
    def test_undirected_success(self, nav):
        result = nav.add_edges("g", [{"from": "A", "to": "B"}])
        assert result["status"] == "success"

    def test_directed_success(self, nav):
        result = nav.add_edges("g", [{"from": "A", "to": "B"}], directed=True)
        assert result["status"] == "success"

    def test_missing_graph_id(self, nav):
        result = nav.add_edges("", [{"from": "A", "to": "B"}])
        assert result["status"] == "failed"

    def test_missing_edges(self, nav):
        result = nav.add_edges("g", [])
        assert result["status"] == "failed"

    def test_additive(self, nav):
        nav.add_edges("g", [{"from": "A", "to": "B"}])
        nav.add_edges("g", [{"from": "A", "to": "C"}])
        result = nav.list_nodes("g")
        assert result["count"] >= 2  # A and at least one of B, C


# ---------------------------------------------------------------------------
# get_neighbors
# ---------------------------------------------------------------------------

class TestGetNeighbors:
    def test_direct_neighbors_detected(self, undirected_nav):
        result = undirected_nav.get_neighbors("g", "A")
        assert result["status"] == "success"
        names = [n["node"] for n in result["neighbors"]]
        assert "B" in names
        assert "C" in names

    def test_non_neighbor_not_returned(self, undirected_nav):
        result = undirected_nav.get_neighbors("g", "A")
        names = [n["node"] for n in result["neighbors"]]
        # D is two hops from A, should not appear as direct neighbor
        assert "D" not in names

    def test_node_without_edges_returns_empty(self, undirected_nav):
        # Query a node name that was never added
        result = undirected_nav.get_neighbors("g", "Z_not_in_graph")
        assert result["neighbors"] == []

    def test_unknown_graph_returns_failed(self, nav):
        result = nav.get_neighbors("no_graph", "A")
        assert result["status"] == "failed"

    def test_directed_only_forward(self, directed_nav):
        # X→Y exists; Y→X should NOT be a neighbor in the directed graph
        result = directed_nav.get_neighbors("dg", "Y")
        names = [n["node"] for n in result["neighbors"]]
        assert "Z" in names
        assert "X" not in names


# ---------------------------------------------------------------------------
# are_neighbors
# ---------------------------------------------------------------------------

class TestAreNeighbors:
    def test_direct_edge_true(self, undirected_nav):
        result = undirected_nav.are_neighbors("g", "A", "B")
        assert result["status"] == "success"
        assert result["are_neighbors"] is True

    def test_two_hop_false(self, undirected_nav):
        result = undirected_nav.are_neighbors("g", "A", "D")
        assert result["are_neighbors"] is False

    def test_unknown_graph(self, nav):
        result = nav.are_neighbors("no_graph", "A", "B")
        assert result["status"] == "failed"


# ---------------------------------------------------------------------------
# list_nodes
# ---------------------------------------------------------------------------

class TestListNodes:
    def test_returns_nodes_with_outgoing_edges(self, undirected_nav):
        result = undirected_nav.list_nodes("g")
        assert result["status"] == "success"
        assert result["count"] >= 4  # A, B, C, D all have edges in undirected graph

    def test_unknown_graph(self, nav):
        result = nav.list_nodes("no_graph")
        assert result["status"] == "failed"


# ---------------------------------------------------------------------------
# State persistence
# ---------------------------------------------------------------------------

class TestPersistence:
    def test_graph_survives_reinstantiation(self, tmp_state_dir):
        n1 = GraphNavigator()
        n1.add_edges("g", [{"from": "A", "to": "B"}])

        n2 = GraphNavigator()
        result = n2.get_neighbors("g", "A")
        assert result["status"] == "success"
        names = [x["node"] for x in result["neighbors"]]
        assert "B" in names
