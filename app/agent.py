# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
import json
from typing import Any, Dict, List, Optional
import uuid

from google import genai
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors.agent_engine_sandbox_code_executor import AgentEngineSandboxCodeExecutor
from google.adk.models import Gemini
from google.adk.tools import ToolContext
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.cloud import firestore, storage
from google.genai import types

PROJECT_ID = "qwiklabs-gcp-04-ff165325328d"
BUCKET_NAME = "cardiopulse-health-assets-5325328d"
MEMORY_BANK_ID = "3396134132479164416"
AGENT_ENGINE_ID = "projects/1416204582/locations/us-east1/reasoningEngines/3396134132479164416"
LOCATION = "us-east1"
MODEL = "gemini-3.6-flash"

_db: Optional[firestore.Client] = None
_storage_client: Optional[storage.Client] = None
_genai_client: Optional[genai.Client] = None

def get_firestore_client() -> firestore.Client:
    global _db
    if _db is None:
        _db = firestore.Client(project=PROJECT_ID)
    return _db

def get_storage_client() -> storage.Client:
    global _storage_client
    if _storage_client is None:
        _storage_client = storage.Client(project=PROJECT_ID)
    return _storage_client

def get_genai_client() -> genai.Client:
    global _genai_client
    if _genai_client is None:
        _genai_client = genai.Client(vertexai=True, location="global")
    return _genai_client

def evaluate_blood_pressure(systolic: int, diastolic: int) -> str:
    """Evaluates systolic and diastolic readings against American Heart Association (AHA) guidelines."""
    if systolic < 120 and diastolic < 80:
        return "Normal"
    elif 120 <= systolic <= 129 and diastolic < 80:
        return "Elevated"
    elif (130 <= systolic <= 139) or (80 <= diastolic <= 89):
        return "Stage 1 Hypertension"
    elif (140 <= systolic < 180) or (90 <= diastolic < 120):
        return "Stage 2 Hypertension"
    else:
        return "Hypertensive Crisis (Seek immediate medical attention)"

def log_blood_pressure_reading(
    systolic: int,
    diastolic: int,
    pulse: Optional[int] = None,
    notes: Optional[str] = None
) -> Dict[str, Any]:
    """Records a new blood pressure reading into Firestore.

    Args:
        systolic: Systolic blood pressure in mmHg (upper number).
        diastolic: Diastolic blood pressure in mmHg (lower number).
        pulse: Heart rate in beats per minute (optional).
        notes: Context or circumstances, e.g. resting, post-workout, stress, morning (optional).

    Returns:
        A dictionary confirming the saved record with its ID, category, and timestamp.
    """
    db = get_firestore_client()
    record_id = f"bp-{datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{str(uuid.uuid4())[:6]}"
    category = evaluate_blood_pressure(systolic, diastolic)
    timestamp = datetime.datetime.utcnow().isoformat() + "Z"

    reading_doc = {
        "id": record_id,
        "systolic": int(systolic),
        "diastolic": int(diastolic),
        "pulse": int(pulse) if pulse is not None else None,
        "category": category,
        "notes": notes or "",
        "timestamp": timestamp,
        "status": "Recorded",
    }

    db.collection("blood_pressure_readings").document(record_id).set(reading_doc)
    return {
        "status": "success",
        "message": f"Recorded reading {systolic}/{diastolic} mmHg (Category: {category}).",
        "record": reading_doc,
    }

def get_blood_pressure_history(limit: int = 10) -> List[Dict[str, Any]]:
    """Retrieves the history of registered blood pressure readings from Firestore.

    Args:
        limit: Maximum number of recent readings to retrieve (default: 10).

    Returns:
        A list of blood pressure readings with systolic, diastolic, pulse, category, notes, and timestamp.
    """
    db = get_firestore_client()
    docs = db.collection("blood_pressure_readings").stream()
    
    results: List[Dict[str, Any]] = []
    for doc in docs:
        data = doc.to_dict()
        results.append(data)

    results.sort(key=lambda item: item.get("timestamp", ""), reverse=True)
    return results[:limit]

def calculate_cardio_metrics(systolic: int, diastolic: int) -> Dict[str, Any]:
    """Calculates Mean Arterial Pressure (MAP) and Pulse Pressure from blood pressure readings.

    Args:
        systolic: Systolic blood pressure in mmHg.
        diastolic: Diastolic blood pressure in mmHg.

    Returns:
        A dictionary containing the calculated MAP, pulse pressure, and their clinical interpretation.
    """
    pulse_pressure = int(systolic - diastolic)
    map_value = round((2 * diastolic + systolic) / 3, 1)

    if map_value < 70:
        map_status = "Low (Risk of under-perfusion to vital organs)"
    elif 70 <= map_value <= 100:
        map_status = "Optimal (Normal tissue and organ perfusion)"
    else:
        map_status = "High (Elevated cardiovascular strain)"

    if pulse_pressure < 40:
        pp_status = "Narrow (Can indicate reduced cardiac output)"
    elif 40 <= pulse_pressure <= 60:
        pp_status = "Normal"
    else:
        pp_status = "Wide (May indicate arterial stiffness or high stroke volume)"

    return {
        "systolic": systolic,
        "diastolic": diastolic,
        "mean_arterial_pressure_mmhg": map_value,
        "mean_arterial_pressure_status": map_status,
        "pulse_pressure_mmhg": pulse_pressure,
        "pulse_pressure_status": pp_status,
    }

