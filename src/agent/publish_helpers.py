from typing import Dict


def build_publish_for_answer(payload: Dict, system_message) -> Dict:
    # increment trace_id and sequence by 1
    ti = payload["trace_info"].copy()
    ti["trace_id"] = ti["trace_id"] + 1
    ti["sequence"] = ti["sequence"] + 1
    ti["retry_count"] = ti.get("retry_count", 0)

    # slot‐filling phase info
    filled   = payload["orchestration"]["actions"]["parameters"]["filled_slots"]
    to_collect = payload["orchestration"]["actions"]["parameters"]["slots_to_collect"]
    # remove any LLM_outputText key
    filled_clean = {k: v for k, v in filled.items() if k != "LLM_outputText"}
    pending = [s for s in to_collect if s not in filled_clean]

    meta = payload["metadata"].copy()
    meta["source_service"] = "chat-agent"

    publish = {
        "session_id":   payload["session_id"],
        "message_id":   payload["message_id"],
        "timestamp":    payload["timestamp"],
        "version":      payload["version"],
        "trace_info":   ti,
        "metadata":     meta,
        "state": {
            "current": {
                "user_input": payload["state"]["current"]["user_input"],
                "intent_phase": payload["state"]["current"]["intent_phase"],
                "slot_filling_phase": {
                    "status":        "in_progress",
                    "filled_slots":  filled_clean,
                    "pending_slots": pending,
                }
            },
            "previous_transition": payload["state"]["transition"],
            "transition":          "system_message_created"
        },
        "system_message": {
            "text":     system_message.content,
            "language": payload["metadata"]["language"]
        }
    }
    return publish



def build_publish_for_confirmation(payload: Dict, system_text: str) -> Dict:

    ti = payload["trace_info"].copy()
    ti["trace_id"] = ti["trace_id"] + 1
    ti["sequence"] = ti["sequence"] + 1
    ti["retry_count"] = ti.get("retry_count", 0)

    params = payload["orchestration"]["actions"]["parameters"]["parameters_to_confirm"]

    meta = payload["metadata"].copy()
    meta["source_service"] = "chat-agent"

    publish = {
        "session_id": payload["session_id"],
        "message_id": payload["message_id"],
        "timestamp":  payload["timestamp"],
        "version":    payload["version"],
        "trace_info": ti,
        "metadata":   meta,
        "state": {
            "current": {
                "confirmation_phase": {
                    "status":               "pending",
                    "action_to_confirm":    "search_hotels",
                    "parameters_to_confirm": params
                }
            },
            "previous_transition": payload["state"]["transition"],
            "transition":          "awaiting_confirmation"
        },
        "system_message": {
            "text":     system_text,
            "language": payload["metadata"]["language"]
        }
    }
    return publish


def build_publish_for_hotels(payload: Dict, system_text: str) -> Dict:
    ti = payload["trace_info"].copy()
    ti["trace_id"] = ti["trace_id"] + 1
    ti["sequence"] = ti["sequence"] + 1
    ti["retry_count"] = ti.get("retry_count", 0)

    params = payload["orchestration"]["actions"].get("parameters", {})
    total = params.get("total_results_count", 0)
    raw_hotels = params.get("chosen_hotels", [])
    # normalize to list
    if isinstance(raw_hotels, list):
        hotels = raw_hotels
    elif raw_hotels:
        hotels = [raw_hotels]
    else:
        hotels = []

    meta = payload["metadata"].copy()
    meta["source_service"] = "chat-agent"

    publish = {
        "session_id": payload["session_id"],
        "message_id": payload["message_id"],
        "timestamp":  payload["timestamp"],
        "version":    payload["version"],
        "trace_info": ti,
        "metadata":   meta,
        "state": {
            "total_results_count": total,
            "results_in_message": {
                "chosen_hotels": hotels
            },
            "previous_transition": payload["state"].get("previous_transition"),
            "transition":          payload["state"].get("transition", "request_chat_show_hotels")
        },
        "system_message": {
            "text":     system_text,
            "language": payload["metadata"]["language"]
        }
    }

    return publish


