import asyncio
import google.auth
import google.auth.transport.requests
import httpx
from a2a.client import ClientFactory, ClientConfig
from a2a.types import AgentCard, SendMessageRequest, Message, Part
import json

creds, _ = google.auth.default()
creds.refresh(google.auth.transport.requests.Request())
token = creds.token

A2A_BASE = 'https://us-east1-aiplatform.googleapis.com/reasoningEngines/v1/projects/1416204582/locations/us-east1/reasoningEngines/3108607443769229312/api/a2a/app'
A2A_CARD = f'{A2A_BASE}/.well-known/agent-card.json'

async def test():
    async with httpx.AsyncClient(timeout=60) as client:
        client.headers.update({'Authorization': f'Bearer {token}'})
        res = await client.get(A2A_CARD)
        card_data = res.json()
        card_data['url'] = A2A_BASE
        card = AgentCard(**card_data)
        
        factory = ClientFactory(
            ClientConfig(
                httpx_client=client,
            )
        )
        a2a_client = factory.create(card)
        
        # In a2a_pb2 Message, parts is repeated Part
        msg = Message(role="USER")
        # In 1.2.1, Part has a 'text' field (it's a protobuf message wrapper).
        part = Part(text="What is my blood pressure?")
        msg.parts.append(part)
        
        req = SendMessageRequest(message=msg)
        
        async for event in a2a_client.send_message(req):
            print("Event:", event)

asyncio.run(test())
