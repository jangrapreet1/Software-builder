from __future__ import annotations

import json
import os
import asyncio
import time
import contextlib
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, UploadFile, File, WebSocket, WebSocketDisconnect, Request, Body

from services.chat_storage import ChatStorage
from services.chat_agent import ChatAgent
from config.settings import Settings
from slowapi import Limiter
from slowapi.util import get_remote_address
from prometheus_client import Counter, Histogram, CollectorRegistry

router = APIRouter(prefix="/api/chat", tags=["chat"])

REPO_ROOT = Path(__file__).resolve().parents[1]
CHAT_DIR = REPO_ROOT / ".sb_artifacts" / "chat_sessions"
SETTINGS = Settings()
storage = ChatStorage(str(CHAT_DIR))
agent = ChatAgent(REPO_ROOT, storage, SETTINGS)
limiter = Limiter(key_func=get_remote_address)

# Chat metrics (initialized from coordinator with custom registry)
CHAT_MESSAGES: Counter | None = None
CHAT_ERRORS: Counter | None = None
CHAT_PATCHES_APPLIED: Counter | None = None
CHAT_TOOL_CALLS: Counter | None = None
CHAT_DURATION: Histogram | None = None


def initialize_chat_metrics(registry: CollectorRegistry) -> None:
    global CHAT_MESSAGES, CHAT_ERRORS, CHAT_PATCHES_APPLIED, CHAT_TOOL_CALLS, CHAT_DURATION
    if CHAT_MESSAGES is not None:
        return
    CHAT_MESSAGES = Counter("chat_messages_total", "chat messages posted", registry=registry)
    CHAT_ERRORS = Counter("chat_errors_total", "chat errors total", registry=registry)
    CHAT_PATCHES_APPLIED = Counter("chat_patches_applied_total", "patches applied via chat", registry=registry)
    CHAT_TOOL_CALLS = Counter("chat_tool_calls_total", "tool calls from chat", ["tool"], registry=registry)
    CHAT_DURATION = Histogram(
        "chat_request_duration_seconds",
        "duration of chat responses",
        buckets=(0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10),
        registry=registry,
    )


def _safe_resolve(path: str) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = (REPO_ROOT / path).resolve()
    else:
        p = p.resolve()
    root = REPO_ROOT.resolve()
    try:
        # Ensure path is inside root (or equal to root)
        p.relative_to(root)
    except ValueError:
        if p != root:
            raise HTTPException(status_code=400, detail="path not allowed")
    return p


def _to_relative(p: Path) -> str:
    root = REPO_ROOT.resolve()
    try:
        return str(p.resolve().relative_to(root))
    except Exception:
        return str(p.resolve())


@router.post("/sessions")
async def create_session(payload: Dict[str, Any] | None = None):
    title = (payload or {}).get("title") if isinstance(payload, dict) else None
    return storage.create_session(title=title)


@router.get("/sessions")
async def list_sessions():
    return {"sessions": storage.list_sessions()}


@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    s = storage.get_session(session_id)
    if not s:
        raise HTTPException(status_code=404, detail="session not found")
    return s


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    ok = storage.delete_session(session_id)
    return {"deleted": bool(ok)}


@router.get("/{session_id}/history")
async def get_history(session_id: str, limit: int = 50, offset: int = 0):
    return {"messages": storage.get_history(session_id, limit=limit, offset=offset)}


@router.get("/{session_id}/state")
async def get_state(session_id: str):
    return {"state": storage.get_session_state(session_id)}


@router.put("/{session_id}/state")
async def put_state(session_id: str, request: Request, payload: Dict[str, Any]):
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="invalid body")
    patch: Dict[str, Any] = {}
    if "context_root" in payload and payload.get("context_root"):
        try:
            cr = _safe_resolve(str(payload["context_root"]))
            patch["context_root"] = _to_relative(cr)
        except HTTPException as e:
            raise e
        except Exception:
            raise HTTPException(status_code=400, detail="invalid context_root")
    if "active_file" in payload and payload.get("active_file"):
        try:
            af = _safe_resolve(str(payload["active_file"]))
            patch["active_file"] = _to_relative(af)
        except HTTPException as e:
            raise e
        except Exception:
            raise HTTPException(status_code=400, detail="invalid active_file")
    state = storage.update_session_state(session_id, patch)
    return {"state": state}


@limiter.limit(SETTINGS.rate_limit_chat_attachment)
@router.post("/{session_id}/attachments")
async def upload_attachment(session_id: str, request: Request, file: UploadFile = File(...)):
    data = await file.read()
    # Limit attachment size to 5MB
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="attachment too large (max 5MB)")
    meta = storage.save_attachment(session_id, file.filename, data)
    return {"attachment": meta}


@limiter.limit(SETTINGS.rate_limit_chat_message)
@router.post("/{session_id}/messages")
async def post_message(session_id: str, request: Request, payload: Dict[str, Any]):
    text = (payload or {}).get("text")
    if not text or not str(text).strip():
        raise HTTPException(status_code=400, detail="text required")
    file_refs = (payload or {}).get("file_refs") or []
    attachments = (payload or {}).get("attachments") or []
    msg = storage.add_message(session_id, role="user", content=text, file_refs=file_refs, attachment_ids=attachments)
    if CHAT_MESSAGES:
        CHAT_MESSAGES.inc()
    return {"message": msg}


@router.get("/{session_id}/context/read")
async def context_read(session_id: str, path: str):
    p = _safe_resolve(path)
    if not p.exists() or not p.is_file():
        raise HTTPException(status_code=404, detail="file not found")
    try:
        data = p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        raise HTTPException(status_code=400, detail="unable to read file as text")
    return {"path": str(p.relative_to(REPO_ROOT)), "content": data}


