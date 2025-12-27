import os
import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any

class ChatStorage:
    def __init__(self, base_dir: str):
        self.base = Path(base_dir)
        self.base.mkdir(parents=True, exist_ok=True)

    def _session_dir(self, session_id: str) -> Path:
        return self.base / session_id

    def _session_file(self, session_id: str) -> Path:
        return self._session_dir(session_id) / "session.json"

    def _attachments_dir(self, session_id: str) -> Path:
        d = self._session_dir(session_id) / "attachments"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def create_session(self, title: Optional[str] = None) -> Dict[str, Any]:
        session_id = str(uuid.uuid4())
        sd = self._session_dir(session_id)
        sd.mkdir(parents=True, exist_ok=True)
        data = {
            "id": session_id,
            "title": title or "Untitled",
            "created_at": datetime.utcnow().isoformat() + "Z",
            "updated_at": datetime.utcnow().isoformat() + "Z",
            "messages": [],
        }
        self._session_file(session_id).write_text(json.dumps(data))
        return data

    def list_sessions(self) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        for p in sorted(self.base.glob("*/session.json")):
            try:
                data = json.loads(p.read_text())
                items.append({
                    "id": data.get("id"),
                    "title": data.get("title"),
                    "created_at": data.get("created_at"),
                    "updated_at": data.get("updated_at"),
                    "message_count": len(data.get("messages", [])),
                })
            except Exception:
                continue
        return items

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        f = self._session_file(session_id)
        if not f.exists():
            return None
        try:
            return json.loads(f.read_text())
        except Exception:
            return None

    def delete_session(self, session_id: str) -> bool:
        d = self._session_dir(session_id)
        if not d.exists():
            return False
        for root, dirs, files in os.walk(d, topdown=False):
            for name in files:
                try:
                    Path(root, name).unlink()
                except Exception:
                    pass
            for name in dirs:
                try:
                    Path(root, name).rmdir()
                except Exception:
                    pass
        try:
            d.rmdir()
            return True
        except Exception:
            return False

    def add_message(self, session_id: str, role: str, content: str, file_refs: Optional[List[str]] = None, attachment_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        s = self.get_session(session_id)
        if not s:
            raise ValueError("session not found")
        msg = {
            "id": str(uuid.uuid4()),
            "role": role,
            "content": content,
            "file_refs": file_refs or [],
            "attachments": attachment_ids or [],
            "ts": datetime.utcnow().isoformat() + "Z",
        }
        s["messages"].append(msg)
        s["updated_at"] = datetime.utcnow().isoformat() + "Z"
        self._session_file(session_id).write_text(json.dumps(s))
        return msg

    def get_history(self, session_id: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        s = self.get_session(session_id)
        if not s:
            return []
        msgs = s.get("messages", [])
        return msgs[offset: offset + limit]

    # --- Session state helpers ---
    def update_session_state(self, session_id: str, patch: Dict[str, Any]) -> Dict[str, Any]:
        s = self.get_session(session_id)
        if not s:
            raise ValueError("session not found")
        state = s.get("state") or {}
        if not isinstance(state, dict):
            state = {}
        state.update({k: v for k, v in (patch or {}).items() if v is not None})
        s["state"] = state
        self._session_file(session_id).write_text(json.dumps(s))
        return state

    def get_session_state(self, session_id: str) -> Dict[str, Any]:
        s = self.get_session(session_id)
        if not s:
            return {}
        st = s.get("state")
        return st if isinstance(st, dict) else {}

    def save_attachment(self, session_id: str, filename: str, data: bytes) -> Dict[str, Any]:
        att_id = str(uuid.uuid4())
        safe_name = filename.replace("..", "_").replace("/", "_").replace("\\", "_")
        path = self._attachments_dir(session_id) / f"{att_id}_{safe_name}"
        path.write_bytes(data)
        meta = {"id": att_id, "filename": filename, "size": len(data)}
        meta_file = self._session_dir(session_id) / "attachments.json"
        items: List[Dict[str, Any]] = []
        if meta_file.exists():
            try:
                items = json.loads(meta_file.read_text())
            except Exception:
                items = []
        items.append(meta)
        meta_file.write_text(json.dumps(items))
        return meta

    def resolve_attachment_path(self, session_id: str, attachment_id: str) -> Optional[Path]:
        d = self._attachments_dir(session_id)
        for p in d.iterdir():
            if p.name.startswith(attachment_id + "_"):
                return p
        return None
