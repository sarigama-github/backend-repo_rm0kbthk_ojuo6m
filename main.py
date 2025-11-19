import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from database import db, create_document, get_documents
from schemas import PlayerSettings, GhostRecord, ProgressRecord

app = FastAPI(title="Shadow Sprint API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"name": "Shadow Sprint API", "status": "ok"}

# ---------- Models for requests ----------
class SettingsUpdate(BaseModel):
    volume: Optional[bool] = None
    vibration: Optional[bool] = None
    language: Optional[str] = None

class GhostUpsert(BaseModel):
    player_id: str
    level: int
    time_ms: int
    inputs: List[dict]

class ProgressUpdate(BaseModel):
    player_id: str
    won_level: int

# ---------- Helper ----------
COLLECTION_SETTINGS = "playersettings"
COLLECTION_GHOST = "ghostrecord"
COLLECTION_PROGRESS = "progressrecord"

MAX_LEVELS = 15

# ---------- Settings Endpoints ----------
@app.get("/api/settings/{player_id}")
def get_settings(player_id: str):
    if db is None:
        return {"volume": True, "vibration": True, "language": "es"}
    doc = db[COLLECTION_SETTINGS].find_one({"player_id": player_id})
    if not doc:
        default = PlayerSettings(player_id=player_id)
        create_document(COLLECTION_SETTINGS, default)
        return default.model_dump()
    doc["_id"] = str(doc["_id"])  # make serializable
    return {k: doc[k] for k in ["player_id", "volume", "vibration", "language"]}

@app.post("/api/settings/{player_id}")
def update_settings(player_id: str, payload: SettingsUpdate):
    data = {k: v for k, v in payload.model_dump().items() if v is not None}
    if db is None:
        return {"player_id": player_id, **{"volume": True, "vibration": True, "language": "es"}, **data}
    db[COLLECTION_SETTINGS].update_one({"player_id": player_id}, {"$set": data}, upsert=True)
    doc = db[COLLECTION_SETTINGS].find_one({"player_id": player_id})
    doc["_id"] = str(doc["_id"])  # make serializable
    return {k: doc[k] for k in ["player_id", "volume", "vibration", "language"]}

# ---------- Levels & Progress ----------
@app.get("/api/levels")
def get_levels():
    return {"levels": list(range(1, MAX_LEVELS + 1))}

@app.get("/api/progress/{player_id}")
def get_progress(player_id: str):
    if db is None:
        return {"player_id": player_id, "unlocked_upto": 1}
    doc = db[COLLECTION_PROGRESS].find_one({"player_id": player_id})
    if not doc:
        progress = ProgressRecord(player_id=player_id)
        create_document(COLLECTION_PROGRESS, progress)
        return progress.model_dump()
    doc["_id"] = str(doc["_id"])  # make serializable
    return {k: doc[k] for k in ["player_id", "unlocked_upto"]}

@app.post("/api/progress/unlock")
def unlock_next(progress: ProgressUpdate):
    if progress.won_level < 1 or progress.won_level >= MAX_LEVELS:
        return {"status": "ok"}
    if db is None:
        return {"status": "ok"}
    rec = db[COLLECTION_PROGRESS].find_one({"player_id": progress.player_id})
    if not rec:
        rec = ProgressRecord(player_id=progress.player_id)
        create_document(COLLECTION_PROGRESS, rec)
        rec = db[COLLECTION_PROGRESS].find_one({"player_id": progress.player_id})
    unlocked = rec.get("unlocked_upto", 1)
    if progress.won_level >= unlocked:
        db[COLLECTION_PROGRESS].update_one({"player_id": progress.player_id}, {"$set": {"unlocked_upto": progress.won_level + 1}})
    return {"status": "ok"}

# ---------- Ghosts ----------
@app.get("/api/ghost/{player_id}/{level}")
def get_ghost(player_id: str, level: int):
    if db is None:
        # basic generic ghost: slow linear taps every 700ms for 7 seconds
        generic = {"player_id": player_id, "level": level, "time_ms": 8000,
                   "inputs": [{"start_ms": i*700, "end_ms": i*700+120, "kind": "tap"} for i in range(10)]}
        return generic
    doc = db[COLLECTION_GHOST].find_one({"player_id": player_id, "level": level})
    if not doc:
        generic = {"player_id": player_id, "level": level, "time_ms": 8000,
                   "inputs": [{"start_ms": i*700, "end_ms": i*700+120, "kind": "tap"} for i in range(10)]}
        return generic
    doc["_id"] = str(doc["_id"])  # make serializable
    return {k: doc[k] for k in ["player_id", "level", "time_ms", "inputs"]}

@app.post("/api/ghost")
def upsert_ghost(payload: GhostUpsert):
    if db is None:
        return {"status": "ok"}
    existing = db[COLLECTION_GHOST].find_one({"player_id": payload.player_id, "level": payload.level})
    if not existing or payload.time_ms < existing.get("time_ms", 1e9):
        db[COLLECTION_GHOST].update_one(
            {"player_id": payload.player_id, "level": payload.level},
            {"$set": payload.model_dump()},
            upsert=True,
        )
    return {"status": "ok"}

# ---------- Classification ----------
@app.get("/api/classification/{player_id}")
def classification(player_id: str):
    if db is None:
        return {"tier": "Bronze"}
    times = list(db[COLLECTION_GHOST].find({"player_id": player_id}))
    if not times:
        return {"tier": "Bronze"}
    avg = sum(t.get("time_ms", 0) for t in times) / max(1, len(times))
    if avg < 5500:
        tier = "Gold"
    elif avg < 7500:
        tier = "Silver"
    else:
        tier = "Bronze"
    return {"tier": tier}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available" if db is None else "✅ Connected",
    }
    return response

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
