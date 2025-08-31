# import json
# import re
# from types import SimpleNamespace
# from typing import Dict
# import redis.asyncio as aioredis
# from typing import Optional, Any
# import time
#
# import openai
# from langchain_openai import ChatOpenAI
#
# from src.agent.publish_helpers import build_publish_for_answer, build_publish_for_confirmation, \
#     build_publish_for_hotels, build_publish_rejection, build_publish_for_ui, build_publish_for_detail, \
#     build_publish_for_hotel_list, build_publish_for_others, build_publish_for_show_hotels, build_publish_for_hotel_compare
# from src.config.config import AppConfig
# from src.prompt_lib.hotel_prompts import get_hotel_list_prompt, get_hotel_detail_prompt, \
#     get_hotel_feature_response_prompt, get_hotel_list_with_descriptions_prompt, get_hotel_detail_single_answer_prompt, \
#     get_slot_fixing_prompt, get_hotel_compare_prompt, get_empty_hotels_prompt
# from src.runner.streaming import session_queues
# from src.utils import logger
#
#
# MODEL_NAME = "gpt-4o-mini"
#
#
# async def get_answer(payload: dict, redis_client, redis_channel_publish: str):
#     """
#     1) Build the hotel‐list prompt via get_hotel_list_prompt()
#     2) Invoke ChatOpenAI directly with that prompt
#     3) Stream the LLM's response in 3‐word chunks
#     """
#
#     user_id    = payload["metadata"]["user_id"]
#     session_id = payload["session_id"]
#     session_key = f"{user_id}_{session_id}"
#
#     # # ensure the in‐memory queue exists
#     # if session_key not in session_queues:
#     #     session_queues[session_key] = Queue()
#
#     # 1) build prompt strictly via your helper
#     missing_fields: list[str] = payload.get("orchestration", {}).get("actions", {}).get("parameters", {}).get("slots_to_collect", [])
#     logger.info(f"[Chat Agent] Missing fields: {missing_fields!r}")
#     context: str = payload.get("state", {}).get("current", {}).get("conversation_context", "")
#
#     intent_from_orch = payload.get("state", {}).get("current", {}).get("intent_phase", {}).get("intent", "unknown")
#
#     prompt_str = ""
#
#     if intent_from_orch == "hotel_list":
#         prompt_str = get_hotel_list_prompt(missing_fields, context)
#
#     elif intent_from_orch == "hotel_detail":
#         prompt_str = get_hotel_detail_prompt(missing_fields, context)
#
#
#     # # 2) call the LLM directly
#     # llm = get_llm()
#     # ai_message = llm.invoke([HumanMessage(content=prompt_str)])
#     # content = ai_message.content
#
#     # prepare messages for the API
#     messages = [{"role": "user", "content": prompt_str}]
#
#     # 2) invoke the OpenAI Chat Completions API
#     openai.api_key = AppConfig.OPENAI_API_KEY
#     start_time = time.time()
#     response = openai.chat.completions.create(
#         model=MODEL_NAME,
#         messages=messages,
#         temperature=0.7
#     )
#     end_time = time.time()
#     logger.info(f"[Chat Agent] Response time: {end_time - start_time:.2f} seconds")
#     content = response.choices[0].message.content
#
#     # wrap into a simple object so build_publish_for_answer can read .content
#     ai_message = SimpleNamespace(content=content)
#     logger.info(f"[Chat Agent] LLM response: {content!r}")
#
#     # publish the orchestrated answer JSON
#     publish_chat_state = build_publish_for_answer(payload, ai_message)
#     logger.info(f"[Chat Agent] Publish state: {publish_chat_state}")
#     await redis_client.publish(redis_channel_publish, json.dumps(publish_chat_state))
#
#     hotel_info = []
#
#     publish_ui = build_publish_for_ui(payload, content, hotel_info)
#     logger.info(f"[Chat Agent] Publish UI: {publish_ui}")
#     await redis_client.publish("gateway", json.dumps(publish_ui, ensure_ascii=False))
#
#     # 3) enqueue 3-word chunks
#     for chunk in chunker(content):
#         session_queues[session_key].put({"chunk": chunk})
#         print(f"[Chat Agent] queued confirmation chunk for {session_key!r}: {chunk!r}")
#     session_queues[session_key].put({"done": True})
#     print(f"[Chat Agent] queued DONE for {session_key!r}")
#
#     return ai_message, payload
#
#
# # async def get_list_answer(payload: dict, redis_client, redis_channel_publish: str):
# #
# #     user_id = payload["metadata"]["user_id"]
# #     session_id = payload["session_id"]
# #     session_key = f"{user_id}_{session_id}"
# #
# #     prompt_str = ""
# #
# #     # prepare messages for the API
# #     messages = [{"role": "user", "content": prompt_str}]
# #
# #     # 2) invoke the OpenAI Chat Completions API
# #     openai.api_key = AppConfig.OPENAI_API_KEY
# #     start_time = time.time()
# #     response = openai.chat.completions.create(
# #         model=MODEL_NAME,
# #         messages=messages,
# #         temperature=0.7
# #     )
# #     end_time = time.time()
# #     logger.info(f"[Chat Agent] Response time: {end_time - start_time:.2f} seconds")
# #     content = response.choices[0].message.content
# #
# #     # wrap into a simple object so build_publish_for_answer can read .content
# #     ai_message = SimpleNamespace(content=content)
# #     logger.info(f"[Chat Agent] LLM response: {content!r}")
# #
# #     # publish the orchestrated answer JSON
# #     publish = build_publish_for_answer(payload, ai_message)
# #     await redis_client.publish(redis_channel_publish, json.dumps(publish))
# #
# #     # 3) enqueue 3-word chunks
# #     for chunk in chunker(content):
# #         session_queues[session_key].put({"chunk": chunk})
# #         print(f"[Chat Agent] queued confirmation chunk for {session_key!r}: {chunk!r}")
# #     session_queues[session_key].put({"done": True})
# #     print(f"[Chat Agent] queued DONE for {session_key!r}")
# #
# #     return ai_message, payload
#
#
# async def get_confirmation(payload: Dict, redis_client, redis_channel_publish: str):
#     """
#     Build and publish a fixed confirmation prompt based on
#     payload["orchestration"]["actions"]["parameters"]["normalized_parameters"].
#     Also stream to session_queue.
#     """
#     user_id    = payload["metadata"]["user_id"]
#     session_id = payload["session_id"]
#     session_key = f"{user_id}_{session_id}"
#
#     # # If the session queue doesn't exist, create it
#     # if session_key not in session_queues:
#     #     session_queues[session_key] = Queue()
#
#     params = payload["orchestration"]["actions"]["parameters"]["parameters_to_confirm"]
#
#     # Build a simple bullet list of only the non-empty parameters
#     hotel_list = [
#         f"- {key}: {value}"
#         for key, value in params.items()
#         if value  # skip empty strings
#     ]
#
#     # TODO: Make the answer better
#     # Prepend the question and join with newlines
#     text = "Bu özellikleri onaylıyor musunuz?\n" + "\n".join(hotel_list)
#     # text = f"Bu özellikleri onaylıyor musunuz: {params}?"
#
#     # 1) publish orchestration JSON
#     publish = build_publish_for_confirmation(payload, text)
#     await redis_client.publish(redis_channel_publish, json.dumps(publish))
#
#     hotel_info = []
#
#     publish_ui = build_publish_for_ui(payload, text, hotel_info)
#     logger.info(f"[Chat Agent] Publish UI: {publish_ui}")
#     await redis_client.publish("gateway", json.dumps(publish_ui, ensure_ascii=False))
#
#     # 2) stream confirmation question
#     for chunk in chunker(text):
#         session_queues[session_key].put({"chunk": chunk})
#         print(f"[Chat Agent] queued confirmation chunk for {session_key!r}: {chunk!r}")
#     session_queues[session_key].put({"done": True})
#     print(f"[Chat Agent] queued DONE for {session_key!r}")
#
#
# # hotels_from_json: gateway için 'hotel_info' olarak göndereceğim mesaj
# # hotels: llm mesajı üretmek için kullanacağım mesaj -> redis cache’den geliyor
# # TODO: mesaj içine gömme yerine, gateway publish için ayrı bir key açılacak ve chosen_hotels gönderilecek.
# async def get_requested_hotels(payload: Dict, redis_client, redis_channel_publish: str):
#
#     user_id     = payload["metadata"]["user_id"]
#     session_id  = payload["session_id"]
#     session_key = f"{user_id}_{session_id}"
#
#     # Get user question and Redis cache key from payload
#     # user_question = payload["orchestration"]["actions"]["parameters"]["user_query"]
#     redis_cache_key = payload.get("orchestration", {}).get("actions", {}).get("redis_cache_address")
#     logger.info(f"Payload orchestration actions: {payload.get('orchestration', {}).get('actions', {})}")
#     logger.info(f"Extracted redis_cache_key: {redis_cache_key}")
#
#     if redis_cache_key is None:
#         logger.error(f"Redis cache key is None for session_key: {session_key}")
#
#     # Get hotels from payload
#     hotels_raw = payload.get("orchestration", {}).get("actions", {}).get("parameters", {}).get("chosen_hotels", [])
#     print(f"[Chat Agent] Hotels from JSON: {hotels_raw!r}")
#
#     # Get hotel names from the payload hotels
#     hotel_names = [h["hotel_name"] for h in hotels_raw]
#
#     # Get features from Redis cache
#     raw = await redis_client.get(redis_cache_key)  # Ensure raw is awaited
#     if not raw:
#         hotels = []
#         logger.warning(f"[Chat Agent - requested hotels] Redis cache not found for {session_key!r}")
#     else:
#         data = json.loads(raw)  # Decode raw to string before loading JSON
#         hotels_full = data.get("hotels", [])
#
#         # hotels = hotels_full[0:5]  # Limit to first 5 hotels
#
#         filtered_hotels = []
#         for name in hotel_names:
#             for h in hotels_full:
#                 if h.get("name") == name:
#                     filtered_hotels.append(h)
#                     break
#
#         hotels = filtered_hotels
#
#         logger.info(f"[Chat Agent - requested hotels] Retrieved hotels from Redis cache: {hotels!r}")
#
#     if isinstance(hotels_raw, list):
#         hotels_from_json = hotels_raw
#     elif hotels_raw is None:
#         hotels_from_json = []
#     else:
#         hotels_from_json = [hotels_raw]
#
#     ############
#
#     if not hotels:
#         prompt_str = get_hotel_list_with_descriptions_prompt(hotels_from_json)
#     else:
#         prompt_str = get_hotel_list_with_descriptions_prompt(hotels)
#
#     # prepare messages for the API
#     messages = [{"role": "user", "content": prompt_str}]
#
#     # 2) invoke the OpenAI Chat Completions API
#     openai.api_key = AppConfig.OPENAI_API_KEY
#     start_time = time.time()
#     response = openai.chat.completions.create(
#         model=MODEL_NAME,
#         messages=messages,
#         temperature=0.7
#     )
#     end_time = time.time()
#     logger.info(f"[Chat Agent] Response time: {end_time - start_time:.2f} seconds")
#     content = response.choices[0].message.content
#
#
#     # hotels_standard = transform_hotels(hotels_from_json)
#
#     #new_content = embed_hotel_data_by_bold(content, hotels_from_json)
#     # print(f"[Chat Agent] New content with embedded hotel data: {new_content!r}")
#
#     # wrap into a simple object so build_publish_for_answer can read .content
#     ai_message = SimpleNamespace(content=content)
#     logger.info(f"[Chat Agent] LLM response: {content!r}")
#
#     # publish the orchestrated answer JSON
#     publish = build_publish_for_hotel_list(payload, content)
#     await redis_client.publish(redis_channel_publish, json.dumps(publish))
#
#     publish_ui = build_publish_for_ui(payload, content, hotels_from_json)
#     logger.info(f"[Chat Agent] Publish UI: {publish_ui}")
#     await redis_client.publish("gateway", json.dumps(publish_ui, ensure_ascii=False))
#
#
#
#     # 3) enqueue 3-word chunks
#     for chunk in chunker(content):
#         session_queues[session_key].put({"chunk": chunk})
#         print(f"[Chat Agent] queued confirmation chunk for {session_key!r}: {chunk!r}")
#     session_queues[session_key].put({"done": True})
#     print(f"[Chat Agent] queued DONE for {session_key!r}")
#
#     return ai_message, payload
#
#
#
# async def get_out_of_scope(payload: Dict, redis_client, redis_channel_publish: str):
#     """
#     Handle out of scope logic here.
#     For now, just send a fixed message to the user.
#     """
#     user_id     = payload["metadata"]["user_id"]
#     session_id  = payload["session_id"]
#     session_key = f"{user_id}_{session_id}"
#
#     text = "Üzgünüm, bu isteğe yardımcı olamam. Başka bir şey sormak ister misiniz?"
#
#     # 1) publish orchestration JSON
#     publish = build_publish_for_hotels(payload, text)
#     await redis_client.publish(redis_channel_publish, json.dumps(publish))
#
#     hotel_info = []
#
#     publish_ui = build_publish_for_ui(payload, text, hotel_info)
#     logger.info(f"[Chat Agent] Publish UI: {publish_ui}")
#     await redis_client.publish("gateway", json.dumps(publish_ui, ensure_ascii=False))
#
#     # 2) stream out the out of scope message
#     for chunk in chunker(text):
#         session_queues[session_key].put({"chunk": chunk})
#         print(f"[Chat Agent] queued out of scope chunk for {session_key!r}: {chunk!r}")
#     session_queues[session_key].put({"done": True})
#     print(f"[Chat Agent] queued DONE for {session_key!r}")
#
#
# async def get_rejection(payload: Dict, redis_client, redis_channel_publish: str):
#     """
#     Handle rejection logic here.
#     For now, just send a fixed message to the user.
#     """
#     user_id     = payload["metadata"]["user_id"]
#     session_id  = payload["session_id"]
#     session_key = f"{user_id}_{session_id}"
#
#     text = "Onayınız reddedildi. İstediğiniz kriterleri tekrar eder misiniz? Otel adı, konum, tarih gibi bilgileri verebilirsiniz."
#
#     publish = build_publish_rejection(payload, text)
#     await redis_client.publish(redis_channel_publish, json.dumps(publish))
#
#     hotel_info = []
#
#     publish_ui = build_publish_for_ui(payload, text, hotel_info)
#     logger.info(f"[Chat Agent] Publish UI: {publish_ui}")
#     await redis_client.publish("gateway", json.dumps(publish_ui, ensure_ascii=False))
#
#     # 2) stream out the rejection message
#     for chunk in chunker(text):
#         session_queues[session_key].put({"chunk": chunk})
#         print(f"[Chat Agent] queued rejection chunk for {session_key!r}: {chunk!r}")
#     session_queues[session_key].put({"done": True})
#     print(f"[Chat Agent] queued DONE for {session_key!r}")
#
#
# async def get_greeting(payload: Dict, redis_client, redis_channel_publish: str):
#     """
#     Handle greeting logic here.
#     For now, just send a fixed greeting message to the user.
#     """
#     user_id     = payload["metadata"]["user_id"]
#     session_id  = payload["session_id"]
#     session_key = f"{user_id}_{session_id}"
#
#     text = "Merhaba! Size nasıl yardımcı olabilirim?"
#
#     # 1) publish orchestration JSON
#     publish = build_publish_for_others(payload, text)
#     redis_client.publish(redis_channel_publish, json.dumps(publish))
#
#     hotel_info = []
#
#     publish_ui = build_publish_for_ui(payload, text, hotel_info)
#     logger.info(f"[Chat Agent] Publish UI: {publish_ui}")
#     await redis_client.publish("gateway", json.dumps(publish_ui, ensure_ascii=False))
#
#     # 2) stream out the greeting message
#     for chunk in chunker(text):
#         session_queues[session_key].put({"chunk": chunk})
#         print(f"[Chat Agent] queued greeting chunk for {session_key!r}: {chunk!r}")
#     session_queues[session_key].put({"done": True})
#     print(f"[Chat Agent] queued DONE for {session_key!r}")
#
#
# async def get_hotel_detail_answer(payload: Dict, redis_client, redis_channel_publish: str):
#     """
#     Handle cache check logic here.
#     For now, just send a fixed message to the user.
#     """
#     user_id     = payload["metadata"]["user_id"]
#     session_id  = payload["session_id"]
#     session_key = f"{user_id}_{session_id}"
#
#     ############
#
#     # Get Redis cache key from payload
#     redis_cache_key = payload.get("orchestration", {}).get("actions", {}).get("redis_cache_address")
#
#     # Get features from Redis hotel_detail cache
#     features = await redis_client.get(redis_cache_key)  # Ensure features is awaited
#     if features is None:
#         features = []
#         logger.warning(f"[Chat Agent - detail] Redis cache not found for {session_key!r}")
#     else:
#         # features = json.loads(features).get("hotel_detail_ask_general", []).get("all_features", [])
#         features = json.loads(features) # TODO: Now, it takes the whole object, not just features, will discuss later
#
#     logger.info(f"[Chat Agent] Retrieved features from Redis cache: {features!r}")
#
#     # Get user question from Redis conversation cache
#     conv = await get_conversation_async(session_id, user_id)
#     if conv is None:
#         logger.warning(f"[Chat Agent] Conversation from Redis is None for session_id={session_id}, user_id={user_id}")
#         conv = {}
#     print(f"[Chat Agent] Conversation from Redis: {conv!r}")
#
#     user_question = conv.get("chat_data", {}).get("filled_slots", {}).get("LLM_outputText", "")
#
#     # Print the user question and features for debugging
#     logger.info(f"[Chat Agent] User question: {user_question!r}")
#     logger.info(f"[Chat Agent] Features: {features!r}")
#
#     ############
#
#     prompt_str = get_hotel_feature_response_prompt(user_question, features)
#
#     # prepare messages for the API
#     messages = [{"role": "user", "content": prompt_str}]
#
#     # 2) invoke the OpenAI Chat Completions API
#     openai.api_key = AppConfig.OPENAI_API_KEY
#     start_time = time.time()
#     response = openai.chat.completions.create(
#         model=MODEL_NAME,
#         messages=messages,
#         temperature=0.7
#     )
#     end_time = time.time()
#     logger.info(f"[Chat Agent] Response time: {end_time - start_time:.2f} seconds")
#     content = response.choices[0].message.content
#
#     # wrap into a simple object so build_publish_for_answer can read .content
#     ai_message = SimpleNamespace(content=content)
#     logger.info(f"[Chat Agent] LLM response: {content!r}")
#
#     # publish the orchestrated answer JSON
#     publish = build_publish_for_detail(payload, content)
#     await redis_client.publish(redis_channel_publish, json.dumps(publish))
#
#     hotel_info = []
#
#     publish = build_publish_for_ui(payload, content, hotel_info)
#     await redis_client.publish("gateway", json.dumps(publish, ensure_ascii=False))
#
#     # 3) enqueue 3-word chunks
#     for chunk in chunker(content):
#         session_queues[session_key].put({"chunk": chunk})
#         print(f"[Chat Agent] queued confirmation chunk for {session_key!r}: {chunk!r}")
#     session_queues[session_key].put({"done": True})
#     print(f"[Chat Agent] queued DONE for {session_key!r}")
#
#     return ai_message, payload
#
# # TODO: Will add links for this function
# async def get_hotel_single_answer(payload: Dict, redis_client, redis_channel_publish: str):
#
#     user_id = payload["metadata"]["user_id"]
#     session_id = payload["session_id"]
#     session_key = f"{user_id}_{session_id}"
#
#     # Get user question and Redis cache key from payload
#     # user_question = payload["orchestration"]["actions"]["parameters"]["user_query"]
#     redis_cache_key = payload.get("orchestration", {}).get("actions", {}).get("redis_cache_address")
#     logger.info(f"Payload orchestration actions: {payload.get('orchestration', {}).get('actions', {})}")
#     logger.info(f"Extracted redis_cache_key: {redis_cache_key}")
#
#     hotel = payload.get("orchestration", {}).get("actions", {}).get("parameters", {}).get("chosen_hotels", {})
#
#     # Get user question from Redis conversation cache
#     conv = await get_conversation_async(session_id, user_id)
#     if conv is None:
#         logger.warning(f"[Chat Agent] Conversation from Redis is None for session_id={session_id}, user_id={user_id}")
#         conv = {}
#     print(f"[Chat Agent] Conversation from Redis (empty hotels): {conv!r}")
#
#     user_question = conv.get("chat_data", {}).get("filled_slots", {}).get("LLM_outputText", "")
#
#     # Get features from Redis hotel_detail cache
#     features = await redis_client.get(redis_cache_key)  # Ensure features is awaited
#     if features is None:
#         features = []
#         logger.warning(f"[Chat Agent - detail] Redis cache not found for {session_key!r}")
#     else:
#         # features = json.loads(features).get("hotel_detail_ask_general", []).get("all_features", [])
#         features = json.loads(features) # TODO: Now, it takes the whole object, not just features, will discuss later
#
#     hotels_raw = payload.get("orchestration", {}).get("actions", {}).get("parameters", {}).get("chosen_hotels",[])
#     print(f"[Chat Agent] Hotels from JSON: {hotels_raw!r}")
#
#     if isinstance(hotels_raw, list):
#         hotels_from_json = hotels_raw
#     elif hotels_raw is None:
#         hotels_from_json = []
#     else:
#         hotels_from_json = [hotels_raw]
#
#     ############
#
#     prompt_str = get_hotel_detail_single_answer_prompt(hotel, features, user_question)
#
#     # prepare messages for the API
#     messages = [{"role": "user", "content": prompt_str}]
#
#     # 2) invoke the OpenAI Chat Completions API
#     openai.api_key = AppConfig.OPENAI_API_KEY
#     start_time = time.time()
#     response = openai.chat.completions.create(
#         model=MODEL_NAME,
#         messages=messages,
#         temperature=0.7
#     )
#     end_time = time.time()
#     logger.info(f"[Chat Agent] Response time: {end_time - start_time:.2f} seconds")
#     content = response.choices[0].message.content
#
#     # wrap into a simple object so build_publish_for_answer can read .content
#     ai_message = SimpleNamespace(content=content)
#     logger.info(f"[Chat Agent] LLM response: {content!r}")
#
#     # publish the orchestrated answer JSON
#     publish = build_publish_for_show_hotels(payload, content)
#     await redis_client.publish(redis_channel_publish, json.dumps(publish))
#
#     publish_ui = build_publish_for_ui(payload, content, hotels_from_json)
#     logger.info(f"[Chat Agent] Publish UI: {publish_ui}")
#     await redis_client.publish("gateway", json.dumps(publish_ui, ensure_ascii=False))
#
#     # 3) enqueue 3-word chunks
#     for chunk in chunker(content):
#         session_queues[session_key].put({"chunk": chunk})
#         print(f"[Chat Agent] queued confirmation chunk for {session_key!r}: {chunk!r}")
#     session_queues[session_key].put({"done": True})
#     print(f"[Chat Agent] queued DONE for {session_key!r}")
#
#     return ai_message, payload
#
#
# async def get_slot_fixing(payload: Dict, redis_client, redis_channel_publish: str):
#     """
#     Handle slot fixing logic here.
#     For now, just send a fixed message to the user.
#     """
#     user_id     = payload["metadata"]["user_id"]
#     session_id  = payload["session_id"]
#     session_key = f"{user_id}_{session_id}"
#
#     filled_slots_raw = payload.get("orchestration", {}).get("actions", {}).get("parameters", {}).get("filled_slots", {})
#     filled_slots = {k: v for k, v in filled_slots_raw.items() if v}  # Filter out empty values
#
#     prompt_str = get_slot_fixing_prompt(filled_slots)
#
#     # prepare messages for the API
#     messages = [{"role": "user", "content": prompt_str}]
#
#     # 2) invoke the OpenAI Chat Completions API
#     openai.api_key = AppConfig.OPENAI_API_KEY
#     start_time = time.time()
#     response = openai.chat.completions.create(
#         model="gpt-4.1-nano",
#         messages=messages,
#         temperature=0.7
#     )
#     end_time = time.time()
#     logger.info(f"[Chat Agent] Response time: {end_time - start_time:.2f} seconds")
#     content = response.choices[0].message.content
#
#     # wrap into a simple object so build_publish_for_answer can read .content
#     ai_message = SimpleNamespace(content=content)
#     logger.info(f"[Chat Agent] LLM response: {content!r}")
#
#     # publish the orchestrated answer JSON
#     publish = build_publish_for_others(payload, content)
#     await redis_client.publish(redis_channel_publish, json.dumps(publish))
#
#     hotel_info = []
#
#     publish_ui = build_publish_for_ui(payload, content, hotel_info)
#     logger.info(f"[Chat Agent] Publish UI: {publish_ui}")
#     await redis_client.publish("gateway", json.dumps(publish_ui, ensure_ascii=False))
#
#     # 3) enqueue 3-word chunks
#     for chunk in chunker(content):
#         session_queues[session_key].put({"chunk": chunk})
#         print(f"[Chat Agent] queued confirmation chunk for {session_key!r}: {chunk!r}")
#     session_queues[session_key].put({"done": True})
#     print(f"[Chat Agent] queued DONE for {session_key!r}")
#
#     return ai_message, payload
#
#
# async def get_empty_hotels(payload: Dict, redis_client, redis_channel_publish: str):
#     """
#     Handle empty hotels logic here.
#     For now, just send a fixed message to the user.
#     """
#     user_id     = payload["metadata"]["user_id"]
#     session_id  = payload["session_id"]
#     session_key = f"{user_id}_{session_id}"
#     flow = payload.get("trace_info", {}).get("flow", "")
#
#     # Get user question from Redis conversation cache
#     conv = await get_conversation_async(session_id, user_id)
#     if conv is None:
#         logger.warning(f"[Chat Agent] Conversation from Redis is None for session_id={session_id}, user_id={user_id}")
#         conv = {}
#     print(f"[Chat Agent] Conversation from Redis (empty hotels): {conv!r}")
#
#     user_question = conv.get("chat_data", {}).get("filled_slots", {}).get("LLM_outputText", "")
#
#     prompt_str = get_empty_hotels_prompt(user_question)
#
#     # prepare messages for the API
#     messages = [{"role": "user", "content": prompt_str}]
#
#     openai.api_key = AppConfig.OPENAI_API_KEY
#     start_time = time.time()
#     response = openai.chat.completions.create(
#         model="gpt-4.1-nano",
#         messages=messages,
#         temperature=0.7
#     )
#     end_time = time.time()
#     logger.info(f"[Chat Agent] Response time: {end_time - start_time:.2f} seconds")
#     text = response.choices[0].message.content
#
#     # text = "Üzgünüm, istediğiniz kriterlere uygun otel veya otel özelliği bulamadım. Size başka bir konuda yardımcı olabilir miyim?"
#
#     # TODO: This part will be separated later
#     # if "hotel_list" in flow:
#     #     text = "Üzgünüm, istediğiniz kriterlere uygun otel bulamadım. Başka bir şey sormak ister misiniz?"
#     # elif "ask" in flow:
#     #     # Check cache for getting the features
#     #     conv = await get_conversation_async(session_id, user_id)
#     #     print(f"[Chat Agent] Conversation from Redis: {conv!r}")
#     #
#     #     feature_query = conv['chat_data']['filled_slots']['featureQuery']
#     #     print(feature_query)
#     #
#     #     # text = "Üzgünüm, bu otelle ilgili özellik bulamadım. Başka bir şey sormak ister misiniz?"
#     #
#     #     prompt_str = get_hotel_detail_ask_empty_hotel_prompt(feature_query)
#     #
#     #     # prepare messages for the API
#     #     messages = [{"role": "user", "content": prompt_str}]
#     #
#     #     openai.api_key = AppConfig.OPENAI_API_KEY
#     #     start_time = time.time()
#     #     response = openai.chat.completions.create(
#     #         model="gpt-4.1-nano",
#     #         messages=messages,
#     #         temperature=0.7
#     #     )
#     #     end_time = time.time()
#     #     logger.info(f"[Chat Agent] Response time: {end_time - start_time:.2f} seconds")
#     #     text = response.choices[0].message.content
#     #
#     # else:
#     #     text = "Üzgünüm, bu otelin özelliklerine erişemedim. Başka bir şey sormak ister misiniz?"
#
#     publish = build_publish_for_others(payload, text)
#     await redis_client.publish(redis_channel_publish, json.dumps(publish))
#
#     hotel_info = []
#
#     publish_ui = build_publish_for_ui(payload, text, hotel_info)
#     logger.info(f"[Chat Agent] Publish UI: {publish_ui}")
#     await redis_client.publish("gateway", json.dumps(publish_ui, ensure_ascii=False))
#
#     # 2) stream out the empty hotels message
#     for chunk in chunker(text):
#         session_queues[session_key].put({"chunk": chunk})
#         print(f"[Chat Agent] queued empty hotels chunk for {session_key!r}: {chunk!r}")
#     session_queues[session_key].put({"done": True})
#     print(f"[Chat Agent] queued DONE for {session_key!r}")
#
#
# def get_llm():
#     """Initialize and return the LLM instance."""
#     api_key = AppConfig.OPENAI_API_KEY
#     if not api_key:
#         raise ValueError("Missing OPENAI_API_KEY")
#     return ChatOpenAI(model="gpt-4o", api_key=api_key, temperature=0.1)
#
#
# def chunker(text: str, size: int = 3):
#     words = text.split()
#     for i in range(0, len(words), size):
#         chunk = " ".join(words[i : i + size])
#         if i + size < len(words):
#             chunk += " "
#         yield chunk
#
# def get_conversation_from_redis(session_id: str, user_id: str, redis_client):
#
#     redis_key = f"prometa_ai:conversation:{session_id}_{user_id}"
#     existing = redis_client.get(redis_key)
#     return existing
#
#
# async def get_conversation_async(session_id: str, user_id: str) -> Optional[Dict[str, Any]]:
#
#     key = f"prometa_ai:conversation:{session_id}_{user_id}"
#     client = aioredis.Redis(
#         host=AppConfig.REDIS_HOST,
#         port=int(AppConfig.REDIS_PORT),
#         db=int(AppConfig.REDIS_DB),
#         decode_responses=True
#     )
#
#     try:
#         raw = await client.get(key)
#         if not raw:
#             return None
#         return json.loads(raw)
#     except (aioredis.RedisError, json.JSONDecodeError):
#         return None
#
#
# async def get_hotel_compare(payload, redis_client, redis_channel_publish):
#     print("Fetching hotel comparison data")
#     # Example logic for hotel comparison
#
#     user_id = payload["metadata"]["user_id"]
#     session_id = payload["session_id"]
#     session_key = f"{user_id}_{session_id}"
#
#     ############
#     # Get Redis cache key from payload
#     redis_cache_keys = payload.get("orchestration", {}).get("actions", {}).get("redis_cache_address", [])
#
#     if len(redis_cache_keys) >= 2:
#         redis_key_1 = redis_cache_keys[0]
#         redis_key_2 = redis_cache_keys[1]
#     else:
#         redis_key_1 = None
#         redis_key_2 = None
#
#     # Get features from Redis hotel cache
#     features_1 = await redis_client.get(redis_key_1)  # Ensure features is awaited
#     features_2 = await redis_client.get(redis_key_2)
#     if features_1 is None or features_2 is None:
#         features_1 = []
#         features_2 = []
#         logger.warning(f"[Chat Agent - compare] Redis cache not found for {session_key!r}")
#     else:
#         features_1 = json.loads(features_1)
#         features_2 = json.loads(features_2)
#
#     logger.info(f"[Chat Agent - compare] Retrieved features from Redis cache: {features_1!r}, {features_2!r}")
#
#     # Get hotel information from payload
#     chosen_hotels = payload.get("orchestration", {}).get("actions", {}).get("parameters", {}).get("chosen_hotels", {})
#     hotel_1 = chosen_hotels[0]
#     hotel_2 = chosen_hotels[1] if len(chosen_hotels) > 1 else {}
#
#     prompt_str = get_hotel_compare_prompt(hotel_1, hotel_2, features_1, features_2)
#
#     # prepare messages for the API
#     messages = [{"role": "user", "content": prompt_str}]
#
#     # 2) invoke the OpenAI Chat Completions API
#     openai.api_key = AppConfig.OPENAI_API_KEY
#     start_time = time.time()
#     response = openai.chat.completions.create(
#         model=MODEL_NAME,
#         messages=messages,
#         temperature=0.7
#     )
#     end_time = time.time()
#     logger.info(f"[Chat Agent] Response time: {end_time - start_time:.2f} seconds")
#     content = response.choices[0].message.content
#
#     # wrap into a simple object so build_publish_for_answer can read .content
#     ai_message = SimpleNamespace(content=content)
#     logger.info(f"[Chat Agent] LLM response: {content!r}")
#
#     # publish the orchestrated answer JSON
#     publish = build_publish_for_hotel_compare(payload, content)
#     await redis_client.publish(redis_channel_publish, json.dumps(publish))
#
#     hotels_raw = payload.get("orchestration", {}).get("actions", {}).get("parameters", {}).get("chosen_hotels",[])
#     print(f"[Chat Agent] Hotels from JSON: {hotels_raw!r}")
#
#     if isinstance(hotels_raw, list):
#         hotels_from_json = hotels_raw
#     elif hotels_raw is None:
#         hotels_from_json = []
#     else:
#         hotels_from_json = [hotels_raw]
#
#     publish = build_publish_for_ui(payload, content, hotels_from_json)
#     await redis_client.publish("gateway", json.dumps(publish, ensure_ascii=False))
#
#     # 3) enqueue 3-word chunks
#     for chunk in chunker(content):
#         session_queues[session_key].put({"chunk": chunk})
#         print(f"[Chat Agent] queued confirmation chunk for {session_key!r}: {chunk!r}")
#     session_queues[session_key].put({"done": True})
#     print(f"[Chat Agent] queued DONE for {session_key!r}")
#
#     return ai_message, payload
#
#
# def embed_hotel_data_by_bold(content: str, hotels: list[dict]) -> str:
#     """
#     content: LLM'den gelen metin, içinde **Otel Adı** şeklinde bold başlıklar var
#     hotels: her öğesi tüm otel bilgisini taşıyan dict’lerden oluşan liste
#     """
#     hotels_iter = iter(hotels)
#
#     def repl(match: re.Match) -> str:
#         # Sıradaki otel bilgisini al
#         hotel = next(hotels_iter, None)
#         if not hotel:
#             # Eğer listede bittiysen, olduğu gibi bırak
#             return match.group(0)
#
#         # 'hotel_name' anahtarını JSON'dan çıkarıp geri kalan tüm alanları inject edeceğiz
#         data = {k: v for k, v in hotel.items() if k != 'hotel_name'}
#         json_str = json.dumps(data, ensure_ascii=False)
#
#         # **Otel Adı** -> **Otel Adı** {hotel_data: {...}}
#         return f"{match.group(0)} {{hotel_data: {json_str}}}"
#
#     # Bold pattern’ini buluyoruz
#     pattern = re.compile(r"\*\*(?P<title>.+?)\*\*")
#     return pattern.sub(repl, content)
#
#
#
# def transform_hotels(hotels_from_json):
#     converted = []
#     for h in hotels_from_json:
#         # Bölge bilgisi: direkt "zone" varsa onu al, yoksa zone_links içinden
#         zone = h.get("zone")
#         if not zone and h.get("zone_links"):
#             zone = h["zone_links"][0].get("name")
#
#         # Enlem/boylam string ise float’a çevir
#         lat = float(h.get("latitude", 0))
#         long = float(h.get("longitude", 0))
#
#         # Resim URL’lerini path alanından çıkart
#         images = [img.get("path") for img in h.get("images", [])]
#
#         # Yıldız sayısını al (hotel_star → stars)
#         stars = h.get("hotel_star") or h.get("stars")
#
#         # Tip bilgisini büyük harfle başlat
#         type_ = h.get("type", "")
#         type_ = type_.capitalize()  # "hotel" → "Hotel"
#
#         converted.append({
#             "zone": zone,
#             "lat": lat,
#             "long": long,
#             "images": images,
#             "stars": stars,
#             "type": type_
#         })
#     return converted
