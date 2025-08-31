# src/chat_agent/parsers.py

from datetime import datetime, timezone
from src.schemas.schemas import (
    GraphState,
    TraceInfo, Metadata, UserInput,
    IntentPhase, SlotFillingPhase,
    ConfirmationPhase, CurrentState,
    StateData, Orchestration, OrchestrationActions
)

# TODO: Make different according to the scenario
def parse_message_to_state(message_data: dict) -> GraphState:
    """
    Ingest raw JSON from your orchestrator and turn it into a GraphState.
    """
    session_id = message_data.get("session_id", "")
    message_id = message_data.get("message_id", "")
    timestamp  = message_data.get(
        "timestamp",
        datetime.now(timezone.utc).isoformat()
    )
    version   = message_data.get("version", "1.0.0")

    ti = message_data.get("trace_info", {})
    trace_info = TraceInfo(
        trace_id   = ti.get("trace_id", 0),
        sequence   = ti.get("sequence", 0),
        flow       = ti.get("flow", "hotel_list_flow"),
        retry_count= ti.get("retry_count", 0),
    )

    md = message_data.get("metadata", {})
    metadata = Metadata(
        user_id        = md.get("user_id", ""),
        application_id = md.get("application_id", ""),
        language       = md.get("language", ""),
        source_service = md.get("source_service", "orchestrator"),
        event_type     = md.get("event_type", "next_action"),
        customerid_ui  = md.get("customerid_ui"),
        travelUsageType= md.get("travelUsageType"),
        redis_cache_address_general_info = md.get("redis_cache_address_general_info"),
        redis_cache_address_price_policy = md.get("redis_cache_address_price_policy")
    )

    st = message_data.get("state", {})
    curr = st.get("current", {})

    # user_input
    ui = curr.get("user_input")
    user_input = None
    if ui:
        user_input = UserInput(
            text     = ui.get("text", ""),
            language = ui.get("language", "tr")
        )

    # intent_phase
    ip = curr.get("intent_phase")
    intent_phase = None
    if ip:
        intent_phase = IntentPhase(
            status   = ip.get("status", ""),
            intent   = ip.get("intent", ""),
            entities = ip.get("entities", {})
        )

    # slot_filling_phase
    sf = curr.get("slot_filling_phase")
    slot_filling_phase = None
    if sf:
        slot_filling_phase = SlotFillingPhase(
            status       = sf.get("status", ""),
            filled_slots = sf.get("filled_slots", {}),
            pending_slots= sf.get("pending_slots", [])
        )

    # confirmation_phase
    cp = curr.get("confirmation_phase")
    confirmation_phase = None
    if cp:
        confirmation_phase = ConfirmationPhase(
            status               = cp.get("status", ""),
            action_to_confirm    = cp.get("action_to_confirm", ""),
            parameters_to_confirm= cp.get("parameters_to_confirm", {})
        )

    current_state = CurrentState(
        user_input        = user_input,
        intent_phase      = intent_phase,
        slot_filling_phase= slot_filling_phase,
        confirmation_phase= confirmation_phase
    )

    state = StateData(
        current    = current_state,
        transition = st.get("transition", ""),
        previous_transition = st.get("previous_transition", "")
    )

    # orchestration (optional)
    orch = message_data.get("orchestration")
    orchestration = None
    if orch:
        a = orch.get("actions", {})
        actions = OrchestrationActions(
            service    = a.get("service", ""),
            action     = a.get("action", ""),
            parameters = a.get("parameters", {})
        )
        orchestration = Orchestration(
            flow_director = orch.get("flow_director", "orchestrator"),
            flow_id       = orch.get("flow_id", "hotel_list_flow"),
            node_id       = orch.get("node_id", ""),
            actions       = actions
        )

    return GraphState(
        session_id   = session_id,
        message_id   = message_id,
        timestamp    = timestamp,
        version      = version,
        trace_info   = trace_info,
        metadata     = metadata,
        state        = state,
        orchestration= orchestration
    )