@router.get("/{session_id}/context/search")
async def context_search(session_id: str, q: str, max_results: int = 100):
    results: List[Dict[str, Any]] = []
    root = REPO_ROOT.resolve()
    ignored = {".git", "node_modules", "__pycache__", "dist", "build", "venv", ".venv"}
    for dirpath, dirnames, filenames in os.walk(root):
        dn = Path(dirpath).name
        if dn in ignored:
            dirnames[:] = []
            continue
        for fn in filenames:
            fp = Path(dirpath) / fn
            try:
                text = fp.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            lines = text.splitlines()
            for idx, line in enumerate(lines, 1):
                if q in line:
                    results.append({"path": str(fp.relative_to(root)), "line": line[:500], "line_no": idx})
                    if len(results) >= max_results:
                        return {"results": results}
    return {"results": results}


@limiter.limit(SETTINGS.rate_limit_chat_patch)
@router.post("/{session_id}/patch/dry-run")
async def patch_dry_run(session_id: str, request: Request, edits: Dict[str, Any] = Body(...)):
    items = edits.get("edits") if isinstance(edits, dict) else None
    if not isinstance(items, list) or not items:
        raise HTTPException(status_code=400, detail="edits required")
    previews: List[Dict[str, Any]] = []
    for e in items:
        path = e.get("path")
        old = e.get("old")
        new = e.get("new")
        if not path or old is None or new is None:
            raise HTTPException(status_code=400, detail="invalid edit item")
        p = _safe_resolve(path)
        if not p.exists() or not p.is_file():
            raise HTTPException(status_code=404, detail=f"file not found: {path}")
        try:
            content = p.read_text(encoding="utf-8", errors="strict")
        except Exception:
            raise HTTPException(status_code=400, detail=f"unable to read: {path}")
        will_change = old in content and (new != old)
        before_len = len(content)
        after = content.replace(old, new)
        after_len = len(after)
        previews.append({
            "path": str(p.relative_to(REPO_ROOT)),
            "will_change": bool(will_change),
            "before_len": before_len,
            "after_len": after_len,
        })
    return {"previews": previews}


@limiter.limit(SETTINGS.rate_limit_chat_patch)
@router.post("/{session_id}/patch/apply")
async def patch_apply(session_id: str, request: Request, edits: Dict[str, Any] = Body(...)):
    # Require explicit permission for write operations
    pm = getattr(getattr(request, "app", None), "state", None)
    pm = getattr(pm, "permission_manager", None)
    if not pm or not pm.has_permission(session_id, "allow_write"):
        raise HTTPException(status_code=403, detail="permission required: allow_write")
    items = edits.get("edits") if isinstance(edits, dict) else None
    if not isinstance(items, list) or not items:
        raise HTTPException(status_code=400, detail="edits required")
    applied: List[str] = []
    for e in items:
        path = e.get("path")
        old = e.get("old")
        new = e.get("new")
        if not path or old is None or new is None:
            raise HTTPException(status_code=400, detail="invalid edit item")
        p = _safe_resolve(path)
        if not p.exists() or not p.is_file():
            raise HTTPException(status_code=404, detail=f"file not found: {path}")
        try:
            content = p.read_text(encoding="utf-8", errors="strict")
        except Exception:
            raise HTTPException(status_code=400, detail=f"unable to read: {path}")
        if old not in content:
            continue
        updated = content.replace(old, new)
        p.write_text(updated, encoding="utf-8")
        applied.append(str(p.relative_to(REPO_ROOT)))
        try:
            storage.add_message(session_id, role="assistant", content=f"Applied edit to {p.relative_to(REPO_ROOT)}")
        except Exception:
            pass
    if CHAT_PATCHES_APPLIED and applied:
        CHAT_PATCHES_APPLIED.inc(len(applied))
    return {"applied": applied}


@router.websocket("/ws/{session_id}")
async def chat_ws(websocket: WebSocket, session_id: str):
    await websocket.accept()
    await websocket.send_json({"type": "status", "value": "connected", "session_id": session_id})
    try:
        while True:
            # Wait for a client event
            try:
                msg = await websocket.receive_json()
            except WebSocketDisconnect:
                break
            except Exception:
                # If non-JSON, ignore
                continue

            if not isinstance(msg, dict):
                continue
            msg_type = msg.get("type")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            if msg_type == "user_message":
                text = (msg.get("text") or "").strip()
                if not text:
                    await websocket.send_json({"type": "error", "message": "empty message"})
                    continue
                # Persist user message
                storage.add_message(session_id, role="user", content=text)
                if CHAT_MESSAGES:
                    CHAT_MESSAGES.inc()
                # Stream assistant reply via ChatAgent
                start = time.time()
                async for event in agent.stream_reply(session_id, text):
                    try:
                        await websocket.send_json(event)
                        if event.get("type") == "tool" and CHAT_TOOL_CALLS:
                            CHAT_TOOL_CALLS.labels(tool=event.get("tool") or "unknown").inc()
                    except WebSocketDisconnect:
                        return
                # One final marker for UI convenience
                await websocket.send_json({"type": "complete"})
                if CHAT_DURATION:
                    CHAT_DURATION.observe(max(0.0, time.time() - start))
                continue

            # Unknown msg type
            await websocket.send_json({"type": "error", "message": "unknown message type"})

    except WebSocketDisconnect:
        return
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
        if CHAT_ERRORS:
            CHAT_ERRORS.inc()
    finally:
        with contextlib.suppress(Exception):
            await websocket.close()
