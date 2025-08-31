import json
import time
from types import SimpleNamespace
from typing import Dict, Any
from src.config.system_message import HOTEL_ASSISTANT_SYSTEM_MESSAGE

import openai
import redis.asyncio as aioredis

from src.utils.answer_helpers_general import (
    get_user_session,
    call_llm,
    publish_and_stream,
    get_conversation_async,
)

from src.agent.publish_helpers import (
    build_publish_for_answer,
    build_publish_for_confirmation,
    build_publish_for_hotels,
    build_publish_rejection,
    build_publish_for_ui,
    build_publish_for_detail,
    build_publish_for_hotel_list,
    build_publish_for_others,
    build_publish_for_show_hotels,
    build_publish_for_hotel_compare,
    build_publish_for_serpapi
)
from src.config.config import AppConfig
from src.prompt_lib.hotel_prompts import (
    get_hotel_list_prompt,
    get_hotel_detail_prompt,
    get_hotel_list_with_descriptions_prompt,
    get_hotel_detail_single_answer_prompt,
    get_hotel_feature_response_prompt,
    get_slot_fixing_prompt,
    get_empty_hotels_prompt,
    get_hotel_compare_prompt,
    get_out_of_scope_prompt,
    get_cheapest_hotel_prompt,
    get_serpapi_search_prompt,
    get_greeting_prompt,
    get_hotel_similar_prompt,
    get_hotel_detail_single_room_answer_prompt
)
from src.utils import logger


# This method is used to ask the missing slots to the user
async def get_answer(payload: dict, redis_client, redis_channel_publish: str):

    missing = payload.get("orchestration", {}).get("actions", {}).get("parameters", {}).get("slots_to_collect", [])
    context = payload.get("state", {}).get("current", {}).get("conversation_context", "")
    intent = payload.get("state", {}).get("current", {}).get("intent_phase", {}).get("intent", "unknown")

    # Get user question from Redis conversation cache
    user_id, session_id, _ = get_user_session(payload)
    conv = await get_conversation_async(session_id, user_id)
    if conv is None:
        logger.warning(f"[Chat Agent] Conversation from Redis is None for session_id={session_id}, user_id={user_id}")
        conv = {}
    user_messages = conv.get("user_messages", [])
    question = user_messages[-1].get("user", "") if user_messages else ""
    print(f"[Chat Agent] User question: {question!r}")

    # Get chat history from Redis conversation cache
    chat_history = conv.get("chat_history", "")
    print(f"[Chat Agent] Chat history: {chat_history!r}")

    prompt = get_hotel_list_prompt(missing, context, question, chat_history)

    # if intent == "hotel_list":
    #     prompt = get_hotel_list_prompt(missing, context)
    # elif intent == "hotel_detail":
    #     prompt = get_hotel_detail_prompt(missing, context)

    content = await call_llm(prompt, HOTEL_ASSISTANT_SYSTEM_MESSAGE)

    await publish_and_stream(
        payload,
        content,
        redis_client,
        redis_channel_publish,
        build_publish_for_answer,
        build_publish_for_ui,
        hotel_info=[],
        answer_message=True,
    )
    return SimpleNamespace(content=content), payload

# This method is used to ask the user to confirm the parameters
async def get_confirmation(payload: Dict, redis_client, redis_channel_publish: str):

    params = payload.get("orchestration", {}).get("actions", {}).get("parameters", {}).get("parameters_to_confirm", {})
    hotel_list = []
    for k, v in params.items():
        # Filter out empty values
        if v:
            hotel_list.append(f"- {k}: {v}")
    text = "Bu özellikleri onaylıyor musunuz?\n" + "\n".join(hotel_list)

    await publish_and_stream(
        payload,
        text,
        redis_client,
        redis_channel_publish,
        build_publish_for_confirmation,
        build_publish_for_ui,
    )


