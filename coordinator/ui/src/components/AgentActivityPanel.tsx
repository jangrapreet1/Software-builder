import React, { useEffect, useMemo, useRef, useState } from 'react';

export interface AgentEvent {
  timestamp: string;
  agent: string;
  stage: string;
  message: string;
  level?: 'info' | 'success' | 'warning' | 'error' | string;
  metadata?: Record<string, any>;
}

interface AgentActivityPanelProps {
  buildId: string;
  compact?: boolean;
}

const getAgentBadge = (agent: string) => {
  const a = (agent || '').toLowerCase();
  if (a.includes('coordinator')) return { icon: 'fa-brain', color: 'text-indigo-400 bg-indigo-500/10 border-indigo-500/30' };
  if (a.includes('backend')) return { icon: 'fa-server', color: 'text-blue-400 bg-blue-500/10 border-blue-500/30' };
  if (a.includes('frontend')) return { icon: 'fa-palette', color: 'text-purple-400 bg-purple-500/10 border-purple-500/30' };
  if (a.includes('integration')) return { icon: 'fa-cubes', color: 'text-cyan-400 bg-cyan-500/10 border-cyan-500/30' };
  if (a.includes('validator') || a.includes('preflight')) return { icon: 'fa-shield-halved', color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30' };
  if (a.includes('resolver') || a.includes('problem')) return { icon: 'fa-wrench', color: 'text-amber-400 bg-amber-500/10 border-amber-500/30' };
  if (a.includes('dependency')) return { icon: 'fa-box-open', color: 'text-orange-400 bg-orange-500/10 border-orange-500/30' };
  return { icon: 'fa-robot', color: 'text-gray-400 bg-white/5 border-white/10' };
};

const getLevelBadge = (level?: string) => {
  const l = (level || 'info').toLowerCase();
  if (l === 'error') return 'text-red-400 bg-red-500/10 border-red-500/30';
  if (l === 'warning') return 'text-amber-400 bg-amber-500/10 border-amber-500/30';
  if (l === 'success') return 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30';
  return 'text-blue-400 bg-blue-500/10 border-blue-500/30';
};

export const AgentActivityPanel: React.FC<AgentActivityPanelProps> = ({ buildId, compact = false }) => {
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [filterAgent, setFilterAgent] = useState<string>('all');
  const [filterLevel, setFilterLevel] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const wsRef = useRef<WebSocket | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  const filtered = useMemo(() => {
    return events.filter((e) => {
      const byAgent = filterAgent === 'all' || e.agent === filterAgent;
      const byLevel = filterLevel === 'all' || (e.level || 'info').toLowerCase() === filterLevel;
      const bySearch = !searchQuery.trim() || 
        e.message.toLowerCase().includes(searchQuery.toLowerCase()) ||
        e.agent.toLowerCase().includes(searchQuery.toLowerCase()) ||
        e.stage.toLowerCase().includes(searchQuery.toLowerCase());
      return byAgent && byLevel && bySearch;
    });
  }, [events, filterAgent, filterLevel, searchQuery]);

  useEffect(() => {
    let cancelled = false;

    const loadBacklog = async () => {
      if (!buildId) return;
      try {
        const res = await fetch(`/api/build/${buildId}/activity?limit=200`);
        const data = await res.json();
        if (!cancelled && Array.isArray(data?.events)) {
          setEvents(data.events);
        }
      } catch {}
    };

    const connectWS = () => {
      if (!buildId) return;
      try {
        const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
        const ws = new WebSocket(`${proto}://${window.location.host}/ws/agent-activity/${buildId}`);
        wsRef.current = ws;

        ws.onmessage = (ev) => {
          try {
            const evt = JSON.parse(ev.data);
            if (evt && (evt.timestamp || evt.message)) {
              setEvents((prev) => [...prev, evt].slice(-500));
            }
          } catch {}
        };

        ws.onclose = () => { wsRef.current = null; };
        ws.onerror = () => {
          try { ws.close(); } catch {}
          wsRef.current = null;
        };
      } catch {}
    };

    loadBacklog().then(connectWS);

    return () => {
      cancelled = true;
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        try { wsRef.current.close(); } catch {}
      }
      wsRef.current = null;
    };
  }, [buildId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [events]);

  const agents = useMemo(() => {
    const set = new Set<string>(events.map((e) => e.agent));
    return ['all', ...Array.from(set)];
  }, [events]);

  return (
    <div className={`glass-panel rounded-2xl flex flex-col h-full overflow-hidden ${compact ? 'p-3' : 'p-6'}`}>
      {/* Header Controls */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4 pb-3 border-b border-white/5 shrink-0">
        <div className="flex items-center space-x-2">
          <div className="w-8 h-8 rounded-xl bg-indigo-500/20 text-indigo-400 flex items-center justify-center border border-indigo-500/30">
            <i className="fas fa-network-wired text-xs"></i>
          </div>
          <div>
            <h3 className="font-bold text-white text-sm">Agent Activity Stream</h3>
            <p className="text-[11px] text-gray-400">Step-by-step real-time agent execution</p>
          </div>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-2 text-xs">
          <div className="relative">
            <input
              type="text"
              placeholder="Search agent logs..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="bg-black/30 text-white placeholder-gray-500 text-xs px-3 py-1.5 pl-7 rounded-lg border border-white/10 outline-none focus:border-indigo-500/50 w-36"
            />
            <i className="fas fa-search absolute left-2.5 top-2 text-[10px] text-gray-500"></i>
          </div>

          <select
            value={filterAgent}
            onChange={(e) => setFilterAgent(e.target.value)}
            className="bg-black/40 text-gray-300 text-xs px-2.5 py-1.5 rounded-lg border border-white/10 outline-none focus:border-indigo-500/50"
          >
            {agents.map((a) => (
              <option key={a} value={a} className="bg-slate-900">{a === 'all' ? 'All Agents' : a}</option>
            ))}
          </select>

          <select
            value={filterLevel}
            onChange={(e) => setFilterLevel(e.target.value)}
            className="bg-black/40 text-gray-300 text-xs px-2.5 py-1.5 rounded-lg border border-white/10 outline-none focus:border-indigo-500/50"
          >
            <option value="all" className="bg-slate-900">All Levels</option>
            <option value="info" className="bg-slate-900">Info</option>
            <option value="success" className="bg-slate-900">Success</option>
            <option value="warning" className="bg-slate-900">Warning</option>
            <option value="error" className="bg-slate-900">Error</option>
          </select>
        </div>
      </div>

      {/* Events Timeline */}
      <div className="flex-1 overflow-y-auto space-y-2.5 custom-scrollbar pr-1">
        {filtered.length === 0 && (
          <div className="text-center py-12 text-gray-500 text-xs flex flex-col items-center gap-2">
            <i className="fas fa-stream text-2xl text-gray-600"></i>
            <span>No agent activity recorded yet for this session.</span>
          </div>
        )}

        {filtered.map((evt, idx) => {
          const agentBadge = getAgentBadge(evt.agent);
          const levelBadge = getLevelBadge(evt.level);
          const ts = evt.timestamp ? new Date(evt.timestamp).toLocaleTimeString() : '';

          return (
            <div
              key={`${evt.timestamp}-${idx}`}
              className="glass-panel p-3 rounded-xl border border-white/5 hover:border-white/15 transition-all text-xs flex items-start gap-3 animate-fade-in"
            >
              {/* Agent icon badge */}
              <div className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 border ${agentBadge.color}`}>
                <i className={`fas ${agentBadge.icon} text-xs`}></i>
              </div>

              {/* Event Content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-2 mb-1">
                  <div className="flex items-center gap-1.5 truncate">
                    <span className="font-semibold text-white truncate">{evt.agent || 'Workflow'}</span>
                    <span className="text-[10px] text-gray-500 uppercase tracking-wider font-mono">· {evt.stage}</span>
                  </div>
                  <div className="flex items-center gap-1.5 shrink-0">
                    {evt.level && (
                      <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold uppercase tracking-wider border ${levelBadge}`}>
                        {evt.level}
                      </span>
                    )}
                    {ts && <span className="text-[10px] text-gray-500 font-mono">{ts}</span>}
                  </div>
                </div>

                <div className="text-gray-300 leading-relaxed font-sans">{evt.message}</div>

                {/* Metadata details */}
                {evt.metadata && Object.keys(evt.metadata).length > 0 && (
                  <div className="mt-2 pt-1.5 border-t border-white/5 grid grid-cols-2 gap-x-4 gap-y-1 font-mono text-[10px] text-gray-400">
                    {Object.entries(evt.metadata).map(([k, v]) => (
                      <div key={k} className="truncate">
                        <span className="text-indigo-400">{k}:</span> {typeof v === 'object' ? JSON.stringify(v) : String(v)}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          );
        })}
        <div ref={bottomRef} />
      </div>
    </div>
  );
};
