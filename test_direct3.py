import asyncio
import google.auth
import google.auth.transport.requests
import httpx

creds, _ = google.auth.default()
creds.refresh(google.auth.transport.requests.Request())
token = creds.token

# We must use /reasoningEngines/v1/ prefix per earlier log
A2A_BASE = 'https://us-east1-aiplatform.googleapis.com/reasoningEngines/v1/projects/1416204582/locations/us-east1/reasoningEngines/3108607443769229312/api/a2a/app'

async def test():
    async with httpx.AsyncClient() as client:
        # What endpoints are actually serving? Let's check card.
        res = await client.get(
            f'{A2A_BASE}/.well-known/agent-card.json',
            headers={'Authorization': f'Bearer {token}'}
        )
        print('Card GET:', res.status_code)
        if res.status_code == 200:
            print(res.text[:300])
        
        # Test creating a task (this uses the jsonrpc endpoint in a2a-sdk < 1.0 vs http-server in 1.x)
        # Using a2a-sdk < 1.0 JSON-RPC payload format for create_context
        payload = {
            "jsonrpc": "2.0",
            "method": "create_context",
            "id": 1,
            "params": {}
        }
        res = await client.post(
            f'{A2A_BASE}',
            headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
            json=payload
        )
        print('JSON-RPC POST:', res.status_code, res.text)

asyncio.run(test())