# V2: Get hotel details and price information from redis cache -> redis_cache_address_general_info, redis_cache_address_price_policy
async def get_requested_hotels(payload: Dict[str, Any], redis_client, redis_channel_publish: str):
    # 1) Retrieve general and price-policy key lists from metadata
    meta = payload.get("metadata", {})
    general_keys = meta.get("redis_cache_address_general_info", [])
    price_keys = meta.get("redis_cache_address_price_policy", [])

    print(f"[Chat Agent] Payload: {payload!r}")

    print(f"General keys are: {general_keys!r}")
    print(f"Price keys are: {price_keys!r}")

    # 2) Get the hotels selected by the user (fallback)
    hotels_raw = payload.get("orchestration", {}) \
                        .get("actions", {}) \
                        .get("parameters", {}) \
                        .get("chosen_hotels", [])
    hotel_names = [h["hotel_name"] for h in hotels_raw] if isinstance(hotels_raw, list) else []

    if isinstance(hotels_raw, list):
        hotels_list = hotels_raw
    elif hotels_raw is None:
        hotels_list = []
    else:
        hotels_list = [hotels_raw]

    # 3) For each hotel, fetch general and price data from Redis, parse JSON, and merge
    fetched = []
    for idx, gkey in enumerate(general_keys):
        try:
            raw_g = await redis_client.get(gkey)
            general_data = json.loads(raw_g) if raw_g else {}
        except Exception as e:
            logger.error(f"[Chat Agent] Error fetching/parsing general info for key {gkey}: {e}", exc_info=True)
            general_data = {}

        # If the price-policy key matches, fetch it; otherwise, use an empty dict
        price_data = {}
        if idx < len(price_keys):
            pkey = price_keys[idx]
            try:
                raw_p = await redis_client.get(pkey)
                price_data = json.loads(raw_p) if raw_p else {}
            except Exception as e:
                logger.error(f"[Chat Agent] Error fetching/parsing price policy for key {pkey}: {e}", exc_info=True)

        # If this hotel exists in the fetched list (name matches), add it
        name = general_data.get("name")
        if name and name in hotel_names:
            # merge: overwrite price_data
            merged = {**general_data, **price_data}
            fetched.append(merged)

    if not fetched:
        logger.warning(f"[Chat Agent] No hotels fetched from Redis (keys: {general_keys}), falling back to payload hotels.")

    # 4) Retrieve the user's question
    user_id, session_id, _ = get_user_session(payload)
    conv = await get_conversation_async(session_id, user_id) or {}

    user_messages = conv.get("user_messages", [])
    question = user_messages[-1].get("user", "") if user_messages else ""

    print(f"[Chat Agent] User question 2: {question!r}")

    chat_history = conv.get("chat_history", "")
    print(f"[Chat Agent] Chat history: {chat_history!r}")

    # 5) Prepare the prompt — first from Redis data, otherwise from payload
    hotel_input = fetched if fetched else hotels_raw

    print(f"HOTEL INPUT: {hotel_input!r}")

    # If the postQuery has 'cheap' label, find the cheapest hotel in list and generate a different message
    post_query = payload.get("orchestration", {}).get("actions", {}).get("parameters", {}).get("filled_slots", {}).get("postQuery", [])

    if isinstance(post_query, list) and "cheap" in post_query:
        logger.info(f"[Chat Agent] PostQuery contains 'CHEAP'")

        def get_price(hotel):
            price_str = hotel["price"].split()[0] # Get the numeric part of the price
            return float(price_str)

        sorted_hotels = sorted(hotel_input, key=get_price)
        cheapest_hotel = sorted_hotels[0]

        print(f"[Chat Agent] Cheapest hotel: {cheapest_hotel!r}")
        prompt = get_cheapest_hotel_prompt(cheapest_hotel, question)
    else:
        prompt = get_hotel_list_with_descriptions_prompt(hotel_input, question, chat_history)

    # 6) LLM call
    content = await call_llm(prompt, HOTEL_ASSISTANT_SYSTEM_MESSAGE)

    await publish_and_stream(
        payload,
        content,
        redis_client,
        redis_channel_publish,
        build_publish_for_hotel_list,
        build_publish_for_ui,
        hotel_info=hotels_list,
    )

    return SimpleNamespace(content=content), payload


# async def get_out_of_scope(payload: Dict[str, Any], redis_client, redis_channel_publish: str):
#    text = "Üzgünüm, bu isteğe yardımcı olamam. Başka bir şey sormak ister misiniz?"
#
#    await publish_and_stream(
#        payload,
#        text,
#        redis_client,
#        redis_channel_publish,
#        build_publish_for_hotels,
#        build_publish_for_ui,
#    )


