#!/usr/bin/env python3
"""
Job Match AI - Career Context Server
Serves career profile data to the Chrome extension via HTTP.
"""

import json
import uvicorn
from pathlib import Path
from datetime import datetime
from typing import List
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Career Context Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

DATA_DIR = Path(__file__).parent / "data"
PROFILE_FILE = DATA_DIR / "profile.json"
PRIORITIES_FILE = DATA_DIR / "priorities.json"
BLACKLIST_FILE = DATA_DIR / "blacklist.json"
TRACKER_FILE = DATA_DIR / "tracker.jsonl"

DATA_DIR.mkdir(exist_ok=True)


def load_json(path: Path):
    if not path.exists():
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


@app.get("/context")
def get_context():
    """Returns full career context for job analysis."""
    return {
        "profile": load_json(PROFILE_FILE),
        "priorities": load_json(PRIORITIES_FILE),
        "blacklist": load_json(BLACKLIST_FILE),
    }


class AnalysisEntry(BaseModel):
    job_url: str
    company: str
    position: str
    match_score: int
    recommendation: str
    reasoning: str
    red_flags: List[str]
    green_flags: List[str]


@app.post("/analysis")
def save_analysis(entry: AnalysisEntry):
    """Saves job analysis result to tracker."""
    record = {"timestamp": datetime.now().isoformat(), **entry.model_dump()}
    with open(TRACKER_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps(record, ensure_ascii=False) + '\n')
    return {"status": "saved"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8765)
