import sys
import os
from openai import OpenAI

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.config import settings

def test_openai_connection():
    """Test connection to OpenAI API"""
    print("Testing OpenAI API connection...")
    
    if not settings.OPENAI_API_KEY:
        print("OpenAI API key not set. Please check your .env file.")
        return False
    
    try:
        # Initialize OpenAI client
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        
        # Test with a simple completion
        print("Sending test request to OpenAI API...")
        response = client.chat.completions.create(
            model=settings.DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello, are you working?"}
            ],
            max_tokens=50
        )
        
        # Print the response
        print(f"✅ OpenAI API response: {response.choices[0].message.content}")
        
        # Test embeddings
        print("\nTesting embeddings API...")
        embedding_response = client.embeddings.create(
            model=settings.EMBEDDING_MODEL,
            input="This is a test document for embeddings."
        )
        
        # Check if we got embeddings
        if embedding_response.data and len(embedding_response.data) > 0:
            embedding_length = len(embedding_response.data[0].embedding)
            print(f"✅ Embeddings API working. Vector dimension: {embedding_length}")
        else:
            print("❌ Failed to get embeddings")
            return False
        
        print("\nOpenAI API connection test successful!")
        return True
    
    except Exception as e:
        print(f"❌ Error connecting to OpenAI API: {str(e)}")
        print("\nTroubleshooting tips:")
        print("1. Check that your OPENAI_API_KEY is correct")
        print("2. Make sure you have internet access")
        print("3. Check if your OpenAI account has sufficient credits")
        print("4. Verify that the requested model is available for your account")
        return False

if __name__ == "__main__":
    test_openai_connection()