def build_publish_out_of_scope(payload: Dict, system_text: str) -> Dict:
    ti = payload["trace_info"].copy()
    ti["trace_id"] = ti["trace_id"] + 1
    ti["sequence"] = ti["sequence"] + 1
    ti["retry_count"] = ti.get("retry_count", 0)

    meta = payload["metadata"].copy()
    meta["source_service"] = "chat-agent"

    publish = {
        "session_id": payload["session_id"],
        "message_id": payload["message_id"],
        "timestamp":  payload["timestamp"],
        "version":    payload["version"],
        "trace_info": ti,
        "metadata":   meta,
        "state": {
            "previous_transition": payload["state"]["previous_transition"],
            "transition":          "out_of_scope"
        },
        "system_message": {
            "text":     system_text,
            "language": payload["metadata"]["language"]
        }
    }
    return publish


def build_publish_rejection(payload: Dict, system_text: str) -> Dict:
    ti = payload["trace_info"].copy()
    ti["trace_id"] = ti["trace_id"] + 1
    ti["sequence"] = ti["sequence"] + 1
    ti["retry_count"] = ti.get("retry_count", 0)

    meta = payload["metadata"].copy()
    meta["source_service"] = "chat-agent"

    filled = payload["orchestration"]["actions"]["parameters"].get("filled_slots", {})
    to_collect = payload["orchestration"]["actions"]["parameters"].get("slots_to_collect", [])
    filled_clean = {k: v for k, v in filled.items() if k != "LLM_outputText"}
    pending = [s for s in to_collect if s not in filled_clean]

    publish = {
        "session_id": payload["session_id"],
        "message_id": payload["message_id"],
        "timestamp":  payload["timestamp"],
        "version":    payload["version"],
        "trace_info": ti,
        "metadata":   meta,
        "state": {
            "previous_transition": payload["state"]["previous_transition"],
            "transition":          "refill_after_rejection",
            "slot_filling_phase": {
                "status":        "rejected",
                "filled_slots":  filled_clean,
                "pending_slots": pending,
            }
        },
        "system_message": {
            "text":     system_text,
            "language": payload["metadata"]["language"]
        }
    }
    return publish

# gateway
def build_publish_for_ui(payload: Dict, system_text: str, hotels: list[str]) -> Dict:

    message = {
        "end": "True",
        "user_id": payload["metadata"]["user_id"],
        "session_id": payload["session_id"],
        "sequence": payload["trace_info"]["sequence"] + 1,
        "trace_id": payload["trace_info"]["trace_id"] + 1,
        "message_id": payload["message_id"],
        "response": "chat",
        "chat": system_text,
        "hotel_info": hotels,
        "system_message": ""
    }

    return message

def build_publish_for_serpapi(payload: Dict, system_text: str, places: list[dict]) -> Dict:

    message = {
        "end": "True",
        "user_id": payload["metadata"]["user_id"],
        "session_id": payload["session_id"],
        "sequence": payload["trace_info"]["sequence"] + 1,
        "trace_id": payload["trace_info"]["trace_id"] + 1,
        "message_id": payload["message_id"],
        "response": "chat",
        "chat": system_text,
        "place_info": places,
        "system_message": ""
    }

    return message


def build_publish_for_detail(payload: Dict, system_text: str) -> Dict:
    ti = payload["trace_info"].copy()
    ti["trace_id"] += 1
    ti["sequence"] += 1
    ti["retry_count"] = ti.get("retry_count", 0)

    meta = payload["metadata"].copy()
    meta["source_service"] = "chat_agent"

    # chosen_hotel = payload["orchestration"]["actions"]["parameters"]["chosen_hotels"]
    current_state = {
        "intent_phase": {
            "intent": "hotel_detail_ask_followup",
            "status": "in_progress",
            "entities": {}
        },
        "cache_check_phase": {
            "status": "cache_hit",
            # "redis_cache_address": payload["metadata"]["redis_cache_address"][0],
            "hotel_found": "", # TODO: fill with actual hotel name
            "cache_timestamp": ""
        }
    }

    publish = {
        "session_id": payload["session_id"],
        "message_id": payload["message_id"],
        "timestamp": payload["timestamp"],
        "version": payload["version"],
        "trace_info": ti,
        "metadata": meta,
        "state": {
            "current": current_state,
            "previous_transition": payload["state"].get("previous_transition", ""),
            "transition": "cache_hit_response_ready"
        },
        "system_message": {
            "text": system_text,
            "language": payload["metadata"]["language"],
            "response_time_ms": ""  # TODO: calculate or fill elsewhere
        }
    }

    return publish



