import asyncio
import google.auth
import google.auth.transport.requests
import httpx

creds, _ = google.auth.default()
creds.refresh(google.auth.transport.requests.Request())
token = creds.token

A2A_BASE = 'https://us-east1-aiplatform.googleapis.com/v1/projects/1416204582/locations/us-east1/reasoningEngines/3108607443769229312/api/a2a/app'

async def test():
    async with httpx.AsyncClient() as client:
        # Create task context
        res = await client.post(
            f'{A2A_BASE}/tasks',
            headers={'Authorization': f'Bearer {token}'}
        )
        print('Tasks POST:', res.status_code)
        if res.status_code == 200:
            task_id = res.json().get('taskId')
            print(f'Got task_id: {task_id}')
        else:
            print(res.text)

asyncio.run(test())