async def get_out_of_scope(payload: Dict[str, Any], redis_client, redis_channel_publish: str):
    # Extract Redis cache keys from the payload
    meta = payload.get("metadata", {})
    general_keys = meta.get("redis_cache_address_general_info", [])
    price_keys = meta.get("redis_cache_address_price_policy", [])

    general_key = general_keys[0] if isinstance(general_keys, list) and general_keys else None
    price_key = price_keys[0] if isinstance(price_keys, list) and price_keys else None

    # 2) Redis’ten hem genel bilgileri hem de fiyat-politika verisini çek
    raw_general = None
    raw_price = None
    try:
        if general_key:
            raw_general = await redis_client.get(general_key)
    except Exception as e:
        logger.error(f"[Chat Agent] Error fetching general info from Redis for key {general_key!r}: {e}", exc_info=True)

    try:
        if price_key:
            raw_price = await redis_client.get(price_key)
    except Exception as e:
        logger.error(f"[Chat Agent] Error fetching price policy from Redis for key {price_key!r}: {e}", exc_info=True)

    # 3) JSON parse; hata durumunda boş dict
    try:
        general_data = json.loads(raw_general) if raw_general else {}
    except json.JSONDecodeError as e:
        logger.error(f"[Chat Agent] Failed to decode JSON from general_info: {e}", exc_info=True)
        general_data = {}

    try:
        price_data = json.loads(raw_price) if raw_price else {}
    except json.JSONDecodeError as e:
        logger.error(f"[Chat Agent] Failed to decode JSON from price_policy: {e}", exc_info=True)
        price_data = {}

    logger.info(f"[Chat Agent] OUT OF SCOPE - General data: {general_data!r}")
    logger.info(f"[Chat Agent] OUT OF SCOPE - Price-policy data: {price_data!r}")

    user_id, session_id, _ = get_user_session(payload)
    conv = await get_conversation_async(session_id, user_id) or {}

    user_messages = conv.get("user_messages", [])
    question = user_messages[-1].get("user", "") if user_messages else ""

    chat_history = conv.get("chat_history", "")
    print(f"[Chat Agent] Chat history: {chat_history!r}")

    # Construct the prompt using the fetched data
    prompt = get_out_of_scope_prompt(general_data, price_data, question, chat_history)

    # Call the LLM with the constructed prompt
    content = await call_llm(prompt, HOTEL_ASSISTANT_SYSTEM_MESSAGE)

    # Respond with the LLM-generated content
    await publish_and_stream(
        payload,
        content,
        redis_client,
        redis_channel_publish,
        build_publish_for_hotels,
        build_publish_for_ui,
    )



async def get_rejection(payload: Dict[str, Any], redis_client, redis_channel_publish: str):
    text = "Onayınız reddedildi. İstediğiniz kriterleri tekrar eder misiniz? Otel adı, konum, tarih gibi bilgileri verebilirsiniz."

    await publish_and_stream(
        payload,
        text,
        redis_client,
        redis_channel_publish,
        build_publish_rejection,
        build_publish_for_ui,
    )

async def get_greeting(payload: Dict[str, Any], redis_client, redis_channel_publish: str):
    # text = "Merhaba! Size nasıl yardımcı olabilirim?"

    # Get user question from Redis conversation cache
    user_id, session_id, _ = get_user_session(payload)
    conv = await get_conversation_async(session_id, user_id)
    if conv is None:
        logger.warning(f"[Chat Agent] Conversation from Redis is None for session_id={session_id}, user_id={user_id}")
        conv = {}
    user_messages = conv.get("user_messages", [])
    question = user_messages[-1].get("user", "") if user_messages else ""

    print(f"[Chat Agent] User question: {question!r}")

    chat_history = conv.get("chat_history", "")
    print(f"[Chat Agent] Chat history: {chat_history!r}")

    # Prepare the greeting prompt
    prompt = get_greeting_prompt(question, chat_history)
    content = await call_llm(prompt, HOTEL_ASSISTANT_SYSTEM_MESSAGE)

    await publish_and_stream(
        payload,
        content,
        redis_client,
        redis_channel_publish,
        build_publish_for_others,
        build_publish_for_ui,
    )


