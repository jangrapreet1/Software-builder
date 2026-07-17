import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { apiClient } from '../utils/apiClient';

interface ChangesPanelProps {
  sessionId: string;
  contextRoot?: string;
  selectedPath?: string;
}

interface EditRow {
  id: string;
  path: string;
  old: string;
  new: string;
}

interface DryRunPreview {
  path: string;
  will_change: boolean;
  before_len: number;
  after_len: number;
}

const joinPath = (base?: string, rel?: string) => {
  const b = (base || '').replace(/\\/g, '/').replace(/^\.+\//, '');
  const r = (rel || '').replace(/\\/g, '/').replace(/^\.+\//, '');
  if (!b) return r;
  if (!r) return b;
  return `${b.replace(/\/$/, '')}/${r.replace(/^\//, '')}`;
};

export const ChangesPanel: React.FC<ChangesPanelProps> = ({ sessionId, contextRoot, selectedPath }) => {
  const suggestedPath = useMemo(() => joinPath(contextRoot, selectedPath), [contextRoot, selectedPath]);
  const [edits, setEdits] = useState<EditRow[]>([]);
  const [previews, setPreviews] = useState<DryRunPreview[] | null>(null);
  const [loading, setLoading] = useState<'idle' | 'dry' | 'apply'>('idle');
  const [msg, setMsg] = useState<string>('');

  useEffect(() => {
    if (!edits.length && suggestedPath) {
      setEdits([{ id: crypto.randomUUID(), path: suggestedPath, old: '', new: '' }]);
    }
  }, [suggestedPath]);

  const setRow = (id: string, patch: Partial<EditRow>) => {
    setEdits((prev) => prev.map((e) => (e.id === id ? { ...e, ...patch } : e)));
  };

  const addRow = () => {
    setEdits((prev) => [...prev, { id: crypto.randomUUID(), path: suggestedPath || '', old: '', new: '' }]);
  };

  const removeRow = (id: string) => {
    setEdits((prev) => prev.filter((e) => e.id !== id));
  };

  const grantWrite = useCallback(async () => {
    if (!sessionId) return;
    try {
      await apiClient.post('/api/session/permissions', {
        session_id: sessionId,
        actions: ['allow_write'],
        commands: [],
        duration: 3600,
      }, { suppressErrorNotification: true });
      setMsg('Granted allow_write permission for this session.');
    } catch (e: any) {
      setMsg(`Grant permission failed: ${e?.message || e}`);
    }
  }, [sessionId]);

  const dryRun = useCallback(async () => {
    setMsg('');
    setPreviews(null);
    if (!sessionId || !edits.length) return;
    setLoading('dry');
    try {
      const body = { edits: edits.map((e) => ({ path: e.path, old: e.old, new: e.new })) };
      const res = await apiClient.post<{ previews: DryRunPreview[] }>(`/api/chat/${sessionId}/patch/dry-run`, body);
      setPreviews(res.previews || []);
      setMsg(`Dry-run completed for ${res.previews?.length ?? 0} file(s).`);
    } catch (e: any) {
      setMsg(e?.message || 'Dry-run failed');
    } finally {
      setLoading('idle');
    }
  }, [sessionId, edits]);

  // Listen for external requests to add a change (from Chat diffs)
  useEffect(() => {
    const handler = (ev: Event) => {
      const detail = (ev as CustomEvent<any>).detail || {};
      const path = String(detail.path || '').trim();
      const oldText = String(detail.old || '');
      const newText = String(detail.new || '');
      if (!path) return;
      setEdits((prev) => [...prev, { id: crypto.randomUUID(), path, old: oldText, new: newText }]);
      setMsg(`Added change for ${path}`);
      try { console.debug('[ChangesPanel] received sb:add-change', detail); } catch {}
    };
    window.addEventListener('sb:add-change' as any, handler as any);
    document.addEventListener('sb:add-change' as any, handler as any);
    return () => {
      window.removeEventListener('sb:add-change' as any, handler as any);
      document.removeEventListener('sb:add-change' as any, handler as any);
    };
  }, []);

  // Direct callable for ChatPanel
  useEffect(() => {
    const g: any = window as any;
    g.__sbAddChangeDirect = (detail: any) => {
      const path = String(detail?.path || '').trim();
      const oldText = String(detail?.old || '');
      const newText = String(detail?.new || '');
      if (!path) return false;
      setEdits((prev) => [...prev, { id: crypto.randomUUID(), path, old: oldText, new: newText }]);
      setMsg(`Added change for ${path}`);
      try { console.debug('[ChangesPanel] direct add change', detail); } catch {}
      return true;
    };
    return () => { try { delete (window as any).__sbAddChangeDirect; } catch {} };
  }, []);

  // Fallback: drain global queue if events were missed
  useEffect(() => {
    const flush = () => {
      try {
        const g: any = window as any;
        const q: any[] = Array.isArray(g.__sbAddChangeQueue) ? g.__sbAddChangeQueue : [];
        if (!q.length) return;
        g.__sbAddChangeQueue = [];
        for (const detail of q) {
          const path = String(detail?.path || '').trim();
          const oldText = String(detail?.old || '');
          const newText = String(detail?.new || '');
          if (!path) continue;
          setEdits((prev) => [...prev, { id: crypto.randomUUID(), path, old: oldText, new: newText }]);
          setMsg(`Added change for ${path}`);
          try { console.debug('[ChangesPanel] flushed queued add-change', detail); } catch {}
        }
      } catch {}
    };
    const id = window.setInterval(flush, 700);
    flush();
    return () => window.clearInterval(id);
  }, []);

  const apply = useCallback(async () => {
    setMsg('');
    if (!sessionId || !edits.length) return;
    setLoading('apply');
    try {
      const body = { edits: edits.map((e) => ({ path: e.path, old: e.old, new: e.new })) };
      const res = await fetch(`/api/chat/${sessionId}/patch/apply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json().catch(() => ({}));
      if (res.status === 403) {
        setMsg(data?.detail || 'Permission required: allow_write');
        return;
      }
      if (!res.ok) throw new Error(data?.detail || data?.message || 'Apply failed');
      const applied = (data?.applied || []) as string[];
      setMsg(`Applied: ${applied.length} file(s).`);
    } catch (e: any) {
      setMsg(e?.message || 'Apply failed');
    } finally {
      setLoading('idle');
    }
  }, [sessionId, edits]);

  return (
    <div className="bg-white rounded border p-3">
      <div className="flex items-center justify-between mb-2">
        <div className="text-sm font-semibold text-gray-700">Changes</div>
        <div className="flex items-center gap-2">
          <button onClick={dryRun} disabled={!sessionId || !edits.length || loading !== 'idle'} className="text-xs px-2 py-1 rounded bg-gray-800 text-white disabled:opacity-50">Dry‑run</button>
          <button onClick={apply} disabled={!sessionId || !edits.length || loading !== 'idle'} className="text-xs px-2 py-1 rounded bg-blue-600 text-white disabled:opacity-50">Apply</button>
          <button onClick={grantWrite} className="text-xs px-2 py-1 rounded bg-amber-600 text-white">Grant write</button>
        </div>
      </div>

      <div className="space-y-2">
        {edits.map((e) => (
          <div key={e.id} className="border rounded p-2">
            <div className="flex items-center gap-2 mb-2">
              <input
                className="flex-1 text-xs border rounded px-2 py-1"
                placeholder="path (repo-relative)"
                value={e.path}
                onChange={(ev)=>setRow(e.id, { path: ev.target.value })}
              />
              <button onClick={()=>removeRow(e.id)} className="text-xs px-2 py-1 rounded bg-gray-100 hover:bg-gray-200">Remove</button>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <textarea
                className="text-xs border rounded p-2 h-20"
                placeholder="old text"
                value={e.old}
                onChange={(ev)=>setRow(e.id, { old: ev.target.value })}
              />
              <textarea
                className="text-xs border rounded p-2 h-20"
                placeholder="new text"
                value={e.new}
                onChange={(ev)=>setRow(e.id, { new: ev.target.value })}
              />
            </div>
          </div>
        ))}
        <button onClick={addRow} className="text-xs px-2 py-1 rounded bg-gray-100 hover:bg-gray-200">Add edit</button>
      </div>

      {previews && (
        <div className="mt-3 border-t pt-2">
          <div className="text-xs text-gray-600 font-semibold mb-1">Preview</div>
          <div className="space-y-1">
            {previews.map((p, idx) => (
              <div key={idx} className={`text-xs px-2 py-1 rounded border ${p.will_change ? 'bg-green-50 border-green-200 text-green-800' : 'bg-gray-50 border-gray-200 text-gray-700'}`}>
                <div className="font-mono">{p.path}</div>
                <div>Will change: {String(p.will_change)}</div>
                <div>Before: {p.before_len} chars → After: {p.after_len} chars</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {msg && (
        <div className="mt-2 text-xs text-gray-700">{msg}</div>
      )}
    </div>
  );
};

export default ChangesPanel;
