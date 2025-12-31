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
      return () => { try { ws.close(); } catch { } };
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
    try { wsRef.current?.send('__exit__'); wsRef.current?.close(); } catch { }
  };

  return (
    <div className="glass-panel overflow-hidden flex flex-col h-full rounded-xl border border-white/10">
      <div className="flex items-center justify-between px-4 py-2 border-b border-white/5 bg-black/20">
        <div className="text-xs font-bold text-gray-400 uppercase tracking-wider flex items-center">
          <i className="fas fa-terminal mr-2 text-accent"></i>
          Terminal
        </div>
        <div className="text-[10px] font-mono">
          {connected ? <span className="text-emerald-400 flex items-center"><span className="w-1.5 h-1.5 rounded-full bg-emerald-400 mr-1.5 animate-pulse"></span>Connected</span> : <span className="text-red-400 flex items-center"><span className="w-1.5 h-1.5 rounded-full bg-red-400 mr-1.5"></span>Disconnected</span>}
        </div>
      </div>
      <pre className="flex-1 p-4 text-xs font-mono whitespace-pre-wrap overflow-auto bg-[#0c0c0e]/80 text-gray-300 custom-scrollbar leading-relaxed">
        {output || <span className="text-gray-600 italic">Initializing terminal connection...</span>}
      </pre>
      <div className="flex items-center gap-2 p-2 border-t border-white/5 bg-black/20 backdrop-blur-sm">
        <div className="flex-1 relative">
          <span className="absolute left-3 top-1/2 transform -translate-y-1/2 text-primary font-bold text-xs">$</span>
          <input
            type="text"
            className="w-full text-xs bg-black/40 border border-white/10 rounded-lg pl-6 pr-3 py-2 text-white placeholder-gray-600 focus:ring-1 focus:ring-primary/50 outline-none font-mono transition-all"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') sendLine(); }}
            placeholder="Type command..."
          />
        </div>
        <button onClick={sendLine} className="px-4 py-2 text-xs bg-primary/20 hover:bg-primary/30 text-primary hover:text-white rounded-lg font-bold border border-primary/20 transition-colors">Run</button>
        <button onClick={close} className="px-3 py-2 text-xs glass-button text-gray-400 hover:text-white rounded-lg">
          <i className="fas fa-power-off"></i>
        </button>
      </div>
    </div>
  );
};