# V3: Get hotel details and price information from redis cache -> redis_cache_address_general_info, redis_cache_address_price_policy
async def get_hotel_detail_answer(payload: Dict, redis_client, redis_channel_publish: str):
    # 1) Cache key’leri metadata’dan çıkar
    meta = payload.get("metadata", {})
    general_keys = meta.get("redis_cache_address_general_info", [])
    price_keys = meta.get("redis_cache_address_price_policy", [])

    hotel_raw = payload.get("orchestration", {}).get("actions", {}).get("parameters", {}).get("chosen_hotels", {})
    # feature_query = payload.get("orchestration", {}).get("actions", {}).get("parameters", {}).get("filled_slots", {}).get("featureQuery", [])

    feature_query = (
            payload.get("orchestration", {})
            .get("actions", {})
            .get("parameters", {})
            .get("filled_slots", {})
            .get("featureQuery") or []
    )
    if not isinstance(feature_query, list):
        feature_query = [feature_query]

    print(f"[Chat Agent] Feature query: {feature_query!r}")

    general_key = general_keys[0] if isinstance(general_keys, list) and general_keys else None
    price_key = price_keys[0] if isinstance(price_keys, list) and price_keys else None

    # 2) Redis’ten hem genel bilgileri hem de fiyat-politika verisini çek
    raw_general = None
    raw_price = None
    try:
        if general_key:
            raw_general = await redis_client.get(general_key)
    except Exception as e:
        logger.error(f"[Chat Agent] Error fetching general info from Redis for key {general_key!r}: {e}", exc_info=True)

    try:
        if price_key:
            raw_price = await redis_client.get(price_key)
    except Exception as e:
        logger.error(f"[Chat Agent] Error fetching price policy from Redis for key {price_key!r}: {e}", exc_info=True)

    # 3) JSON parse; hata durumunda boş dict
    try:
        general_data = json.loads(raw_general) if raw_general else {}
    except json.JSONDecodeError as e:
        logger.error(f"[Chat Agent] Failed to decode JSON from general_info: {e}", exc_info=True)
        general_data = {}

    try:
        price_data = json.loads(raw_price) if raw_price else {}
    except json.JSONDecodeError as e:
        logger.error(f"[Chat Agent] Failed to decode JSON from price_policy: {e}", exc_info=True)
        price_data = {}

    logger.info(f"[Chat Agent] General data: {general_data!r}")
    logger.info(f"[Chat Agent] Price-policy data: {price_data!r}")

    # 4) Birleştirilmiş hotel_detail objesini oluştur
    #    (price_data içindeki alanlar general_data’nın üzerine yazılacak)
    hotel_detail = {**general_data, **price_data}

    # Eğer cache tamamen boşsa (ikisi de boş dict) hotel_raw'u kullan.
    if not hotel_detail:
        logger.warning("[Chat Agent] Cache empty, falling back to hotel_raw from payload.")
        # hotel_raw dict değilse ya da None ise, boş dict ver
        hotel_detail = hotel_raw if isinstance(hotel_raw, dict) else {}
    # (Opsiyonel) Cache kısmi ise ve hotel_raw’da ek alanlar varsa merge etmek istersen:
    # elif hotel_raw:
    #     hotel_detail = {**hotel_detail, **hotel_raw}

    # 5) Kullanıcı sorusunu al ve prompt’u hazırla
    user_id, session_id, _ = get_user_session(payload)
    conv = await get_conversation_async(session_id, user_id) or {}

    user_messages = conv.get("user_messages", [])
    question = user_messages[-1].get("user", "") if user_messages else ""

    print(f"[Chat Agent] User question: {question!r}")
    print(f"[Chat Agent] HOTEL DETAIL: {hotel_detail!r}")

    chat_history = conv.get("chat_history", "")
    print(f"[Chat Agent] Chat history: {chat_history!r}")

    # features = hotel_detail.get("features", [])
    print(f"[Chat Agent] Feature query: {feature_query!r}")
    prompt = get_hotel_feature_response_prompt(question, hotel_detail, feature_query, chat_history)

    # 6) LLM çağrısı
    content = await call_llm(prompt, HOTEL_ASSISTANT_SYSTEM_MESSAGE)

    # 8) UI’a yayınla ve stream et
    await publish_and_stream(
        payload,
        content,
        redis_client,
        redis_channel_publish,
        build_publish_for_detail,
        build_publish_for_ui,
    )

    return SimpleNamespace(content=content), payload


