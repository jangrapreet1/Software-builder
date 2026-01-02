import React, { useCallback, useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
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

// Slash command definitions
const SLASH_COMMANDS = [
  { cmd: '/fix', desc: 'Fix errors in current file', icon: 'fa-wrench', color: 'text-red-400' },
  { cmd: '/test', desc: 'Generate tests for code', icon: 'fa-flask', color: 'text-green-400' },
  { cmd: '/explain', desc: 'Explain selected code', icon: 'fa-lightbulb', color: 'text-yellow-400' },
  { cmd: '/refactor', desc: 'Suggest refactoring', icon: 'fa-recycle', color: 'text-blue-400' },
  { cmd: '/doc', desc: 'Generate documentation', icon: 'fa-file-alt', color: 'text-purple-400' },
  { cmd: '/search', desc: 'Search codebase', icon: 'fa-search', color: 'text-cyan-400' },
  { cmd: '/run', desc: 'Run a terminal command', icon: 'fa-terminal', color: 'text-orange-400' },
];

// Enhanced Diff Block with actions
interface EnhancedDiffBlockProps {
  text: string;
  filePath?: string;
  onApply?: (diffText: string, filePath: string) => Promise<void>;
  onReject?: () => void;
}

const EnhancedDiffBlock: React.FC<EnhancedDiffBlockProps> = ({ text, filePath, onApply, onReject }) => {
  const [applying, setApplying] = React.useState(false);
  const [applied, setApplied] = React.useState(false);
  const [rejected, setRejected] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const lines = text.replace(/\r\n/g, '\n').split('\n');

  const renderLine = (ln: string, i: number) => {
    let cls = 'bg-[#1e1e1e] text-[#d4d4d4]';
    let prefix = ' ';
    if (ln.startsWith('@@')) {
      cls = 'bg-[#264f78] text-[#569cd6]';
      prefix = '';
    } else if (ln.startsWith('+++') || ln.startsWith('---')) {
      cls = 'bg-[#1e1e1e] text-[#808080]';
      prefix = '';
    } else if (ln.startsWith('+')) {
      cls = 'bg-[#1d3d1d] text-[#4ec9b0]';
      prefix = '+';
    } else if (ln.startsWith('-')) {
      cls = 'bg-[#3d1d1d] text-[#f14c4c]';
      prefix = '-';
    }
    return (
      <div key={i} className={`text-xs font-mono px-3 py-0.5 ${cls} flex`}>
        <span className="w-4 text-[#606060] mr-2 select-none">{prefix}</span>
        <span className="flex-1">{ln.slice(prefix === ' ' ? 0 : 1) || '\u00A0'}</span>
      </div>
    );
  };

  const handleApply = async () => {
    if (!onApply || !filePath) return;
    setApplying(true);
    setError(null);
    try {
      await onApply(text, filePath);
      setApplied(true);
    } catch (e: any) {
      setError(e?.message || 'Failed to apply');
    } finally {
      setApplying(false);
    }
  };

  const handleReject = () => {
    setRejected(true);
    onReject?.();
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(text);
  };

  if (rejected) {
    return (
      <div className="text-xs text-gray-500 italic py-2">
        <i className="fas fa-times-circle mr-1"></i> Change rejected
      </div>
    );
  }

  return (
    <div className={`border rounded-lg overflow-hidden ${applied ? 'border-green-500/50' : 'border-[#3c3c3c]'}`}>
      {/* Header with file path */}
      <div className="flex items-center justify-between px-3 py-1.5 bg-[#252526] border-b border-[#3c3c3c]">
        <div className="flex items-center gap-2 text-xs">
          <i className="fas fa-file-code text-[#007acc]"></i>
          <span className="text-[#cccccc] font-mono truncate max-w-[200px]">{filePath || 'unknown'}</span>
        </div>
        <div className="flex items-center gap-1">
          {applied ? (
            <span className="text-green-400 text-xs flex items-center gap-1">
              <i className="fas fa-check-circle"></i> Applied
            </span>
          ) : (
            <>
              <button
                onClick={handleCopy}
                className="px-2 py-0.5 text-[10px] rounded bg-[#3c3c3c] hover:bg-[#4c4c4c] text-gray-300 transition-colors"
                title="Copy diff"
              >
                <i className="fas fa-copy"></i>
              </button>
              <button
                onClick={handleReject}
                className="px-2 py-0.5 text-[10px] rounded bg-[#f14c4c]/20 hover:bg-[#f14c4c]/40 text-[#f14c4c] transition-colors"
                title="Reject"
              >
                <i className="fas fa-times mr-1"></i>Reject
              </button>
              <button
                onClick={handleApply}
                disabled={applying || !onApply}
                className="px-2 py-0.5 text-[10px] rounded bg-[#4ec9b0]/20 hover:bg-[#4ec9b0]/40 text-[#4ec9b0] transition-colors disabled:opacity-50"
                title="Apply changes"
              >
                {applying ? (
                  <i className="fas fa-circle-notch fa-spin mr-1"></i>
                ) : (
                  <i className="fas fa-check mr-1"></i>
                )}
                Apply
              </button>
            </>
          )}
        </div>
      </div>

      {/* Diff content */}
      <div className="overflow-auto max-h-80 bg-[#1e1e1e]">
        {lines.map(renderLine)}
      </div>

      {/* Error message */}
      {error && (
        <div className="px-3 py-1.5 bg-[#3d1d1d] text-[#f14c4c] text-xs">
          <i className="fas fa-exclamation-triangle mr-1"></i> {error}
        </div>
      )}
    </div>
  );
};

// Keep old DiffBlock for backwards compatibility 
const DiffBlock: React.FC<{ text: string }> = ({ text }) => {
  return <EnhancedDiffBlock text={text} />;
};

// Command Block for terminal/bash code with Run button
interface CommandBlockProps {
  code: string;
  language: string;
  onRun?: (command: string) => void;
}

const CommandBlock: React.FC<CommandBlockProps> = ({ code, language, onRun }) => {
  const [copied, setCopied] = React.useState(false);
  const [running, setRunning] = React.useState(false);

  const isRunnable = ['bash', 'sh', 'shell', 'zsh', 'powershell', 'cmd', 'terminal'].includes(language.toLowerCase());

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleRun = async () => {
    if (!onRun) return;
    setRunning(true);
    try {
      onRun(code.trim());
    } finally {
      setTimeout(() => setRunning(false), 1000);
    }
  };

  return (
    <div className="border border-[#3c3c3c] rounded-lg overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-1.5 bg-[#252526] border-b border-[#3c3c3c]">
        <div className="flex items-center gap-2 text-xs">
          <i className={`fas ${isRunnable ? 'fa-terminal' : 'fa-code'} text-[#569cd6]`}></i>
          <span className="text-[#808080] font-mono">{language || 'code'}</span>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={handleCopy}
            className="px-2 py-0.5 text-[10px] rounded bg-[#3c3c3c] hover:bg-[#4c4c4c] text-gray-300 transition-colors"
            title="Copy code"
          >
            {copied ? <i className="fas fa-check text-green-400"></i> : <i className="fas fa-copy"></i>}
          </button>
          {isRunnable && onRun && (
            <button
              onClick={handleRun}
              disabled={running}
              className="px-2 py-0.5 text-[10px] rounded bg-[#4ec9b0]/20 hover:bg-[#4ec9b0]/40 text-[#4ec9b0] transition-colors disabled:opacity-50 flex items-center gap-1"
              title="Run in terminal"
            >
              {running ? (
                <i className="fas fa-circle-notch fa-spin"></i>
              ) : (
                <i className="fas fa-play"></i>
              )}
              Run
            </button>
          )}
        </div>
      </div>

      {/* Code content */}
      <div className="overflow-auto max-h-80 bg-[#1e1e1e] p-3">
        <pre className="text-xs font-mono text-[#d4d4d4] whitespace-pre-wrap break-words">
          {code}
        </pre>
      </div>
    </div>
  );
};

function renderMessageContent(
  content: string,
  fallbackPath?: string,
  onApply?: (diffText: string, filePath: string) => Promise<void>,
  onRunCommand?: (command: string) => void,
): JSX.Element {
  // Handle all code blocks - diffs get special treatment
  const codeBlockRe = /```(\w+)?\s*([\s\S]*?)```/g;
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
    const oldMatch = norm.match(/^(?:-|\-)(.*)$/m);
    const newMatch = norm.match(/^(?:\+|\+)(.*)$/m);
    let oldLine = oldMatch ? (oldMatch[1] || '').trim() : '';
    let newLine = newMatch ? (newMatch[1] || '').trim() : '';
    if (!path && fallbackPath) path = sanitizePath(fallbackPath);
    return { path: sanitizePath(path), oldLine, newLine };
  };
  while ((m = codeBlockRe.exec(content)) !== null) {
    const pre = content.slice(last, m.index);
    if (pre.trim()) {
      // Use ReactMarkdown for text content to render markdown properly
      parts.push(
        <div key={`t-${last}`} className="prose prose-invert prose-sm max-w-none">
          <ReactMarkdown>{pre}</ReactMarkdown>
        </div>
      );
    }

    const language = (m[1] || '').toLowerCase();
    const code = m[2];
    const blockKey = `c-${m.index}`;

    // Check if content looks like a diff (regardless of language tag)
    const looksLikeDiff = language === 'diff' ||
      /(^---\s|^\+\+\+\s|^@@\s)/m.test(code) &&
      (/^\+[^+]/m.test(code) || /^-[^-]/m.test(code));

    if (looksLikeDiff) {
      // Diff blocks use EnhancedDiffBlock
      const info = extractDiffInfo(code);
      parts.push(
        <EnhancedDiffBlock
          key={blockKey}
          text={code}
          filePath={info.path || fallbackPath}
          onApply={onApply}
        />
      );
    } else {
      // Other code blocks use CommandBlock (with Run button for shell commands)
      parts.push(
        <CommandBlock
          key={blockKey}
          language={language || 'code'}
          code={code}
          onRun={onRunCommand}
        />
      );
    }
    last = codeBlockRe.lastIndex;
  }
  const tail = content.slice(last);
  if (parts.length === 0) {
    const looksLikeUnified = /(---\s|\+\+\+\s|^@@\s)/m.test(content) && /^(\+|-)/m.test(content);
    if (looksLikeUnified) {
      const info = extractDiffInfo(content);
      return (
        <EnhancedDiffBlock
          text={content}
          filePath={info.path || fallbackPath}
          onApply={onApply}
        />
      );
    }
  }
  if (tail.trim()) {
    // Use ReactMarkdown for trailing text too
    parts.push(
      <div key={`t-end`} className="prose prose-invert prose-sm max-w-none">
        <ReactMarkdown>{tail}</ReactMarkdown>
      </div>
    );
  }
  if (parts.length === 0) {
    // Plain text without code blocks - render with markdown
    return (
      <div className="prose prose-invert prose-sm max-w-none">
        <ReactMarkdown>{content}</ReactMarkdown>
      </div>
    );
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

  // Slash command autocomplete state
  const [showCommandPalette, setShowCommandPalette] = useState(false);
  const [selectedCommandIndex, setSelectedCommandIndex] = useState(0);
  const filteredCommands = input.startsWith('/')
    ? SLASH_COMMANDS.filter(c => c.cmd.toLowerCase().startsWith(input.toLowerCase().split(' ')[0]))
    : [];

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

  // Self-correction loop: listen for terminal errors and auto-request fix
  const retryCountRef = useRef<number>(0);
  const MAX_RETRIES = 3;

  useEffect(() => {
    const handleTerminalError = (e: CustomEvent<{ error: string; command: string }>) => {
      const { error, command } = e.detail;

      // Prevent infinite loops
      if (retryCountRef.current >= MAX_RETRIES) {
        setMessages((prev) => [...prev, {
          role: 'system',
          content: `⚠️ Auto-fix limit reached (${MAX_RETRIES} attempts). Please review the error manually.`
        }]);
        retryCountRef.current = 0;
        return;
      }

      retryCountRef.current++;

      // Send error to AI for fix suggestion
      const fixRequest = `/fix The following command failed:\n\`${command}\`\n\nError output:\n\`\`\`\n${error}\n\`\`\`\n\nPlease analyze the error and suggest a fix.`;

      setMessages((prev) => [...prev, {
        role: 'system',
        content: `🔄 Auto-fix attempt ${retryCountRef.current}/${MAX_RETRIES}: Detected error in terminal output`
      }]);

      // Send the fix request via WebSocket
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'user_message', text: fixRequest }));
        setMessages((prev) => [...prev, { role: 'user', content: fixRequest }]);
      }
    };

    window.addEventListener('sb:terminal-error', handleTerminalError as unknown as EventListener);
    return () => window.removeEventListener('sb:terminal-error', handleTerminalError as unknown as EventListener);
  }, []);

  // Reset retry count when user sends a message manually
  useEffect(() => {
    if (input === '') {
      // Don't reset on empty - this fires after each send
    }
  }, [input]);

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

  // Apply diff to a file - reads current content, applies changes, writes back
  const applyDiff = useCallback(async (diffText: string, filePath: string): Promise<void> => {
    if (!contextRoot) {
      throw new Error('No context root specified');
    }

    // Prefer the currently selected file path if available
    // The diff might have a generic or incorrect path, but we know which file user asked about
    const actualPath = selectedPath || filePath;

    if (!actualPath) {
      throw new Error('No file path specified');
    }

    console.log('[ApplyDiff] Applying to:', actualPath, 'in', contextRoot);
    console.log('[ApplyDiff] Diff path was:', filePath, 'Selected path:', selectedPath);
    console.log('[ApplyDiff] Diff text preview:', diffText.slice(0, 200));

    // First, read the original file
    let originalContent = '';
    try {
      const readRes = await fetch(`/api/fs/read?root=${encodeURIComponent(contextRoot)}&path=${encodeURIComponent(actualPath)}`);
      const readData = await readRes.json();
      console.log('[ApplyDiff] Read response:', readData);
      if (readData.error === 'file_not_found') {
        // New file - no original content
        originalContent = '';
        console.log('[ApplyDiff] File not found, treating as new file');
      } else if (readData.content !== undefined) {
        originalContent = readData.content;
        console.log('[ApplyDiff] Read', originalContent.length, 'chars from original file');
      }
    } catch (e) {
      console.warn('[ApplyDiff] Could not read original file, treating as new:', e);
      originalContent = '';
    }

    // Parse the diff and apply changes
    const diffLines = diffText.replace(/\r\n/g, '\n').split('\n');
    let newContent: string;

    // Check if this looks like a unified diff with hunk headers
    const hasHunkHeaders = diffLines.some(l => l.startsWith('@@'));

    if (hasHunkHeaders && originalContent) {
      // Apply as a proper patch
      const originalLines = originalContent.split('\n');
      const resultLines = [...originalLines];
      let offset = 0; // Track line number shift due to insertions/deletions

      for (let i = 0; i < diffLines.length; i++) {
        const line = diffLines[i];

        // Parse hunk header: @@ -start,count +start,count @@
        const hunkMatch = line.match(/^@@\s*-(\d+)(?:,\d+)?\s*\+(\d+)(?:,\d+)?\s*@@/);
        if (hunkMatch) {
          const oldStart = parseInt(hunkMatch[1], 10) - 1; // 0-indexed
          let currentLine = oldStart + offset;

          // Process lines in this hunk
          for (let j = i + 1; j < diffLines.length; j++) {
            const hunkLine = diffLines[j];

            // Stop at next hunk or end of diff
            if (hunkLine.startsWith('@@') || hunkLine.startsWith('diff ') ||
              hunkLine.startsWith('---') || hunkLine.startsWith('+++')) {
              i = j - 1;
              break;
            }

            if (hunkLine.startsWith('-')) {
              // Delete line
              if (currentLine < resultLines.length) {
                resultLines.splice(currentLine, 1);
                offset--;
              }
            } else if (hunkLine.startsWith('+')) {
              // Insert line
              const content = hunkLine.slice(1);
              resultLines.splice(currentLine, 0, content);
              currentLine++;
              offset++;
            } else if (hunkLine.startsWith(' ') || hunkLine === '') {
              // Context line - just move forward
              currentLine++;
            }

            if (j === diffLines.length - 1) {
              i = j;
              break;
            }
          }
        }
      }

      newContent = resultLines.join('\n');
    } else {
      // Simple diff or plain new content
      // Check if there are any diff markers at all
      const hasDiffMarkers = diffLines.some(l =>
        l.startsWith('+') || l.startsWith('-') || l.startsWith(' ')
      );

      if (hasDiffMarkers) {
        // Extract lines from diff format
        const addedLines: string[] = [];
        for (const line of diffLines) {
          // Skip diff headers
          if (line.startsWith('---') || line.startsWith('+++') ||
            line.startsWith('@@') || line.startsWith('diff ')) {
            continue;
          }
          // Collect added lines
          if (line.startsWith('+')) {
            addedLines.push(line.slice(1));
          } else if (!line.startsWith('-')) {
            // Context line (starts with space) or unchanged line
            addedLines.push(line.startsWith(' ') ? line.slice(1) : line);
          }
        }
        newContent = addedLines.join('\n');
      } else {
        // No diff markers - treat entire content as new file content
        console.log('[ApplyDiff] No diff markers found, using entire content as new file');
        newContent = diffText;
      }
    }

    // Safety check: don't write empty content unless original was also empty
    if (!newContent.trim() && originalContent.trim()) {
      console.error('[ApplyDiff] Would create empty file from non-empty original - aborting');
      throw new Error('Diff parsing resulted in empty content. This would delete your file. Please review the diff manually.');
    }

    console.log('[ApplyDiff] New content length:', newContent.length);

    // Write the new content to the file
    const res = await fetch('/api/fs/write', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        root: contextRoot,
        path: actualPath,
        content: newContent
      })
    });

    if (!res.ok) {
      const error = await res.json().catch(() => ({}));
      throw new Error(error?.detail || error?.message || `Write failed: ${res.status}`);
    }

    console.log('[ApplyDiff] Write successful to:', actualPath);

    // Success feedback
    showToast(`Applied changes to ${actualPath.split('/').pop()}`);

    // Dispatch event to refresh editor if it has the file open
    window.dispatchEvent(new CustomEvent('sb:file-updated', {
      detail: { path: actualPath, root: contextRoot }
    }));
  }, [contextRoot, selectedPath]);

  // Run a command in the terminal
  const runCommand = useCallback((command: string) => {
    // Dispatch event for terminal to pick up
    window.dispatchEvent(new CustomEvent('sb:run-command', {
      detail: { command, cwd: contextRoot }
    }));
    showToast(`Running: ${command.slice(0, 30)}${command.length > 30 ? '...' : ''}`);

    // Also send as a system message to the chat for context
    setMessages((prev) => [...prev, {
      role: 'system',
      content: `🖥️ Running command: \`${command}\``
    }]);
  }, [contextRoot]);

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
                  {renderMessageContent(m.content, activeDisplayPath, applyDiff, runCommand)}
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

              {/* Command Palette Dropdown */}
              {input.startsWith('/') && filteredCommands.length > 0 && (
                <div className="absolute bottom-full left-0 right-0 mb-2 bg-[#252526] border border-[#3c3c3c] rounded-lg shadow-xl overflow-hidden z-50">
                  <div className="text-[10px] text-gray-500 px-3 py-1.5 border-b border-[#3c3c3c] uppercase tracking-wider">Commands</div>
                  {filteredCommands.map((cmd, idx) => (
                    <button
                      key={cmd.cmd}
                      onClick={() => {
                        setInput(cmd.cmd + ' ');
                        setSelectedCommandIndex(0);
                        inputRef.current?.focus();
                      }}
                      className={`w-full text-left px-3 py-2 flex items-center gap-3 transition-colors ${idx === selectedCommandIndex
                        ? 'bg-[#37373d] text-white'
                        : 'text-gray-300 hover:bg-[#2a2d2e]'
                        }`}
                    >
                      <i className={`fas ${cmd.icon} ${cmd.color} text-sm w-4`}></i>
                      <div className="flex-1">
                        <span className="font-medium text-sm">{cmd.cmd}</span>
                        <span className="text-gray-500 text-xs ml-2">{cmd.desc}</span>
                      </div>
                      {idx === selectedCommandIndex && (
                        <span className="text-[10px] text-gray-500 bg-[#3c3c3c] px-1.5 py-0.5 rounded">Tab</span>
                      )}
                    </button>
                  ))}
                </div>
              )}

              <div className="flex items-end gap-2 p-1.5">
                <textarea
                  value={input}
                  onChange={(e) => {
                    setInput(e.target.value);
                    // Reset command selection when input changes
                    if (e.target.value.startsWith('/')) {
                      setSelectedCommandIndex(0);
                      setShowCommandPalette(true);
                    } else {
                      setShowCommandPalette(false);
                    }
                  }}
                  onKeyDown={(e) => {
                    // Handle command palette navigation
                    if (input.startsWith('/') && filteredCommands.length > 0) {
                      if (e.key === 'ArrowDown') {
                        e.preventDefault();
                        setSelectedCommandIndex(prev => Math.min(prev + 1, filteredCommands.length - 1));
                        return;
                      }
                      if (e.key === 'ArrowUp') {
                        e.preventDefault();
                        setSelectedCommandIndex(prev => Math.max(prev - 1, 0));
                        return;
                      }
                      if (e.key === 'Tab' || (e.key === 'Enter' && !e.shiftKey && !input.includes(' '))) {
                        e.preventDefault();
                        const selected = filteredCommands[selectedCommandIndex];
                        if (selected) {
                          setInput(selected.cmd + ' ');
                          setSelectedCommandIndex(0);
                        }
                        return;
                      }
                    }
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      onSend();
                    }
                  }}
                  ref={inputRef as any}
                  className="flex-1 bg-transparent border-none text-white placeholder-gray-500 text-sm focus:ring-0 max-h-32 min-h-[40px] py-2 px-2 resize-none custom-scrollbar"
                  placeholder="Ask AI or type / for commands..."
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
