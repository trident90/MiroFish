"""
Graph Storage Abstract Interface

Defines a backend-agnostic interface for knowledge graph operations.
Implementations can use Zep Cloud, Graphiti + Neo4j, or any other graph backend.

Switch between backends via GRAPH_BACKEND environment variable ('zep' or 'graphiti').
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class GraphNode:
    """Unified node representation across backends."""
    uuid: str
    name: str
    labels: List[str] = field(default_factory=list)
    summary: str = ""
    attributes: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[str] = None


@dataclass
class GraphEdge:
    """Unified edge representation across backends."""
    uuid: str
    name: str
    fact: str = ""
    source_node_uuid: str = ""
    target_node_uuid: str = ""
    source_node_name: str = ""
    target_node_name: str = ""
    attributes: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[str] = None
    valid_at: Optional[str] = None
    invalid_at: Optional[str] = None
    expired_at: Optional[str] = None


@dataclass
class SearchResult:
    """Unified search result."""
    facts: List[Dict[str, Any]] = field(default_factory=list)
    edges: List[GraphEdge] = field(default_factory=list)
    nodes: List[GraphNode] = field(default_factory=list)
    query: str = ""
    total_count: int = 0


@dataclass
class EpisodeStatus:
    """Status of an episode/data ingestion."""
    uuid: str
    processed: bool = False


class GraphStorage(ABC):
    """
    Abstract interface for knowledge graph operations.

    All graph backends must implement this interface.
    Services (graph_builder, zep_tools, etc.) interact only through this interface.
    """

    # ── Graph Lifecycle ──

    @abstractmethod
    def create_graph(self, graph_id: str, name: str, description: str = "") -> str:
        """Create a new graph. Returns graph_id."""
        ...

    @abstractmethod
    def delete_graph(self, graph_id: str) -> None:
        """Delete a graph and all its data."""
        ...

    # ── Ontology ──

    @abstractmethod
    def set_ontology(self, graph_id: str, ontology: Dict[str, Any]) -> None:
        """
        Set the ontology (entity types + edge types) for a graph.
        ontology format: {"entity_types": [...], "edge_types": [...]}
        """
        ...

    # ── Data Ingestion ──

    @abstractmethod
    def add_episodes(self, graph_id: str, texts: List[str], batch_size: int = 3) -> List[str]:
        """
        Add text episodes to the graph for entity/relation extraction.
        Returns list of episode UUIDs for tracking.
        """
        ...

    @abstractmethod
    def get_episode_status(self, episode_uuid: str) -> EpisodeStatus:
        """Check if an episode has been processed."""
        ...

    @abstractmethod
    def add_memory(self, graph_id: str, text: str) -> None:
        """Add a single memory/activity text to the graph."""
        ...

    # ── Node Operations ──

    @abstractmethod
    def get_all_nodes(self, graph_id: str) -> List[GraphNode]:
        """Get all nodes in a graph."""
        ...

    @abstractmethod
    def get_node(self, graph_id: str, node_uuid: str) -> Optional[GraphNode]:
        """Get a single node by UUID."""
        ...

    @abstractmethod
    def get_node_edges(self, graph_id: str, node_uuid: str) -> List[GraphEdge]:
        """Get all edges connected to a node."""
        ...

    # ── Edge Operations ──

    @abstractmethod
    def get_all_edges(self, graph_id: str) -> List[GraphEdge]:
        """Get all edges in a graph."""
        ...

    # ── Search ──

    @abstractmethod
    def search(
        self,
        graph_id: str,
        query: str,
        limit: int = 10,
        scope: str = "edges",
        reranker: Optional[str] = None
    ) -> SearchResult:
        """
        Semantic + keyword hybrid search on the graph.
        scope: 'edges', 'nodes', or 'both'
        """
        ...
