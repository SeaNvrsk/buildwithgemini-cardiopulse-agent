import asyncio
import google.auth
import google.auth.transport.requests
import httpx
from a2a.client import ClientFactory, ClientConfig
from a2a.types import AgentCard, SendMessageRequest, Message, Part, Role
from google.protobuf import json_format

creds, _ = google.auth.default()
creds.refresh(google.auth.transport.requests.Request())
token = creds.token

A2A_BASE = 'https://us-east1-aiplatform.googleapis.com/reasoningEngines/v1/projects/1416204582/locations/us-east1/reasoningEngines/3108607443769229312/api/a2a/app'

async def test():
    async with httpx.AsyncClient(timeout=60) as client:
        client.headers.update({'Authorization': f'Bearer {token}'})
        res = await client.get(f'{A2A_BASE}/.well-known/agent-card.json')
        card_data = res.json()
        
        card = AgentCard()
        json_format.ParseDict(card_data, card, ignore_unknown_fields=True)
        # Point the client back to the base url because AgentRuntime passthrough doesn't put full URLs in the card
        if len(card.supported_interfaces) > 0:
            card.supported_interfaces[0].url = A2A_BASE
        
        factory = ClientFactory(ClientConfig(httpx_client=client))
        a2a_client = factory.create(card)
        
        # In a2a-sdk 1.x, we use SendMessageRequest
        msg = Message(role=Role.Value('ROLE_USER'))
        msg.parts.append(Part(text="What is my blood pressure?"))
        
        req = SendMessageRequest(message=msg)
        
        # When sending, context is optional, but if we have context_id or task_id, we can set it in SendMessageRequest
        # Actually let's just send a new message.
        try:
            async for event in a2a_client.send_message(req):
                print("Event:", event)
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

asyncio.run(test())
