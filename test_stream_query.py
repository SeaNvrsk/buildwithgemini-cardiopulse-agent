import vertexai
from google.cloud import aiplatform

vertexai.init(project='qwiklabs-gcp-04-ff165325328d', location='us-east1')

# Wait, Agent Runtime 1.1.0 deployments don't support stream_query
# But let's check what aiplatform sees
from google.cloud.aiplatform.compat.types import reasoning_engine as gca_reasoning_engine
re = aiplatform.ReasoningEngine('projects/1416204582/locations/us-east1/reasoningEngines/3108607443769229312')
print("Class methods:")
for m in re.gca_resource.spec.class_methods:
    print(f" - {m.name} (api_mode: {m.api_mode})")

