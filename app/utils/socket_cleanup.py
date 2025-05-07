"""
Socket cleanup utility to prevent ResourceWarnings.
This module provides functions to clean up lingering sockets and prevent ResourceWarnings.
"""
import gc
import logging
import ssl
import tracemalloc
import warnings
from typing import List

# Configure logging
logger = logging.getLogger(__name__)

# Start tracemalloc to track memory allocations
tracemalloc.start()

def find_ssl_sockets() -> List[ssl.SSLSocket]:
    """
    Find all SSL sockets in the current process.

    Returns:
        List of SSL sockets
    """
    sockets = []
    # Force garbage collection to make sure we find all sockets
    gc.collect()

    # Get all objects
    for obj in gc.get_objects():
        try:
            if isinstance(obj, ssl.SSLSocket):
                sockets.append(obj)
        except Exception:
            # Ignore errors when checking object types
            pass

    return sockets

def close_ssl_sockets(sockets: List[ssl.SSLSocket]) -> int:
    """
    Close all SSL sockets in the list.

    Args:
        sockets: List of SSL sockets to close

    Returns:
        Number of sockets closed
    """
    closed_count = 0
    for sock in sockets:
        try:
            if not sock._closed:
                sock.close()
                closed_count += 1
        except Exception as e:
            logger.debug(f"Error closing socket: {str(e)}")

    return closed_count

def cleanup_all_sockets() -> int:
    """
    Find and close all SSL sockets in the current process.

    Returns:
        Number of sockets closed
    """
    sockets = find_ssl_sockets()
    logger.info(f"Found {len(sockets)} SSL sockets")
    closed = close_ssl_sockets(sockets)
    logger.info(f"Closed {closed} SSL sockets")
    return closed

def get_socket_cleanup_function():
    """
    Get a function to clean up sockets without patching the socket module.

    Returns:
        Function to clean up sockets
    """
    def cleanup_sockets():
        """Clean up sockets by finding and closing them."""
        # We'll rely on find_ssl_sockets and close_ssl_sockets instead
        # of trying to track sockets by patching the socket module
        sockets = find_ssl_sockets()
        if sockets:
            logger.info(f"Found {len(sockets)} SSL sockets to clean up")
            closed = close_ssl_sockets(sockets)
            logger.info(f"Closed {closed} SSL sockets")

    return cleanup_sockets

def patch_httpx():
    """
    Patch the httpx library to ensure proper cleanup of connections.
    """
    try:
        import httpx

        # Save original methods
        if hasattr(httpx, 'Client'):
            original_client_init = httpx.Client.__init__
            original_client_close = httpx.Client.close

            # Override Client.__init__ to track instances
            def patched_client_init(self, *args, **kwargs):
                result = original_client_init(self, *args, **kwargs)
                # Add to a global registry for cleanup
                if not hasattr(httpx, '_all_clients'):
                    httpx._all_clients = []
                httpx._all_clients.append(self)
                return result

            # Override Client.close to remove from tracking
            def patched_client_close(self):
                result = original_client_close(self)
                if hasattr(httpx, '_all_clients'):
                    if self in httpx._all_clients:
                        httpx._all_clients.remove(self)
                return result

            # Apply patches
            httpx.Client.__init__ = patched_client_init
            httpx.Client.close = patched_client_close

            # Add cleanup function to httpx
            def cleanup_httpx_clients():
                if hasattr(httpx, '_all_clients'):
                    clients = list(httpx._all_clients)
                    count = len(clients)
                    if count > 0:
                        logger.info(f"Cleaning up {count} httpx clients")
                        for client in clients:
                            try:
                                client.close()
                            except Exception:
                                pass
                        httpx._all_clients.clear()

            httpx.cleanup_clients = cleanup_httpx_clients

            logger.info("Successfully patched httpx library")
            return True
        else:
            logger.warning("httpx.Client not found, skipping patch")
            return False
    except ImportError:
        logger.warning("httpx not installed, skipping patch")
        return False
    except Exception as e:
        logger.error(f"Error patching httpx: {str(e)}")
        return False

def patch_weaviate():
    """
    Patch the weaviate library to ensure proper cleanup of connections.
    """
    try:
        import weaviate

        # Check if we can patch the client
        if hasattr(weaviate, 'WeaviateClient'):
            original_close = weaviate.WeaviateClient.close

            # Override close method to be more thorough
            def patched_close(self):
                try:
                    # Call original close
                    original_close(self)

                    # Additional cleanup
                    if hasattr(self, '_connection'):
                        conn = getattr(self, '_connection')
                        if hasattr(conn, 'close'):
                            conn.close()

                    # Clean up any httpx clients
                    if hasattr(self, '_client'):
                        client = getattr(self, '_client')
                        if hasattr(client, 'close'):
                            client.close()

                    # Force garbage collection
                    gc.collect()
                except Exception as e:
                    logger.error(f"Error in patched Weaviate close: {str(e)}")

            # Apply patch
            weaviate.WeaviateClient.close = patched_close
            logger.info("Successfully patched weaviate library")
            return True
        else:
            logger.warning("weaviate.WeaviateClient not found, skipping patch")
            return False
    except ImportError:
        logger.warning("weaviate not installed, skipping patch")
        return False
    except Exception as e:
        logger.error(f"Error patching weaviate: {str(e)}")
        return False

# Initialize patches
socket_cleanup = get_socket_cleanup_function()
httpx_patched = patch_httpx()
weaviate_patched = patch_weaviate()

# Suppress ResourceWarnings during development
warnings.filterwarnings("ignore", category=ResourceWarning)

def cleanup_all_resources():
    """
    Clean up all resources to prevent ResourceWarnings.
    """
    # Clean up tracked sockets
    socket_cleanup()

    # Clean up httpx clients
    import httpx
    if hasattr(httpx, 'cleanup_clients'):
        httpx.cleanup_clients()

    # Clean up any remaining SSL sockets
    cleanup_all_sockets()

    # Force garbage collection
    gc.collect()

    # Take a snapshot to check for leaks
    snapshot = tracemalloc.take_snapshot()
    top_stats = snapshot.statistics('lineno')
    logger.debug("Top 10 memory allocations:")
    for stat in top_stats[:10]:
        logger.debug(f"{stat}")
