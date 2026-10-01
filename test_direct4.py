import asyncio
import google.auth
import google.auth.transport.requests
import httpx

creds, _ = google.auth.default()
creds.refresh(google.auth.transport.requests.Request())
token = creds.token

A2A_BASE = 'https://us-east1-aiplatform.googleapis.com/v1/projects/1416204582/locations/us-east1/reasoningEngines/3108607443769229312'

async def test():
    async with httpx.AsyncClient(timeout=60) as client:
        # Let's try the streamQuery endpoint explicitly
        payload = {
            "message": "Hello!"
        }
        res = await client.post(
            f'{A2A_BASE}:streamQuery',
            headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
            json=payload
        )
        print('streamQuery POST:', res.status_code)
        if res.status_code == 200:
            for line in res.iter_lines():
                if line: print(line)
        else:
            print(res.text)

asyncio.run(test())
