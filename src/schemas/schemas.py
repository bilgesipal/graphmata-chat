from typing import Dict, List, Any, Optional, TypedDict
from pydantic import BaseModel, Field

class TraceInfo(BaseModel):
    trace_id: int
    flow: str
    sequence: int
    retry_count: int = 0


class Metadata(BaseModel):
    user_id: str
    application_id: str
    language: str = "tr"
    source_service: str
    event_type: str
    customerid_ui: Optional[List[str]] = None  # Made optional
    travelUsageType: Optional[str] = None  # Made optional
    redis_cache_address_general_info: Optional[List[Any]] = None
    redis_cache_address_price_policy: Optional[List[Any]] = None

class UserInput(BaseModel):
    text: str
    language: str = "tr"


class IntentPhase(BaseModel):
    status: str
    intent: str
    entities: Dict[str, Any] = {}


class SlotFillingPhase(BaseModel):
    status: str  # "in_progress", "completed"
    filled_slots: Dict[str, Any] = {}
    pending_slots: List[str] = []


class ConfirmationPhase(BaseModel):
    status: str  # "pending", "confirmed", "rejected"
    action_to_confirm: str = ""
    parameters_to_confirm: Dict[str, Any] = {}


class CurrentState(BaseModel):
    user_input: Optional[UserInput] = None
    intent_phase: Optional[IntentPhase] = None
    slot_filling_phase: Optional[SlotFillingPhase] = None
    confirmation_phase: Optional[ConfirmationPhase] = None


class StateData(BaseModel):
    current: CurrentState
    transition: str = ""
    previous_transition: str = ""  # Yeni alan eklendit


class OrchestrationActions(BaseModel):
    service: str
    action: str
    parameters: Dict[str, Any] = {}


class Orchestration(BaseModel):
    flow_director: str
    flow_id: str
    node_id: str = ""
    actions: OrchestrationActions


class SystemMessage(BaseModel):
    text: str
    language: str = "tr"


class GraphState(BaseModel):
    """Main state model for LangGraph"""
    session_id: str
    message_id: str
    timestamp: str
    version: str = "1.0.0"
    trace_info: TraceInfo
    metadata: Metadata
    state: StateData
    orchestration: Optional[Orchestration] = None
    system_message: Optional[SystemMessage] = None
    route: Optional[str] = None
    prompt: Optional[str] = None