def search_medication_info(medication_name: str) -> Dict[str, Any]:
    """Queries the openFDA Public API for official drug labeling, indications, and usage information.

    Args:
        medication_name: Name of the medication or active ingredient (e.g., 'lisinopril', 'amlodipine', 'losartan').

    Returns:
        A dictionary with brand/generic names, clinical indications, and warnings from the openFDA database.
    """
    import os
    import urllib.parse
    import urllib.request

    api_key = os.getenv("OPENFDA_API_KEY", "")
    safe_name = urllib.parse.quote(medication_name.strip())
    query_url = f"https://api.fda.gov/drug/label.json?search=openfda.generic_name:{safe_name}+openfda.brand_name:{safe_name}&limit=1"
    if api_key:
        query_url += f"&api_key={api_key}"

    req = urllib.request.Request(query_url, headers={"User-Agent": "CardioPulseAgent/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            results = data.get("results", [])
            if not results:
                return {"found": False, "message": f"No openFDA label found for {medication_name}."}
            drug_info = results[0]
            openfda = drug_info.get("openfda", {})

            return {
                "found": True,
                "brand_name": openfda.get("brand_name", [medication_name])[0],
                "generic_name": openfda.get("generic_name", [medication_name])[0],
                "substance_name": openfda.get("substance_name", []),
                "indications_and_usage": drug_info.get("indications_and_usage", ["No indication information available."])[0][:600],
                "warnings": drug_info.get("warnings", ["No warning label available."])[0][:400] if "warnings" in drug_info else "No specific warnings listed.",
            }
    except Exception as e:
        return {"found": False, "error": f"Failed to retrieve information from openFDA: {str(e)}"}

async def generate_cardio_wellness_badge(
    status_title: str,
    prompt_description: str,
    tool_context: ToolContext,
) -> Dict[str, Any]:
    """Generates an illustrative cardiovascular wellness badge or health milestone icon.

    Saves the generated image as an ADK artifact (so it appears in the Playground Artifacts tab)
    and uploads it to the public Cloud Storage bucket, returning its public HTTPS URL.

    Args:
        status_title: Short title of the badge or milestone, e.g. 'Normal BP Streak', 'Heart Optimal', 'Resting Baseline'.
        prompt_description: Description of the visual elements, colors, and badge symbols.
        tool_context: Tool execution context provided by the ADK runtime.

    Returns:
        A dictionary with the public HTTPS URL of the image and artifact details.
    """
    genai_client = get_genai_client()
    storage_client = get_storage_client()

    full_prompt = (
        f"A clean, modern, minimalist vector health illustration badge: {status_title}. "
        f"Theme: cardiovascular wellness and vital signs monitoring. {prompt_description}. "
        "Flat graphic design, vibrant colors on clean solid background, high resolution icon."
    )

    response = genai_client.models.generate_content(
        model="gemini-3.1-flash-lite-image",
        contents=full_prompt,
    )

    image_part = response.candidates[0].content.parts[0]
    image_bytes = image_part.inline_data.data
    mime_type = image_part.inline_data.mime_type or "image/jpeg"
    ext = "jpg" if "jpeg" in mime_type else "png"

    filename = f"wellness-badge-{datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{str(uuid.uuid4())[:6]}.{ext}"

    # 1. Save as ADK artifact
    artifact_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
    tool_context.save_artifact(filename=filename, artifact=artifact_part)

    # 2. Upload to public Cloud Storage bucket
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(filename)
    blob.upload_from_string(image_bytes, content_type=mime_type)
    public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{filename}"

    return {
        "status": "success",
        "title": status_title,
        "artifact_filename": filename,
        "public_url": public_url,
        "message": f"Badge '{status_title}' successfully generated, saved to artifacts, and uploaded to {public_url}",
    }

from .a2ui_prompt import A2UI_INSTRUCTION
from .a2ui_utils import a2ui_callback

INSTRUCTION = A2UI_INSTRUCTION

# WRITE: after each turn, send the session to Memory Bank for extraction.
async def generate_memories_callback(callback_context: CallbackContext):
    await callback_context.add_session_to_memory()
    return None

root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model=MODEL,
        client_kwargs={"location": "global"},
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=INSTRUCTION,
    code_executor=AgentEngineSandboxCodeExecutor(
        agent_engine_resource_name=AGENT_ENGINE_ID,
    ),
    tools=[
        PreloadMemoryTool(),
        log_blood_pressure_reading,
        get_blood_pressure_history,
        calculate_cardio_metrics,
        search_medication_info,
        generate_cardio_wellness_badge,
    ],
    after_model_callback=a2ui_callback,
    after_agent_callback=generate_memories_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
