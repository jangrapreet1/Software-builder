import React, { useEffect, useMemo, useRef, useState } from 'react';

interface TerminalPanelProps {
  cwd: string;
}

export const TerminalPanel: React.FC<TerminalPanelProps> = ({ cwd }) => {
  const [connected, setConnected] = useState(false);
  const [output, setOutput] = useState<string>('');
  const [input, setInput] = useState<string>('');
  const wsRef = useRef<WebSocket | null>(null);
  const termId = useMemo(() => `term-${Date.now()}`, []);

  useEffect(() => {
    try {
      const url = `/api/term/${encodeURIComponent(termId)}?cwd=${encodeURIComponent(cwd)}`.replace('http', 'ws');
      const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
      const host = window.location.host;
      const full = `${protocol}://${host}${url}`;
      const ws = new WebSocket(full);
      wsRef.current = ws;
      ws.onopen = () => setConnected(true);
      ws.onmessage = (ev) => setOutput((prev) => prev + ev.data);
      ws.onerror = () => setConnected(false);
      ws.onclose = () => setConnected(false);
      return () => { try { ws.close(); } catch {} };
    } catch {
      setConnected(false);
    }
  }, [cwd, termId]);

  const sendLine = () => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    wsRef.current.send(input);
    setInput('');
  };

  const close = () => {
    try { wsRef.current?.send('__exit__'); wsRef.current?.close(); } catch {}
  };

  return (
    <div className="border rounded-lg bg-white overflow-hidden">
      <div className="flex items-center justify-between px-3 py-2 border-b bg-gray-50">
        <div className="text-sm font-semibold">Terminal</div>
        <div className="text-xs">
          {connected ? <span className="text-green-600">Connected</span> : <span className="text-gray-500">Disconnected</span>}
        </div>
      </div>
      <pre className="p-3 text-sm whitespace-pre-wrap h-60 overflow-auto bg-black text-green-200">{output || 'Connecting...'}</pre>
      <div className="flex items-center gap-2 p-2 border-t bg-gray-50">
        <input
          type="text"
          className="flex-1 text-sm border rounded px-2 py-1"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type command and press Run"
        />
        <button onClick={sendLine} className="px-3 py-1 text-sm bg-blue-600 text-white rounded">Run</button>
        <button onClick={close} className="px-3 py-1 text-sm bg-gray-200 rounded">Close</button>
      </div>
    </div>
  );
};