# This method is used to answer hotel details about a single hotel
async def get_hotel_single_answer(payload: Dict, redis_client, redis_channel_publish: str):

    user_id, session_id, _ = get_user_session(payload)

    # 1) Cache key’leri metadata’dan çıkar
    meta = payload.get("metadata", {})
    general_keys = meta.get("redis_cache_address_general_info", [])
    price_keys = meta.get("redis_cache_address_price_policy", [])

    hotel_raw = payload.get("orchestration", {}).get("actions", {}).get("parameters", {}).get("chosen_hotels", {})
    # feature_query = payload.get("orchestration", {}).get("actions", {}).get("parameters", {}).get("filled_slots", {}).get("featureQuery", [])

    feature_query = (
            payload.get("orchestration", {})
            .get("actions", {})
            .get("parameters", {})
            .get("filled_slots", {})
            .get("featureQuery") or []
    )
    if not isinstance(feature_query, list):
        feature_query = [feature_query]

    print(f"[Chat Agent] Feature query: {feature_query!r}")

    general_key = general_keys[0] if isinstance(general_keys, list) and general_keys else None
    price_key = price_keys[0] if isinstance(price_keys, list) and price_keys else None

    # 2) Redis’ten hem genel bilgileri hem de fiyat-politika verisini çek
    raw_general = None
    raw_price = None
    try:
        if general_key:
            raw_general = await redis_client.get(general_key)
    except Exception as e:
        logger.error(f"[Chat Agent] Error fetching general info from Redis for key {general_key!r}: {e}", exc_info=True)

    try:
        if price_key:
            raw_price = await redis_client.get(price_key)
    except Exception as e:
        logger.error(f"[Chat Agent] Error fetching price policy from Redis for key {price_key!r}: {e}", exc_info=True)

    # 3) JSON parse; hata durumunda boş dict
    try:
        general_data = json.loads(raw_general) if raw_general else {}
    except json.JSONDecodeError as e:
        logger.error(f"[Chat Agent] Failed to decode JSON from general_info: {e}", exc_info=True)
        general_data = {}

    try:
        price_data = json.loads(raw_price) if raw_price else {}
    except json.JSONDecodeError as e:
        logger.error(f"[Chat Agent] Failed to decode JSON from price_policy: {e}", exc_info=True)
        price_data = {}

    logger.info(f"[Chat Agent] General data: {general_data!r}")
    logger.info(f"[Chat Agent] Price-policy data: {price_data!r}")



    # Get user question from Redis conversation cache
    conv = await get_conversation_async(session_id, user_id)
    if conv is None:
        logger.warning(f"[Chat Agent] Conversation from Redis is NONE for session_id={session_id}, user_id={user_id}")
        conv = {}

    # print(f"[Chat Agent] Conversation from Redis: {conv!r}")
    # question = conv.get("chat_data", {}).get("filled_slots", {}).get("LLM_outputText", "") if conv else ""
    # print(f"[Chat Agent] User question: {question!r}")

    user_messages = conv.get("user_messages", [])
    question = user_messages[-1].get("user", "") if user_messages else ""
    print(f"[Chat Agent] User question 2: {question!r}")

    # Get hotel list from payload
    hotel_raw = payload.get("orchestration", {}).get("actions", {}).get("parameters", {}).get("chosen_hotels", {})

    # Drop 'images', 'hotel_id' in hotel_raw if it exists
    if isinstance(hotel_raw, dict):
        hotel_raw.pop("images", None)
        hotel_raw.pop("hotel_id", None)

    logger.info(f"[Chat Agent] Retrieved hotel from payload: {hotel_raw!r}")

    if isinstance(hotel_raw, list):
        hotels_list = hotel_raw
    elif hotel_raw is None:
        hotels_list = []
    else:
        hotels_list = [hotel_raw]

    chat_history = conv.get("chat_history", "")
    print(f"[Chat Agent] Chat history: {chat_history!r}")

    # Handle hotel room flow
    flow = payload.get("trace_info", {}).get("flow", "")
    if "hotel_room" in flow:
        print(f"[Chat Agent] Hotel room flow")
        # Take room and board info from general_data
        room_and_board_info = general_data.get("room_and_board_info", {})
        prompt = get_hotel_detail_single_room_answer_prompt(user_question=question,
                                                            chat_history=chat_history,
                                                            room_info=room_and_board_info
                                                            )
    else:
        prompt = get_hotel_detail_single_answer_prompt(hotel_raw, question, general_data, price_data, chat_history)

    content = await call_llm(prompt, HOTEL_ASSISTANT_SYSTEM_MESSAGE)

    await publish_and_stream(
        payload,
        content,
        redis_client,
        redis_channel_publish,
        build_publish_for_show_hotels,
        build_publish_for_ui,
        hotel_info=hotels_list,
    )
    return SimpleNamespace(content=content), payload