def build_publish_for_hotel_list(payload: Dict, system_text: str) -> Dict:
    # increment trace_id and sequence by 1
    ti = payload["trace_info"].copy()
    ti["trace_id"] = ti["trace_id"] + 1
    ti["sequence"] = ti["sequence"] + 1
    ti["retry_count"] = ti.get("retry_count", 0)

    # slot‐filling phase info
    # filled   = payload["orchestration"]["actions"]["parameters"]["filled_slots"]
    # to_collect = payload["orchestration"]["actions"]["parameters"]["slots_to_collect"]
    # remove any LLM_outputText key
    # filled_clean = {k: v for k, v in filled.items() if k != "LLM_outputText"}
    # pending = [s for s in to_collect if s not in filled_clean]

    meta = payload["metadata"].copy()
    meta["source_service"] = "chat-agent"

    publish = {
        "session_id":   payload["session_id"],
        "message_id":   payload["message_id"],
        "timestamp":    payload["timestamp"],
        "version":      payload["version"],
        "trace_info":   ti,
        "metadata":     meta,
        "state": {
            "current": {
                "user_input": payload["state"]["current"]["user_input"],
                "intent_phase": payload["state"]["current"]["intent_phase"],
                "slot_filling_phase": {
                    "status":        "in_progress",
                }
            },
            "previous_transition": payload["state"]["transition"],
            "transition":          "system_message_created"
        },
        "system_message": {
            "text":     system_text,
            "language": payload["metadata"]["language"]
        }
    }
    return publish



def build_publish_for_others(payload: Dict, system_text: str) -> Dict:
    ti = payload["trace_info"].copy()
    ti["trace_id"] = ti["trace_id"] + 1
    ti["sequence"] = ti["sequence"] + 1
    ti["retry_count"] = ti.get("retry_count", 0)

    meta = payload["metadata"].copy()
    meta["source_service"] = "chat-agent"

    publish = {
        "session_id": payload["session_id"],
        "message_id": payload["message_id"],
        "timestamp":  payload["timestamp"],
        "version":    payload["version"],
        "trace_info": ti,
        "metadata":   meta,
        "state": {
            "previous_transition": payload["state"]["previous_transition"],
            "transition":          "others"
        },
        "system_message": {
            "text":     system_text,
            "language": payload["metadata"]["language"]
        }
    }
    return publish




def build_publish_for_show_hotels(payload: Dict, system_message_text: str) -> Dict:
    """Build the publish JSON for the show_hotels action based on the given payload."""
    # increment trace_id and sequence by 1
    ti = payload["trace_info"].copy()
    ti["trace_id"] = ti.get("trace_id", 0) + 1
    ti["sequence"] = ti.get("sequence", 0) + 1
    ti["retry_count"] = ti.get("retry_count", 0)

    # update flow name to include suffix
    flow = payload["trace_info"].get("flow", "")
    ti["flow"] = f"{flow}_flow"

    # copy metadata and set source_service
    meta = payload["metadata"].copy()
    meta["source_service"] = "chat-agent"

    # extract orchestration details
    orch = payload["orchestration"]["actions"]
    params = orch.get("parameters", {})

    # prepare state with results
    chosen = params.get("chosen_hotels")
    results_list = chosen if isinstance(chosen, list) else [chosen]

    state = {
        "total_results_count": params.get("total_results_count"),
        # "redis_cache_address": payload["metadata"].get("redis_cache_address", None),
        "results_in_message": {"chosen_hotels": results_list},
        "previous_transition": payload["state"].get("transition"),
        "transition": "chat_show_hotels"
    }

    # assemble publish payload
    publish = {
        "session_id": payload.get("session_id"),
        "message_id": payload.get("message_id"),
        "timestamp": payload.get("timestamp"),
        "version": payload.get("version"),
        "trace_info": ti,
        "metadata": meta,
        "state": state,
        "system_message": {
            "text": system_message_text,
            "language": payload.get("metadata", {}).get("language")
        }
    }
    return publish


