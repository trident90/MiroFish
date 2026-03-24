"""
Graph Storage Factory

Creates the appropriate GraphStorage implementation based on GRAPH_BACKEND config.
Supports 'zep' (default) and 'graphiti' backends.
"""

from ..config import Config
from ..utils.logger import get_logger
from .graph_storage import GraphStorage

logger = get_logger('mirofish.graph_storage')


def create_graph_storage() -> GraphStorage:
    """
    Create a GraphStorage instance based on GRAPH_BACKEND configuration.

    Environment variables:
        GRAPH_BACKEND: 'zep' (default) or 'graphiti'

    For 'zep':
        ZEP_API_KEY: Required

    For 'graphiti':
        GRAPHITI_URL: Graphiti server URL (default: http://localhost:8002)
        NEO4J_URI: Neo4j bolt URI (default: bolt://localhost:7687)
        NEO4J_USER: Neo4j username (default: neo4j)
        NEO4J_PASSWORD: Neo4j password
    """
    backend = getattr(Config, 'GRAPH_BACKEND', 'zep')

    if backend == 'graphiti':
        logger.info("Using Graphiti + Neo4j graph storage backend (on-premise)")
        from .graph_storage_graphiti import GraphitiGraphStorage
        return GraphitiGraphStorage(
            graphiti_url=getattr(Config, 'GRAPHITI_URL', 'http://localhost:8002'),
            neo4j_uri=getattr(Config, 'NEO4J_URI', 'bolt://localhost:7687'),
            neo4j_user=getattr(Config, 'NEO4J_USER', 'neo4j'),
            neo4j_password=getattr(Config, 'NEO4J_PASSWORD', ''),
        )
    else:
        logger.info("Using Zep Cloud graph storage backend")
        from .graph_storage_zep import ZepGraphStorage
        return ZepGraphStorage(api_key=Config.ZEP_API_KEY)
