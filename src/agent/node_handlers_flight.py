from datetime import datetime, timezone

from src.agent.answer_helpers_flight import (
    get_slot_filling,
    get_flight_search,
    get_flight_ask
)
from src.config.config import AppConfig
from src.schemas.schemas import *
from src.utils import redis_manager

redis_channel_publish = AppConfig.REDIS_PUBLISH_CHAT

def flight_route_decider(state: GraphState) -> GraphState:
    """Decide flight phase: slot collection, search, booking or cancel."""
    print("route phase flight - determining action type")
    d = state.model_dump()

    # bump trace
    d["trace_info"]["sequence"] = int(d["trace_info"]["sequence"]) + 1
    d["metadata"]["source_service"] = "chat_slot"
    d["timestamp"] = datetime.now(timezone.utc).isoformat()

    # Safely read orchestration actions
    try:
        orch = d.get("orchestration")
        actions = orch.get("actions", {}) if isinstance(orch, dict) else {}
    except Exception as e:
        print(f"Error reading orchestration: {e}")
        actions = {}
    transition = d.get("state", {}).get("transition", "")
    action = actions.get("action", "")
    print(f"Transition: {transition}, Action: {action}")

    # Determine route based on transition or action
    if transition == "proceed_to_slot_filling":
        route = "slot_collection"
    elif transition == "request_chat_show_flight":
        route = "search"
    elif transition == "proceed_to_cache_check":
        route = "flight_ask"
    else:
        # fallback to default search phase
        route = "search"

    print(f"flight_route_decider determined route: {route}")
    d["route"] = route
    return GraphState.model_validate(d)


#########################################
# # Added flight-specific handlers
async def handle_flight_search(state: GraphState) -> GraphState:
    print("Handling flight search")
    payload = state.model_dump()
    redis_client = redis_manager.get_client()
    await get_flight_search(payload, redis_client, redis_channel_publish)
    return state

async def handle_flight_ask(state: GraphState) -> GraphState:
    print("Handling flight ask")
    payload = state.model_dump()
    redis_client = redis_manager.get_client()
    await get_flight_ask(payload, redis_client, redis_channel_publish)
    return state

# async def handle_flight_cancel(state: GraphState) -> GraphState:
#     print("Handling flight cancellation")
#     # Implement flight cancellation logic here
#     return state

async def handle_slot_collection_flight(state: GraphState) -> GraphState:
    print("Handling slot collection - flight")
    payload = state.model_dump()
    redis_client = redis_manager.get_client()
    await get_slot_filling(payload, redis_client, redis_channel_publish)
    return state






