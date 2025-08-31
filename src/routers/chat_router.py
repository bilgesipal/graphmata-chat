import uuid
from queue import Queue

from fastapi import HTTPException, Response, APIRouter
from fastapi.responses import StreamingResponse

from src.agent.chat_agent import ChatSlotAgent
from src.utils import logger

router = APIRouter(tags=["Chat"])

@router.get("/health")
async def health_check():
    return {"status": "ok"}



# @router.get("/stream/{user_id}/{session_id}")
# async def stream_chat(user_id: str, session_id: str):
#     session_key = f"{user_id}_{session_id}"
#
#     logger.info(f"[Streaming] streaming opened session key: {session_key}")
#
#     if session_key not in session_queues:
#         session_queues[session_key] = Queue()
#
#     # Print all active session keys
#     logger.info(f"[Streaming] Active session keys: {list(session_queues.keys())}")
#
#     return StreamingResponse(
#         generate_chat_response(session_key),
#         media_type="text/event-stream"
#     )


@router.post("/test_process",
          summary="Streamlit Query Processing for Entities and Intent"
          )
async def llm_response(
        payload: dict,
        response: Response
):
    """
    Trigger intent processing with user input. Results will be published
    to Redis PubSub, not returned in the response.
    """
    request_id = str(uuid.uuid4())
    response.headers["X-Request-ID"] = request_id
    logger.info(f"Payload received: {payload}")

    try:
        # Initialize ChatSlotAgent
        chat_service = ChatSlotAgent()

        # Extract session key
        user_id = payload["metadata"]["user_id"]
        session_id = payload["session_id"]
        session_key = f"{user_id}_{session_id}"

        # # Ensure session key exists in session_queues
        # if session_key not in session_queues:
        #     session_queues[session_key] = Queue()

        # Process the payload using ChatSlotAgent
        result = chat_service.process_message_async(payload)

        logger.info(f"Processed result: {result}")

        return {
            "request_id": request_id,
            "result": result.model_dump() if hasattr(result, "model_dump") else result
        }

    except Exception as e:
        logger.error(f"Error processing payload: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")