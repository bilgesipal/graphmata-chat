import openai
from src.config.config import AppConfig
from .graph_builder import build_state_graph
from .parsers import parse_message_to_state

# configure OpenAI key once
openai.api_key = AppConfig.OPENAI_API_KEY


class ChatSlotAgent:
    def __init__(self):
        # Registers all nodes and builds the LangGraph state graph.
        print("Building LangGraph state graph...")
        self.graph = build_state_graph()

    async def process_message_async(self, message_data: dict):

        # After parsing we have a GraphState object ready to be processed
        initial_state = parse_message_to_state(message_data)

        # Print the initial state for debugging purposes
        print("Initial State:", initial_state)

        # LangGraph starts an asynchronous execution loop
        # ainvoke: fires off a tiny 'async state machine' loop that runs the graph

        # If you want to watch the graph in action, you can call astream
        # yourself and get each node’s output as it happens( or every LLM token,
        # if you’ve built your nodes that way).

        result = await self.graph.ainvoke(initial_state)

        # Ensure result is a dict or has the required attributes
        if isinstance(result, dict):
            return result
        elif hasattr(result, "model_dump"):
            return result.model_dump()
        else:
            raise TypeError("Result must be a dict or have a 'model_dump' method")

    def get_prompt(self, state):
        """
        Extract the prompt field for sending to the LLM.
        """
        if hasattr(state, "prompt"):
            return state.prompt
        if isinstance(state, dict):
            return state.get("prompt", None)  # Varsayılan olarak None döndür
        return None

    def create_output_message(self, state) -> dict:
        """
        Build the outbound message payload from the final GraphState.
        """
        # get a plain dict
        if isinstance(state, dict):
            s = state
        elif hasattr(state, "model_dump"):
            s = state.model_dump()
        else:
            raise TypeError("State must be a dict or have a 'model_dump' method")

        return {
            "session_id": s.get("session_id"),
            "message_id": s.get("message_id"),
            "timestamp": s.get("timestamp"),
            "version": s.get("version"),
            "trace_info": s.get("trace_info"),
            "metadata": s.get("metadata"),
            "state": s.get("state"),
        }