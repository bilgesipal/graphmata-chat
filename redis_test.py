import json
import redis
from typing import Dict, List, Optional, Union, Any
import redis.asyncio as aioredis
from src.config.config import AppConfig

from src.utils import redis_manager

async def get_redis_client():
    try:
        client = aioredis.Redis(
            host=AppConfig.REDIS_HOST,
            port=int(AppConfig.REDIS_PORT),
            db=int(AppConfig.REDIS_DB),
            decode_responses=True
        )

        await client.ping()
        print("Connected to Redis")
        return client
    except redis.ConnectionError as e:
        print(f"Redis connection failed: {e}")
        raise


class RedisConversationRetriever:
    """
    A class to retrieve conversation data from Redis cache using a specific key pattern.
    """

    def __init__(
            self,
            key_prefix: str = "prometa_ai:conversation:"
    ):
        self.redis_client = redis.Redis(
            host=AppConfig.REDIS_HOST,
            port=int(AppConfig.REDIS_PORT),
            db=int(AppConfig.REDIS_DB),
            decode_responses=True
        )
        self.key_prefix = key_prefix

    def get_conversation(self, user_email: str) -> Optional[Dict[str, Any]]:
        """ Retrieve a conversation for a specific user.       """
        key = f"{self.key_prefix}{user_email}"
        try:
            data = self.redis_client.get(key)
            if data:
                return json.loads(data)
            return None
        except json.JSONDecodeError:
            print(f"Error decoding JSON data for key: {key}")
            return None
        except redis.RedisError as e:
            print(f"Redis error when retrieving key {key}: {e}")
            return None



# Example usage
if __name__ == "__main__":
    retriever = RedisConversationRetriever()

    # Example: Get conversation for a specific user
    conversation = retriever.get_conversation("session_926_prometa@bizigo.com")
    if conversation:
        print(f"Found conversation: {conversation} ")
    else:
        print("No conversation found")

