import json

from typing import Dict
from fastapi import APIRouter, Request, status
from src.config.config import AppConfig
from src.utils import redis_manager

router = APIRouter(tags=["Health"])



@router.get("/api/v1/healthcheck",
            status_code=status.HTTP_200_OK,
            summary="Health Check Endpoint",
            description="This is the health endpoint, you can check the health of the services with it.",
            )

def healthcheck():
    return {"status": "ok"}



@router.get(
    "/api/v1/healthcheck/pubsub",
    summary="Health Check Endpoint for Pub/Sub",
    description="This is the health endpoint, you can check the health of the services with it.",
)
async def get_redis_pubsub():
    try:
        payload = {"state": {"save": "true", "dump": "false"}}
        await redis_manager.publish("chat-state-update", json.dumps(payload))
        return {"status": "published", "payload": payload}
    except Exception as e:
        return {"error": str(e)}


@router.get(
    "/api/v1/healthcheck/redis_conn",
    summary="Health Check Endpoint",
    description="This is the health endpoint, you can check the health of the services with it.",
)
async def get_redis_client():
    try:
        await redis_manager.ping()
        return {"status": "connected"}
    except Exception as e:
        return {"error": str(e)}




@router.get(
    "/api/v1/healthcheck/keys",
    summary="Health Check Endpoint",
    description="This is the health endpoint, you can check passwords.",
)
async def health_ready_keys() -> Dict[str, str]:
        try:
            openai_key = AppConfig.OPENAI_API_KEY
            openai_key_short = openai_key[:6] + "..." if openai_key else "Missing"
        except Exception as e:
            openai_key_short = f"Error: {str(e)}"

        return {
            "status": "ok",
            "openai_key": openai_key_short,
            "redis_host": AppConfig.REDIS_HOST,
            "redis_port": AppConfig.REDIS_PORT,
        }
