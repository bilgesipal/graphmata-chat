import json
import traceback
from src.agent.chat_agent import ChatSlotAgent
from src.utils import logger
from queue import Queue

session_queues = {}  # Define session_queues locally as a dictionary

_chat_service = ChatSlotAgent() # Initialize the ChatSlotAgent globally

async def handle_message(message: str):
    """
    Handle incoming Redis messages.

    EN: Processes incoming Redis messages by parsing the payload, invoking the ChatSlotAgent,
        and logging the results.

    TR: Gelen Redis mesajlarını işleyerek yükü ayrıştırır, ChatSlotAgent'ı çağırır
        ve sonuçları loglar.

    Args:
        message (str): The raw message received from Redis.
    """
    logger.info(f"Handling Redis message: {message}")

    # 1) JSON parse
    try:
        payload = json.loads(message)
    except json.JSONDecodeError as e:
        logger.error(f"[JSONDecodeError] Failed to decode Redis message: {e}")
        return
    except Exception as e:
        logger.error(f"[UnexpectedError] While parsing JSON: {e}\n{traceback.format_exc()}")
        return

    # 2) Extract metadata
    try:
        user_id = payload["metadata"]["user_id"]
        session_id = payload["session_id"]
    except KeyError as e:
        logger.error(f"[KeyError] Missing expected key in payload: {e}\nPayload: {payload}")
        return
    except Exception as e:
        logger.error(f"[UnexpectedError] While extracting metadata: {e}\n{traceback.format_exc()}")
        return

    # 3) Ensure session queue exists
    session_key = f"{user_id}_{session_id}"
    try:
        if session_key not in session_queues:
            logger.info(f"Creating new session queue for {session_key}")
            session_queues[session_key] = Queue()
    except Exception as e:
        logger.error(f"[QueueError] Could not create/access session queue: {e}\n{traceback.format_exc()}")
        return

    # 4) Initialize and invoke ChatSlotAgent
    # try:
    #     chat_service = ChatSlotAgent()
    # except Exception as e:
    #     logger.error(f"[InitError] Failed to initialize ChatSlotAgent: {e}\n{traceback.format_exc()}")
    #     return
    #
    # try:
    #     result = await chat_service.process_message_async(payload)
    try:
        result = await _chat_service.process_message_async(payload)
    except Exception as e:
        logger.error(f"[AgentError] Error in ChatSlotAgent.process_message_async: {e}\n{traceback.format_exc()}")
        return

    # 5) Extract state from result
    try:
        if isinstance(result, dict):
            state_data = result.get("state", {})
        elif hasattr(result, "state"):
            state_data = result.state
        else:
            raise TypeError("Result must be a dict or have a 'state' attribute")

        # if isinstance(result, dict):
        #     state_data = result
        # elif hasattr(result, "model_dump"):
        #     state_data = result.model_dump()
        # else:
        #     raise TypeError("…")

        logger.info(f"[AgentResult] Received result: {state_data}")

    except TypeError as e:
        logger.error(f"[TypeError] {e}\nResult: {result}")
        return
    except Exception as e:
        logger.error(f"[UnexpectedError] While extracting state: {e}\n{traceback.format_exc()}")
        return

    # 6) Log final state
    try:
        logger.info(f"Processed result state: {state_data}")
    except Exception as e:
        logger.error(f"[LogError] Failed to log processed result: {e}\n{traceback.format_exc()}")
