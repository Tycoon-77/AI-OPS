"""
Service dependency graph helpers — used by correlator, origin, priority.
"""
from __future__ import annotations

import json
import sqlite3
from functools import lru_cache

import networkx as nx


def build_undirected_graph(conn: sqlite3.Connection) -> nx.Graph:
    """Undirected graph for graph-distance calculations."""
    G: nx.Graph = nx.Graph()
    for row in conn.execute("SELECT service_id, tier FROM services"):
        G.add_node(row["service_id"], tier=row["tier"])
    for row in conn.execute("SELECT src_service, dst_service FROM service_edges"):
        G.add_edge(row["src_service"], row["dst_service"])
    return G


def build_directed_graph(conn: sqlite3.Connection) -> nx.DiGraph:
    """
    Directed graph: edge src→dst means src DEPENDS ON dst.
    Ancestors of a node = services that (transitively) depend on it.
    """
    G: nx.DiGraph = nx.DiGraph()
    for row in conn.execute("SELECT service_id, tier FROM services"):
        G.add_node(row["service_id"], tier=row["tier"])
    for row in conn.execute("SELECT src_service, dst_service FROM service_edges"):
        G.add_edge(row["src_service"], row["dst_service"])
    return G


def graph_dist(G: nx.Graph, a: str, b: str, cap: int = 6) -> int:
    """Undirected shortest-path length between services, capped at *cap*."""
    if a == b:
        return 0
    try:
        return min(nx.shortest_path_length(G, a, b), cap)
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return cap


def transitive_dependents(DG: nx.DiGraph, service: str) -> set[str]:
    """All services that (directly or transitively) depend on *service*."""
    # ancestors in the directed graph where edge = depends-on
    try:
        return nx.ancestors(DG, service)
    except nx.NodeNotFound:
        return set()


def dep_path(DG: nx.DiGraph, origin: str, target: str) -> str:
    """Human-readable dependency path from origin to target (or empty string)."""
    try:
        path = nx.shortest_path(DG, origin, target)
        return " > ".join(path)
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return ""
