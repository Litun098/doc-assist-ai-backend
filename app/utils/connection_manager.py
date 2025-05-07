"""
Connection manager for handling external service connections.
This utility helps manage connections to external services like Supabase, Weaviate, etc.
It ensures proper initialization and cleanup of connections to prevent resource leaks.
"""
import logging
import time
from typing import Dict, Any, Optional, List
from contextlib import contextmanager
import atexit

# Supabase
from supabase import create_client, Client

# Weaviate
import weaviate
from weaviate.classes.init import Auth, AdditionalConfig, Timeout

# Configuration
from config.config import settings

# Configure logging
logger = logging.getLogger(__name__)

class ConnectionManager:
    """
    Connection manager for handling external service connections.
    Implements the Singleton pattern to ensure only one instance exists.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConnectionManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the connection manager if not already initialized."""
        if self._initialized:
            return

        # Initialize connection pools
        self._supabase_clients: Dict[str, Client] = {}
        self._weaviate_clients: Dict[str, Any] = {}
        self._other_connections: Dict[str, Any] = {}

        # Register cleanup handler
        atexit.register(self.close_all_connections)

        self._initialized = True
        logger.info("Connection manager initialized")

    def get_supabase_client(self, key_type: str = "default") -> Optional[Client]:
        """
        Get a Supabase client from the pool or create a new one.

        Args:
            key_type: Type of key to use ('default' or 'service')

        Returns:
            Supabase client or None if creation fails
        """
        # Check if client already exists in pool
        if key_type in self._supabase_clients:
            return self._supabase_clients[key_type]

        # Create new client
        try:
            if key_type == "service" and settings.SUPABASE_SERVICE_KEY:
                logger.info(f"Creating Supabase client with service role key")
                client = create_client(
                    supabase_url=settings.SUPABASE_URL,
                    supabase_key=settings.SUPABASE_SERVICE_KEY
                )
            else:
                logger.info(f"Creating Supabase client with default key")
                client = create_client(
                    supabase_url=settings.SUPABASE_URL,
                    supabase_key=settings.SUPABASE_KEY
                )

            # Store in pool
            self._supabase_clients[key_type] = client
            return client
        except Exception as e:
            logger.error(f"Error creating Supabase client: {str(e)}")
            return None

    def get_weaviate_client(self, client_id: str = "default") -> Optional[Any]:
        """
        Get a Weaviate client from the pool or create a new one.

        Args:
            client_id: Identifier for the client

        Returns:
            Weaviate client or None if creation fails
        """
        # Check if client already exists in pool
        if client_id in self._weaviate_clients:
            return self._weaviate_clients[client_id]

        # Create new client
        if settings.WEAVIATE_URL and settings.WEAVIATE_API_KEY:
            try:
                # Make sure we're using the REST endpoint, not gRPC
                weaviate_url = settings.WEAVIATE_URL
                if not weaviate_url.startswith("https://"):
                    weaviate_url = f"https://{weaviate_url}"

                logger.info(f"Connecting to Weaviate at {weaviate_url}")

                # Use retry logic for connection
                max_retries = 3
                retry_count = 0
                connection_successful = False

                while retry_count < max_retries and not connection_successful:
                    try:
                        client = weaviate.connect_to_weaviate_cloud(
                            cluster_url=weaviate_url,
                            auth_credentials=Auth.api_key(settings.WEAVIATE_API_KEY),
                            skip_init_checks=True,  # Skip initialization checks
                            additional_config=AdditionalConfig(
                                timeout=Timeout(init=60)  # Increase timeout to 60 seconds
                            )
                        )
                        connection_successful = True
                        logger.info("Successfully connected to Weaviate")
                    except Exception as e:
                        retry_count += 1
                        logger.warning(f"Weaviate connection attempt {retry_count} failed: {str(e)}")
                        if retry_count < max_retries:
                            logger.info(f"Retrying connection to Weaviate ({retry_count}/{max_retries})...")
                            time.sleep(1)  # Wait 1 second before retrying

                if connection_successful:
                    # Store in pool
                    self._weaviate_clients[client_id] = client
                    return client
                else:
                    logger.error("Failed to connect to Weaviate after multiple attempts")
                    return None
            except Exception as e:
                logger.error(f"Error connecting to Weaviate: {str(e)}")
                return None
        else:
            logger.warning("Weaviate URL or API key not configured")
            return None

    def close_supabase_connections(self):
        """Close all Supabase connections."""
        for key, client in self._supabase_clients.items():
            try:
                # Supabase doesn't have an explicit close method, but we can clear the reference
                logger.info(f"Clearing Supabase client: {key}")

                # Try to close any httpx clients that might be used by Supabase
                if client and hasattr(client, 'rest'):
                    # Access the underlying httpx client if possible
                    if hasattr(client.rest, 'client'):
                        try:
                            if hasattr(client.rest.client, 'close'):
                                client.rest.client.close()
                            elif hasattr(client.rest.client, 'aclose'):
                                import asyncio
                                try:
                                    loop = asyncio.get_event_loop()
                                    if loop.is_running():
                                        loop.create_task(client.rest.client.aclose())
                                    else:
                                        loop.run_until_complete(client.rest.client.aclose())
                                except Exception:
                                    pass
                        except Exception as http_e:
                            logger.error(f"Error closing httpx client for Supabase: {str(http_e)}")

                # Clear the reference
                self._supabase_clients[key] = None
            except Exception as e:
                logger.error(f"Error closing Supabase client {key}: {str(e)}")

        # Clear the dictionary
        self._supabase_clients.clear()

        # Try to clean up any httpx clients
        try:
            import httpx
            # Close any global httpx clients
            for client_attr in ['_default_async_client', '_default_sync_client']:
                if hasattr(httpx, client_attr):
                    client = getattr(httpx, client_attr)
                    if client:
                        if hasattr(client, 'close'):
                            client.close()
                        elif hasattr(client, 'aclose'):
                            import asyncio
                            try:
                                loop = asyncio.get_event_loop()
                                if loop.is_running():
                                    loop.create_task(client.aclose())
                                else:
                                    loop.run_until_complete(client.aclose())
                            except Exception:
                                pass
        except Exception as http_e:
            logger.error(f"Error closing global httpx clients: {str(http_e)}")

    def close_weaviate_connections(self):
        """Close all Weaviate connections."""
        for key, client in self._weaviate_clients.items():
            try:
                if client:
                    logger.info(f"Closing Weaviate client: {key}")
                    # Try multiple approaches to ensure proper cleanup
                    try:
                        # Standard close method
                        client.close()
                    except Exception as close_error:
                        logger.error(f"Error in standard close for Weaviate client {key}: {str(close_error)}")

                        # Try to access and close the underlying HTTP client if available
                        try:
                            if hasattr(client, '_connection'):
                                conn = getattr(client, '_connection')
                                if hasattr(conn, 'close'):
                                    conn.close()
                        except Exception as conn_error:
                            logger.error(f"Error closing Weaviate connection: {str(conn_error)}")

                    # Force garbage collection of the client
                    import gc
                    self._weaviate_clients[key] = None
                    gc.collect()
            except Exception as e:
                logger.error(f"Error closing Weaviate client {key}: {str(e)}")

        # Clear the dictionary
        self._weaviate_clients.clear()

        # Try to clean up any grpc channels that might be used by Weaviate
        try:
            import grpc
            # Force garbage collection to clean up any grpc channels
            gc.collect()
        except Exception:
            pass

    def close_all_connections(self):
        """Close all connections."""
        logger.info("Closing all connections")

        # Close Supabase connections
        self.close_supabase_connections()

        # Close Weaviate connections
        self.close_weaviate_connections()

        # Close other connections
        for key, conn in self._other_connections.items():
            try:
                if hasattr(conn, 'close') and callable(getattr(conn, 'close')):
                    logger.info(f"Closing connection: {key}")
                    conn.close()
            except Exception as e:
                logger.error(f"Error closing connection {key}: {str(e)}")

        # Clear the dictionary
        self._other_connections.clear()

        # Final cleanup of any remaining HTTP clients
        try:
            # Clean up any httpx clients
            import httpx
            import importlib

            # Try to reload httpx to ensure we have the latest state
            importlib.reload(httpx)

            # Close any default clients
            if hasattr(httpx, 'get_async_client'):
                client = httpx.get_async_client()
                if client and hasattr(client, 'aclose'):
                    import asyncio
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            loop.create_task(client.aclose())
                        else:
                            loop.run_until_complete(client.aclose())
                    except Exception:
                        pass

            if hasattr(httpx, 'get_client'):
                client = httpx.get_client()
                if client and hasattr(client, 'close'):
                    client.close()
        except Exception as http_e:
            logger.error(f"Error in final HTTP client cleanup: {str(http_e)}")

        # Force garbage collection to clean up any remaining resources
        import gc
        gc.collect()

    @contextmanager
    def supabase_client(self, key_type: str = "default"):
        """
        Context manager for Supabase client.

        Args:
            key_type: Type of key to use ('default' or 'service')

        Yields:
            Supabase client
        """
        client = self.get_supabase_client(key_type)
        try:
            yield client
        finally:
            # We don't close the client here as it's managed by the pool
            pass

    @contextmanager
    def weaviate_client(self, client_id: str = "default"):
        """
        Context manager for Weaviate client.

        Args:
            client_id: Identifier for the client

        Yields:
            Weaviate client
        """
        client = self.get_weaviate_client(client_id)
        try:
            yield client
        finally:
            # We don't close the client here as it's managed by the pool
            pass

# Create a singleton instance
connection_manager = ConnectionManager()
