import asyncio
import google.auth
import google.auth.transport.requests
import httpx
from a2a.client import ClientFactory, ClientConfig
from a2a.types import AgentCard, SendMessageRequest, Message, Part
from google.protobuf import json_format
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
        print('Card JSON:', card_data)
        
        # Parse into protobuf
        card = AgentCard()
        json_format.ParseDict(card_data, card, ignore_unknown_fields=True)
        # Manually overwrite the URL of the interface since AgentRuntime doesn't serve the full path
        if len(card.supported_interfaces) > 0:
            card.supported_interfaces[0].url = A2A_BASE
        
        factory = ClientFactory(
            ClientConfig(
                httpx_client=client,
            )
        )
        a2a_client = factory.create(card)
        
        msg = Message(role="ROLE_USER")
        msg.parts.append(Part(text="What is my blood pressure?"))
        req = SendMessageRequest(message=msg)
        
        async for event in a2a_client.send_message(req):
            print("Event:", event)

asyncio.run(test())
