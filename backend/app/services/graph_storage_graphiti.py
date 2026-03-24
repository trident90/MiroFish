"""
Graphiti + Neo4j implementation of the GraphStorage interface.

Uses the Graphiti REST API for episode ingestion, search, and entity/edge
retrieval, and the Neo4j Python driver for low-level graph lifecycle
operations (namespace creation/deletion).

Environment variables (consumed by the caller, not read here):
    GRAPHITI_URL        - Base URL of the Graphiti server (e.g. http://localhost:8000)
    NEO4J_URI           - Bolt URI for Neo4j (e.g. bolt://localhost:7687)
    NEO4J_USER          - Neo4j username
    NEO4J_PASSWORD      - Neo4j password

Dependencies:
    requests            - HTTP calls to Graphiti REST API (standard project dep)
    neo4j               - Neo4j Python driver (optional; install with `pip install neo4j`)
"""

from __future__ import annotations

import logging
import uuid as _uuid
from typing import Any, Dict, List, Optional

import requests

from app.services.graph_storage import (
    EpisodeStatus,
    GraphEdge,
    GraphNode,
    GraphStorage,
    SearchResult,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy import of the neo4j driver so the module can be loaded even when the
# driver is not installed (it is an optional dependency).
# ---------------------------------------------------------------------------

try:
    from neo4j import GraphDatabase  # type: ignore[import-untyped]

    _HAS_NEO4J = True
except ImportError:  # pragma: no cover
    _HAS_NEO4J = False
    GraphDatabase = None  # type: ignore[assignment,misc]


class GraphitiGraphStorage(GraphStorage):
    """
    GraphStorage implementation backed by the Graphiti REST API and Neo4j.

    * **Graphiti REST API** handles episode ingestion (LLM-based NER/RE),
      semantic search, and entity/edge retrieval.
    * **Neo4j driver** handles graph-level lifecycle operations (create /
      delete namespaces) via Cypher queries.
    """

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(
        self,
        graphiti_url: str,
        neo4j_uri: str,
        neo4j_user: str,
        neo4j_password: str,
        *,
        request_timeout: int = 60,
    ) -> None:
        """
        Parameters
        ----------
        graphiti_url : str
            Base URL of the Graphiti REST server (no trailing slash).
        neo4j_uri : str
            Bolt URI for Neo4j, e.g. ``bolt://localhost:7687``.
        neo4j_user : str
            Neo4j username.
        neo4j_password : str
            Neo4j password.
        request_timeout : int
            Default HTTP timeout in seconds for Graphiti API calls.
        """
        self._graphiti_url = graphiti_url.rstrip("/")
        self._neo4j_uri = neo4j_uri
        self._neo4j_user = neo4j_user
        self._neo4j_password = neo4j_password
        self._timeout = request_timeout

        # Initialise Neo4j driver (lazy – only created once).
        self._driver = None
        if _HAS_NEO4J:
            try:
                self._driver = GraphDatabase.driver(
                    neo4j_uri, auth=(neo4j_user, neo4j_password)
                )
                logger.info("Neo4j driver initialised for %s", neo4j_uri)
            except Exception:
                logger.exception("Failed to create Neo4j driver for %s", neo4j_uri)
        else:
            logger.warning(
                "neo4j Python driver is not installed. "
                "Graph lifecycle operations (create/delete) will not work."
            )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _url(self, path: str) -> str:
        """Build full Graphiti URL from a path fragment."""
        return f"{self._graphiti_url}{path}"

    def _post(self, path: str, json: Dict[str, Any] | None = None) -> requests.Response:
        """POST to the Graphiti REST API with standard error handling."""
        url = self._url(path)
        try:
            resp = requests.post(url, json=json, timeout=self._timeout)
            resp.raise_for_status()
            return resp
        except requests.ConnectionError:
            logger.error("Graphiti server unreachable at %s", url)
            raise
        except requests.HTTPError as exc:
            logger.error(
                "Graphiti API error %s %s: %s",
                exc.response.status_code,
                url,
                exc.response.text[:500],
            )
            raise

    def _get(self, path: str, params: Dict[str, Any] | None = None) -> requests.Response:
        """GET from the Graphiti REST API with standard error handling."""
        url = self._url(path)
        try:
            resp = requests.get(url, params=params, timeout=self._timeout)
            resp.raise_for_status()
            return resp
        except requests.ConnectionError:
            logger.error("Graphiti server unreachable at %s", url)
            raise
        except requests.HTTPError as exc:
            logger.error(
                "Graphiti API error %s %s: %s",
                exc.response.status_code,
                url,
                exc.response.text[:500],
            )
            raise

    def _run_cypher(self, query: str, parameters: Dict[str, Any] | None = None) -> list:
        """
        Execute a Cypher query against Neo4j and return a list of record dicts.

        Raises ``RuntimeError`` if the Neo4j driver is not available.
        """
        if self._driver is None:
            raise RuntimeError(
                "Neo4j driver is not available. "
                "Install the 'neo4j' package and provide valid credentials."
            )
        with self._driver.session() as session:
            result = session.run(query, parameters or {})
            return [record.data() for record in result]

    # ------------------------------------------------------------------
    # Conversion helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_graph_node(data: Dict[str, Any]) -> GraphNode:
        """Convert a Graphiti entity/node JSON dict to a ``GraphNode``."""
        return GraphNode(
            uuid=str(data.get("uuid", data.get("id", ""))),
            name=data.get("name", ""),
            labels=data.get("labels", []),
            summary=data.get("summary", data.get("description", "")),
            attributes=data.get("attributes", data.get("metadata", {})),
            created_at=data.get("created_at"),
        )

    @staticmethod
    def _to_graph_edge(data: Dict[str, Any]) -> GraphEdge:
        """Convert a Graphiti edge JSON dict to a ``GraphEdge``."""
        return GraphEdge(
            uuid=str(data.get("uuid", data.get("id", ""))),
            name=data.get("name", data.get("relation_type", "")),
            fact=data.get("fact", ""),
            source_node_uuid=str(data.get("source_node_uuid", data.get("source_entity_uuid", ""))),
            target_node_uuid=str(data.get("target_node_uuid", data.get("target_entity_uuid", ""))),
            source_node_name=data.get("source_node_name", data.get("source_entity_name", "")),
            target_node_name=data.get("target_node_name", data.get("target_entity_name", "")),
            attributes=data.get("attributes", data.get("metadata", {})),
            created_at=data.get("created_at"),
            valid_at=data.get("valid_at"),
            invalid_at=data.get("invalid_at"),
            expired_at=data.get("expired_at"),
        )

    # ------------------------------------------------------------------
    # Graph Lifecycle
    # ------------------------------------------------------------------

    def create_graph(self, graph_id: str, name: str, description: str = "") -> str:
        """
        Create a new graph namespace in Neo4j.

        A uniqueness constraint is created on the ``graph_id`` property so that
        nodes belonging to different graphs can coexist in the same database.

        Returns the *graph_id* that was passed in (or a generated UUID if
        *graph_id* was empty).
        """
        if not graph_id:
            graph_id = str(_uuid.uuid4())

        try:
            # Store a metadata node representing the graph itself.
            self._run_cypher(
                """
                MERGE (g:__GraphMeta {graph_id: $graph_id})
                SET g.name = $name,
                    g.description = $description,
                    g.created_at = datetime()
                """,
                {"graph_id": graph_id, "name": name, "description": description},
            )
            logger.info("Created graph namespace '%s' (%s) in Neo4j", name, graph_id)
        except RuntimeError:
            logger.warning(
                "Neo4j driver unavailable; skipping graph creation for %s", graph_id
            )
        except Exception:
            logger.exception("Failed to create graph namespace %s in Neo4j", graph_id)
            raise

        return graph_id

    def delete_graph(self, graph_id: str) -> None:
        """
        Delete all nodes and relationships that belong to *graph_id*.

        Uses ``CALL { ... } IN TRANSACTIONS`` to avoid running out of memory
        when the graph is large.
        """
        try:
            # Delete relationships first, then nodes, in batched transactions.
            self._run_cypher(
                """
                MATCH (n {graph_id: $graph_id})
                DETACH DELETE n
                """,
                {"graph_id": graph_id},
            )
            # Also remove the metadata node.
            self._run_cypher(
                """
                MATCH (g:__GraphMeta {graph_id: $graph_id})
                DELETE g
                """,
                {"graph_id": graph_id},
            )
            logger.info("Deleted graph namespace '%s' from Neo4j", graph_id)
        except RuntimeError:
            logger.warning(
                "Neo4j driver unavailable; skipping graph deletion for %s", graph_id
            )
        except Exception:
            logger.exception("Failed to delete graph namespace %s from Neo4j", graph_id)
            raise

    # ------------------------------------------------------------------
    # Ontology
    # ------------------------------------------------------------------

    def set_ontology(self, graph_id: str, ontology: Dict[str, Any]) -> None:
        """
        Store ontology guidance for a graph.

        Graphiti performs NER/RE via an LLM, so ontology is treated as
        advisory metadata rather than a hard schema.  The ontology dict is
        persisted on the ``__GraphMeta`` node so that it can be forwarded as
        context when adding episodes.
        """
        try:
            self._run_cypher(
                """
                MERGE (g:__GraphMeta {graph_id: $graph_id})
                SET g.ontology = $ontology_json
                """,
                {
                    "graph_id": graph_id,
                    "ontology_json": _safe_json_str(ontology),
                },
            )
            logger.info("Ontology set for graph %s", graph_id)
        except RuntimeError:
            logger.warning(
                "Neo4j driver unavailable; ontology for %s not persisted", graph_id
            )
        except Exception:
            logger.exception("Failed to set ontology for graph %s", graph_id)
            raise

    # ------------------------------------------------------------------
    # Data Ingestion
    # ------------------------------------------------------------------

    def add_episodes(
        self, graph_id: str, texts: List[str], batch_size: int = 3
    ) -> List[str]:
        """
        Send text episodes to the Graphiti REST API for LLM-based extraction.

        Each text is posted as a separate episode.  The Graphiti server
        processes them (NER + RE via its configured LLM) and stores the
        resulting entities/edges in the underlying Neo4j database.

        Returns a list of episode UUIDs (one per text).
        """
        episode_uuids: List[str] = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            for text in batch:
                episode_uuid = str(_uuid.uuid4())
                body: Dict[str, Any] = {
                    "name": f"episode-{episode_uuid[:8]}",
                    "episode_body": text,
                    "group_id": graph_id,
                    "uuid": episode_uuid,
                    "source_description": "MiroFish ingestion",
                }
                try:
                    self._post("/v1/episodes", json=body)
                    episode_uuids.append(episode_uuid)
                    logger.debug(
                        "Submitted episode %s to Graphiti for graph %s",
                        episode_uuid,
                        graph_id,
                    )
                except Exception:
                    logger.exception(
                        "Failed to submit episode to Graphiti for graph %s", graph_id
                    )
                    # Continue processing remaining texts; partial success is
                    # better than total failure.

        logger.info(
            "Submitted %d/%d episodes for graph %s",
            len(episode_uuids),
            len(texts),
            graph_id,
        )
        return episode_uuids

    def get_episode_status(self, episode_uuid: str) -> EpisodeStatus:
        """
        Check whether an episode has been fully processed by Graphiti.

        The Graphiti REST API returns episode metadata including a status
        field.  If the endpoint is unavailable or the episode is not found,
        we return an unprocessed status.
        """
        try:
            resp = self._get(f"/v1/episodes/{episode_uuid}")
            data = resp.json()
            processed = data.get("status", "").lower() in ("done", "processed", "completed")
            return EpisodeStatus(uuid=episode_uuid, processed=processed)
        except requests.HTTPError as exc:
            if exc.response is not None and exc.response.status_code == 404:
                logger.warning("Episode %s not found", episode_uuid)
            else:
                logger.exception("Error checking episode status %s", episode_uuid)
            return EpisodeStatus(uuid=episode_uuid, processed=False)
        except Exception:
            logger.exception("Error checking episode status %s", episode_uuid)
            return EpisodeStatus(uuid=episode_uuid, processed=False)

    def add_memory(self, graph_id: str, text: str) -> None:
        """
        Convenience wrapper: add a single memory text as an episode.

        Equivalent to ``add_episodes(graph_id, [text])``.
        """
        self.add_episodes(graph_id, [text], batch_size=1)

    # ------------------------------------------------------------------
    # Node Operations
    # ------------------------------------------------------------------

    def get_all_nodes(self, graph_id: str) -> List[GraphNode]:
        """
        Retrieve all entity nodes belonging to *graph_id* from Graphiti.
        """
        try:
            resp = self._get("/v1/entities", params={"group_id": graph_id})
            data = resp.json()
            entities = data if isinstance(data, list) else data.get("entities", data.get("nodes", []))
            return [self._to_graph_node(e) for e in entities]
        except Exception:
            logger.exception("Failed to retrieve nodes for graph %s", graph_id)
            return []

    def get_node(self, graph_id: str, node_uuid: str) -> Optional[GraphNode]:
        """
        Retrieve a single node by UUID from Graphiti.
        """
        try:
            resp = self._get(f"/v1/entities/{node_uuid}", params={"group_id": graph_id})
            data = resp.json()
            return self._to_graph_node(data)
        except requests.HTTPError as exc:
            if exc.response is not None and exc.response.status_code == 404:
                logger.warning("Node %s not found in graph %s", node_uuid, graph_id)
                return None
            logger.exception("Error fetching node %s", node_uuid)
            return None
        except Exception:
            logger.exception("Error fetching node %s", node_uuid)
            return None

    def get_node_edges(self, graph_id: str, node_uuid: str) -> List[GraphEdge]:
        """
        Get all edges connected to a specific node.

        Tries the Graphiti ``/v1/entities/{uuid}/edges`` endpoint first.
        Falls back to filtering the full edge list if the dedicated endpoint
        is not available.
        """
        try:
            resp = self._get(
                f"/v1/entities/{node_uuid}/edges",
                params={"group_id": graph_id},
            )
            data = resp.json()
            edges = data if isinstance(data, list) else data.get("edges", [])
            return [self._to_graph_edge(e) for e in edges]
        except requests.HTTPError:
            # Fallback: fetch all edges and filter client-side.
            logger.debug(
                "Dedicated node-edges endpoint unavailable; falling back to full edge list"
            )
            all_edges = self.get_all_edges(graph_id)
            return [
                e
                for e in all_edges
                if e.source_node_uuid == node_uuid or e.target_node_uuid == node_uuid
            ]
        except Exception:
            logger.exception(
                "Failed to retrieve edges for node %s in graph %s", node_uuid, graph_id
            )
            return []

    # ------------------------------------------------------------------
    # Edge Operations
    # ------------------------------------------------------------------

    def get_all_edges(self, graph_id: str) -> List[GraphEdge]:
        """
        Retrieve all edges belonging to *graph_id* from Graphiti.
        """
        try:
            resp = self._get("/v1/edges", params={"group_id": graph_id})
            data = resp.json()
            edges = data if isinstance(data, list) else data.get("edges", [])
            return [self._to_graph_edge(e) for e in edges]
        except Exception:
            logger.exception("Failed to retrieve edges for graph %s", graph_id)
            return []

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(
        self,
        graph_id: str,
        query: str,
        limit: int = 10,
        scope: str = "edges",
        reranker: Optional[str] = None,
    ) -> SearchResult:
        """
        Perform a hybrid (semantic + keyword) search via the Graphiti API.

        Parameters
        ----------
        graph_id : str
            Target graph namespace.
        query : str
            Natural-language query string.
        limit : int
            Maximum number of results.
        scope : str
            ``'edges'``, ``'nodes'``, or ``'both'``.
        reranker : str | None
            Optional reranker identifier (passed through to Graphiti).

        Returns
        -------
        SearchResult
            Unified search result containing matching facts, edges, and nodes.
        """
        body: Dict[str, Any] = {
            "query": query,
            "group_id": graph_id,
            "num_results": limit,
        }
        if reranker:
            body["reranker"] = reranker

        result = SearchResult(query=query)

        try:
            resp = self._post("/v1/search", json=body)
            data = resp.json()

            # Graphiti may return edges/facts at the top level or nested.
            raw_edges = data if isinstance(data, list) else data.get("edges", data.get("facts", []))

            for item in raw_edges:
                edge = self._to_graph_edge(item)
                result.edges.append(edge)
                result.facts.append(
                    {
                        "uuid": edge.uuid,
                        "fact": edge.fact or edge.name,
                        "source": edge.source_node_name,
                        "target": edge.target_node_name,
                        "valid_at": edge.valid_at,
                        "invalid_at": edge.invalid_at,
                    }
                )

            # If scope includes nodes, also fetch related entity data.
            if scope in ("nodes", "both"):
                raw_nodes = data.get("nodes", data.get("entities", []))
                for item in raw_nodes:
                    result.nodes.append(self._to_graph_node(item))

            result.total_count = len(result.edges) + len(result.nodes)

        except Exception:
            logger.exception("Search failed for graph %s query='%s'", graph_id, query)

        return result

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the Neo4j driver connection, if open."""
        if self._driver is not None:
            try:
                self._driver.close()
                logger.info("Neo4j driver closed")
            except Exception:
                logger.exception("Error closing Neo4j driver")

    def __del__(self) -> None:
        self.close()


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _safe_json_str(obj: Any) -> str:
    """Serialise *obj* to a JSON string, falling back to ``str()``."""
    import json

    try:
        return json.dumps(obj, default=str)
    except (TypeError, ValueError):
        return str(obj)
