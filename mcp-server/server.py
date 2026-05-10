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
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

app = FastAPI(title="Career Context Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "PUT"],
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


def save_json(path: Path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


@app.get("/context")
def get_context():
    return {
        "profile": load_json(PROFILE_FILE),
        "priorities": load_json(PRIORITIES_FILE),
        "blacklist": load_json(BLACKLIST_FILE),
    }


@app.get("/profile")
def get_profile():
    return load_json(PROFILE_FILE) or {}


@app.put("/profile")
def update_profile(data: dict):
    save_json(PROFILE_FILE, data)
    return {"status": "saved"}


@app.get("/priorities")
def get_priorities():
    return load_json(PRIORITIES_FILE) or {}


@app.put("/priorities")
def update_priorities(data: dict):
    save_json(PRIORITIES_FILE, data)
    return {"status": "saved"}


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
    record = {"timestamp": datetime.now().isoformat(), **entry.model_dump()}
    with open(TRACKER_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps(record, ensure_ascii=False) + '\n')
    return {"status": "saved"}


@app.get("/tracker", response_class=HTMLResponse)
def tracker_page():
    entries = []
    if TRACKER_FILE.exists():
        with open(TRACKER_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
    entries.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

    rows = ""
    for e in entries:
        score = e.get("match_score", 0)
        color = "#22c55e" if score >= 70 else "#f59e0b" if score >= 50 else "#ef4444"
        rec = e.get("recommendation", "")
        rec_bg = "#dcfce7" if rec == "Apply" else "#fef9c3" if rec == "Consider" else "#fee2e2"
        ts = e.get("timestamp", "")[:16].replace("T", " ")
        url = e.get("job_url", "")
        company = e.get("company", "—")
        position = e.get("position", "—")
        reasoning = e.get("reasoning", "")
        red = ", ".join(e.get("red_flags", []))
        green = ", ".join(e.get("green_flags", []))
        rows += f"""
        <tr>
          <td>{ts}</td>
          <td>{'<a href="' + url + '" target="_blank">' + company + '</a>' if url else company}</td>
          <td>{position}</td>
          <td style="color:{color};font-weight:bold;text-align:center">{score}</td>
          <td style="background:{rec_bg};text-align:center;border-radius:4px">{rec}</td>
          <td style="font-size:12px">{reasoning}</td>
          <td style="font-size:11px;color:#ef4444">{red}</td>
          <td style="font-size:11px;color:#22c55e">{green}</td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Job Match Tracker</title>
  <style>
    body {{ font-family: system-ui, sans-serif; padding: 24px; background: #f8fafc; color: #1e293b; }}
    h1 {{ margin-bottom: 4px; }}
    p {{ color: #64748b; margin-bottom: 20px; }}
    table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,.1); }}
    th {{ background: #1e293b; color: white; padding: 10px 12px; text-align: left; font-size: 13px; }}
    td {{ padding: 10px 12px; border-bottom: 1px solid #e2e8f0; vertical-align: top; }}
    tr:last-child td {{ border-bottom: none; }}
    tr:hover td {{ background: #f1f5f9; }}
    a {{ color: #6366f1; }}
    .empty {{ text-align: center; padding: 48px; color: #94a3b8; }}
  </style>
</head>
<body>
  <h1>Job Match Tracker</h1>
  <p>{len(entries)} vacancies analysed</p>
  <table>
    <thead>
      <tr>
        <th>Date</th><th>Company</th><th>Position</th>
        <th>Score</th><th>Decision</th><th>Reasoning</th>
        <th>Red flags</th><th>Green flags</th>
      </tr>
    </thead>
    <tbody>
      {''.join(rows) if entries else '<tr><td colspan="8" class="empty">No analyses yet. Select job text → right click → Analyze Job Match.</td></tr>'}
    </tbody>
  </table>
</body>
</html>"""


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8765)
