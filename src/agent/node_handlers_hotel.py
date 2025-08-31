# src/chat_agent/handlers.py

from datetime import datetime, timezone
from src.config.config import AppConfig
from src.schemas.schemas import *
from src.agent.answer_helpers_hotel import (
    get_answer,
    get_confirmation,
    get_requested_hotels,
    get_out_of_scope,
    get_rejection,
    get_greeting,
    get_hotel_detail_answer,
    get_hotel_single_answer,
    get_slot_fixing,
    get_empty_hotels,
    get_hotel_compare,
    get_serpapi_search,
    get_hotel_similar
)
from src.utils import redis_manager

# same list you had in the class
REQUIRED_SLOTS = [
    "hotelNameQuery",
    "hotelStarQuery",
    "location",
    "poi",
    "featureQuery",
    "checkinDate",
    "checkoutDate",
    "per_night",
    "NumberOfPeople",
    "NumberOfRooms"
]

redis_channel_publish = AppConfig.REDIS_PUBLISH_CHAT

def hotel_route_decider(state: GraphState) -> GraphState:
    """Decide whether we're collecting slots, asking for confirmation, or default."""
    print("route phase hotel - determining action type")
    d = state.model_dump()

    # bump trace
    d["trace_info"]["sequence"] = int(d["trace_info"]["sequence"]) + 1
    d["metadata"]["source_service"] = "chat_slot"
    d["timestamp"]  = datetime.now(timezone.utc).isoformat()

    transition = d.get("state", {}).get("transition", "")
    previous_transition = d.get("state", {}).get("previous_transition", "")

    flow = d.get("trace_info", {}).get("flow", "")
    if "hotel_detail" in flow:
        print("Flow contains 'hotel_detail'")

    # Safely read orchestration actions
    try:
        orch = d.get("orchestration")
        if not isinstance(orch, dict):
            print("Warning: orchestration missing or invalid.")
            actions = {}
        else:
            actions = orch.get("actions", {})
    except Exception as e:
        print(f"Error reading orchestration: {e}")
        actions = {}
    action = actions.get("action", "")

    print(f"Transition: {transition}, Action: {action}")

    # TODO: route map dictionary -> hotel, car, flight. Bir special fonksiyon içinde.
    # TODO: Demo'dan sonra bakılacak toplarma kısmı -> route map dictionary

    # Reads the incoming transition and tags the state with the appropriate route name
    if transition == "proceed_to_slot_filling":
        route = "slot_collection"
    elif flow == "serpapi":
        route = "serpapi_search"
    elif transition == "proceed_to_confirmation": # TODO: remove this
        route = "confirmation_request"
    elif transition == "request_chat_show_hotels":
        if "hotel_detail" in flow or "hotel_room" in flow:
            print("REQUEST CHAT SHOW HOTELS - Flow contains 'hotel_detail' or 'hotel_room', routing to answer_single_hotel")
            route = "answer_single_hotel"
        elif "hotel_ask" in flow:
            print("REQUEST CHAT SHOW HOTELS - Flow contains 'hotel_ask', routing to cache_check")
            route = "cache_check"
        elif "hotel_comparison" in flow:
            print("REQUEST CHAT SHOW HOTELS - Flow contains 'hotel_comparison', routing to hotel_compare")
            route = "hotel_compare"
        elif "hotel_similar" in flow:
            print("REQUEST CHAT SHOW HOTELS - Flow contains 'hotel_similar', routing to hotel_compare")
            route = "hotel_similar"
        else:
            print("REQUEST CHAT SHOW HOTELS - Flow routing to show_hotels")
            route = "show_hotels"
    elif transition == "refill_after_rejection":
        route = "rejection"
    elif transition == "proceed_to_greeting":
        route = "greeting"
    elif transition == "proceed_to_cache_check":
        if "hotel_comparison" in flow:
            print("PROCEED TO CACHE CHECK - Flow contains 'hotel_comparison', routing to hotel_compare")
            route = "hotel_compare"
        else:
            print("PROCEED TO CACHE CHECK - Flow does not contain 'hotel_comparison', routing to cache_check")
            route = "cache_check" # hotel_ask flow
    elif transition == "proceed_to_slot_fixing":
        route = "slot_fixing"
    elif transition == "request_chat_empty_hotels":
        route = "empty_hotels"
    elif transition == "proceed_to_hotel_compare":
        route = "hotel_compare"
    elif transition == "proceed_to_out_of_scope":
        route = "out_of_scope"
    else:
        route = "default"

    print(f"hotel_route_decider determined route: {route}")
    d["route"] = route
    return GraphState.model_validate(d)