# This method is used to generate answer when the user asks for hotel details but the feature is not found
async def get_slot_fixing(payload: Dict, redis_client, redis_channel_publish: str):

    filled = payload.get("orchestration", {}).get("actions", {}).get("parameters", {}).get("filled_slots", {})
    filled_slots = {k: v for k, v in filled.items() if v}

    prompt = get_slot_fixing_prompt(filled_slots)

    content = await call_llm(prompt, HOTEL_ASSISTANT_SYSTEM_MESSAGE)

    await publish_and_stream(
        payload,
        content,
        redis_client,
        redis_channel_publish,
        build_publish_for_others,
        build_publish_for_ui,
    )
    return SimpleNamespace(content=content), payload


# This method is used to generate answer when no hotels are found
async def get_empty_hotels(payload: Dict, redis_client, redis_channel_publish: str):
    user_id, session_id, _ = get_user_session(payload)

    # Get user question from Redis conversation cache
    conv = await get_conversation_async(session_id, user_id)
    if conv is None:
        logger.warning(f"[Chat Agent] Conversation from Redis is None for session_id={session_id}, user_id={user_id}")
        conv = {}

    # question = conv.get("chat_data", {}).get("filled_slots", {}).get("LLM_outputText", "") if conv else ""
    user_messages = conv.get("user_messages", [])
    question = user_messages[-1].get("user", "") if user_messages else ""

    print(f"[Chat Agent] User question: {question!r}")

    chat_history = conv.get("chat_history", "")
    print(f"[Chat Agent] Chat history: {chat_history!r}")

    prompt = get_empty_hotels_prompt(question, chat_history)

    content = await call_llm(prompt, HOTEL_ASSISTANT_SYSTEM_MESSAGE)
    await publish_and_stream(
        payload,
        content,
        redis_client,
        redis_channel_publish,
        build_publish_for_others,
        build_publish_for_ui,
    )
    return SimpleNamespace(content=content), payload



async def get_hotel_compare(payload, redis_client, redis_channel_publish):
    # 1) Retrieve general and price-policy key lists from metadata
    meta = payload.get("metadata", {})
    general_keys = meta.get("redis_cache_address_general_info", [])
    price_keys = meta.get("redis_cache_address_price_policy", [])

    # 2) Get the hotels selected by the user (fallback)
    chosen = payload.get("orchestration", {}) \
                    .get("actions", {}) \
                    .get("parameters", {}) \
                    .get("chosen_hotels", [])
    if not isinstance(chosen, list):
        chosen = [chosen] if chosen else []

    # 3) For both hotels, fetch general + price data from Redis and merge them
    hotels_data = []
    for idx in (0, 1):
        # 3a) Retrieve keys
        gkey = general_keys[idx] if idx < len(general_keys) else None
        pkey = price_keys[idx]   if idx < len(price_keys)   else None

        # 3b) Fetch from Redis and parse JSON
        general_data = {}
        if gkey:
            try:
                raw_g = await redis_client.get(gkey)
                general_data = json.loads(raw_g) if raw_g else {}
            except Exception as e:
                logger.error(f"[Chat Agent‑compare] Error with general_info key {gkey}: {e}", exc_info=True)

        price_data = {}
        if pkey:
            try:
                raw_p = await redis_client.get(pkey)
                price_data = json.loads(raw_p) if raw_p else {}
            except Exception as e:
                logger.error(f"[Chat Agent‑compare] Error with price_policy key {pkey}: {e}", exc_info=True)

        # 3c) If nothing is retrieved from Redis, use the selected hotel from the payload as fallback
        if not general_data and idx < len(chosen):
            merged = chosen[idx]
        else:
            merged = {**general_data, **price_data}

        hotels_data.append(merged)

    # 4) Prepare feature lists
    features_1 = hotels_data[0].get("features", []) if len(hotels_data) > 0 else []
    features_2 = hotels_data[1].get("features", []) if len(hotels_data) > 1 else []

    print(f"[Chat Agent‑compare] Hotel 1 : {hotels_data[0]!r}")
    print(f"[Chat Agent‑compare] Hotel 2 : {hotels_data[1]!r}")

    # Get user question from redis conversation cache
    user_id, session_id, _ = get_user_session(payload)
    conv = await get_conversation_async(session_id, user_id)
    if conv is None:
        logger.warning(f"[Chat Agent] Conversation from Redis is None for session_id={session_id}, user_id={user_id}")
        conv = {}
    user_messages = conv.get("user_messages", [])
    question = user_messages[-1].get("user", "") if user_messages else ""
    print(f"[Chat Agent] User question: {question!r}")

    # Get chat history from Redis conversation cache
    chat_history = conv.get("chat_history", "")

    # 5) Create the prompt and call the LLM
    prompt = get_hotel_compare_prompt(hotels_data[0], hotels_data[1], features_1, features_2, question, chat_history)
    content = await call_llm(prompt, HOTEL_ASSISTANT_SYSTEM_MESSAGE)

    await publish_and_stream(
        payload,
        content,
        redis_client,
        redis_channel_publish,
        build_publish_for_hotel_compare,
        build_publish_for_ui,
        hotel_info=chosen,
    )

    return SimpleNamespace(content=content), payload



