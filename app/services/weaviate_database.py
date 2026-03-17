"""
This module contains the WeaviateDatabase class, which provides methods to interact with a Weaviate vector
database.

A module-level singleton instance is provided via ``get_weaviate_db()`` so that
the underlying gRPC/HTTP connection is reused across tool calls instead of
being created and torn down on every invocation.
"""

import asyncio

import weaviate
from weaviate.classes.query import Filter
from weaviate.classes.query import MetadataQuery
from app.config import weaviate_config
from app.utils.get_logger import get_logger
import logging

logger = get_logger(name=__name__, level=logging.DEBUG)

# Default court filter per collection (used when case_ids is None)
_DEFAULT_COURT_FILTER: dict[str, str] = {
    COLLECTION_SC: "SUPREME COURT OF INDIA",
    COLLECTION_HC: "HIGH COURT",
    COLLECTION_OTHERS: "",
}

# Court hierarchy: lower number = higher priority.
# SC cases always appear before HC, HC before Others.
_COURT_TIER: dict[str, int] = {
    COLLECTION_SC: 0,
    COLLECTION_HC: 1,
    COLLECTION_OTHERS: 2,
}


class WeaviateDatabase(object):
    """
    Async Weaviate client that keeps its connection alive across calls.
    Use ``get_weaviate_db()`` to obtain the shared singleton instance.
    """

    def __init__(self):
        self.client = None

    async def connect(self):
        """
        Establish (or re-establish) the connection to Weaviate.
        """
        if self.client is not None:
            # Already connected – check if still alive
            if self.client.is_connected():
                logger.debug("Weaviate client already connected, reusing")
                return
            else:
                logger.debug("Weaviate client disconnected, reconnecting")

        self.client = weaviate.use_async_with_custom(
            http_host=weaviate_config.http_host,
            http_port=weaviate_config.http_port,
            http_secure=False,
            grpc_host=weaviate_config.grpc_host,
            grpc_port=weaviate_config.grpc_port,
            grpc_secure=False,
        )
        await self.client.connect()
        logger.debug("Weaviate client connected successfully")

    async def _ensure_connected(self):
        """Lazily connect if not already connected."""
        if self.client is None or not self.client.is_connected():
            await self.connect()

    async def _search_single_collection(
        self,
        collection_name: str,
        case_ids: list[str] | None,
        query_embedding: list[float],
        top_k: int,
        similarity_type: str,
    ):
        """
        Run a near-vector search on a single Weaviate collection.

        Returns the raw query response object.
        """
        collection = self.client.collections.get(collection_name)

        if case_ids is not None:
            response = await collection.query.near_vector(
                near_vector=query_embedding,
                limit=top_k,
                filters=(
                    Filter.by_property("iLOCaseNo").contains_any(case_ids)
                    & Filter.by_property("content_Label").equal(similarity_type)
                    & Filter.by_property("contentType").equal("Paragraph")
                ),
                return_metadata=MetadataQuery(distance=True),
            )
        else:
            # Build a base filter on content_Label + contentType
            base_filter = (
                Filter.by_property("content_Label").equal(similarity_type)
                & Filter.by_property("contentType").equal("Paragraph")
            )

            # Add a court filter if a default exists for this collection
            default_court = _DEFAULT_COURT_FILTER.get(collection_name, "")
            if default_court:
                base_filter = (
                    Filter.by_property("court").equal(default_court)
                    & base_filter
                )

            response = await collection.query.near_vector(
                near_vector=query_embedding,
                limit=top_k,
                filters=base_filter,
                return_metadata=MetadataQuery(distance=True),
            )

        return response

    async def search_similar_content_in_specific_cases(
        self,
        case_ids: list[str] | None,
        query_embedding: list[float],
        top_k: int = 10,
        similarity_type: str = "Facts",
    ):
        """
        Search for similar content across **all** collections (SC, HC, OTHERS).

        Queries are fired in parallel.  Results from every collection are
        merged and sorted by **court hierarchy first** (SC → HC → Others),
        then by similarity distance within each tier, and trimmed to ``top_k``.

        Args:
            case_ids: List of iLOCaseNo values from Neo4j.  If ``None`` the
                search runs across all cases (filtered by a default court
                value per collection where available).
            query_embedding: The embedding vector for the search query.
            top_k: Number of results to return (after merging).
            similarity_type: Component of the case to match against.
                One of ``['Rules', 'Facts', 'Issues', 'Analysis', 'Conclusion']``.
        """
        await self._ensure_connected()

        all_collections = [weaviate_config.collections_sc, weaviate_config.collections_hc, weaviate_config.collections_others]

        # Query all collections in parallel
        responses = await asyncio.gather(
            *(
                self._search_single_collection(
                    collection_name=coll,
                    case_ids=case_ids,
                    query_embedding=query_embedding,
                    top_k=top_k,
                    similarity_type=similarity_type,
                )
                for coll in all_collections
            )
        )

        # Merge objects from all responses, tagging each with its court tier
        all_objects = []
        for coll, resp in zip(all_collections, responses):
            tier = _COURT_TIER.get(coll, 99)
            for obj in resp.objects:
                # Attach tier so the sort key can access it
                obj._court_tier = tier
                all_objects.append(obj)

        # Sort by court hierarchy first (SC=0 → HC=1 → Others=2),
        # then by similarity distance within the same tier.
        all_objects.sort(
            key=lambda obj: (
                obj._court_tier,
                obj.metadata.distance
                if obj.metadata and obj.metadata.distance is not None
                else float("inf"),
            )
        )

        # Build a response-like object with the merged & trimmed results
        merged = responses[0]              # reuse the first response shell
        merged.objects = all_objects[:top_k]
        return merged

    async def close_db(self):
        """
        Close the Weaviate client connection.
        """
        if self.client is not None:
            await self.client.close()
            self.client = None
            logger.debug("Weaviate client closed")


# ---- Singleton access ----

_instance: WeaviateDatabase | None = None


def get_weaviate_db() -> WeaviateDatabase:
    """Return the shared ``WeaviateDatabase`` singleton."""
    global _instance
    if _instance is None:
        logger.debug("Creating shared WeaviateDatabase singleton")
        _instance = WeaviateDatabase()
    return _instance
