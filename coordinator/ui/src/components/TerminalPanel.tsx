import React, { useEffect, useMemo, useRef, useState, useCallback } from 'react';

// Error patterns to detect in terminal output
const ERROR_PATTERNS = [
  /error:/i,
  /failed:/i,
  /exception:/i,
  /traceback/i,
  /syntaxerror/i,
  /typeerror/i,
  /referenceerror/i,
  /command not found/i,
  /permission denied/i,
  /no such file or directory/i,
  /cannot find module/i,
  /module not found/i,
  /compilation failed/i,
  /build failed/i,
];

interface TerminalPanelProps {
  cwd: string;
}

export const TerminalPanel: React.FC<TerminalPanelProps> = ({ cwd }) => {
  const [connected, setConnected] = useState(false);
  const [output, setOutput] = useState<string>('');
  const [input, setInput] = useState<string>('');
  const wsRef = useRef<WebSocket | null>(null);
  const termId = useMemo(() => `term-${Date.now()}`, []);
  const lastCommandRef = useRef<string>('');
  const errorBufferRef = useRef<string>('');

  // Check if output contains an error
  const checkForErrors = useCallback((text: string, command: string) => {
    const hasError = ERROR_PATTERNS.some(pattern => pattern.test(text));
    if (hasError) {
      // Dispatch error event for ChatPanel to handle
      console.log('[Terminal] Error detected in output');
      window.dispatchEvent(new CustomEvent('sb:terminal-error', {
        detail: {
          error: text.slice(-500), // Last 500 chars for context
          command: command
        }
      }));
    }
  }, []);

  useEffect(() => {
    try {
      const url = `/api/term/${encodeURIComponent(termId)}?cwd=${encodeURIComponent(cwd)}`.replace('http', 'ws');
      const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
      const host = window.location.host;
      const full = `${protocol}://${host}${url}`;
      const ws = new WebSocket(full);
      wsRef.current = ws;
      ws.onopen = () => setConnected(true);
      ws.onmessage = (ev) => {
        const data = ev.data;
        setOutput((prev) => prev + data);

        // Buffer output for error detection
        errorBufferRef.current += data;

        // Check for errors after a brief delay (to accumulate output)
        setTimeout(() => {
          if (errorBufferRef.current) {
            checkForErrors(errorBufferRef.current, lastCommandRef.current);
            errorBufferRef.current = '';
          }
        }, 500);
      };
      ws.onerror = () => setConnected(false);
      ws.onclose = () => setConnected(false);
      return () => { try { ws.close(); } catch { } };
    } catch {
      setConnected(false);
    }
  }, [cwd, termId, checkForErrors]);

  // Listen for external run command events (from ChatPanel)
  useEffect(() => {
    const handleRunCommand = (e: CustomEvent<{ command: string; cwd?: string }>) => {
      const { command } = e.detail;
      if (command && wsRef.current?.readyState === WebSocket.OPEN) {
        lastCommandRef.current = command; // Track for error reporting
        wsRef.current.send(command);
        setOutput((prev) => prev + `\n$ ${command}\n`);
      }
    };

    window.addEventListener('sb:run-command', handleRunCommand as EventListener);
    return () => window.removeEventListener('sb:run-command', handleRunCommand as EventListener);
  }, []);

  const sendLine = () => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    wsRef.current.send(input);
    setInput('');
  };

  const close = () => {
    try { wsRef.current?.send('__exit__'); wsRef.current?.close(); } catch { }
  };

  return (
    <div className="flex flex-col h-full bg-[#1e1e1e] overflow-hidden">
      {/* Terminal Header */}
      <div className="h-8 flex items-center justify-between px-3 border-b border-[#3c3c3c] bg-[#252526] flex-shrink-0">
        <div className="flex items-center gap-2 text-[11px] text-[#cccccc]">
          <i className="fas fa-terminal text-[#6796e6]"></i>
          <span className="font-medium">Terminal</span>
        </div>
        <div className="flex items-center gap-2">
          <span className={`text-[10px] flex items-center gap-1 ${connected ? 'text-[#4ec9b0]' : 'text-[#f14c4c]'}`}>
            <span className={`w-1.5 h-1.5 rounded-full ${connected ? 'bg-[#4ec9b0]' : 'bg-[#f14c4c]'}`}></span>
            {connected ? 'Connected' : 'Disconnected'}
          </span>
          <button onClick={close} className="w-5 h-5 flex items-center justify-center hover:bg-[#3c3c3c] rounded text-[#858585] hover:text-white">
            <i className="fas fa-times text-[10px]"></i>
          </button>
        </div>
      </div>

      {/* Terminal Output */}
      <pre className="flex-1 p-3 text-[13px] font-mono whitespace-pre-wrap overflow-auto bg-[#1e1e1e] text-[#cccccc] leading-relaxed">
        {output || <span className="text-[#5a5a5a]">Terminal ready...</span>}
      </pre>

      {/* Terminal Input */}
      <div className="flex items-center gap-2 px-3 py-2 border-t border-[#3c3c3c] bg-[#252526]">
        <span className="text-[#4ec9b0] font-mono text-[13px]">$</span>
        <input
          type="text"
          className="flex-1 text-[13px] bg-transparent border-none outline-none text-[#cccccc] placeholder-[#5a5a5a] font-mono"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') sendLine(); }}
          placeholder="Enter command..."
        />
        <button
          onClick={sendLine}
          className="px-3 py-1 text-[11px] bg-[#0e639c] hover:bg-[#1177bb] text-white rounded font-medium"
        >
          Run
        </button>
      </div>
    </div>
  );
};
