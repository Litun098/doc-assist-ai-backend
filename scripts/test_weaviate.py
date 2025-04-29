import sys
import os
import weaviate

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.config import settings

def test_weaviate_connection():
    """Test connection to Weaviate"""
    print("Testing Weaviate connection...")

    if not settings.WEAVIATE_URL or not settings.WEAVIATE_API_KEY:
        print("Weaviate URL or API key not set. Please check your .env file.")
        return False

    try:
        # Try the new Weaviate client format first
        try:
            from weaviate.classes.init import Auth, AdditionalConfig, Timeout
            print("Using new Weaviate client format...")
            # Make sure we're using the REST endpoint, not gRPC
            weaviate_url = settings.WEAVIATE_URL
            if not weaviate_url.startswith("https://"):
                weaviate_url = f"https://{weaviate_url}"

            print(f"Connecting to Weaviate at {weaviate_url}")
            client = weaviate.connect_to_weaviate_cloud(
                cluster_url=weaviate_url,
                auth_credentials=Auth.api_key(settings.WEAVIATE_API_KEY),
                skip_init_checks=True,  # Skip gRPC health checks
                additional_config=AdditionalConfig(
                    timeout=Timeout(init=60)  # Increase timeout to 60 seconds
                )
            )
        except (ImportError, AttributeError):
            # Fall back to the older client format
            print("Using legacy Weaviate client format...")
            client = weaviate.Client(
                url=settings.WEAVIATE_URL,
                auth_client_secret=weaviate.AuthApiKey(api_key=settings.WEAVIATE_API_KEY)
            )

        # Check if client is ready
        print("✅ Weaviate connection successful!")

        # Get schema - handle v4 client API
        try:
            # Try v4 API to list collections
            try:
                collections = client.collections.list_all()
                collection_names = []

                # Handle different return types
                for collection in collections:
                    if hasattr(collection, 'name'):
                        collection_names.append(collection.name)
                    elif isinstance(collection, str):
                        collection_names.append(collection)
                    elif isinstance(collection, dict) and 'name' in collection:
                        collection_names.append(collection['name'])

                print(f"Available collections: {', '.join(collection_names) if collection_names else 'None'}")

                # Check if DocumentChunks collection exists
                if settings.LLAMAINDEX_INDEX_NAME in collection_names:
                    print(f"✅ {settings.LLAMAINDEX_INDEX_NAME} collection exists")
                else:
                    print(f"❌ {settings.LLAMAINDEX_INDEX_NAME} collection does not exist. Run scripts/init_weaviate.py to create it.")

                # Close the connection properly
                try:
                    client.close()
                    print("Weaviate connection closed properly")
                except Exception as close_error:
                    print(f"Warning: Could not close Weaviate connection: {str(close_error)}")

                return True
            except Exception as e:
                print(f"Error listing collections: {str(e)}")

                # Try alternative approach for v4 API
                try:
                    # Some versions might have different methods
                    print("Trying alternative approach...")
                    meta = client.get_meta()
                    print(f"Weaviate version: {meta.get('version', 'unknown')}")

                    # Close the connection properly
                    try:
                        client.close()
                        print("Weaviate connection closed properly")
                    except Exception as close_error:
                        print(f"Warning: Could not close Weaviate connection: {str(close_error)}")

                    return True
                except Exception as alt_e:
                    print(f"Error with alternative approach: {str(alt_e)}")
                    raise
        except Exception as e:
            print(f"❌ Error connecting to Weaviate: {str(e)}")

            # Try to close the connection anyway
            try:
                client.close()
            except:
                pass

            return False

    except Exception as e:
        print(f"❌ Error connecting to Weaviate: {str(e)}")
        print("\nTroubleshooting tips:")
        print("1. Check that your WEAVIATE_URL is correct")
        print("2. Check that your WEAVIATE_API_KEY is correct")
        print("3. Make sure you have internet access and can reach the Weaviate API")
        print("4. Verify that your Weaviate instance is active")
        return False

if __name__ == "__main__":
    test_weaviate_connection()
