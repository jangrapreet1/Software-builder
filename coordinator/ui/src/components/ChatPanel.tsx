import React, { useCallback, useEffect, useRef, useState } from 'react';
import { apiClient } from '../utils/apiClient';

interface ChatSessionMeta {
  id: string;
  title?: string;
  created_at?: string;
  updated_at?: string;
  message_count?: number;
}

interface ChatMessage {
  id?: string;
  role: 'user' | 'assistant' | 'tool' | 'system';
  content: string;
  ts?: string;
}

type WsEvent =
  | { type: 'status'; value: string; session_id: string }
  | { type: 'token'; token: string }
  | { type: 'tool'; tool?: string; arg?: string; content?: string }
  | { type: 'done'; content: string }
  | { type: 'complete' }
  | { type: 'error'; message: string };

const wsUrlFor = (sessionId: string) => {
  const isSecure = window.location.protocol === 'https:';
  const base = `${isSecure ? 'wss' : 'ws'}://${window.location.host}`;
  return `${base}/api/chat/ws/${sessionId}`;
};

const DiffBlock: React.FC<{ text: string }> = ({ text }) => {
  const lines = text.replace(/\r\n/g, '\n').split('\n');
  const renderLine = (ln: string, i: number) => {
    let cls = 'bg-white text-gray-800';
    if (ln.startsWith('@@')) cls = 'bg-indigo-50 text-indigo-800';
    else if (ln.startsWith('+++') || ln.startsWith('---')) cls = 'bg-gray-50 text-gray-600';
    else if (ln.startsWith('+')) cls = 'bg-green-50 text-green-800';
    else if (ln.startsWith('-')) cls = 'bg-red-50 text-red-800';
    else cls = 'bg-white text-gray-800';
    return (
      <div key={i} className={`text-xs font-mono px-2 py-0.5 ${cls}`}>{ln || '\u00A0'}</div>
    );
  };
  return (
    <div className="border rounded overflow-auto max-h-96">
      {lines.map(renderLine)}
    </div>
  );
};

