import json
import time
from types import SimpleNamespace
from typing import Any, Dict, Optional, List, Tuple

import openai
import redis.asyncio as aioredis

from src.utils import redis_manager, logger
from src.config.config import AppConfig

# Configure OpenAI
openai.api_key = AppConfig.OPENAI_API_KEY
MODEL_NAME = "gpt-4o-mini"
GATEWAY_STREAM = "gateway"

# Helper function to extract user session information from payload
def get_user_session(payload: Dict[str, Any]) -> Tuple[str, str, str]:
    user_id = payload["metadata"]["user_id"]
    session_id = payload["session_id"]
    return user_id, session_id, f"{user_id}_{session_id}"

# # Helper function to call the LLM with a prompt
# async def call_llm(prompt: str) -> str:
#     messages = [{"role": "user", "content": prompt}]
#     start = time.time()
#     response = openai.chat.completions.create(
#         model=MODEL_NAME,
#         messages=messages,
#         temperature=0.7,
#     )
#     logger.info(f"LLM call took {time.time() - start:.2f}s")
#     return response.choices[0].message.content


# Helper function to call the LLM with a prompt
async def call_llm(prompt: str, system_message: str = None) -> str:
    messages = []

    if system_message:
        messages.append({"role": "system", "content": system_message})
    messages.append({"role": "user", "content": prompt})

    start = time.time()
    response = openai.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        temperature=0.7,
    )

    # stream = openai.chat.completions.create(
    #     model=MODEL_NAME,
    #     messages=messages,
    #     temperature=0.7,
    #     stream=True
    # )
    #
    # response = ""
    # async for chunk in stream:
    #     if 'choices' in chunk and len(chunk.choices) > 0:
    #         delta = chunk.choices[0].delta
    #         if hasattr(delta, 'content'):
    #             response += delta.content
    #     # Go to redis

    logger.info(f"LLM call took {time.time() - start:.2f}s")
    return response.choices[0].message.content

# Helper function to publish content to 'chat-state-update' and 'gateway' channels
async def publish_and_stream(
    payload: Dict[str, Any],
    content: str,
    redis_client,
    redis_channel_publish: str,
    orchestrated_fn,
    ui_fn,
    hotel_info: Optional[List[Any]] = None,
    answer_message: bool = False,
) -> None:

    if redis_client is None:
        logger.info(f"[ANSWER HELPERS] Redis client is None")
        await redis_manager.connect()
        redis_client = redis_manager.get_client()
    else:
        logger.info(f"[ANSWER HELPERS] Redis client is NOT None")

    # Orchestrated publish
    # param = SimpleNamespace(content=content) if answer_message else content
    if answer_message:
        param = SimpleNamespace(content=content)
    else:
        param = content

    logger.info(f"Generated content: {content!r}")

    # UI publish to Redis Stream
    info = hotel_info or []
    ui = ui_fn(payload, content, info)
    print("[ANSWER HELPERS] Publishing to Redis Stream:")
    await redis_client.xadd(
        GATEWAY_STREAM,
        fields={
            "data": json.dumps(ui, ensure_ascii=False),
            "timestamp": int(time.time()),
            "message_type": "chat",
            "session_id": payload.get("session_id"),
            "message_id": payload.get("message_id")
        },
        id="*"
    )

    orch = orchestrated_fn(payload, param)
    await redis_client.publish(redis_channel_publish, json.dumps(orch))

    # UI publish
    # info = hotel_info or []
    # ui = ui_fn(payload, content, info)
    # await redis_client.publish("gateway", json.dumps(ui, ensure_ascii=False))


# Helper function to get conversation data from Redis
async def get_conversation_async(session_id: str, user_id: str) -> Optional[Dict[str, Any]]:

    key = f"prometa_ai:conversation:{session_id}_{user_id}"

    # TODO: redismanager get_client should be used here
    client = aioredis.Redis(
        host=AppConfig.REDIS_HOST,
        port=int(AppConfig.REDIS_PORT),
        db=int(AppConfig.REDIS_DB),
        decode_responses=True
    )

    try:
        raw = await client.get(key)
        if not raw:
            return None
        return json.loads(raw)
    except (aioredis.RedisError, json.JSONDecodeError):
        return None
