"""Lead Finder — FastAPI backend"""
import csv
import json
import os
import subprocess
import sys
import threading
import uuid
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

load_dotenv()

app = FastAPI(title="Lead Finder")

BASE = Path(__file__).parent
DATA = BASE / "data"
STATIC = BASE / "static"
OUT = BASE / "out"

for d in (DATA, STATIC, OUT):
    d.mkdir(exist_ok=True)

WORKSPACE_FILE = DATA / "workspace.json"
VIEWS_FILE = DATA / "views.json"
STATUS_FILE = DATA / "search_status.json"
LEADS_CACHE = DATA / "leads_cache.json"

_lock = threading.Lock()


def _load(path: Path, default=None):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return default if default is not None else {}


def _save(path: Path, data):
    with _lock:
        path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


def _lead_id(row: dict) -> str:
    key = f"{row.get('business_name', '')}{row.get('address', '')}"
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, key))


def leads_from_csv() -> list:
    csv_path = OUT / "digital_opportunity_leads.csv"
    if not csv_path.exists():
        return []
    leads = []
    with open(csv_path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            row["id"] = _lead_id(row)
            leads.append(dict(row))
    return leads


# ── Status ────────────────────────────────────────────────────────────────────

@app.get("/api/status")
def get_status():
    key = os.getenv("GOOGLE_PLACES_API_KEY", "")
    configured = bool(key and key.strip() and "your_real_api_key" not in key)
    return {
        "api_key_configured": configured,
        "search_status": _load(STATUS_FILE, {"state": "idle", "message": "Ready to search"}),
        "lead_count": len(_load(LEADS_CACHE, [])),
    }


# ── Search ────────────────────────────────────────────────────────────────────

def _run_search():
    lines = []

    def _update(state: str, message: str):
        _save(STATUS_FILE, {
            "state": state,
            "message": message,
            "lines": lines[-100:],
            "updated_at": datetime.now().isoformat(),
        })

    _update("running", "Starting search…")
    try:
        proc = subprocess.Popen(
            [sys.executable, "-u", "main.py", "--config", "config.yaml", "--out", "./out"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=str(BASE),
        )
        for line in proc.stdout:
            line = line.rstrip()
            if line:
                lines.append(line)
                _update("running", line)
        proc.wait()
        if proc.returncode == 0:
            leads = leads_from_csv()
            _save(LEADS_CACHE, leads)
            _update("done", f"Complete — {len(leads)} leads found")
        else:
            _update("error", "Search failed — check terminal for details")
    except Exception as e:
        _update("error", str(e))


@app.post("/api/search/start")
def start_search():
    if _load(STATUS_FILE, {}).get("state") == "running":
        return {"ok": False, "message": "Already running"}
    threading.Thread(target=_run_search, daemon=True).start()
    return {"ok": True}


@app.get("/api/search/progress")
async def search_progress():
    import asyncio

    async def _stream():
        last = None
        for _ in range(7200):
            data = _load(STATUS_FILE, {"state": "idle"})
            serialized = json.dumps(data)
            if serialized != last:
                yield f"data: {serialized}\n\n"
                last = serialized
            if data.get("state") in ("done", "error", "idle"):
                break
            await asyncio.sleep(1)

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Leads ─────────────────────────────────────────────────────────────────────

@app.get("/api/leads")
def get_leads():
    leads = _load(LEADS_CACHE, None)
    if leads is None:
        leads = leads_from_csv()
        if leads:
            _save(LEADS_CACHE, leads)
    workspace_ids = set(_load(WORKSPACE_FILE, {}).keys())
    available = [l for l in leads if l["id"] not in workspace_ids]
    return {
        "no_website": [l for l in available if not l.get("website")],
        "needs_improvement": [l for l in available if l.get("website")],
    }


# ── Workspace ─────────────────────────────────────────────────────────────────

@app.get("/api/workspace")
def get_workspace():
    return list(_load(WORKSPACE_FILE, {}).values())


@app.post("/api/workspace/add")
async def add_to_workspace(request: Request):
    body = await request.json()
    ids = body.get("ids", [])
    all_leads = _load(LEADS_CACHE, []) or leads_from_csv()
    by_id = {l["id"]: l for l in all_leads}
    workspace = _load(WORKSPACE_FILE, {})
    added = 0
    for lead_id in ids:
        if lead_id in by_id and lead_id not in workspace:
            lead = dict(by_id[lead_id])
            lead.update({
                "workspace_status": "active",
                "workspace_action": "not_contacted",
                "workspace_added_at": datetime.now().isoformat(),
                "notes": "",
            })
            workspace[lead_id] = lead
            added += 1
    _save(WORKSPACE_FILE, workspace)
    return {"ok": True, "added": added}


@app.put("/api/workspace/{lead_id}")
async def update_workspace_lead(lead_id: str, request: Request):
    body = await request.json()
    workspace = _load(WORKSPACE_FILE, {})
    if lead_id not in workspace:
        raise HTTPException(404, "Not found")
    workspace[lead_id].update(body)
    _save(WORKSPACE_FILE, workspace)
    return workspace[lead_id]


@app.delete("/api/workspace/{lead_id}")
def remove_from_workspace(lead_id: str):
    workspace = _load(WORKSPACE_FILE, {})
    workspace.pop(lead_id, None)
    _save(WORKSPACE_FILE, workspace)
    return {"ok": True}


# ── Views ─────────────────────────────────────────────────────────────────────

@app.get("/api/views")
def get_views():
    return _load(VIEWS_FILE, [])


@app.post("/api/views")
async def create_view(request: Request):
    view = await request.json()
    views = _load(VIEWS_FILE, [])
    view["id"] = str(uuid.uuid4())
    view["created_at"] = datetime.now().isoformat()
    views.append(view)
    _save(VIEWS_FILE, views)
    return view


@app.delete("/api/views/{view_id}")
def delete_view(view_id: str):
    views = [v for v in _load(VIEWS_FILE, []) if v["id"] != view_id]
    _save(VIEWS_FILE, views)
    return {"ok": True}


# ── Static (must be last) ─────────────────────────────────────────────────────
app.mount("/", StaticFiles(directory=str(STATIC), html=True), name="static")