function renderMessageContent(
  content: string,
  fallbackPath?: string,
  onAdded?: (label: string) => void,
): JSX.Element {
  const re = /```diff\s*([\s\S]*?)```/g;
  const parts: React.ReactNode[] = [];
  let last = 0;
  let m: RegExpExecArray | null;
  const extractDiffInfo = (text: string) => {
    const norm = text.replace(/\r\n/g, '\n');
    const sanitizePath = (p: string) => (p || '').trim().split(/\s+/)[0].replace(/^a\//, '').replace(/^b\//, '');
    let path = '';
    // Robust: try regex across the whole text first (handles single-line diffs)
    let mFile = norm.match(/^\+\+\+\s+[ab]\/([^\s]+)/m) || norm.match(/^---\s+[ab]\/([^\s]+)/m);
    if (mFile) {
      path = sanitizePath(mFile[1]);
    } else {
      // Fallback: scan by lines
      const lines = norm.split('\n');
      for (const ln of lines) {
        if (ln.startsWith('+++ ')) { path = sanitizePath(ln.slice(4)); break; }
        if (ln.startsWith('--- ')) { path = sanitizePath(ln.slice(4)); }
      }
    }
    // Find representative removed/added lines
    const oldMatch = norm.match(/^(?:-|\-)(?!-)(.*)$/m);
    const newMatch = norm.match(/^(?:\+|\+)(?!\+)(.*)$/m);
    let oldLine = oldMatch ? (oldMatch[1] || '').trim() : '';
    let newLine = newMatch ? (newMatch[1] || '').trim() : '';
    if (!path && fallbackPath) path = sanitizePath(fallbackPath);
    return { path: sanitizePath(path), oldLine, newLine };
  };
  while ((m = re.exec(content)) !== null) {
    const pre = content.slice(last, m.index);
    if (pre.trim()) {
      parts.push(<div key={`t-${last}`} className="whitespace-pre-wrap break-words text-sm">{pre}</div>);
    }
    const blockKey = `d-${m.index}`;
    parts.push(<DiffBlock key={blockKey} text={m[1]} />);
    const info = extractDiffInfo(m[1]);
    parts.push(
      <div key={`toolbar-${blockKey}`} className="flex items-center gap-2 mt-1">
        <button
          className="text-xs px-2 py-1 rounded bg-gray-100 hover:bg-gray-200"
          onClick={() => {
            const detail = { path: info.path, old: info.oldLine, new: info.newLine };
            const ev1 = new CustomEvent('sb:add-change' as any, { detail, bubbles: true, composed: true } as any);
            const ev2 = new CustomEvent('sb:add-change' as any, { detail, bubbles: true, composed: true } as any);
            window.dispatchEvent(ev1);
            document.dispatchEvent(ev2);
            console.debug('[Chat] Add to Changes dispatched', detail);
            (window as any).__lastAddChange = detail;
            const label = (detail.path || '').split(/\s+/)[0] || 'change';
            onAdded && onAdded(label);
            // global queue fallback
            try {
              const g: any = window as any;
              g.__sbAddChangeQueue = g.__sbAddChangeQueue || [];
              g.__sbAddChangeQueue.push(detail);
              if (typeof g.__sbAddChangeDirect === 'function') {
                g.__sbAddChangeDirect(detail);
              }
            } catch {}
          }}
        >
          Add to Changes
        </button>
      </div>
    );
    last = re.lastIndex;
  }
  const tail = content.slice(last);
  if (parts.length === 0) {
    const looksLikeUnified = /(---\s|\+\+\+\s|^@@\s)/m.test(content) && /^(\+|-)/m.test(content);
    if (looksLikeUnified) {
      const info = extractDiffInfo(content);
      return (
        <div className="space-y-2">
          <DiffBlock text={content} />
          <div className="flex items-center gap-2">
            <button
              className="text-xs px-2 py-1 rounded bg-gray-100 hover:bg-gray-200"
              onClick={() => {
                const detail = { path: info.path, old: info.oldLine, new: info.newLine };
                const ev1 = new CustomEvent('sb:add-change' as any, { detail, bubbles: true, composed: true } as any);
                const ev2 = new CustomEvent('sb:add-change' as any, { detail, bubbles: true, composed: true } as any);
                window.dispatchEvent(ev1);
                document.dispatchEvent(ev2);
                console.debug('[Chat] Add to Changes dispatched', detail);
                (window as any).__lastAddChange = detail;
                const label = (detail.path || '').split(/\s+/)[0] || 'change';
                onAdded && onAdded(label);
                try {
                  const g: any = window as any;
                  g.__sbAddChangeQueue = g.__sbAddChangeQueue || [];
                  g.__sbAddChangeQueue.push(detail);
                  if (typeof g.__sbAddChangeDirect === 'function') {
                    g.__sbAddChangeDirect(detail);
                  }
                } catch {}
              }}
            >
              Add to Changes
            </button>
          </div>
        </div>
      );
    }
  }
  if (tail.trim()) {
    parts.push(<div key={`t-end`} className="whitespace-pre-wrap break-words text-sm">{tail}</div>);
  }
  if (parts.length === 0) {
    return <div className="whitespace-pre-wrap break-words text-sm">{content}</div>;
  }
  return <div className="space-y-2">{parts}</div>;
}

interface ChatPanelProps {
  embedded?: boolean;
  contextRoot?: string;
  hideSessionList?: boolean;
  selectedPath?: string;
  onSessionReady?: (sessionId: string) => void;
}

export const ChatPanel: React.FC<ChatPanelProps> = ({ embedded = false, contextRoot, hideSessionList, selectedPath, onSessionReady }) => {
  const [sessions, setSessions] = useState<ChatSessionMeta[]>([]);
  const [sessionId, setSessionId] = useState<string>('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState<string>('');
  const [connecting, setConnecting] = useState(false);
  const [connected, setConnected] = useState(false);
  const [uploading, setUploading] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const streamingBufferRef = useRef<string>('');
  const [search, setSearch] = useState<string>('');
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [toast, setToast] = useState<string>('');

  const joinPath = (base?: string, rel?: string) => {
    const b = (base || '').replace(/\\/g, '/').replace(/^\.+\//, '');
    const r = (rel || '').replace(/\\/g, '/').replace(/^\.+\//, '');
    if (!b) return r;
    if (!r) return b;
    return `${b.replace(/\/$/, '')}/${r.replace(/^\//, '')}`;
  };

  const loadSessions = useCallback(async () => {
    const data = await apiClient.get<{ sessions: ChatSessionMeta[] }>(`/api/chat/sessions`, {
      suppressErrorNotification: true,
    });
    setSessions(data.sessions || []);
    return data.sessions || [];
  }, []);

  const ensureSession = useCallback(async () => {
    const existing = await loadSessions();
    if (existing.length > 0) {
      setSessionId(existing[0].id);
      if (onSessionReady) onSessionReady(existing[0].id);
      return existing[0].id;
    }
    const created = await apiClient.post(`/api/chat/sessions`, {});
    setSessionId(created.id);
    if (onSessionReady) onSessionReady(created.id);
    await loadSessions();
    return created.id as string;
  }, [loadSessions]);

  const loadHistory = useCallback(async (sid: string) => {
    const data = await apiClient.get<{ messages: ChatMessage[] }>(`/api/chat/${sid}/history`, {
      suppressErrorNotification: true,
    });
    setMessages(data.messages || []);
  }, []);

  const closeWs = useCallback(() => {
    try {
      if (wsRef.current) {
        wsRef.current.close();
      }
    } catch {}
    wsRef.current = null;
    setConnected(false);
  }, []);

  const openWs = useCallback((sid: string) => {
    closeWs();
    setConnecting(true);
    const ws = new WebSocket(wsUrlFor(sid));
    wsRef.current = ws;

    ws.onopen = () => {
      setConnecting(false);
      setConnected(true);
    };

    ws.onclose = () => {
      setConnected(false);
      setConnecting(false);
    };

    ws.onerror = () => {
      setConnected(false);
      setConnecting(false);
    };

    ws.onmessage = (evt) => {
      try {
        const data: WsEvent = JSON.parse(evt.data);
        if (data.type === 'token') {
          streamingBufferRef.current += data.token;
          // Optimistic UI: show as the last assistant message streaming
          setMessages((prev) => {
            const copy = [...prev];
            // if last is assistant placeholder, update it, else push new
            if (copy.length > 0 && copy[copy.length - 1].role === 'assistant' && copy[copy.length - 1].content.endsWith('…')) {
              copy[copy.length - 1] = {
                ...copy[copy.length - 1],
                content: streamingBufferRef.current + '…',
              };
            } else {
              copy.push({ role: 'assistant', content: streamingBufferRef.current + '…' });
            }
            return copy;
          });
        } else if (data.type === 'done') {
          const finalText = data.content;
          streamingBufferRef.current = '';
          setMessages((prev) => {
            const copy = [...prev];
            // replace last assistant streaming with final
            if (copy.length > 0 && copy[copy.length - 1].role === 'assistant' && copy[copy.length - 1].content.endsWith('…')) {
              copy[copy.length - 1] = { role: 'assistant', content: finalText };
            } else {
              copy.push({ role: 'assistant', content: finalText });
            }
            return copy;
          });
        } else if (data.type === 'tool') {
          setMessages((prev) => [
            ...prev,
            { role: 'tool', content: `[${data.tool || 'tool'}] ${data.arg || ''}\n${data.content || ''}`.trim() },
          ]);
        } else if (data.type === 'error') {
          setMessages((prev) => [...prev, { role: 'system', content: `Error: ${data.message}` }]);
        }
      } catch {
        // ignore non-JSON
      }
    };
  }, [closeWs]);

  const contextSentRef = useRef<string | null>(null);

  useEffect(() => {
    (async () => {
      const sid = await ensureSession();
      await loadHistory(sid);
      openWs(sid);
      if (contextRoot && contextSentRef.current !== sid) {
        try {
          await apiClient.post(`/api/chat/${sid}/messages`, {
            text: `Context: focus on project root ${contextRoot}. Limit reads/searches and changes to this subtree unless instructed otherwise.`,
          }, { suppressErrorNotification: true });
          setMessages((prev) => [
            ...prev,
            { role: 'system', content: `Context set: project root ${contextRoot}` },
          ]);
          contextSentRef.current = sid;
        } catch {
          // ignore context send failure
        }
      }
    })();
    return () => closeWs();
  }, [ensureSession, loadHistory, openWs, closeWs, contextRoot]);

  // Push active file + context root to backend session state when they change
  useEffect(() => {
    if (!sessionId) return;
    const payload: any = {};
    if (contextRoot) payload.context_root = contextRoot;
    if (selectedPath) payload.active_file = joinPath(contextRoot, selectedPath);
    if (Object.keys(payload).length === 0) return;
    apiClient.put(`/api/chat/${sessionId}/state`, payload, { suppressErrorNotification: true }).catch(()=>{});
  }, [sessionId, selectedPath, contextRoot]);

  const onSelectSession = async (sid: string) => {
    setSessionId(sid);
    if (onSessionReady) onSessionReady(sid);
    await loadHistory(sid);
    openWs(sid);
  };

  const onSend = useCallback(async () => {
    const text = input.trim();
    if (!text || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    setMessages((prev) => [...prev, { role: 'user', content: text }]);
    wsRef.current.send(JSON.stringify({ type: 'user_message', text }));
    setInput('');
  }, [input]);

  const sendWS = (text: string) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    wsRef.current.send(JSON.stringify({ type: 'user_message', text }));
    setMessages((prev) => [...prev, { role: 'user', content: text }]);
  };

  const readCurrentFile = () => {
    const rel = (selectedPath || '').trim();
    if (!rel) return;
    sendWS(`@this`);
  };

  const doSearch = () => {
    const q = (search || '').trim();
    if (!q) return;
    sendWS(`/search ${q}`);
  };

  const grantWrite = async () => {
    if (!sessionId) return;
    try {
      await apiClient.post('/api/session/permissions', {
        session_id: sessionId,
        actions: ['allow_write'],
        duration: 3600,
      }, { suppressErrorNotification: true });
      setMessages((prev) => [...prev, { role: 'system', content: 'Granted allow_write permission for this session.' }]);
    } catch (e: any) {
      setMessages((prev) => [...prev, { role: 'system', content: `Grant permission failed: ${e?.message || e}` }]);
    }
  };

  const onUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || !sessionId) return;
    const file = files[0];
    const form = new FormData();
    form.append('file', file);
    try {
      setUploading(true);
      const res = await fetch(`/api/chat/${sessionId}/attachments`, { method: 'POST', body: form });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail || data?.message || 'Upload failed');
      setMessages((prev) => [...prev, { role: 'system', content: `Uploaded attachment: ${data?.attachment?.filename || file.name}` }]);
    } catch (err: any) {
      setMessages((prev) => [...prev, { role: 'system', content: `Upload error: ${err?.message || err}` }]);
    } finally {
      setUploading(false);
      e.target.value = '';
    }
  };
  const activeDisplayPath = selectedPath ? joinPath(contextRoot, selectedPath) : '';

  const insertAtCaret = (text: string) => {
    const el = inputRef.current;
    if (!el) {
      setInput((prev) => (prev + text));
      return;
    }
    const start = el.selectionStart ?? el.value.length;
    const end = el.selectionEnd ?? el.value.length;
    const newVal = el.value.slice(0, start) + text + el.value.slice(end);
    setInput(newVal);
    // restore caret after React state flush
    requestAnimationFrame(() => {
      if (inputRef.current) {
        const pos = start + text.length;
        inputRef.current.selectionStart = pos;
        inputRef.current.selectionEnd = pos;
        inputRef.current.focus();
      }
    });
  };

  const handleDropOnComposer = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const plain = e.dataTransfer.getData('text/plain');
    let mention = (plain || '').trim();
    if (!mention) {
      const uri = e.dataTransfer.getData('text/uri-list');
      if (uri) mention = `@${uri}`;
    }
    if (mention && mention.startsWith('@')) {
      insertAtCaret(mention + ' ');
    }
  };

  const allowDrop = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(''), 1800);
  };

  const hideList = hideSessionList ?? embedded;

  return (
    <div className={embedded ? '' : 'container mx-auto px-4 py-8'}>
      <div className={embedded ? (hideList ? '' : 'grid grid-cols-1 lg:grid-cols-4 gap-3') : 'grid grid-cols-1 lg:grid-cols-4 gap-6'}>
        {!hideList && (
        <aside className={embedded ? 'bg-white rounded border p-3 lg:col-span-1' : 'bg-white rounded-lg shadow p-4 lg:col-span-1'}>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-gray-700">Sessions</h2>
            <button
              className="text-xs px-2 py-1 rounded bg-blue-600 text-white hover:bg-blue-700"
              onClick={async () => {
                const created = await apiClient.post(`/api/chat/sessions`, {});
                setSessions((prev) => [{ id: created.id, title: created.title }, ...prev]);
                onSelectSession(created.id);
              }}
            >New</button>
          </div>
          <div className="space-y-2 max-h-80 overflow-auto">
            {sessions.map((s) => (
              <button
                key={s.id}
                onClick={() => onSelectSession(s.id)}
                className={`w-full text-left px-3 py-2 rounded border ${sessionId === s.id ? 'bg-blue-50 border-blue-200' : 'bg-white border-gray-200 hover:bg-gray-50'}`}
              >
                <div className="text-sm font-medium text-gray-800 truncate">{s.title || s.id.slice(0, 8)}</div>
                <div className="text-[10px] text-gray-500">{s.message_count ?? 0} messages</div>
              </button>
            ))}
          </div>
        </aside>
        )}

        <section className={embedded ? (hideList ? 'bg-white rounded border p-3 flex flex-col h-[65vh]' : 'bg-white rounded border p-3 lg:col-span-3 flex flex-col h-[60vh]') : 'bg-white rounded-lg shadow p-4 lg:col-span-3 flex flex-col h-[70vh]'}>
          <div className="flex items-center justify-between mb-3">
            <div className="text-sm text-gray-600 flex items-center gap-2">
              <span>Agent Chat</span>
              <span className="text-gray-400">•</span>
              <span className="font-mono text-xs">{sessionId?.slice(0, 8) || '...'}</span>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={async () => {
                  const created = await apiClient.post(`/api/chat/sessions`, {});
                  setSessions((prev) => [{ id: created.id, title: created.title }, ...prev]);
                  onSelectSession(created.id);
                }}
                className="text-xs px-2 py-1 rounded bg-blue-600 text-white hover:bg-blue-700"
                title="New chat"
              >
                + New
              </button>
              <button onClick={readCurrentFile} disabled={!selectedPath} className="text-xs px-2 py-1 rounded bg-gray-100 hover:bg-gray-200 disabled:opacity-50" title="Read current file">Read file</button>
              <div className="flex items-center gap-1">
                <input value={search} onChange={(e)=>setSearch(e.target.value)} placeholder="Search" className="text-xs px-2 py-1 border rounded w-28" />
                <button onClick={doSearch} className="text-xs px-2 py-1 rounded bg-gray-100 hover:bg-gray-200">Go</button>
              </div>
              <button onClick={grantWrite} className="text-xs px-2 py-1 rounded bg-amber-600 text-white hover:bg-amber-700" title="Grant allow_write">Grant write</button>
              <span className="text-xs text-gray-500">{connecting ? 'Connecting…' : connected ? 'Connected' : 'Disconnected'}</span>
            </div>
          </div>

          <div className="flex-1 overflow-auto space-y-3 pr-1">
            {messages.map((m, idx) => (
              <div key={idx} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[85%] px-3 py-2 rounded ${m.role === 'user' ? 'bg-blue-600 text-white' : m.role === 'assistant' ? 'bg-gray-100 text-gray-800' : 'bg-amber-50 text-amber-900 border border-amber-200'}`}>
                  {renderMessageContent(m.content, activeDisplayPath, (label) => showToast(`Sent to Changes: ${label}`))}
                </div>
              </div>
            ))}
          </div>

          <div className="mt-3 pt-3 border-t border-gray-200">
            <div className="flex items-center justify-between mb-2 text-xs text-gray-600">
              <div className="truncate pr-2">
                <span className="text-gray-500">Active file: </span>
                <span className="font-mono break-all">{activeDisplayPath || 'No file selected'}</span>
              </div>
              <button onClick={readCurrentFile} disabled={!selectedPath} className="text-xs px-2 py-1 rounded bg-gray-100 hover:bg-gray-200 disabled:opacity-50">Read file</button>
            </div>
            <div className="flex items-center gap-2" onDragOver={allowDrop} onDrop={handleDropOnComposer}>
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') onSend(); }}
                ref={inputRef}
                className="flex-1 px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                placeholder="Type a message. Try @this, @path/to/file, or /search query"
              />
              <button onClick={onSend} className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">Send</button>
              <label className="px-3 py-2 bg-gray-100 rounded cursor-pointer text-sm hover:bg-gray-200">
                <input type="file" className="hidden" onChange={onUpload} />
                {uploading ? 'Uploading…' : 'Attach'}
              </label>
            </div>
          </div>
          {toast && (
            <div className="fixed bottom-4 right-6 z-50">
              <div className="px-3 py-2 bg-gray-900 text-white text-xs rounded shadow">{toast}</div>
            </div>
          )}
        </section>
      </div>
    </div>
  );
};

export default ChatPanel;
