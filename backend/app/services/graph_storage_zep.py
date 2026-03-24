"""
Zep Cloud Implementation of the GraphStorage Interface

Wraps Zep Cloud SDK calls into the backend-agnostic GraphStorage abstract
interface so that callers can swap between Zep and other graph backends
(e.g. Graphiti + Neo4j) without changing any business logic.
"""

from __future__ import annotations

import time
import uuid as _uuid
import warnings
from typing import Any, Dict, List, Optional

from pydantic import Field
from zep_cloud import EpisodeData, EntityEdgeSourceTarget
from zep_cloud.client import Zep
from zep_cloud.external_clients.ontology import EdgeModel, EntityModel, EntityText

from ..config import Config
from ..utils.logger import get_logger
from ..utils.zep_paging import fetch_all_nodes, fetch_all_edges
from .graph_storage import (
    EpisodeStatus,
    GraphEdge,
    GraphNode,
    GraphStorage,
    SearchResult,
)

logger = get_logger("mirofish.graph_storage_zep")

# Zep reserved attribute names that must be prefixed to avoid SDK conflicts.
_RESERVED_NAMES = frozenset(
    {"uuid", "name", "group_id", "name_embedding", "summary", "created_at"}
)


def _safe_attr_name(attr_name: str) -> str:
    """Return a safe attribute name that does not collide with Zep reserved fields."""
    if attr_name.lower() in _RESERVED_NAMES:
        return f"entity_{attr_name}"
    return attr_name


def _get_uuid(obj: Any) -> str:
    """Extract UUID from a Zep SDK object (uses ``uuid_`` first, then ``uuid``)."""
    return getattr(obj, "uuid_", None) or getattr(obj, "uuid", "") or ""


def _str_or_none(value: Any) -> Optional[str]:
    """Stringify a value if not None."""
    return str(value) if value is not None else None


# ---------------------------------------------------------------------------
# Converters: Zep SDK objects  -->  GraphStorage dataclasses
# ---------------------------------------------------------------------------

def _zep_node_to_graph_node(node: Any) -> GraphNode:
    return GraphNode(
        uuid=_get_uuid(node),
        name=node.name or "",
        labels=node.labels or [],
        summary=node.summary or "",
        attributes=node.attributes or {},
        created_at=_str_or_none(getattr(node, "created_at", None)),
    )


def _zep_edge_to_graph_edge(edge: Any, node_map: Optional[Dict[str, str]] = None) -> GraphEdge:
    source_uuid = getattr(edge, "source_node_uuid", "") or ""
    target_uuid = getattr(edge, "target_node_uuid", "") or ""
    return GraphEdge(
        uuid=_get_uuid(edge),
        name=edge.name or "",
        fact=getattr(edge, "fact", "") or "",
        source_node_uuid=source_uuid,
        target_node_uuid=target_uuid,
        source_node_name=(node_map or {}).get(source_uuid, ""),
        target_node_name=(node_map or {}).get(target_uuid, ""),
        attributes=getattr(edge, "attributes", None) or {},
        created_at=_str_or_none(getattr(edge, "created_at", None)),
        valid_at=_str_or_none(getattr(edge, "valid_at", None)),
        invalid_at=_str_or_none(getattr(edge, "invalid_at", None)),
        expired_at=_str_or_none(getattr(edge, "expired_at", None)),
    )


# ---------------------------------------------------------------------------
# ZepGraphStorage
# ---------------------------------------------------------------------------

