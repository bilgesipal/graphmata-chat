from langgraph.graph import StateGraph, END
from src.schemas.schemas import GraphState
from src.agent.node_handlers_hotel import (
    hotel_route_decider,
    handle_slot_collection,
    handle_confirmation_request,
    handle_default,
    handle_show_hotels,
    handle_out_of_scope,
    handle_rejection,
    handle_greeting,
    handle_cache_check,
    handle_answer_single_hotel,
    handle_slot_fixing,
    handle_empty_hotels,
    handle_hotel_compare,
    handle_serpapi_search,
    handle_hotel_similar
)

from src.agent.node_handlers_flight import (
    flight_route_decider,
    handle_slot_collection_flight,
    handle_flight_search,
    handle_flight_ask
)


def build_state_graph():
    """
    Build and return a compiled LangGraph StateGraph
    """
    builder = StateGraph(GraphState)

    # --- Top-level flow router ------------------------------------------------
    def route_flow(state):
        """
        Route to either hotel or flight sub-graph based on state.flowType
        """
        if hasattr(state, "model_dump"):
            d = state.model_dump()
        elif isinstance(state, dict):
            d = state
        else:
            d = dict(state)

        # Check intent for the flow type
        flow = d.get("trace_info", {}).get("flow", "")
        if "flight" in flow:
            return "flight"
        else:
            return "hotel"

        # return d.get("flowType", "hotel")  # default to hotel

    builder.add_node("check_flow_and_branch", lambda s: s)
    builder.add_conditional_edges(
        "check_flow_and_branch",
        route_flow,
        {
            "hotel":  "check_hotel_phase_and_branch",
            "flight": "check_flight_phase_and_branch",
        }
    )

    # --- Hotel sub-graph (existing) -------------------------------------------
    # Phase router for hotel flow
    def route_hotel_phase(state):
        if hasattr(state, "model_dump"):
            d = state.model_dump()
        elif isinstance(state, dict):
            d = state
        else:
            d = dict(state)
        return d.get("route")

    builder.add_node("check_hotel_phase_and_branch", hotel_route_decider)
    builder.add_node("handle_slot_collection", handle_slot_collection)
    builder.add_node("handle_confirmation_request", handle_confirmation_request)
    builder.add_node("handle_default", handle_default)
    builder.add_node("handle_show_hotels", handle_show_hotels)
    builder.add_node("handle_out_of_scope", handle_out_of_scope)
    builder.add_node("handle_rejection", handle_rejection)
    builder.add_node("handle_greeting", handle_greeting)
    builder.add_node("handle_cache_check", handle_cache_check)
    builder.add_node("handle_answer_single_hotel", handle_answer_single_hotel)
    builder.add_node("handle_slot_fixing", handle_slot_fixing)
    builder.add_node("handle_empty_hotels", handle_empty_hotels)
    builder.add_node("handle_hotel_compare", handle_hotel_compare)
    builder.add_node("handle_serpapi_search", handle_serpapi_search)
    builder.add_node("handle_hotel_similar", handle_hotel_similar)

    builder.add_conditional_edges(
        "check_hotel_phase_and_branch",
        route_hotel_phase,
        {
            "slot_collection":      "handle_slot_collection",
            "confirmation_request": "handle_confirmation_request",
            "show_hotels":          "handle_show_hotels",
            "out_of_scope":         "handle_out_of_scope",
            "rejection":            "handle_rejection",
            "greeting":             "handle_greeting",
            "cache_check":          "handle_cache_check",
            "answer_single_hotel":  "handle_answer_single_hotel",
            "slot_fixing":          "handle_slot_fixing",
            "empty_hotels":         "handle_empty_hotels",
            "hotel_compare":        "handle_hotel_compare",
            "serpapi_search":       "handle_serpapi_search",
            "hotel_similar":        "handle_hotel_similar",
        }
    )

    # End hotel handlers
    for node in [
        "handle_slot_collection", "handle_confirmation_request", "handle_default",
        "handle_show_hotels", "handle_out_of_scope", "handle_rejection",
        "handle_greeting", "handle_cache_check", "handle_answer_single_hotel",
        "handle_slot_fixing", "handle_empty_hotels", "handle_hotel_compare",
    ]:
        builder.add_edge(node, END)

    # --- Flight sub-graph ------------------------------------------------------
    # Phase router for flight flow
    def route_flight_phase(state: GraphState) -> str:
        """Read the pre-determined flight route from state."""
        if hasattr(state, "model_dump"):
            d = state.model_dump()
        elif isinstance(state, dict):
            d = state
        else:
            d = dict(state)
        return d.get("route", "search")

    builder.add_node("check_flight_phase_and_branch", flight_route_decider)
    builder.add_node("handle_slot_collection_flight", handle_slot_collection_flight)
    builder.add_node("handle_flight_search", handle_flight_search)
    builder.add_node("handle_flight_ask", handle_flight_ask)

    builder.add_conditional_edges(
        "check_flight_phase_and_branch",
        route_flight_phase,
        {
            "slot_collection": "handle_slot_collection_flight",
            "search": "handle_flight_search",
            "flight_ask":   "handle_flight_ask",
        }
    )

    # End flight handlers
    for node in ["handle_slot_collection_flight", "handle_flight_search", "handle_flight_ask"]:
        builder.add_edge(node, END)

    # --- Set entry-point -------------------------------------------------------
    builder.set_entry_point("check_flow_and_branch")

    # Compile and return
    return builder.compile()
