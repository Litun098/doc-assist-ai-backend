import weaviate
import sys
import os

# For newer Weaviate client
try:
    from weaviate.classes.init import Auth
    USING_NEW_CLIENT = True
except ImportError:
    USING_NEW_CLIENT = False

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.config import settings

def init_weaviate():
    """Initialize Weaviate schema"""
    if not settings.WEAVIATE_URL or not settings.WEAVIATE_API_KEY:
        print("Weaviate URL or API key not set. Skipping initialization.")
        return

    # Initialize Weaviate client
    if USING_NEW_CLIENT:
        try:
            from weaviate.classes.init import AdditionalConfig, Timeout

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
        except ImportError:
            # Older version of weaviate-client that doesn't have AdditionalConfig
            # Make sure we're using the REST endpoint, not gRPC
            weaviate_url = settings.WEAVIATE_URL
            if not weaviate_url.startswith("https://"):
                weaviate_url = f"https://{weaviate_url}"

            print(f"Connecting to Weaviate at {weaviate_url}")
            client = weaviate.connect_to_weaviate_cloud(
                cluster_url=weaviate_url,
                auth_credentials=Auth.api_key(settings.WEAVIATE_API_KEY),
                skip_init_checks=True,  # Skip gRPC health checks
            )
    else:
        client = weaviate.Client(
            url=settings.WEAVIATE_URL,
            auth_client_secret=weaviate.AuthApiKey(api_key=settings.WEAVIATE_API_KEY)
        )

    # Check if collection exists - handle both v3 and v4 client APIs
    collection_exists = False
    try:
        # Try v4 API first
        print("Checking if collection exists using v4 API...")
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

            print(f"Found collections: {collection_names}")
            collection_exists = settings.LLAMAINDEX_INDEX_NAME in collection_names
        except Exception as e:
            print(f"Error listing collections with v4 API: {str(e)}")
            collection_exists = False
    except AttributeError:
        # Fall back to v3 API
        print("Falling back to v3 API...")
        try:
            schema = client.schema.get()
            classes = [c["class"] for c in schema["classes"]] if "classes" in schema else []
            print(f"Found classes: {classes}")
            collection_exists = settings.LLAMAINDEX_INDEX_NAME in classes
        except Exception as e:
            print(f"Error getting schema with v3 API: {str(e)}")
            collection_exists = False

    # Create collection if it doesn't exist
    if not collection_exists:
        print(f"Creating {settings.LLAMAINDEX_INDEX_NAME} collection in Weaviate...")

        try:
            # Try v4 API first
            print("Attempting to create collection using v4 API...")
            try:
                # Define properties with correct data types for v4
                properties = [
                    {
                        "name": "content",
                        "data_type": ["text"],
                        "description": "The text content of the chunk"
                    },
                    {
                        "name": "file_id",
                        "data_type": ["string"],
                        "description": "The ID of the file this chunk belongs to"
                    },
                    {
                        "name": "user_id",
                        "data_type": ["string"],
                        "description": "The ID of the user who owns this document"
                    },
                    {
                        "name": "page_number",
                        "data_type": ["int"],
                        "description": "The page number this chunk is from"
                    },
                    {
                        "name": "chunk_index",
                        "data_type": ["int"],
                        "description": "The index of this chunk within the file"
                    },
                    {
                        "name": "chunking_strategy",
                        "data_type": ["string"],
                        "description": "The chunking strategy used (fixed_size or topic_based)"
                    },
                    {
                        "name": "heading",
                        "data_type": ["text"],
                        "description": "The heading or title of the section (for topic-based chunks)"
                    },
                    {
                        "name": "metadata",
                        "data_type": ["text"],
                        "description": "Additional metadata about the chunk"
                    }
                ]

                # Try to create the collection with correct v4 API format
                try:
                    # Import the correct data types for v4 API
                    from weaviate.classes.config import Property, DataType

                    properties_v4 = [
                        Property(name="content", data_type=DataType.TEXT, description="The text content of the chunk"),
                        Property(name="file_id", data_type=DataType.TEXT, description="The ID of the file this chunk belongs to"),
                        Property(name="user_id", data_type=DataType.TEXT, description="The ID of the user who owns this document"),
                        Property(name="page_number", data_type=DataType.INT, description="The page number this chunk is from"),
                        Property(name="chunk_index", data_type=DataType.INT, description="The index of this chunk within the file"),
                        Property(name="chunking_strategy", data_type=DataType.TEXT, description="The chunking strategy used"),
                        Property(name="heading", data_type=DataType.TEXT, description="The heading or title of the section"),
                        Property(name="metadata", data_type=DataType.TEXT, description="Additional metadata about the chunk")
                    ]

                    client.collections.create(
                        name=settings.LLAMAINDEX_INDEX_NAME,
                        description="A collection of document chunks for retrieval",
                        properties=properties_v4
                    )
                except ImportError:
                    # Fallback to simple creation without properties
                    client.collections.create(
                        name=settings.LLAMAINDEX_INDEX_NAME,
                        description="A collection of document chunks for retrieval"
                    )
                print(f"Successfully created collection {settings.LLAMAINDEX_INDEX_NAME} using v4 API")
            except Exception as e:
                print(f"Error creating collection with v4 API: {str(e)}")
                # Try simple collection creation without properties as fallback
                try:
                    print("Trying simple collection creation...")
                    client.collections.create(
                        name=settings.LLAMAINDEX_INDEX_NAME,
                        description="A collection of document chunks for retrieval"
                    )
                    print(f"Successfully created collection {settings.LLAMAINDEX_INDEX_NAME} using simple creation")
                except Exception as simple_e:
                    print(f"Error with simple collection creation: {str(simple_e)}")
                    raise
        except AttributeError:
            # Fall back to v3 API
            print("Falling back to v3 API for collection creation...")
            try:
                class_obj = {
                    "class": settings.LLAMAINDEX_INDEX_NAME,
                    "description": "A collection of document chunks for retrieval",
                    "vectorizer": "none",  # We'll provide our own vectors
                    "properties": [
                        {
                            "name": "content",
                            "dataType": ["text"],
                            "description": "The text content of the chunk"
                        },
                        {
                            "name": "file_id",
                            "dataType": ["string"],
                            "description": "The ID of the file this chunk belongs to"
                        },
                        {
                            "name": "user_id",
                            "dataType": ["string"],
                            "description": "The ID of the user who owns this document"
                        },
                        {
                            "name": "page_number",
                            "dataType": ["int"],
                            "description": "The page number this chunk is from"
                        },
                        {
                            "name": "chunk_index",
                            "dataType": ["int"],
                            "description": "The index of this chunk within the file"
                        },
                        {
                            "name": "chunking_strategy",
                            "dataType": ["string"],
                            "description": "The chunking strategy used (fixed_size or topic_based)"
                        },
                        {
                            "name": "heading",
                            "dataType": ["text"],
                            "description": "The heading or title of the section (for topic-based chunks)"
                        },
                        {
                            "name": "metadata",
                            "dataType": ["text"],
                            "description": "Additional metadata about the chunk"
                        }
                    ]
                }
                client.schema.create_class(class_obj)
                print(f"Successfully created class {settings.LLAMAINDEX_INDEX_NAME} using v3 API")
            except Exception as e:
                print(f"Error creating class with v3 API: {str(e)}")
                raise

    else:
        print(f"{settings.LLAMAINDEX_INDEX_NAME} collection already exists.")

    # Make sure to close the connection properly
    try:
        client.close()
        print("Weaviate connection closed properly")
    except Exception as e:
        print(f"Error closing Weaviate connection: {str(e)}")

if __name__ == "__main__":
    init_weaviate()
