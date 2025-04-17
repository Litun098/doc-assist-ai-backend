import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.config import settings

def test_redis_config():
    """Test Redis configuration"""
    print("Testing Redis configuration...")

    # Check if Upstash Redis is configured
    if settings.USE_UPSTASH_REDIS:
        print("✅ Upstash Redis REST API is configured:")
        print(f"   URL: {settings.UPSTASH_REDIS_REST_URL}")
        print(f"   Token: {settings.UPSTASH_REDIS_REST_TOKEN[:5]}...{settings.UPSTASH_REDIS_REST_TOKEN[-5:]}")
        print(f"   Port: {settings.UPSTASH_REDIS_PORT}")
    else:
        print("❌ Upstash Redis REST API is not configured")

    # Check Redis URL
    print(f"\nRedis URL: {settings.REDIS_URL}")

    # Check Celery SSL configuration
    if settings.CELERY_BROKER_USE_SSL:
        print("\n✅ Celery SSL configuration is enabled")
    else:
        print("\n❌ Celery SSL configuration is not enabled")

    print("\nRecommendations:")
    if settings.USE_UPSTASH_REDIS:
        if not settings.REDIS_URL.startswith("rediss://"):
            print("- For Upstash Redis with Celery, consider using a rediss:// URL with ssl_cert_reqs=CERT_NONE")
            print("  Example: rediss://:your-token@your-endpoint.upstash.io:443?ssl_cert_reqs=CERT_NONE")
    else:
        print("- For local development, make sure Redis is installed and running")
        print("- For Upstash Redis, set UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN in .env")

if __name__ == "__main__":
    test_redis_config()
