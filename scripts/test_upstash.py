import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.redis_client import UpstashRedisClient
from config.config import settings

def test_upstash_connection():
    """Test connection to Upstash Redis"""
    print("Testing Upstash Redis connection...")

    if not settings.UPSTASH_REDIS_REST_URL or not settings.UPSTASH_REDIS_REST_TOKEN:
        print("Upstash Redis is not configured. Please check your .env file.")
        return False

    try:
        # Create client
        client = UpstashRedisClient(
            url=settings.UPSTASH_REDIS_REST_URL,
            token=settings.UPSTASH_REDIS_REST_TOKEN
        )

        # Test basic operations
        print("Setting test key...")
        client.set("test_key", "Hello from AnyDocAI!")

        print("Getting test key...")
        value = client.get("test_key")
        print(f"Value: {value}")

        print("Setting hash...")
        client.hset("test_hash", "field1", "value1")
        client.hset("test_hash", "field2", "value2")

        print("Getting hash...")
        hash_value = client.hgetall("test_hash")
        print(f"Hash: {hash_value}")

        print("Pushing to list...")
        client.rpush("test_list", "item1", "item2", "item3")

        print("Getting list...")
        list_value = client.lrange("test_list", 0, -1)
        print(f"List: {list_value}")

        print("Cleaning up...")
        client.delete("test_key")
        client.delete("test_hash")
        client.delete("test_list")

        print("Upstash Redis connection test successful!")
        return True

    except Exception as e:
        print(f"Error connecting to Upstash Redis: {str(e)}")
        print("\nTroubleshooting tips:")
        print("1. Check that your UPSTASH_REDIS_REST_URL is correct (should be like https://your-db.upstash.io)")
        print("2. Check that your UPSTASH_REDIS_REST_TOKEN is correct")
        print("3. Make sure you have internet access and can reach the Upstash API")
        print("4. Verify that your Upstash Redis database is active in the Upstash dashboard")
        return False

if __name__ == "__main__":
    test_upstash_connection()
