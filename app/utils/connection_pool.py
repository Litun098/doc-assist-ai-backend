"""
Connection pool for managing HTTP and database connections.
This utility helps prevent ResourceWarnings by properly managing connection lifecycles.
"""
import logging
import atexit
import gc
import ssl
import weakref
from typing import Dict, Any, Optional, List
from contextlib import contextmanager

# Configure logging
logger = logging.getLogger(__name__)

class ConnectionPool:
    """
    Connection pool for managing HTTP and database connections.
    """
    def __init__(self):
        """Initialize the connection pool."""
        self._supabase_clients = {}
        self._weaviate_clients = {}
        self._httpx_clients = []
        self._ssl_sockets = weakref.WeakSet()
        
        # Register cleanup on exit
        atexit.register(self.cleanup_all)
    
    def register_supabase_client(self, client, key_type="default"):
        """
        Register a Supabase client with the pool.
        
        Args:
            client: Supabase client
            key_type: Type of key used ('default' or 'service')
        """
        self._supabase_clients[key_type] = client
        logger.debug(f"Registered Supabase client with key type: {key_type}")
        
        # Patch the client's HTTP client if possible
        try:
            if hasattr(client, '_client'):
                httpx_client = getattr(client, '_client')
                self.register_httpx_client(httpx_client)
        except Exception as e:
            logger.debug(f"Error registering Supabase client's HTTP client: {str(e)}")
    
    def register_weaviate_client(self, client, client_id="default"):
        """
        Register a Weaviate client with the pool.
        
        Args:
            client: Weaviate client
            client_id: Identifier for the client
        """
        self._weaviate_clients[client_id] = client
        logger.debug(f"Registered Weaviate client with ID: {client_id}")
        
        # Patch the client's HTTP client if possible
        try:
            if hasattr(client, '_client'):
                httpx_client = getattr(client, '_client')
                self.register_httpx_client(httpx_client)
        except Exception as e:
            logger.debug(f"Error registering Weaviate client's HTTP client: {str(e)}")
    
    def register_httpx_client(self, client):
        """
        Register an HTTPX client with the pool.
        
        Args:
            client: HTTPX client
        """
        if client not in self._httpx_clients:
            self._httpx_clients.append(client)
            logger.debug(f"Registered HTTPX client: {id(client)}")
    
    def register_ssl_socket(self, socket):
        """
        Register an SSL socket with the pool.
        
        Args:
            socket: SSL socket
        """
        self._ssl_sockets.add(socket)
        logger.debug(f"Registered SSL socket: {id(socket)}")
    
    def cleanup_supabase_clients(self):
        """Clean up all Supabase clients."""
        for key, client in list(self._supabase_clients.items()):
            try:
                # Supabase doesn't have an explicit close method
                # But we can clean up its HTTP client
                if hasattr(client, '_client'):
                    httpx_client = getattr(client, '_client')
                    if hasattr(httpx_client, 'close'):
                        httpx_client.close()
                
                # Remove from pool
                del self._supabase_clients[key]
                logger.debug(f"Cleaned up Supabase client with key type: {key}")
            except Exception as e:
                logger.error(f"Error cleaning up Supabase client: {str(e)}")
    
    def cleanup_weaviate_clients(self):
        """Clean up all Weaviate clients."""
        for client_id, client in list(self._weaviate_clients.items()):
            try:
                # Close the client if it has a close method
                if hasattr(client, 'close'):
                    client.close()
                
                # Remove from pool
                del self._weaviate_clients[client_id]
                logger.debug(f"Cleaned up Weaviate client with ID: {client_id}")
            except Exception as e:
                logger.error(f"Error cleaning up Weaviate client: {str(e)}")
    
    def cleanup_httpx_clients(self):
        """Clean up all HTTPX clients."""
        for client in list(self._httpx_clients):
            try:
                # Close the client if it has a close method
                if hasattr(client, 'close'):
                    client.close()
                
                # Remove from pool
                self._httpx_clients.remove(client)
                logger.debug(f"Cleaned up HTTPX client: {id(client)}")
            except Exception as e:
                logger.error(f"Error cleaning up HTTPX client: {str(e)}")
    
    def cleanup_ssl_sockets(self):
        """Clean up all SSL sockets."""
        count = 0
        for socket in list(self._ssl_sockets):
            try:
                if not socket._closed:
                    socket.close()
                    count += 1
            except Exception:
                pass
        
        if count > 0:
            logger.debug(f"Cleaned up {count} SSL sockets")
    
    def cleanup_all(self):
        """Clean up all connections."""
        logger.info("Cleaning up all connections")
        self.cleanup_supabase_clients()
        self.cleanup_weaviate_clients()
        self.cleanup_httpx_clients()
        self.cleanup_ssl_sockets()
        
        # Force garbage collection
        gc.collect()
    
    @contextmanager
    def supabase_client(self, key_type="default"):
        """
        Context manager for Supabase client.
        
        Args:
            key_type: Type of key to use ('default' or 'service')
        
        Yields:
            Supabase client
        """
        from supabase import create_client
        from config.config import settings
        
        # Create client
        if key_type == "service" and settings.SUPABASE_SERVICE_KEY:
            client = create_client(
                supabase_url=settings.SUPABASE_URL,
                supabase_key=settings.SUPABASE_SERVICE_KEY
            )
        else:
            client = create_client(
                supabase_url=settings.SUPABASE_URL,
                supabase_key=settings.SUPABASE_KEY
            )
        
        # Register client
        self.register_supabase_client(client, key_type)
        
        try:
            yield client
        finally:
            # We don't close the client here as it's managed by the pool
            pass

# Create a singleton instance
connection_pool = ConnectionPool()

# Monkey patch SSL socket creation to track sockets
original_ssl_socket = ssl.SSLSocket.__init__

def patched_ssl_socket_init(self, *args, **kwargs):
    """Patched SSL socket initialization to track sockets."""
    original_ssl_socket(self, *args, **kwargs)
    connection_pool.register_ssl_socket(self)

# Apply the patch
ssl.SSLSocket.__init__ = patched_ssl_socket_init

# Monkey patch HTTPX client creation if available
try:
    import httpx
    
    original_httpx_client_init = httpx.Client.__init__
    
    def patched_httpx_client_init(self, *args, **kwargs):
        """Patched HTTPX client initialization to track clients."""
        original_httpx_client_init(self, *args, **kwargs)
        connection_pool.register_httpx_client(self)
    
    # Apply the patch
    httpx.Client.__init__ = patched_httpx_client_init
    
    logger.debug("Successfully patched HTTPX client")
except ImportError:
    logger.debug("HTTPX not available, skipping patch")
except Exception as e:
    logger.error(f"Error patching HTTPX client: {str(e)}")

# Register cleanup on exit
atexit.register(connection_pool.cleanup_all)
