import asyncio
import google.auth
import google.auth.transport.requests
import httpx
from a2a.client import ClientFactory, ClientConfig, TransportProtocol
from a2a.card import AgentCard
from a2a.models import Message

creds, _ = google.auth.default()
creds.refresh(google.auth.transport.requests.Request())
token = creds.token

A2A_URL = 'https://us-east1-aiplatform.googleapis.com/reasoningEngines/v1/projects/1416204582/locations/us-east1/reasoningEngines/3108607443769229312/api/a2a/app'

async def test():
    async with httpx.AsyncClient(headers={'Authorization': f'Bearer {token}'}, timeout=60) as client:
        # Replicate frontend
        res = await client.get(f"{A2A_URL}/.well-known/agent-card.json")
        card = AgentCard.model_validate(res.json())
        
        factory = ClientFactory(
            ClientConfig(
                supported_transports=[
                    TransportProtocol.jsonrpc,
                    TransportProtocol.http_json,
                ],
                httpx_client=client,
            )
        )
        a2a_client = factory.create(card)
        
        msg = Message(message_id="123", role="USER", parts=[{"text": "Hello"}])
        
        try:
            async for event in a2a_client.send_message(msg):
                print("Event:", event)
        except Exception as e:
            print("Error during send_message:", e)

asyncio.run(test())
