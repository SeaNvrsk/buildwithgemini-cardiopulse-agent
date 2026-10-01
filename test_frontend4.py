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
        if len(card.supported_interfaces) > 0:
            card.supported_interfaces[0].url = A2A_BASE
        
        factory = ClientFactory(ClientConfig(httpx_client=client))
        a2a_client = factory.create(card)
        
        msg = Message(message_id="msg-1", role=Role.Value('ROLE_USER'))
        msg.parts.append(Part(text="What is my blood pressure?"))
        
        req = SendMessageRequest(message=msg)
        
        try:
            async for event in a2a_client.send_message(req):
                print("Event:", event)
        except Exception as e:
            print(f"Error: {e}")

asyncio.run(test())
