"""Minimal FastAPI proxy for a deployed A2A agent (Agent Runtime, agents-cli 1.1.0+).

The browser talks ONLY to this proxy (same origin, no CORS, no GCP creds in the
browser). The proxy authenticates with Application Default Credentials and
forwards chat to the deployed agent over the A2A protocol, returning replies as
structured parts the chat UI knows how to show:

  * {"kind": "text", "text": ...}  -> a normal chat bubble
  * {"kind": "a2ui", "data": ...}  -> one A2UI message (beginRendering /
    surfaceUpdate); static/index.html renders these as a card.

Why A2A: agents-cli 1.1.0 (GA) deploys ADK agents to Agent Runtime as A2A agents
and no longer registers the reasoning-engine operation schema the old
`agent_engines.get(...).stream_query()` path relied on (operation_schemas() comes
back empty). The container serves the A2A protocol over the Agent Engine HTTP
passthrough, so this proxy fetches the agent's card and sends messages with the
a2a-sdk client (the same path `agents-cli run --mode a2a` uses). This works for
both A2A and plain ADK 1.1.0 deployments (the container serves A2A either way).

Run:
  pip install -r requirements.txt
  export AGENT_ENGINE_RESOURCE_NAME="projects/.../locations/.../reasoningEngines/..."
  export AGENT_DIRECTORY="app"   # your agent's app directory (agents-cli-manifest.yaml)
  python main.py                 # -> http://localhost:8080
"""

import os
import uuid
import json

import google.auth
import google.auth.transport.requests
import httpx
from a2a.client import ClientConfig, ClientFactory
from a2a.types import AgentCard, SendMessageRequest, Message, Part, Role
from google.protobuf import json_format
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

RESOURCE = os.environ["AGENT_ENGINE_RESOURCE_NAME"]
AGENT_DIRECTORY = os.environ.get("AGENT_DIRECTORY", "app")
LOCATION = RESOURCE.split("/locations/")[1].split("/")[0]

A2A_BASE = (
    f"https://{LOCATION}-aiplatform.googleapis.com/reasoningEngines/v1/"
    f"{RESOURCE}/api/a2a/{AGENT_DIRECTORY}"
)
A2A_CARD_URL = f"{A2A_BASE}/.well-known/agent-card.json"

_creds, _ = google.auth.default(
    scopes=["https://www.googleapis.com/auth/cloud-platform"]
)

def _auth_headers() -> dict[str, str]:
    _creds.refresh(google.auth.transport.requests.Request())
    return {
        "Authorization": f"Bearer {_creds.token}",
        "Content-Type": "application/json",
    }

app = FastAPI()

@app.exception_handler(Exception)
async def _json_errors(request: Request, exc: Exception):
    return JSONResponse(
        status_code=200,
        content={
            "parts": [{"kind": "text", "text": f"Error: {type(exc).__name__}: {exc}"}]
        },
    )

_contexts: dict[str, str] = {}
_card: AgentCard | None = None

async def _get_card(client: httpx.AsyncClient) -> AgentCard:
    global _card
    if _card is None:
        resp = await client.get(A2A_CARD_URL)
        resp.raise_for_status()
        card_data = resp.json()
        card = AgentCard()
        json_format.ParseDict(card_data, card, ignore_unknown_fields=True)
        if len(card.supported_interfaces) > 0:
            card.supported_interfaces[0].url = A2A_BASE
        _card = card
    return _card

from google.protobuf.json_format import MessageToDict

def _extract_parts(parts) -> list[dict]:
    out: list[dict] = []
    for p in parts:
        if p.HasField("text") and p.text:
            out.append({"kind": "text", "text": p.text})
        elif p.HasField("data"):
            from google.protobuf.json_format import MessageToDict
            struct_dict = MessageToDict(p.data)
            mime = struct_dict.get("metadata", {}).get("mimeType")
            if mime == "application/json+a2ui" and "data" in struct_dict:
                out.append({"kind": "a2ui", "data": struct_dict["data"]})
            elif mime == "application/json+a2ui":
                out.append({"kind": "a2ui", "data": struct_dict})
            elif mime == "text/plain" and "data" in struct_dict:
                text = struct_dict["data"]
                if isinstance(text, str):
                    if text.startswith("<a2a_datapart_json>") and text.endswith("</a2a_datapart_json>"):
                        import json
                        inner = json.loads(text[19:-20])
                        if inner.get("kind") == "data" and "data" in inner:
                            out.append({"kind": "a2ui", "data": inner["data"]})
                    else:
                        out.append({"kind": "text", "text": text})
        elif p.HasField("url"):
            if p.url:
                out.append({"kind": "text", "text": p.url})
    return out

@app.post("/chat")
async def chat(req: Request):
    body = await req.json()
    message = body.get("message", "")
    user_id = body.get("user_id") or "web-user"
    parts: list[dict] = []

    async with httpx.AsyncClient(headers=_auth_headers(), timeout=120) as client:
        card = await _get_card(client)
        factory = ClientFactory(ClientConfig(httpx_client=client))
        a2a_client = factory.create(card)

        msg = Message(
            message_id=str(uuid.uuid4()),
            role=Role.Value('ROLE_USER')
        )
        msg.parts.append(Part(text=message))
        if _contexts.get(user_id):
            msg.context_id = _contexts.get(user_id)

        req = SendMessageRequest(message=msg)

        async for event in a2a_client.send_message(req):
            if event.HasField("task"):
                last_task = event.task
                if last_task.context_id:
                    _contexts[user_id] = last_task.context_id
            elif event.HasField("status_update"):
                if event.status_update.context_id:
                    _contexts[user_id] = event.status_update.context_id
                if event.status_update.status.HasField("message"):
                    s_msg = event.status_update.status.message
                    if s_msg.role == Role.Value('ROLE_AGENT'):
                        for p in s_msg.parts:
                            if p.HasField("text"):
                                parts.append({"kind": "text", "text": p.text})
            elif event.HasField("artifact_update"):
                if event.artifact_update.artifact:
                    parts.extend(_extract_parts(event.artifact_update.artifact.parts))

    if not parts:
        parts = [{"kind": "text", "text": "(The agent didn't return a reply.)"}]
    return JSONResponse({"parts": parts})

app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

