#This file is part of the GraphMata project.
#Trademark (c) 2025 Prometa AI.

from dotenv import load_dotenv

load_dotenv(override=True)

import os
import json

import redis.asyncio as aioredis


class AppConfig:
    """
    Configuration class to load environment variables for various services and models.

    Attributes:
        ENVIRONMENT (str): The current environment (default: "DEVELOPMENT").
        SERVICE_NAME (str): The name of the service (default: "ComplaintClassifierService").
        LOG_LEVEL (str): The log level for the application (default: "INFO").
    """

    ENVIRONMENT = os.getenv("ENVIRONMENT", "TEST")
    SERVICE_NAME = os.getenv("SERVICE_NAME", "CHAT_AGENT")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    NAMESPACE = os.getenv("NAMESPACE", "GraphMata")

    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB = int(os.getenv("REDIS_DB", "15"))
    # redis_client = aioredis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)

    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "sk-xxx")


    REDIS_LISTEN_CHAT = os.getenv("REDIS_LISTEN_CHAT", "chat-agent-trigger")
    REDIS_PUBLISH_CHAT = os.getenv("REDIS_PUBLISH_CHAT", "chat-state-update")
    REDIS_LOG = os.getenv("REDIS_LOG", "service_-logs")




