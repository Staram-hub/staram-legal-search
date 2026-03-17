from neo4j import AsyncGraphDatabase, time as neo4j_time
from neo4j.exceptions import Neo4jError
from app.utils.get_logger import get_logger
import logging
import asyncio
from typing import Optional, Any

logger = get_logger(name=__name__, level=logging.DEBUG)


def _serialize_neo4j_data(data):
    """
    Recursively converts Neo4j-specific types to serializable Python types.
    Specifically handles neo4j.time.Date objects.
    """
    if isinstance(data, neo4j_time.Date):
        return data.isoformat()  # Convert to ISO 8601 string
    elif isinstance(data, dict):
        return {k: _serialize_neo4j_data(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [_serialize_neo4j_data(item) for item in data]
    return data


class Neo4jClient(object):
    """
    Async Neo4j client for executing Cypher queries with timeout support.
    """

    def __init__(
        self,
        uri: str,
        user: str,
        password: str,
        max_connection_lifetime: int = 3600,
        connection_acquisition_timeout: int = 60,
        max_transaction_retry_time: int = 60,
        auto_close: bool = False,
    ):
        """
        Initialize the Neo4j client.

        Args:
            uri (str): Neo4j database URI (e.g., "bolt://localhost:7687")
            user (str): Database username
            password (str): Database password
            max_connection_lifetime (int): Maximum connection lifetime in seconds (default: 3600)
            connection_acquisition_timeout (int): Timeout for acquiring connection in seconds (default: 60)
            max_transaction_retry_time (int): Maximum transaction retry time in seconds (default: 60)
            auto_close (bool): If True, closes connection after each query (default: False)

        Raises:
            ValueError: If required parameters are missing
        """
        if not all([uri, user, password]):
            raise ValueError("URI, user, and password are required")

        self.uri = uri
        self.user = user
        self.password = password
        self.max_connection_lifetime = max_connection_lifetime
        self.connection_acquisition_timeout = connection_acquisition_timeout
        self.max_transaction_retry_time = max_transaction_retry_time
        self.auto_close = auto_close
        self._driver = None

    async def connect(self):
        """
        Establish connection to Neo4j database with configured timeouts.

        Raises:
            Neo4jError: If connection fails
        """
        if self._driver:
            logger.debug("Driver already connected, reusing connection")
            return
            
        try:
            logger.debug(f"Attempting to connect to Neo4j at {self.uri}")
            self._driver = AsyncGraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password),
                max_connection_lifetime=self.max_connection_lifetime,
                connection_acquisition_timeout=self.connection_acquisition_timeout,
                max_transaction_retry_time=self.max_transaction_retry_time,
            )
            # Verify connectivity
            await self._driver.verify_connectivity()
            logger.debug(f"Successfully connected to Neo4j at {self.uri}")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j at {self.uri}: {e}")
            self._driver = None
            raise Neo4jError(f"Connection failed: {e}")

    async def close(self):
        """
        Close the database connection.
        """
        if self._driver:
            try:
                await self._driver.close()
                logger.debug("Neo4j connection closed")
            except Exception as e:
                logger.warning(f"Error closing connection: {e}")
            finally:
                self._driver = None

    async def run_query(
        self,
        query: str,
        parameters: Optional[dict[str, Any]] = None,
        timeout: int = 60,
    ) -> list[dict[str, Any]]:
        """
        Execute a Cypher query against the Neo4j database with timeout support.

        Args:
            query (str): Cypher query string
            parameters (dict, optional): Query parameters
            timeout (int): Query timeout in seconds (default: 60)

        Returns:
            list: Query results as a list of serialized records

        Raises:
            ValueError: If query is missing
            asyncio.TimeoutError: If query exceeds timeout
            Neo4jError: For database-related errors
            Exception: For unexpected errors
        """
        try:
            if not query:
                raise ValueError("Query is required")

            # Connect if not already connected
            if not self._driver:
                logger.debug("No active driver, attempting to connect...")
                await self.connect()
            
            # Double-check driver exists after connection attempt
            if not self._driver:
                raise Neo4jError("Failed to establish database connection")

            async def _execute_query():
                """Inner function to execute the query"""
                async with self._driver.session() as session:
                    result = await session.run(query, parameters or {})
                    data = await result.data()
                    return _serialize_neo4j_data(data)

            # Execute query with timeout
            logger.debug(f"Executing query with {timeout}s timeout")
            data = await asyncio.wait_for(_execute_query(), timeout=timeout)
            logger.debug(f"Query completed successfully, returned {len(data)} records")
            return data

        except asyncio.TimeoutError:
            logger.error(f"Query timeout after {timeout} seconds")
            logger.error(f"Query that timed out: {query[:200]}...")
            raise asyncio.TimeoutError(f"Query execution exceeded {timeout} seconds timeout")

        except Neo4jError as e:
            logger.error(f"Database error: {e}")
            raise

        except AttributeError as e:
            # Specific handling for 'NoneType' object has no attribute 'session'
            logger.error(f"Driver connection error: {e}")
            logger.error("Driver is None - connection may have failed")
            raise Neo4jError(f"Database connection is not available: {e}")

        except Exception as e:
            logger.error(f"Unexpected error during query execution: {e}")
            logger.error(f"Driver state: {self._driver is not None}")
            raise

        finally:
            # Only close if auto_close is enabled
            if self.auto_close and self._driver is not None:
                await self.close()

    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()