async def handle_slot_collection(state: GraphState) -> GraphState:
    print("Handling slot collection")
    payload = state.model_dump()
    redis_client = redis_manager.get_client()
    await get_answer(payload, redis_client, redis_channel_publish)
    return state

async def handle_confirmation_request(state: GraphState) -> GraphState:
    print("Handling confirmation request")
    payload = state.model_dump()
    redis_client = redis_manager.get_client()
    await get_confirmation(payload, redis_client, redis_channel_publish)
    return state

def handle_default(state: GraphState) -> GraphState:
    """Fallback if nothing else matched."""
    print("Handling default case")
    d = state.model_dump()
    d["prompt"] = None
    d["state"]["transition"] = "unknown_action"
    return GraphState.model_validate(d)

async def handle_show_hotels(state: GraphState) -> GraphState:
    print("Handling show hotels")
    payload = state.model_dump()
    redis_client = redis_manager.get_client()
    await get_requested_hotels(payload, redis_client, redis_channel_publish)
    return state

async def handle_out_of_scope(state: GraphState) -> GraphState:
    print("Handling out of scope")
    payload = state.model_dump()
    redis_client = redis_manager.get_client()
    await get_out_of_scope(payload, redis_client, redis_channel_publish)
    return state

async def handle_rejection(state: GraphState) -> GraphState:
    print("Handling rejection")
    payload = state.model_dump()
    redis_client = redis_manager.get_client()
    await get_rejection(payload, redis_client, redis_channel_publish)
    return state

async def handle_greeting(state: GraphState) -> GraphState:
    print("Handling greeting")
    payload = state.model_dump()
    redis_client = redis_manager.get_client()
    await get_greeting(payload, redis_client, redis_channel_publish)
    return state

async def handle_cache_check(state: GraphState) -> GraphState:
    print("Handling cache check")
    payload = state.model_dump()
    redis_client = redis_manager.get_client()
    await get_hotel_detail_answer(payload, redis_client, redis_channel_publish)
    return state

async def handle_answer_single_hotel(state: GraphState) -> GraphState:
    print("Handling answer single hotel")
    payload = state.model_dump()
    redis_client = redis_manager.get_client()
    await get_hotel_single_answer(payload, redis_client, redis_channel_publish)
    return state

async def handle_slot_fixing(state: GraphState) -> GraphState:
    print("Handling slot fixing")
    payload = state.model_dump()
    redis_client = redis_manager.get_client()
    await get_slot_fixing(payload, redis_client, redis_channel_publish)
    return state

async def handle_empty_hotels(state: GraphState) -> GraphState:
    print("Handling empty hotels")
    payload = state.model_dump()
    redis_client = redis_manager.get_client()
    await get_empty_hotels(payload, redis_client, redis_channel_publish)
    return state

async def handle_hotel_compare(state: GraphState) -> GraphState:
    print("Handling hotel compare")
    payload = state.model_dump()
    redis_client = redis_manager.get_client()
    await get_hotel_compare(payload, redis_client, redis_channel_publish)
    return state

async def handle_serpapi_search(state: GraphState) -> GraphState:
    print("Handling SerpAPI search")
    payload = state.model_dump()
    redis_client = redis_manager.get_client()
    await get_serpapi_search(payload, redis_client, redis_channel_publish)
    return state

async def handle_hotel_similar(state: GraphState) -> GraphState:
    print("Handling hotel similar")
    payload = state.model_dump()
    redis_client = redis_manager.get_client()
    await get_hotel_similar(payload, redis_client, redis_channel_publish)
    return state
