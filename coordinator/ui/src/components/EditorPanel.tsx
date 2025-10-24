import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { FileTree } from './FileTree';
import { CodeEditor } from './CodeEditor';
import { TerminalPanel } from './TerminalPanel';
import { SecretsPanel } from './SecretsPanel';

interface EditorPanelProps {
  root: string;
}

const guessLanguage = (path: string) => {
  const lower = path.toLowerCase();
  if (lower.endsWith('.ts')) return 'typescript';
  if (lower.endsWith('.tsx')) return 'typescript';
  if (lower.endsWith('.js')) return 'javascript';
  if (lower.endsWith('.jsx')) return 'javascript';
  if (lower.endsWith('.py')) return 'python';
  if (lower.endsWith('.json')) return 'json';
  if (lower.endsWith('.yml') || lower.endsWith('.yaml')) return 'yaml';
  if (lower.endsWith('.md')) return 'markdown';
  if (lower.endsWith('.html')) return 'html';
  if (lower.endsWith('.css')) return 'css';
  return 'plaintext';
};

export const EditorPanel: React.FC<EditorPanelProps> = ({ root }) => {
  const [selected, setSelected] = useState<string>('');
  const [content, setContent] = useState<string>('');
  const [dirty, setDirty] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const language = useMemo(() => guessLanguage(selected), [selected]);

  const loadFile = useCallback(async (relPath: string) => {
    setError(null);
    setLoading(true);
    try {
      const res = await fetch(`/api/fs/read?root=${encodeURIComponent(root)}&path=${encodeURIComponent(relPath)}`);
      if (!res.ok) {
        throw new Error(`Failed to read file: ${res.status}`);
      }
      const data = await res.json();
      setSelected(relPath);
      setContent(data.content || '');
      setDirty(false);
    } catch (e: any) {
      setError(e?.message ?? 'Failed to read file');
    } finally {
      setLoading(false);
    }
  }, [root]);

  const handleSave = useCallback(async () => {
    if (!selected) return;
    setError(null);
    setLoading(true);
    try {
      const res = await fetch('/api/fs/write', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ root, path: selected, content })
      });
      if (!res.ok) throw new Error(`Save failed: ${res.status}`);
      setDirty(false);
    } catch (e: any) {
      setError(e?.message ?? 'Failed to save file');
    } finally {
      setLoading(false);
    }
  }, [root, selected, content]);

  const handleDownload = useCallback(() => {
    try {
      const url = `/api/app/download?app_path=${encodeURIComponent(root)}`;
      window.open(url, '_blank');
    } catch (e) {
      // no-op
    }
  }, [root]);

  // Git helpers
  const [commitMessage, setCommitMessage] = useState('update via editor');
  const [gitStatus, setGitStatus] = useState<string>('');

  const refreshGitStatus = useCallback(async () => {
    try {
      const res = await fetch(`/api/git/status?repo_path=${encodeURIComponent(root)}`);
      const data = await res.json();
      setGitStatus((data.stdout || data.stderr || '').trim());
    } catch (e: any) {
      setGitStatus(e?.message ?? 'git status failed');
    }
  }, [root]);

  const ensureRepo = useCallback(async () => {
    await fetch('/api/git/init', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ repo_path: root })
    });
    await refreshGitStatus();
  }, [root, refreshGitStatus]);

  const commit = useCallback(async () => {
    await fetch('/api/git/commit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ repo_path: root, message: commitMessage, add_all: true })
    });
    await refreshGitStatus();
  }, [root, commitMessage, refreshGitStatus]);

  useEffect(() => { refreshGitStatus(); }, [refreshGitStatus]);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <div className="lg:col-span-1">
        <FileTree root={root} onSelectFile={loadFile} />
        <div className="mt-3 p-2 border rounded bg-white">
          <div className="text-xs font-semibold mb-1">Git</div>
          <pre className="text-xs whitespace-pre-wrap bg-gray-50 p-2 rounded border max-h-40 overflow-auto">{gitStatus}</pre>
          <div className="flex items-center gap-2 mt-2">
            <button onClick={ensureRepo} className="text-xs px-2 py-1 bg-gray-100 hover:bg-gray-200 rounded">Init</button>
            <input
              className="flex-1 text-xs border rounded px-2 py-1"
              value={commitMessage}
              onChange={(e)=>setCommitMessage(e.target.value)}
              placeholder="Commit message"
              title="Commit message"
              aria-label="Commit message"
            />
            <button onClick={commit} className="text-xs px-2 py-1 bg-blue-600 text-white rounded">Commit</button>
          </div>
        </div>
        <SecretsPanel root={root} />
      </div>
      <div className="lg:col-span-2 space-y-2">
        <div className="flex items-center justify-between">
          <div className="text-sm text-gray-600 truncate" title={selected}>{selected || 'Select a file'}</div>
          <div className="flex items-center gap-2">
            {dirty && <span className="text-xs text-amber-600">Unsaved</span>}
            <button onClick={handleDownload} className="px-3 py-1 rounded bg-gray-700 text-white">Download Code</button>
            <button disabled={!dirty || !selected || loading} onClick={handleSave} className="px-3 py-1 rounded bg-blue-600 text-white disabled:opacity-50">Save</button>
          </div>
        </div>
        <div className="min-h-[400px]">
          {selected ? (
            <CodeEditor language={language} value={content} onChange={(v)=>{ setContent(v); setDirty(true); }} />
          ) : (
            <div className="h-[60vh] border rounded bg-white flex items-center justify-center text-gray-500 text-sm">Select a file to edit</div>
          )}
        </div>
        {/* Integrated terminal */}
        <TerminalPanel cwd={root} />
        {error && <div className="text-sm text-red-600">{error}</div>}
      </div>
    </div>
  );
};
