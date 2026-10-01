import asyncio
from a2a.client import ClientFactory, ClientConfig

async def test_a2a():
    config = ClientConfig(
        a2a_url="https://us-east1-aiplatform.googleapis.com/reasoningEngines/v1/projects/1416204582/locations/us-east1/reasoningEngines/3108607443769229312/api/a2a/app"
    )
    client = await ClientFactory.create(config)
    context_id = await client.create_context()
    
    print(f"Context ID: {context_id}")
    task_id = await client.create_task(context_id=context_id)
    print(f"Task ID: {task_id}")
    
    events = []
    async for event in client.send_message("What is my blood pressure?", task_id=task_id, context_id=context_id):
        events.append(event)
        print(f"Received event type: {type(event)}")
    print(f"Total events: {len(events)}")

if __name__ == "__main__":
    asyncio.run(test_a2a())
