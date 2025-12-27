import os
import asyncio
import re
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional

from config.settings import Settings
from services.chat_storage import ChatStorage


class ChatAgent:
    def __init__(self, repo_root: Path, storage: ChatStorage, settings: Optional[Settings] = None) -> None:
        self.repo_root = repo_root.resolve()
        self.storage = storage
        self.settings = settings  # May be None; we'll read env vars if missing
        self._llm_ready = False
        self._llm = None
        self._init_llm()

    def _init_llm(self) -> None:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI

            model = (
                self.settings.gemini_model if self.settings else os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
            )
            api_key = (
                self.settings.google_api_key if self.settings else os.getenv("GOOGLE_API_KEY")
            )
            if not api_key:
                raise RuntimeError("missing GOOGLE_API_KEY")
            self._llm = ChatGoogleGenerativeAI(
                model=model,
                google_api_key=api_key,
                temperature=0.4,
            )
            self._llm_ready = True
        except Exception:
            # Fallback to echo-like behavior
            self._llm = None
            self._llm_ready = False

    def _safe_path(self, rel: str) -> Path:
        p = Path(rel)
        if not p.is_absolute():
            p = (self.repo_root / rel).resolve()
        else:
            p = p.resolve()
        root = self.repo_root.resolve()
        try:
            p.relative_to(root)
        except ValueError:
            if p != root:
                raise ValueError("path not allowed")
        return p

    def _tool_read(self, path: str, max_bytes: int = 200_000) -> str:
        p = self._safe_path(path)
        if not p.exists() or not p.is_file():
            return f"[read] file not found: {path}"
        try:
            data = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return f"[read] unable to read: {path}"
        if len(data) > max_bytes:
            data = data[:max_bytes] + "\n...[truncated]"
        return f"[read] {path}\n" + data

    def _tool_search(self, q: str, max_results: int = 50) -> str:
        root = self.repo_root
        ignored = {".git", "node_modules", "__pycache__", "dist", "build", "venv", ".venv"}
        results: List[str] = []
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
                for idx, line in enumerate(text.splitlines(), 1):
                    if q in line:
                        results.append(f"{fp.relative_to(root)}:{idx}:{line[:200]}")
                        if len(results) >= max_results:
                            return "\n".join(results)
        return "\n".join(results) if results else f"[search] no results for: {q}"

    async def stream_reply(self, session_id: str, user_text: str) -> AsyncGenerator[Dict[str, Any], None]:
        # Simple command parsing for tools: /read <path>, /search <query>
        lower = user_text.strip()
        # @-mentions for files: e.g. "@path/to/file.py" or "@this"
        try:
            mentions = re.findall(r"@([^\s]+)", user_text)
        except Exception:
            mentions = []
        mention_paths: List[str] = []
        for m in mentions:
            mm = m.strip().strip(')]:;,\'.')
            if not mm:
                continue
            if mm.lower() == "this":
                st = self.storage.get_session_state(session_id)
                af = (st.get("active_file") or "").strip()
                if af:
                    mention_paths.append(af)
                continue
            if any(sep in mm for sep in ("/", "\\")) or "." in mm:
                # If it's a bare filename (no slash), resolve relative to context_root if available
                if ("/" not in mm and "\\" not in mm):
                    st = self.storage.get_session_state(session_id)
                    cr = (st.get("context_root") or "").strip()
                    if cr:
                        try:
                            mm = str((Path(cr) / mm).as_posix())
                        except Exception:
                            pass
                mention_paths.append(mm)
        # de-duplicate while preserving order
        seen = set()
        unique_mentions: List[str] = []
        for p in mention_paths:
            if p not in seen:
                unique_mentions.append(p)
                seen.add(p)
        # Load mentioned files as hidden context (no full content pasted)
        context_docs: List[Dict[str, str]] = []
        if unique_mentions:
            loaded_paths: List[str] = []
            not_found: List[str] = []
            errors: List[str] = []
            for p in unique_mentions:
                try:
                    fp = self._safe_path(p)
                    if not fp.exists() or not fp.is_file():
                        not_found.append(p)
                        continue
                    data = fp.read_text(encoding="utf-8", errors="replace")
                    rel = fp.relative_to(self.repo_root).as_posix()
                    loaded_paths.append(rel)
                    context_docs.append({"path": rel, "content": data})
                except Exception as e:
                    errors.append(f"{p}: {e}")
            # Emit a single concise ack
            if not_found:
                yield {"type": "tool", "tool": "ref", "arg": ",".join(not_found), "content": f"[ref] not found: {', '.join(not_found)}"}
            if loaded_paths:
                total_chars = sum(len(d["content"]) for d in context_docs)
                kb = max(1, total_chars // 1024)
                short_list = ", ".join(loaded_paths[:3]) + (" …" if len(loaded_paths) > 3 else "")
                yield {"type": "tool", "tool": "ref", "arg": ",".join(loaded_paths), "content": f"[ref] loaded {len(loaded_paths)} doc(s): {short_list} (~{kb} KB)"}
            if errors:
                yield {"type": "tool", "tool": "ref", "arg": "errors", "content": f"[ref] errors: {', '.join(errors)}"}
        if lower.startswith("/read "):
            arg = user_text.strip()[6:].strip()
            try:
                content = self._tool_read(arg)
            except Exception as e:
                content = f"[read] error: {e}"
            yield {"type": "tool", "tool": "read", "arg": arg, "content": content}
            # No LLM response after direct tool command
            self.storage.add_message(session_id, role="assistant", content=content)
            return
        if lower.startswith("/search "):
            arg = user_text.strip()[8:].strip()
            content = self._tool_search(arg)
            yield {"type": "tool", "tool": "search", "arg": arg, "content": content}
            self.storage.add_message(session_id, role="assistant", content=content)
            return

        # Build the prompt from recent history (lightweight)
        history = self.storage.get_history(session_id, limit=20)
        # Include a professional style system guidance
        style_line = (
            "system: Respond as a professional software AI assistant. Use concise sections with headings and bullet points; "
            "avoid verbosity and raw large dumps. When proposing changes, be clear and structured."
        )
        # Include session state context if available
        st = self.storage.get_session_state(session_id)
        state_line = None
        if isinstance(st, dict):
            cr = st.get("context_root")
            af = st.get("active_file")
            parts = []
            if cr:
                parts.append(f"context_root={cr}")
            if af:
                parts.append(f"active_file={af}")
            if parts:
                state_line = "system: " + ", ".join(parts)
        history_text = []
        history_text.append(style_line)
        if state_line:
            history_text.append(state_line)
        # Add internal docs to the prompt (not shown to user)
        for d in (context_docs or []):
            # Keep size reasonable
            snippet = d["content"][:120000]
            history_text.append(f"system: file:{d['path']}\n{snippet}")
        for m in history:
            role = m.get("role", "user")
            content = m.get("content", "")
            history_text.append(f"{role}: {content}")
        history_text.append(f"user: {user_text}")
        prompt = "\n".join(history_text[-20:])

        # Generate result
        if self._llm_ready and self._llm is not None:
            try:
                # Synchronous call; break into tokens for streaming effect
                res = self._llm.invoke(prompt)
                full_text = res.content if hasattr(res, "content") else (str(res) if res else "")
            except Exception:
                full_text = "I'm unable to access the model right now."
        else:
            full_text = (
                "(offline mode) I received your message. "
                "You can use /read <path> or /search <query>."
            )

        # Stream tokens (simple chunking by words)
        tokens = full_text.split()
        assembled: List[str] = []
        for i, tok in enumerate(tokens):
            assembled.append(tok)
            if i % 5 == 0:  # throttle chunks
                await asyncio.sleep(0.02)
            yield {"type": "token", "token": tok + (" " if i < len(tokens) - 1 else "")}
        final_text = " ".join(assembled)
        yield {"type": "done", "content": final_text}
        self.storage.add_message(session_id, role="assistant", content=final_text)
