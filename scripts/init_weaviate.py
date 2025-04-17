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
        client = weaviate.connect_to_weaviate_cloud(
            cluster_url=settings.WEAVIATE_URL,
            auth_credentials=Auth.api_key(settings.WEAVIATE_API_KEY),
        )
    else:
        client = weaviate.Client(
            url=settings.WEAVIATE_URL,
            auth_client_secret=weaviate.AuthApiKey(api_key=settings.WEAVIATE_API_KEY)
        )

    # Check if schema exists
    schema = client.schema.get()
    classes = [c["class"] for c in schema["classes"]] if "classes" in schema else []

    # Create schema if it doesn't exist
    if "DocumentChunk" not in classes:
        print("Creating DocumentChunk class in Weaviate...")
        class_obj = {
            "class": "DocumentChunk",
            "description": "A chunk of text from a document",
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
                    "name": "is_first_in_section",
                    "dataType": ["boolean"],
                    "description": "Whether this chunk is the first in its section"
                },
                {
                    "name": "metadata",
                    "dataType": ["text"],
                    "description": "Additional metadata about the chunk"
                }
            ]
        }
        client.schema.create_class(class_obj)
        print("DocumentChunk class created successfully.")
    else:
        print("DocumentChunk class already exists.")

if __name__ == "__main__":
    init_weaviate()
