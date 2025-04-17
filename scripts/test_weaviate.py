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
            from weaviate.classes.init import Auth
            print("Using new Weaviate client format...")
            client = weaviate.connect_to_weaviate_cloud(
                cluster_url=settings.WEAVIATE_URL,
                auth_credentials=Auth.api_key(settings.WEAVIATE_API_KEY),
            )
        except (ImportError, AttributeError):
            # Fall back to the older client format
            print("Using legacy Weaviate client format...")
            client = weaviate.Client(
                url=settings.WEAVIATE_URL,
                auth_client_secret=weaviate.AuthApiKey(api_key=settings.WEAVIATE_API_KEY)
            )
        
        # Check if client is ready
        if client.is_ready():
            print("✅ Weaviate connection successful!")
            
            # Get schema
            schema = client.schema.get()
            classes = [c["class"] for c in schema["classes"]] if "classes" in schema else []
            print(f"Available classes: {', '.join(classes) if classes else 'None'}")
            
            # Check if DocumentChunk class exists
            if "DocumentChunk" in classes:
                print("✅ DocumentChunk class exists")
            else:
                print("❌ DocumentChunk class does not exist. Run scripts/init_weaviate.py to create it.")
            
            return True
        else:
            print("❌ Weaviate is not ready")
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