# # Added flight-specific helper functions
# async def get_flight_search(payload: Dict[str, Any], redis_client, redis_channel_publish: str):
#     text = "Aramak istediğiniz uçuş bilgilerini paylaşabilir misiniz?"
#
#     await publish_and_stream(
#         payload,
#         text,
#         redis_client,
#         redis_channel_publish,
#         build_publish_for_others,
#         build_publish_for_ui,
#     )
#
# async def get_flight_book(payload: Dict[str, Any], redis_client, redis_channel_publish: str):
#     text = "Uçuş rezervasyonu yapmak için gerekli bilgileri paylaşabilir misiniz?"
#
#     await publish_and_stream(
#         payload,
#         text,
#         redis_client,
#         redis_channel_publish,
#         build_publish_for_others,
#         build_publish_for_ui,
#     )
#
# async def get_flight_cancel(payload: Dict[str, Any], redis_client, redis_channel_publish: str):
#     text = "İptal etmek istediğiniz uçuş bilgilerini paylaşabilir misiniz?"
#
#     await publish_and_stream(
#         payload,
#         text,
#         redis_client,
#         redis_channel_publish,
#         build_publish_for_others,
#         build_publish_for_ui,
#     )

async def get_serpapi_search(payload: dict, redis_client, redis_channel_publish: str):
    print("SerpAPI FLOW")

    # Get user question from redis conversation cache
    user_id, session_id, _ = get_user_session(payload)
    conv = await get_conversation_async(session_id, user_id)
    if conv is None:
        logger.warning(f"[Chat Agent] Conversation from Redis is None for session_id={session_id}, user_id={user_id}")
        conv = {}
    user_messages = conv.get("user_messages", [])
    question = user_messages[-1].get("user", "") if user_messages else ""
    print(f"[Chat Agent] User question: {question!r}")

    # The actual result
    serpapi_results = payload.get("orchestration", {}) \
                        .get("actions", {}) \
                        .get("parameters", {}) \
                        .get("serpapi_results", [])

    # The desired location/place to go
    serpapi_keywords = payload.get("orchestration", {}) \
                        .get("actions", {}) \
                        .get("parameters", {}) \
                        .get("serpapi_keywords", [])

    # The location of poi
    location = payload.get("orchestration", {}) \
                        .get("actions", {}) \
                        .get("parameters", {}) \
                        .get("locations", [])

    # example: near Galata Tower, Eifell Tower, etc.
    poi = payload.get("orchestration", {}) \
                        .get("actions", {}) \
                        .get("parameters", {}) \
                        .get("poi", [])

    hotel_name = payload.get("orchestration", {}) \
                        .get("actions", {}) \
                        .get("parameters", {}) \
                        .get("hotelQueryName", "")

    # Turn lists into strings for better readability for prompt
    serpapi_keywords_str = ", ".join(serpapi_keywords) if serpapi_keywords else ""
    location_str = ", ".join(location) if location else ""
    poi_str = ", ".join(poi) if poi else ""
    # results_str = json.dumps(serpapi_results, ensure_ascii=False, indent=2) if serpapi_results else ""

    # Get chat history from Redis conversation cache
    chat_history = conv.get("chat_history", "")

    # Build the list of dictionary for place_info message
    place_info_list = [
        {
            "title": r.get("title"),
            "latitude": r.get("coordinates", {}).get("latitude"),
            "longitude": r.get("coordinates", {}).get("longitude"),
            "rating": r.get("rating"),
            "reviews": r.get("reviews"),
            "address": r.get("address"),
            "thumbnail": r.get("thumbnail"),
            "website": r.get("website"),
        }
        for r in serpapi_results
    ]

    # Drop the 'website', 'thumbnail', 'photos_link', 'serpapi_thumbnail' keys if they exist
    for result in serpapi_results:
        result.pop("website", None)
        result.pop("thumbnail", None)
        result.pop("photos_link", None)
        result.pop("serpapi_thumbnail", None)

    print(f"[Chat Agent] SerpAPI results: {serpapi_results!r}")

    prompt = get_serpapi_search_prompt(user_question=question,
                                       serpapi_results=serpapi_results,
                                       serpapi_keywords=serpapi_keywords_str,
                                       location=location_str,
                                       poi=poi_str,
                                       hotel_name=hotel_name,
                                       chat_history=chat_history)

    content = await call_llm(prompt)

    # Publish response to Redis
    await publish_and_stream(
        payload,
        content,
        redis_client,
        redis_channel_publish,
        build_publish_for_others, # TODO: ...
        build_publish_for_serpapi,
        hotel_info=place_info_list
    )

    return SimpleNamespace(content=content), payload


