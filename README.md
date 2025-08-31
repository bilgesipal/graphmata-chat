# AI Chat Agent Service

A real-time chat service that processes messages via Redis pub/sub, streams responses to clients, and supports dynamic conversational flows. Designed for integration into larger systems requiring live chat, stateful sessions, and scalable message handling.

---

## 🛠️ Tech Stack
- **Python 3.11**
- **FastAPI** (web framework)
- **Uvicorn** (ASGI server)
- **Redis** (pub/sub messaging)
- **Docker** (optional, for containerization)

---

## 📁 Folder Structure

```
├── app.py                  
├── src/
│   ├── agent/              # Chat agent logic, handlers, and Redis publish helpers
│   ├── config/             # Configuration files (e.g., Redis connection)
│   ├── prompt_lib/         # Prompt templates for the agent
│   ├── routers/            # API route definitions (health, streaming, etc.)
│   ├── runner/             # Agent runner and streaming logic
│   └── schemas/            # Pydantic schemas for request/response models
├── requirements.in         
├── Dockerfile              
├── README.md               
```

---




## 📚 Endpoints Documentation

  -  `/health`
  - `/stream/{user_id}/{session_id}`
---

## 🏗️ Project Architecture

- **Real-time streaming**: The streaming mechanism is implemented using a GET endpoint that checks the session_queues dictionary for messages associated with a specific `session_key`. It streams responses in real-time by retrieving chunks of data from the queue and sending them as Server-Sent Events (SSE) until a done marker is received.


- **Redis pub/sub integration**: Publishes and subscribes to Redis channels for message handling. (subscribe to: `chat-agent-trigger`, publish to: `chat-state-update`)


- **Dynamic response handling**: Processes messages with various parameters and slots. (transitions: `request_chat_show_hotels`, `proceed_to_slot_filling`, etc.)

---

## 🗺️ Flow Diagram

```
+-----------------------------------------------------+
|   app.py (FastAPI)                                  |
|  - Main application entry point                     |
|  - Manages agent_runner threads                     |
|  - session_queues: per-user/session queue           |
|  - /stream endpoint: real-time SSE output           |
+-----------------------------------------------------+
          |
          v
+---------------------------+
|   Agent Runner            |
|  (src/runner/)            |
|  - agent_runner.py        |
|  - streaming.py           |
+---------------------------+
          |
          v
+---------------------------+         +---------------------------+
|   Chat Agent              |<------->|   Handlers                |
|  (chat_agent.py)          |         | (handlers.py)             |
+---------------------------+         +---------------------------+
          |
          v
+---------------------------+
|   Redis Pub/Sub           |
|  Channels:                |
|   - chat-agent-trigger    | <--- Input (subscribe)
|   - chat-state-update     | ---> Output (publish)
+---------------------------+
          |
          v
+---------------------------+
|   State Update            |
|  (publish_helpers.py)     |
+---------------------------+
```

### Input/Output Examples

**Input (Redis Channel: chat-agent-trigger):**
- JSON message containing user message and session information.
- Example fields: session_id, message_id, user_id, state, orchestration, etc.

**Output (Redis Channel: chat-state-update):**
- JSON message containing the processed response and updated state.
- Example fields: session_id, message, state, etc.

### Core Files
- app.py: FastAPI application
- src/runner/agent_runner.py: Agent main flow
- src/runner/streaming.py: Streaming operations
- src/agent/chat_agent.py: Chat agent logic
- src/agent/handlers.py: Response handlers for different actions
- src/agent/publish_helpers.py: Redis publish operations

---

## 💡 Usage & API Examples

1. Run the chat service
```
uvicorn app:app --host 0.0.0.0 --port 8002 --reload
```

2. Open a new terminal and run the following command to see the streaming:

```
 curl -N http://localhost:8002/stream/24115/55
```

3. Trigger the Redis pub/sub by publishing message to 'chat-agent-trigger' channel:

```
{
  "session_id": "55",
  "message_id": "7bdbc",
  "timestamp": "2025-06-09T10:00:18.544362Z",
  "version": "1.0.1",
  "trace_info": {
    "trace_id": 2,
    "flow": "hotel_list_flow",
    "sequence": 2,
    "retry_count": 0
  },
  "metadata": {
    "user_id": "24115",
    "application_id": "3334",
    "language": "tr",
    "source_service": "orchestrator",
    "event_type": "next_action"
  },
  "state": {
    "current": {
      "user_input": {
        "text": "Ankarada 5 Mayıs için bir otel bul!",
        "language": "tr"
      },
      "intent_phase": {
        "status": "classified",
        "intent": "hotel_list",
        "confidence": 0.9,
        "entities": {}
      }
    },
    "previous_transition": "intent_classified",
    "transition": "proceed_to_slot_filling"
  },
  "orchestration": {
    "flow_director": "orchestrator",
    "flow_id": "hotel_list_flow",
    "node_id": "slot_filling",
    "actions": {
      "service": "chat_agent",
      "action": "collect_slot",
      "parameters": {
        "filled_slots": {
          "LLM_outputText": "Ankarada 5 Mayıs için bir otel bul!",
          "location": "Ankara",
          "checkinDate": "2025-05-05"
        },
        "slots_to_collect": [
          "location",
          "checkinDate",
          "checkoutDate",
          "poi",
          "hotelStarQuery",
          "featureQuery",
          "per_night"
        ]
      }
    }
  }
}
```

**Sample SSE Response:**
```
data: {"message": "Hello! How can I"}

data: {"message": " help you?"}

data: {"message": " I can assist you"}

... (stream continues until done marker)
```

## License
Copyright © 2025 Prometa AI. All rights reserved.

This is proprietary software. Unauthorized copying or distribution is prohibited.