def build_publish_for_hotel_compare(payload: Dict, system_message_text: str) -> Dict:
    trace_info = payload.get("trace_info", {})
    trace_info["trace_id"] = trace_info.get("trace_id", 0) + 1
    trace_info["sequence"] = trace_info.get("sequence", 0) + 1

    metadata = payload.get("metadata", {})
    metadata["source_service"] = "chat_agent"

    state = {
        "total_results_count": len(payload.get("orchestration", {}).get("actions", {}).get("parameters", {}).get("chosen_hotels", [])),
        # "redis_cache_address": metadata.get("redis_cache_address", [])[0],
        "results_in_message": {
            "chosen_hotels": payload.get("orchestration", {}).get("actions", {}).get("parameters", {}).get("chosen_hotels", [])
        },
        "previous_transition": payload.get("state", {}).get("transition"),
        "transition": "chat_show_hotels"
    }

    publish = {
        "session_id": payload.get("session_id"),
        "message_id": payload.get("message_id"),
        "timestamp": payload.get("timestamp"),
        "version": payload.get("version"),
        "trace_info": trace_info,
        "metadata": metadata,
        "state": state,
        "system_message": {
            "text": system_message_text,
            "language": payload.get("metadata", {}).get("language")
        }
    }

    return publish


#####################################################################################################################
# FLIGHT PUBLISH BUILDERS
#####################################################################################################################

def build_publish_for_flight_slot(payload: Dict, system_message_text: str) -> Dict:
    ti = payload["trace_info"].copy()
    ti["trace_id"] = ti["trace_id"] + 1
    ti["sequence"] = ti["sequence"] + 1
    ti["retry_count"] = ti.get("retry_count", 0)

    # slot‐filling phase info
    filled   = payload["orchestration"]["actions"]["parameters"]["filled_slots"]
    to_collect = payload["orchestration"]["actions"]["parameters"]["slots_to_collect"]
    # remove any LLM_outputText key
    filled_clean = {k: v for k, v in filled.items() if k != "LLM_outputText"}
    pending = [s for s in to_collect if s not in filled_clean]

    meta = payload["metadata"].copy()
    meta["source_service"] = "chat-agent"

    publish = {
        "session_id":   payload["session_id"],
        "message_id":   payload["message_id"],
        "timestamp":    payload["timestamp"],
        "version":      payload["version"],
        "trace_info":   ti,
        "metadata":     meta,
        "state": {
            "current": {
                "user_input": payload["state"]["current"]["user_input"],
                "intent_phase": payload["state"]["current"]["intent_phase"],
                "slot_filling_phase": {
                    "status":        "in_progress",
                    "filled_slots":  filled_clean,
                    "pending_slots": pending,
                }
            },
            "previous_transition": payload["state"]["transition"],
            "transition":          "system_message_created"
        },
        "system_message": {
            "text":     system_message_text,
            "language": payload["metadata"]["language"]
        }
    }
    return publish


def build_publish_for_flight_search(payload: Dict, system_message_text: str) -> Dict:
    ti = payload["trace_info"].copy()
    ti["trace_id"] = ti.get("trace_id", 0) + 1
    ti["sequence"] = ti.get("sequence", 0) + 1
    ti["retry_count"] = ti.get("retry_count", 0)

    meta = payload["metadata"].copy()
    meta["source_service"] = "chat-agent"

    params = payload["orchestration"]["actions"].get("parameters", {})
    total = params.get("total_results_count", 0)
    raw_flights = params.get("chosen_flights", [])
    # normalize to list
    # if isinstance(raw_flights, list):
    #     flights = raw_flights
    # elif raw_flights:
    #     flights = [raw_flights]
    # else:
    #     flights = []

    publish = {
        "session_id": payload["session_id"],
        "message_id": payload["message_id"],
        "timestamp":  payload["timestamp"],
        "version":    payload["version"],
        "trace_info": ti,
        "metadata":   meta,
        "state": {
            "total_results_count": total,
            "results_in_message": {
                "chosen_flights": raw_flights
            },
            "previous_transition": payload.get("state", {}).get("transition"),
            "transition": "chat_show_flight"
        },
        "system_message": {
            "text":     system_message_text,
            "language": payload["metadata"]["language"]
        }
    }

    return publish





