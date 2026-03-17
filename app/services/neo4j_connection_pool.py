"""
Singleton connection pool for Neo4j clients.

Instead of creating a new Neo4jClient per tool call, this module lazily
creates one long-lived client per unique (uri, user) pair and reuses it.
The underlying neo4j async driver already manages its own internal
connection pool, so a single client per database is sufficient.
"""

import asyncio
from typing import Optional
from app.services.neo4j_database import Neo4jClient
from app.utils.get_logger import get_logger
import logging

logger = get_logger(name=__name__, level=logging.DEBUG)

_clients: dict[tuple[str, str], Neo4jClient] = {}
_lock = asyncio.Lock()


def get_neo4j_client(
    uri: str,
    user: str,
    password: str,
    max_connection_lifetime: int = 3600,
    connection_acquisition_timeout: int = 600,
    max_transaction_retry_time: int = 600,
) -> Neo4jClient:
    """
    Return a shared Neo4jClient for the given database.

    If a client for this (uri, user) pair already exists, it is returned
    directly.  Otherwise a new one is created with auto_close=False so
    that the driver stays alive across tool calls.

    The actual TCP connection is established lazily on the first
    ``run_query`` call (Neo4jClient.connect is called inside run_query
    when the driver is None).
    """
    key = (uri, user)
    if key not in _clients:
        logger.debug(f"Creating new shared Neo4jClient for {uri}")
        _clients[key] = Neo4jClient(
            uri=uri,
            user=user,
            password=password,
            max_connection_lifetime=max_connection_lifetime,
            connection_acquisition_timeout=connection_acquisition_timeout,
            max_transaction_retry_time=max_transaction_retry_time,
            auto_close=False,
        )
    return _clients[key]


async def close_all_clients() -> None:
    """Gracefully close every cached Neo4j client (call during app shutdown)."""
    for key, client in _clients.items():
        try:
            await client.close()
            logger.debug(f"Closed shared Neo4jClient for {key}")
        except Exception as e:
            logger.warning(f"Error closing Neo4jClient for {key}: {e}")
    _clients.clear()
