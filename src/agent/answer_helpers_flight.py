from types import SimpleNamespace

import openai

from src.config.config import AppConfig

# Configure
openai.api_key = AppConfig.OPENAI_API_KEY
MODEL_NAME = "gpt-4o-mini"
GATEWAY_STREAM = "gateway"

from src.utils.answer_helpers_general import (
    call_llm,
    publish_and_stream,
)

from src.agent.publish_helpers import (
    build_publish_for_ui,
    build_publish_for_flight_search,
    build_publish_for_flight_slot
)

from src.prompt_lib.flight_prompts import (
    get_slot_filling_prompt,
    get_flight_search_prompt
)

# Helper function to extract prompt variables from the JSON
async def _get_prompt_variables(best_json: dict):
    result = {
        "segments": [],
        "totalDurationMin": best_json["totalDurationMin"],
        "totalPrice": best_json["totalPrice"],
    }

    for seg in best_json["segments"]:
        result["segments"].append({
            "airline": seg["airline"],
            "fromAirport": seg["fromAirport"],
            "toAirport": seg["toAirport"],
            "departure": seg["departure"],
            "arrival": seg["arrival"],
            "durationMin": seg["durationMin"],
            "price": seg["price"],
            "currency": seg["currency"],
            "category": seg["brandPackage"]["category"]
        })

    return result

################################################################

# This method is used to ask the missing slots to the user
async def get_slot_filling(payload: dict, redis_client, redis_channel_publish: str):

    missing = payload.get("orchestration", {}).get("actions", {}).get("parameters", {}).get("slots_to_collect", [])
    # context = payload.get("state", {}).get("current", {}).get("conversation_context", "")
    # intent = payload.get("state", {}).get("current", {}).get("intent_phase", {}).get("intent", "unknown")

    prompt = get_slot_filling_prompt(missing)

    content = await call_llm(prompt)

    await publish_and_stream(
        payload,
        content,
        redis_client,
        redis_channel_publish,
        build_publish_for_flight_slot,
        build_publish_for_ui,
        hotel_info=[],
        answer_message=True,
    )
    return SimpleNamespace(content=content), payload


async def get_flight_search(payload: dict, redis_client, redis_channel_publish: str):

    chosen_flights = payload.get("orchestration", {}).get("actions", {}).get("parameters", {}).get("chosen_flights", {})
    best = chosen_flights.get("best", {})
    cheapest = chosen_flights.get("cheapest", {})
    fastest = chosen_flights.get("fastest", {})

    best_json = await _get_prompt_variables(best)
    cheapest_json = await _get_prompt_variables(cheapest)
    fastest_json = await _get_prompt_variables(fastest)

    prompt = get_flight_search_prompt(best_json, cheapest_json, fastest_json)

    content = await call_llm(prompt)

    await publish_and_stream(
        payload,
        content,
        redis_client,
        redis_channel_publish,
        build_publish_for_flight_search,
        build_publish_for_ui,
        hotel_info=[],
        answer_message=True,
    )
    return SimpleNamespace(content=content), payload


async def get_flight_ask(payload: dict, redis_client, redis_channel_publish: str):

    featureQuery = payload.get("state", {}).get("current", {}).get("intent_phase", {}).get("entities", {}).get("featureQuery", [])
    postQuery = payload.get("state", {}).get("current", {}).get("intent_phase", {}).get("entities", {}).get("postQuery", [])

    missing = []

    prompt = get_slot_filling_prompt(missing)

    content = await call_llm(prompt)

    await publish_and_stream(
        payload,
        content,
        redis_client,
        redis_channel_publish,
        build_publish_for_flight_slot, # TODO: UPDATE FOR FLIGHT
        build_publish_for_ui,
        hotel_info=[],
        answer_message=True,
    )
    return SimpleNamespace(content=content), payload