class ZepGraphStorage(GraphStorage):
    """GraphStorage implementation backed by the Zep Cloud SDK."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or Config.ZEP_API_KEY
        if not self.api_key:
            raise ValueError(
                "ZEP_API_KEY is not configured. "
                "Pass it explicitly or set it via the ZEP_API_KEY environment variable."
            )
        self.client = Zep(api_key=self.api_key)
        logger.info("ZepGraphStorage initialised")

    # ── helpers ──────────────────────────────────────────────────────────

    def _build_node_name_map(self, graph_id: str) -> Dict[str, str]:
        """Return {node_uuid: node_name} for all nodes in the graph."""
        raw_nodes = fetch_all_nodes(self.client, graph_id)
        return {_get_uuid(n): (n.name or "") for n in raw_nodes}

    # ── Graph Lifecycle ──────────────────────────────────────────────────

    def create_graph(self, graph_id: str, name: str, description: str = "") -> str:
        """Create a new graph. Returns graph_id."""
        if not graph_id:
            graph_id = f"mirofish_{_uuid.uuid4().hex[:16]}"
        try:
            self.client.graph.create(
                graph_id=graph_id,
                name=name,
                description=description or "MiroFish Graph",
            )
            logger.info(f"Graph created: graph_id={graph_id}, name={name}")
        except Exception:
            logger.exception(f"Failed to create graph {graph_id}")
            raise
        return graph_id

    def delete_graph(self, graph_id: str) -> None:
        """Delete a graph and all its data."""
        try:
            self.client.graph.delete(graph_id=graph_id)
            logger.info(f"Graph deleted: {graph_id}")
        except Exception:
            logger.exception(f"Failed to delete graph {graph_id}")
            raise

    # ── Ontology ─────────────────────────────────────────────────────────

    def set_ontology(self, graph_id: str, ontology: Dict[str, Any]) -> None:
        """
        Set the ontology (entity types + edge types) for a graph.

        Uses the dynamic Pydantic model approach required by the Zep SDK:
        entity types become EntityModel subclasses and edge types become
        EdgeModel subclasses with source/target constraints.
        """
        # Suppress Pydantic v2 warnings about Field(default=None) from
        # dynamic class creation – this is the pattern Zep SDK requires.
        warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

        # --- entity types ---
        entity_types: Dict[str, type] = {}
        for entity_def in ontology.get("entity_types", []):
            ename = entity_def["name"]
            edesc = entity_def.get("description", f"A {ename} entity.")

            attrs: Dict[str, Any] = {"__doc__": edesc}
            annotations: Dict[str, type] = {}

            for attr_def in entity_def.get("attributes", []):
                attr_name = _safe_attr_name(attr_def["name"])
                attr_desc = attr_def.get("description", attr_name)
                attrs[attr_name] = Field(description=attr_desc, default=None)
                annotations[attr_name] = Optional[EntityText]

            attrs["__annotations__"] = annotations
            entity_class = type(ename, (EntityModel,), attrs)
            entity_class.__doc__ = edesc
            entity_types[ename] = entity_class

        # --- edge types ---
        edge_definitions: Dict[str, tuple] = {}
        for edge_def in ontology.get("edge_types", []):
            ename = edge_def["name"]
            edesc = edge_def.get("description", f"A {ename} relationship.")

            attrs = {"__doc__": edesc}
            annotations: Dict[str, type] = {}

            for attr_def in edge_def.get("attributes", []):
                attr_name = _safe_attr_name(attr_def["name"])
                attr_desc = attr_def.get("description", attr_name)
                attrs[attr_name] = Field(description=attr_desc, default=None)
                annotations[attr_name] = Optional[str]

            attrs["__annotations__"] = annotations
            class_name = "".join(word.capitalize() for word in ename.split("_"))
            edge_class = type(class_name, (EdgeModel,), attrs)
            edge_class.__doc__ = edesc

            source_targets = [
                EntityEdgeSourceTarget(
                    source=st.get("source", "Entity"),
                    target=st.get("target", "Entity"),
                )
                for st in edge_def.get("source_targets", [])
            ]
            if source_targets:
                edge_definitions[ename] = (edge_class, source_targets)

        if entity_types or edge_definitions:
            try:
                self.client.graph.set_ontology(
                    graph_ids=[graph_id],
                    entities=entity_types or None,
                    edges=edge_definitions or None,
                )
                logger.info(
                    f"Ontology set for graph {graph_id}: "
                    f"{len(entity_types)} entity types, {len(edge_definitions)} edge types"
                )
            except Exception:
                logger.exception(f"Failed to set ontology for graph {graph_id}")
                raise
        else:
            logger.warning(f"Empty ontology provided for graph {graph_id}; nothing to set")

    # ── Data Ingestion ───────────────────────────────────────────────────

    def add_episodes(
        self, graph_id: str, texts: List[str], batch_size: int = 3
    ) -> List[str]:
        """
        Add text episodes to the graph for entity/relation extraction.

        Texts are grouped into batches of *batch_size* and submitted via
        ``client.graph.add_batch``.  Returns the list of episode UUIDs for
        downstream status tracking.
        """
        episode_uuids: List[str] = []
        total = len(texts)
        total_batches = (total + batch_size - 1) // batch_size

        for i in range(0, total, batch_size):
            batch_texts = texts[i : i + batch_size]
            batch_num = i // batch_size + 1

            episodes = [EpisodeData(data=text, type="text") for text in batch_texts]

            try:
                batch_result = self.client.graph.add_batch(
                    graph_id=graph_id,
                    episodes=episodes,
                )

                if batch_result and isinstance(batch_result, list):
                    for ep in batch_result:
                        ep_uuid = _get_uuid(ep)
                        if ep_uuid:
                            episode_uuids.append(ep_uuid)

                logger.info(
                    f"Episode batch {batch_num}/{total_batches} sent "
                    f"({len(batch_texts)} texts, graph={graph_id})"
                )
                # Small delay between batches to avoid rate-limiting.
                time.sleep(1)

            except Exception:
                logger.exception(
                    f"Failed to send episode batch {batch_num}/{total_batches} "
                    f"for graph {graph_id}"
                )
                raise

        logger.info(
            f"All episodes submitted: {len(episode_uuids)} UUIDs tracked (graph={graph_id})"
        )
        return episode_uuids

    def get_episode_status(self, episode_uuid: str) -> EpisodeStatus:
        """Check if an episode has been processed."""
        try:
            episode = self.client.graph.episode.get(uuid_=episode_uuid)
            return EpisodeStatus(
                uuid=episode_uuid,
                processed=bool(getattr(episode, "processed", False)),
            )
        except Exception:
            logger.warning(f"Failed to get episode status for {episode_uuid}", exc_info=True)
            return EpisodeStatus(uuid=episode_uuid, processed=False)

    def add_memory(self, graph_id: str, text: str) -> None:
        """Add a single memory/activity text to the graph via ``graph.add``."""
        try:
            self.client.graph.add(
                graph_id=graph_id,
                type="text",
                data=text,
            )
            logger.debug(f"Memory added to graph {graph_id}: {text[:80]}...")
        except Exception:
            logger.exception(f"Failed to add memory to graph {graph_id}")
            raise

    # ── Node Operations ──────────────────────────────────────────────────

    def get_all_nodes(self, graph_id: str) -> List[GraphNode]:
        """Get all nodes in a graph (auto-paginated)."""
        raw_nodes = fetch_all_nodes(self.client, graph_id)
        nodes = [_zep_node_to_graph_node(n) for n in raw_nodes]
        logger.info(f"Fetched {len(nodes)} nodes for graph {graph_id}")
        return nodes

    def get_node(self, graph_id: str, node_uuid: str) -> Optional[GraphNode]:
        """Get a single node by UUID."""
        try:
            raw_node = self.client.graph.node.get(uuid_=node_uuid)
            if raw_node is None:
                return None
            return _zep_node_to_graph_node(raw_node)
        except Exception:
            logger.warning(f"Failed to get node {node_uuid} in graph {graph_id}", exc_info=True)
            return None

    def get_node_edges(self, graph_id: str, node_uuid: str) -> List[GraphEdge]:
        """Get all edges connected to a node."""
        try:
            raw_edges = self.client.graph.node.get_entity_edges(node_uuid=node_uuid)
            node_map = self._build_node_name_map(graph_id)
            return [_zep_edge_to_graph_edge(e, node_map) for e in (raw_edges or [])]
        except Exception:
            logger.warning(
                f"Failed to get edges for node {node_uuid} in graph {graph_id}",
                exc_info=True,
            )
            return []

    # ── Edge Operations ──────────────────────────────────────────────────

    def get_all_edges(self, graph_id: str) -> List[GraphEdge]:
        """Get all edges in a graph (auto-paginated)."""
        raw_edges = fetch_all_edges(self.client, graph_id)
        node_map = self._build_node_name_map(graph_id)
        edges = [_zep_edge_to_graph_edge(e, node_map) for e in raw_edges]
        logger.info(f"Fetched {len(edges)} edges for graph {graph_id}")
        return edges

    # ── Search ───────────────────────────────────────────────────────────

    def search(
        self,
        graph_id: str,
        query: str,
        limit: int = 10,
        scope: str = "edges",
        reranker: Optional[str] = None,
    ) -> SearchResult:
        """
        Semantic + keyword hybrid search on the graph.

        Delegates to ``client.graph.search`` with cross-encoder reranking by
        default.  Falls back to an empty result on failure rather than raising,
        so callers can degrade gracefully.
        """
        effective_reranker = reranker or "cross_encoder"
        try:
            raw = self.client.graph.search(
                graph_id=graph_id,
                query=query,
                limit=limit,
                scope=scope,
                reranker=effective_reranker,
            )
        except Exception:
            logger.exception(f"Search failed for graph {graph_id}, query={query!r}")
            return SearchResult(query=query)

        facts: List[Dict[str, Any]] = []
        edges: List[GraphEdge] = []
        nodes: List[GraphNode] = []

        # Parse edge results
        if hasattr(raw, "edges") and raw.edges:
            for edge in raw.edges:
                fact_text = getattr(edge, "fact", "") or ""
                if fact_text:
                    facts.append({"text": fact_text, "source": "edge"})
                edges.append(
                    GraphEdge(
                        uuid=_get_uuid(edge),
                        name=getattr(edge, "name", "") or "",
                        fact=fact_text,
                        source_node_uuid=getattr(edge, "source_node_uuid", "") or "",
                        target_node_uuid=getattr(edge, "target_node_uuid", "") or "",
                    )
                )

        # Parse node results
        if hasattr(raw, "nodes") and raw.nodes:
            for node in raw.nodes:
                summary = getattr(node, "summary", "") or ""
                node_name = getattr(node, "name", "") or ""
                if summary:
                    facts.append({"text": f"[{node_name}]: {summary}", "source": "node"})
                nodes.append(
                    GraphNode(
                        uuid=_get_uuid(node),
                        name=node_name,
                        labels=getattr(node, "labels", []) or [],
                        summary=summary,
                    )
                )

        logger.info(
            f"Search complete for graph {graph_id}: "
            f"{len(facts)} facts, {len(edges)} edges, {len(nodes)} nodes"
        )
        return SearchResult(
            facts=facts,
            edges=edges,
            nodes=nodes,
            query=query,
            total_count=len(facts),
        )
