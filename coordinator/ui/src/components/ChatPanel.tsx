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
            } catch { }
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
                } catch { }
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
    } catch { }
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
    apiClient.put(`/api/chat/${sessionId}/state`, payload, { suppressErrorNotification: true }).catch(() => { });
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
    <div className={embedded ? 'h-full' : 'container mx-auto px-4 py-8'}>
      <div className={embedded ? 'h-full flex flex-col' : 'grid grid-cols-1 lg:grid-cols-4 gap-6'}>
        {!hideList && (
          <aside className={embedded ? 'glass-panel rounded-xl p-3 lg:col-span-1 mb-4' : 'glass-panel rounded-xl p-4 lg:col-span-1'}>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xs font-bold text-gray-400 uppercase tracking-wider">Sessions</h2>
              <button
                className="text-[10px] px-2 py-1 rounded-lg bg-primary/20 hover:bg-primary/30 text-primary hover:text-white transition-colors border border-primary/20 font-bold"
                onClick={async () => {
                  const created = await apiClient.post(`/api/chat/sessions`, {});
                  setSessions((prev) => [{ id: created.id, title: created.title }, ...prev]);
                  onSelectSession(created.id);
                }}
              >New</button>
            </div>
            <div className="space-y-2 max-h-80 overflow-auto custom-scrollbar pr-1">
              {sessions.map((s) => (
                <button
                  key={s.id}
                  onClick={() => onSelectSession(s.id)}
                  className={`w-full text-left px-3 py-2 rounded-lg border transition-all ${sessionId === s.id ? 'bg-primary/20 border-primary/30 text-white' : 'bg-white/5 border-transparent text-gray-400 hover:bg-white/10 hover:text-gray-200'}`}
                >
                  <div className="text-xs font-medium truncate">{s.title || s.id.slice(0, 8)}</div>
                  <div className="text-[10px] opacity-60">{s.message_count ?? 0} messages</div>
                </button>
              ))}
            </div>
          </aside>
        )}

        <section className={embedded ? 'glass-panel rounded-xl flex flex-col flex-1 min-h-0 overflow-hidden border border-white/10' : 'glass-panel rounded-xl p-0 lg:col-span-3 flex flex-col h-[70vh] border border-white/10'}>
          <div className="flex flex-shrink-0 items-center justify-between p-3 border-b border-white/10 bg-black/20">
            <div className="text-xs text-gray-400 flex items-center gap-2">
              <i className="fas fa-robot text-primary mb-0.5"></i>
              <span className="font-bold text-gray-200">AI Assistant</span>
              <span className="text-gray-600">•</span>
              <span className="font-mono text-[10px] opacity-50">{sessionId?.slice(0, 8) || '...'}</span>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={async () => {
                  const created = await apiClient.post(`/api/chat/sessions`, {});
                  setSessions((prev) => [{ id: created.id, title: created.title }, ...prev]);
                  onSelectSession(created.id);
                }}
                className="w-6 h-6 rounded-lg bg-white/5 hover:bg-white/10 text-gray-400 hover:text-white flex items-center justify-center transition-colors"
                title="New chat"
              >
                <i className="fas fa-plus text-[10px]"></i>
              </button>
              <button onClick={readCurrentFile} disabled={!selectedPath} className="w-6 h-6 rounded-lg bg-white/5 hover:bg-white/10 text-gray-400 hover:text-white flex items-center justify-center disabled:opacity-30 transition-colors" title="Read current file">
                <i className="fas fa-file-code text-[10px]"></i>
              </button>

              <div className="hidden sm:flex items-center gap-1 bg-black/20 rounded-lg p-0.5 border border-white/5">
                <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search..." className="text-[10px] px-2 py-0.5 bg-transparent border-none text-gray-300 w-20 focus:ring-0 placeholder-gray-600" />
                <button onClick={doSearch} className="w-5 h-5 rounded bg-white/10 hover:bg-white/20 text-[10px] text-gray-400 hover:text-white flex items-center justify-center">
                  <i className="fas fa-search"></i>
                </button>
              </div>

              <button onClick={grantWrite} className="px-2 py-1 rounded-lg bg-amber-500/10 hover:bg-amber-500/20 text-amber-500 hover:text-amber-400 border border-amber-500/20 text-[10px] font-bold transition-colors" title="Grant allow_write">
                <i className="fas fa-lock-open mr-1"></i> Grant
              </button>

              <div className={`w-2 h-2 rounded-full ${connecting ? 'bg-yellow-500 animate-pulse' : connected ? 'bg-emerald-500' : 'bg-red-500'}`} title={connecting ? 'Connecting' : connected ? 'Connected' : 'Disconnected'}></div>
            </div>
          </div>

          <div className="flex-1 overflow-auto space-y-4 p-4 custom-scrollbar bg-black/20">
            {messages.map((m, idx) => (
              <div key={idx} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div
                  className={`max-w-[90%] px-4 py-3 rounded-2xl text-sm leading-relaxed shadow-sm ${m.role === 'user'
                    ? 'bg-primary/20 border border-primary/30 text-white rounded-tr-sm'
                    : m.role === 'assistant'
                      ? 'bg-white/5 border border-white/10 text-gray-200 rounded-tl-sm'
                      : 'bg-amber-500/10 border border-amber-500/20 text-amber-200 font-mono text-xs rounded-tl-sm'
                    }`}
                >
                  {m.role === 'assistant' && (
                    <div className="mb-1 text-[10px] font-bold text-primary uppercase tracking-wider opacity-70 flex items-center gap-1">
                      <i className="fas fa-robot"></i> Assistant
                    </div>
                  )}
                  {m.role === 'tool' && (
                    <div className="mb-1 text-[10px] font-bold text-amber-400 uppercase tracking-wider opacity-70 flex items-center gap-1">
                      <i className="fas fa-tools"></i> Tool Output
                    </div>
                  )}
                  {renderMessageContent(m.content, activeDisplayPath, (label) => showToast(`Sent to Changes: ${label}`))}
                </div>
              </div>
            ))}
          </div>

          <div className="flex-shrink-0 p-3 border-t border-white/10 bg-black/40 backdrop-blur-md">
            <div className="flex items-center justify-between mb-2 text-[10px] text-gray-500 font-medium px-1">
              <div className="truncate pr-2 flex items-center">
                <i className="far fa-file mr-1.5 opacity-70"></i>
                <span className="text-gray-600 mr-1">Active file:</span>
                <span className="text-gray-400 font-mono break-all">{activeDisplayPath ? activeDisplayPath.split('/').pop() : 'None'}</span>
              </div>
              <button onClick={readCurrentFile} disabled={!selectedPath} className="text-[10px] px-2 py-0.5 rounded bg-white/5 hover:bg-white/10 hover:text-white disabled:opacity-30 transition-colors">Read Context</button>
            </div>

            <div className="relative group" onDragOver={allowDrop} onDrop={handleDropOnComposer}>
              <div className="absolute inset-0 bg-primary/5 rounded-xl -z-10 group-hover:bg-primary/10 transition-colors"></div>
              <div className="flex items-end gap-2 p-1.5">
                <textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      onSend();
                    }
                  }}
                  ref={inputRef as any}
                  className="flex-1 bg-transparent border-none text-white placeholder-gray-500 text-sm focus:ring-0 max-h-32 min-h-[40px] py-2 px-2 resize-none custom-scrollbar"
                  placeholder="Ask AI assistant..."
                  rows={1}
                />
                <div className="flex flex-col gap-1 pb-1">
                  <label className="w-8 h-8 flex items-center justify-center rounded-lg bg-white/5 hover:bg-white/10 text-gray-400 hover:text-white cursor-pointer transition-colors" title="Attach file">
                    <input type="file" className="hidden" onChange={onUpload} />
                    {uploading ? <i className="fas fa-circle-notch fa-spin text-xs"></i> : <i className="fas fa-paperclip"></i>}
                  </label>
                  <button
                    onClick={onSend}
                    disabled={!input.trim()}
                    className="w-8 h-8 flex items-center justify-center rounded-lg bg-primary hover:bg-primary-600 text-white shadow-lg shadow-primary/20 disabled:opacity-50 disabled:shadow-none transition-all transform active:scale-95"
                  >
                    <i className="fas fa-paper-plane text-xs"></i>
                  </button>
                </div>
              </div>
            </div>
          </div>
          {toast && (
            <div className="absolute bottom-20 right-6 z-50">
              <div className="px-4 py-2 bg-emerald-500 text-white text-xs font-bold rounded-lg shadow-lg shadow-emerald-500/20 animate-fade-in flex items-center">
                <i className="fas fa-check-circle mr-2"></i>
                {toast}
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  );
};

export default ChatPanel;
