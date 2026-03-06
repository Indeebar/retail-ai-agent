"""
Qdrant Cloud vector database connection and CRUD operations.
Manages collections for products, customer history, and promotions.
"""

import os
import logging
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

logger = logging.getLogger(__name__)

# Collection names
PRODUCTS_COLLECTION = "products"
HISTORY_COLLECTION = "customer_history"
PROMOTIONS_COLLECTION = "promotions"

# Vector dimensions (matches all-MiniLM-L6-v2 output)
VECTOR_SIZE = 384


def get_client() -> QdrantClient:
    """
    Returns a connected QdrantClient instance using environment variables.
    Raises RuntimeError if connection fails.
    """
    try:
        url = os.getenv("QDRANT_URL")
        api_key = os.getenv("QDRANT_API_KEY")
        client = QdrantClient(url=url, api_key=api_key)
        logger.info(f"Connected to Qdrant at {url}")
        return client
    except Exception as e:
        logger.error(f"Failed to connect to Qdrant: {e}")
        raise


def ensure_collections_exist(client: QdrantClient) -> None:
    """
    Checks if all 3 collections exist and creates any missing ones.
    Does NOT delete existing collections — never wipes data on startup.
    """
    collections = [PRODUCTS_COLLECTION, HISTORY_COLLECTION, PROMOTIONS_COLLECTION]
    existing = {c.name for c in client.get_collections().collections}

    for name in collections:
        if name in existing:
            logger.info(f"Collection '{name}' already exists")
        else:
            client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
            )
            logger.info(f"Created collection '{name}'")


def upsert_vectors(client: QdrantClient, collection: str, points: list[dict]) -> None:
    """
    Upserts vectors into a Qdrant collection.
    Each point dict must have: id (int), vector (list[float]), payload (dict).
    """
    try:
        point_structs = [
            PointStruct(
                id=p["id"],
                vector=p["vector"],
                payload=p["payload"],
            )
            for p in points
        ]
        client.upsert(collection_name=collection, points=point_structs)
        logger.info(f"Upserted {len(point_structs)} vectors into '{collection}'")
    except Exception as e:
        logger.error(f"Failed to upsert vectors into '{collection}': {e}")
        raise


def semantic_search(
    client: QdrantClient,
    collection: str,
    query_vector: list[float],
    top_k: int = 5,
    filters: dict = None,
) -> list[dict]:
    """
    Performs semantic search against a Qdrant collection.
    Returns list of payload dicts from the top_k results.
    """
    try:
        results = client.search(
            collection_name=collection,
            query_vector=query_vector,
            limit=top_k,
            query_filter=filters,
        )
        payloads = [hit.payload for hit in results]
        logger.info(f"Semantic search on '{collection}': {len(payloads)} results returned")
        return payloads
    except Exception as e:
        logger.error(f"Semantic search failed on '{collection}': {e}")
        return []


def collection_has_data(client: QdrantClient, collection: str) -> bool:
    """
    Returns True if the collection exists and has at least 1 point.
    Used by the indexer to skip re-indexing if already done.
    """
    try:
        info = client.get_collection(collection_name=collection)
        has_data = info.points_count > 0
        logger.info(f"Collection '{collection}' has {info.points_count} points")
        return has_data
    except Exception:
        return False
