# Import packages and modules used throughout the application
from .log import init_logging

logger = init_logging("hotel-service", file=False, stdout=True)

from .async_redis_manager import AsyncRedisManager

# Instantiate Redis manager
redis_manager = AsyncRedisManager()


__all__ = ["redis_manager", "logger"]