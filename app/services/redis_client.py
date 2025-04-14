import requests
from typing import Any, Dict, List, Optional
from config.config import settings

class UpstashRedisClient:
    """Client for Upstash Redis REST API"""

    def __init__(self, url: str, token: str):
        # Remove trailing slash if present
        self.url = url.rstrip('/')
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

    def _make_request(self, endpoint: str, body: Any = None) -> Any:
        """Make a request to the Upstash Redis REST API"""
        response = requests.post(
            f"{self.url}/{endpoint}",
            headers=self.headers,
            json=body
        )

        if response.status_code != 200:
            raise Exception(f"Error from Upstash Redis: {response.text}")

        result = response.json()
        if "error" in result and result["error"]:
            raise Exception(f"Redis error: {result['error']}")

        return result.get("result")

    def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """Set a key-value pair in Redis"""
        if ex is not None:
            return self._make_request(f"set/{key}", {"ex": ex, "value": value}) == "OK"
        else:
            return self._make_request(f"set/{key}", value) == "OK"

    def get(self, key: str) -> Optional[str]:
        """Get a value from Redis by key"""
        return self._make_request(f"get/{key}")

    def delete(self, key: str) -> int:
        """Delete a key from Redis"""
        return self._make_request(f"del/{key}")

    def lpush(self, key: str, *values: str) -> int:
        """Push values to the head of a list"""
        return self._make_request(f"lpush/{key}", list(values))

    def rpush(self, key: str, *values: str) -> int:
        """Push values to the tail of a list"""
        return self._make_request(f"rpush/{key}", list(values))

    def lpop(self, key: str) -> Optional[str]:
        """Pop a value from the head of a list"""
        return self._make_request(f"lpop/{key}")

    def rpop(self, key: str) -> Optional[str]:
        """Pop a value from the tail of a list"""
        return self._make_request(f"rpop/{key}")

    def lrange(self, key: str, start: int, end: int) -> List[str]:
        """Get a range of values from a list"""
        return self._make_request(f"lrange/{key}/{start}/{end}")

    def hset(self, key: str, field: str, value: str) -> int:
        """Set a field in a hash"""
        return self._make_request(f"hset/{key}/{field}", value)

    def hget(self, key: str, field: str) -> Optional[str]:
        """Get a field from a hash"""
        return self._make_request(f"hget/{key}/{field}")

    def hgetall(self, key: str) -> Dict[str, str]:
        """Get all fields and values from a hash"""
        result = self._make_request(f"hgetall/{key}")
        if not result or not isinstance(result, list):
            return {}
        # Convert flat list to dictionary
        return {result[i]: result[i+1] for i in range(0, len(result), 2)}

    def expire(self, key: str, seconds: int) -> int:
        """Set a key's time to live in seconds"""
        return self._make_request(f"expire/{key}/{seconds}")

    def ttl(self, key: str) -> int:
        """Get the time to live for a key in seconds"""
        return self._make_request(f"ttl/{key}")

# Create a singleton instance if Upstash Redis is configured
upstash_redis = None
if settings.USE_UPSTASH_REDIS:
    upstash_redis = UpstashRedisClient(
        url=settings.UPSTASH_REDIS_REST_URL,
        token=settings.UPSTASH_REDIS_REST_TOKEN
    )
