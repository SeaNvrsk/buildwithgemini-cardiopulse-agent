import datetime
from google.cloud import firestore

PROJECT_ID = "qwiklabs-gcp-04-ff165325328d"

def seed():
    db = firestore.Client(project=PROJECT_ID)
    readings_ref = db.collection("blood_pressure_readings")

    sample_readings = [
        {
            "id": "bp-sample-001",
            "systolic": 118,
            "diastolic": 76,
            "pulse": 68,
            "category": "Normal",
            "notes": "Morning reading after waking up, resting 5 mins.",
            "timestamp": "2026-09-28T08:00:00Z",
            "status": "Optimal"
        },
        {
            "id": "bp-sample-002",
            "systolic": 126,
            "diastolic": 78,
            "pulse": 72,
            "category": "Elevated",
            "notes": "Afternoon reading after walking up stairs.",
            "timestamp": "2026-09-29T14:30:00Z",
            "status": "Mildly elevated systolic"
        },
        {
            "id": "bp-sample-003",
            "systolic": 134,
            "diastolic": 84,
            "pulse": 75,
            "category": "Stage 1 Hypertension",
            "notes": "Evening reading after a stressful workday and coffee.",
            "timestamp": "2026-09-30T19:15:00Z",
            "status": "Stage 1"
        },
        {
            "id": "bp-sample-004",
            "systolic": 120,
            "diastolic": 78,
            "pulse": 70,
            "category": "Elevated",
            "notes": "Post meditation and water break.",
            "timestamp": "2026-10-01T09:00:00Z",
            "status": "Controlled"
        }
    ]

    for item in sample_readings:
        readings_ref.document(item["id"]).set(item)
        print(f"Seeded reading: {item['id']} ({item['systolic']}/{item['diastolic']} mmHg)")

    print("Firestore seeding complete.")

if __name__ == "__main__":
    seed()