async def get_hotel_similar(payload: Dict, redis_client, redis_channel_publish: str):
    print("Handling hotel similarity")

    meta = payload.get("metadata", {})
    general_keys = meta.get("redis_cache_address_general_info", [])
    price_keys = meta.get("redis_cache_address_price_policy", [])

    print(f"General keys are: {general_keys!r}")
    print(f"Price keys are: {price_keys!r}")

    # 2) Get the hotels selected by the user (fallback)
    hotels_raw = payload.get("orchestration", {}) \
        .get("actions", {}) \
        .get("parameters", {}) \
        .get("chosen_hotels", [])

    hotel_names = [h["hotel_name"] for h in hotels_raw] if isinstance(hotels_raw, list) else []

    if isinstance(hotels_raw, list):
        hotels_list = hotels_raw
    elif hotels_raw is None:
        hotels_list = []
    else:
        hotels_list = [hotels_raw]

    # For each hotel, fetch general and price data from Redis, parse JSON, and merge
    fetched = []
    for idx, gkey in enumerate(general_keys):
        try:
            raw_g = await redis_client.get(gkey)
            general_data = json.loads(raw_g) if raw_g else {}
        except Exception as e:
            logger.error(f"[Chat Agent] Error fetching/parsing general info for key {gkey}: {e}", exc_info=True)
            general_data = {}

        # If the price-policy key matches, fetch it; otherwise, use an empty dict
        price_data = {}
        if idx < len(price_keys):
            pkey = price_keys[idx]
            try:
                raw_p = await redis_client.get(pkey)
                price_data = json.loads(raw_p) if raw_p else {}
            except Exception as e:
                logger.error(f"[Chat Agent] Error fetching/parsing price policy for key {pkey}: {e}", exc_info=True)

        # If this hotel exists in the fetched list (name matches), add it
        name = general_data.get("name")
        if name and name in hotel_names:
            # merge: overwrite price_data
            merged = {**general_data, **price_data}
            fetched.append(merged)

    if not fetched:
        logger.warning(
            f"[Chat Agent] No hotels fetched from Redis (keys: {general_keys}), falling back to payload hotels.")

    # Retrieve the user's question
    user_id, session_id, _ = get_user_session(payload)
    conv = await get_conversation_async(session_id, user_id) or {}

    user_messages = conv.get("user_messages", [])
    question = user_messages[-1].get("user", "") if user_messages else ""

    print(f"[Chat Agent] User question 2: {question!r}")

    # 5) Prepare the prompt — first from Redis data, otherwise from payload
    hotel_input = fetched if fetched else hotels_raw

    print(f"HOTEL INPUT: {hotel_input!r}")

    # If the postQuery has 'cheap' label, find the cheapest hotel in list and generate a different message
    post_query = payload.get("orchestration", {}).get("actions", {}).get("parameters", {}).get("filled_slots", {}).get(
        "postQuery", [])

    # Get chat history from Redis conversation cache
    chat_history = conv.get("chat_history", "")

    prompt = get_hotel_similar_prompt(hotel_input, question, chat_history)

    # LLM call
    content = await call_llm(prompt, HOTEL_ASSISTANT_SYSTEM_MESSAGE)

    await publish_and_stream(
        payload,
        content,
        redis_client,
        redis_channel_publish,
        build_publish_for_hotel_list,
        build_publish_for_ui,
        hotel_info=hotels_list,
    )
