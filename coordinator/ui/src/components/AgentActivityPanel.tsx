import React, { useEffect, useMemo, useRef, useState } from 'react';

interface AgentEvent {
  timestamp: string;
  agent: string;
  stage: string;
  message: string;
  level?: 'info' | 'success' | 'warning' | 'error' | string;
  metadata?: Record<string, any>;
}

interface AgentActivityPanelProps {
  buildId: string;
}

const levelColor = (lvl?: string) => {
  const v = (lvl || 'info').toLowerCase();
  if (v === 'error') return 'text-red-600';
  if (v === 'warning') return 'text-yellow-700';
  if (v === 'success') return 'text-green-700';
  return 'text-gray-800';
};

export const AgentActivityPanel: React.FC<AgentActivityPanelProps> = ({ buildId }) => {
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [filterAgent, setFilterAgent] = useState<string>('all');
  const [filterLevel, setFilterLevel] = useState<string>('all');
  const wsRef = useRef<WebSocket | null>(null);

  const filtered = useMemo(() => {
    return events.filter((e) => {
      const byAgent = filterAgent === 'all' || e.agent === filterAgent;
      const byLevel = filterLevel === 'all' || (e.level || 'info').toLowerCase() === filterLevel;
      return byAgent && byLevel;
    });
  }, [events, filterAgent, filterLevel]);

  useEffect(() => {
    let cancelled = false;

    const loadBacklog = async () => {
      try {
        const res = await fetch(`/api/build/${buildId}/activity?limit=200`);
        const data = await res.json();
        if (!cancelled && Array.isArray(data?.events)) {
          setEvents(data.events);
        }
      } catch {}
    };

    const connectWS = () => {
      try {
        const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
        const ws = new WebSocket(`${proto}://${window.location.host}/ws/agent-activity/${buildId}`);
        wsRef.current = ws;

        ws.onmessage = (ev) => {
          try {
            const evt = JSON.parse(ev.data);
            if (evt && evt.timestamp) {
              setEvents((prev) => [...prev, evt].slice(-500));
            }
          } catch {}
        };

        ws.onclose = () => {
          wsRef.current = null;
        };
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

  const agents = useMemo(() => {
    const set = new Set<string>(events.map((e) => e.agent));
    return ['all', ...Array.from(set)];
  }, [events]);

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-bold text-gray-900">Agent Activity</h3>
        <div className="flex items-center space-x-2 text-sm">
          <label className="flex items-center space-x-1">
            <span className="text-gray-600">Agent</span>
            <select
              aria-label="Filter by agent"
              value={filterAgent}
              onChange={(e) => setFilterAgent(e.target.value)}
              className="border border-gray-300 rounded px-2 py-1"
            >
              {agents.map((a) => (
                <option key={a} value={a}>{a}</option>
              ))}
            </select>
          </label>
          <label className="flex items-center space-x-1">
            <span className="text-gray-600">Level</span>
            <select
              aria-label="Filter by level"
              value={filterLevel}
              onChange={(e) => setFilterLevel(e.target.value)}
              className="border border-gray-300 rounded px-2 py-1"
            >
              {['all','info','success','warning','error'].map((l) => (
                <option key={l} value={l}>{l}</option>
              ))}
            </select>
          </label>
        </div>
      </div>

      <div className="max-h-72 overflow-y-auto space-y-2">
        {filtered.length === 0 && (
          <div className="text-sm text-gray-500">No activity yet.</div>
        )}
        {filtered.map((evt, idx) => (
          <div key={`${evt.timestamp}-${idx}`} className="flex items-start justify-between">
            <div className="text-sm">
              <div className="text-gray-500 text-xs">{new Date(evt.timestamp).toLocaleTimeString()}</div>
              <div className="font-medium text-gray-800">{evt.agent} · {evt.stage}</div>
              <div className={levelColor(evt.level)}>{evt.message}</div>
            </div>
            {evt.metadata && Object.keys(evt.metadata).length > 0 && (
              <div className="text-xs text-gray-500 ml-4">
                {Object.entries(evt.metadata).map(([k,v]) => (
                  <div key={k}><span className="text-gray-400">{k}:</span> {String(v)}</div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
