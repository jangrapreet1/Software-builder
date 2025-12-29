import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { FileTree } from './FileTree';
import { CodeEditor } from './CodeEditor';
import { TerminalPanel } from './TerminalPanel';
import { SecretsPanel } from './SecretsPanel';
import ChatPanel from './ChatPanel';
import { ChangesPanel } from './ChangesPanel';

interface EditorPanelProps {
  root: string;
}

interface OpenTab {
  path: string;
  content: string;
  dirty: boolean;
  language: string;
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
  const [openTabs, setOpenTabs] = useState<OpenTab[]>([]);
  const [activeTabPath, setActiveTabPath] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [chatSessionId, setChatSessionId] = useState<string>('');

  const activeTab = useMemo(() => openTabs.find(t => t.path === activeTabPath), [openTabs, activeTabPath]);

  const loadFile = useCallback(async (relPath: string) => {
    // Check if already open
    const existing = openTabs.find(t => t.path === relPath);
    if (existing) {
      setActiveTabPath(relPath);
      return;
    }

    setError(null);
    setLoading(true);
    try {
      const res = await fetch(`/api/fs/read?root=${encodeURIComponent(root)}&path=${encodeURIComponent(relPath)}`);
      if (!res.ok) {
        throw new Error(`Failed to read file: ${res.status}`);
      }
      const data = await res.json();
      const newTab: OpenTab = {
        path: relPath,
        content: data.content || '',
        dirty: false,
        language: guessLanguage(relPath)
      };
      setOpenTabs(prev => [...prev, newTab]);
      setActiveTabPath(relPath);
    } catch (e: any) {
      setError(e?.message ?? 'Failed to read file');
    } finally {
      setLoading(false);
    }
  }, [root, openTabs]);

  const handleContentChange = useCallback((newContent: string) => {
    setOpenTabs(prev => prev.map(tab =>
      tab.path === activeTabPath
        ? { ...tab, content: newContent, dirty: true }
        : tab
    ));
  }, [activeTabPath]);

  const handleSave = useCallback(async () => {
    if (!activeTab) return;
    setError(null);
    setLoading(true);
    try {
      const res = await fetch('/api/fs/write', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ root, path: activeTab.path, content: activeTab.content })
      });
      if (!res.ok) throw new Error(`Save failed: ${res.status}`);
      setOpenTabs(prev => prev.map(tab =>
        tab.path === activeTabPath ? { ...tab, dirty: false } : tab
      ));
    } catch (e: any) {
      setError(e?.message ?? 'Failed to save file');
    } finally {
      setLoading(false);
    }
  }, [root, activeTab, activeTabPath]);

  const handleCloseTab = useCallback((pathToClose: string, e?: React.MouseEvent) => {
    e?.stopPropagation();
    const tab = openTabs.find(t => t.path === pathToClose);
    if (tab?.dirty) {
      if (!window.confirm(`"${pathToClose}" has unsaved changes. Close anyway?`)) {
        return;
      }
    }
    setOpenTabs(prev => prev.filter(t => t.path !== pathToClose));
    if (activeTabPath === pathToClose) {
      const remaining = openTabs.filter(t => t.path !== pathToClose);
      setActiveTabPath(remaining.length > 0 ? remaining[remaining.length - 1].path : '');
    }
  }, [openTabs, activeTabPath]);

  const handleDownload = useCallback(() => {
    try {
      const url = `/api/app/download?app_path=${encodeURIComponent(root)}`;
      window.open(url, '_blank');
    } catch (e) {
      // no-op
    }
  }, [root]);

  // Keyboard shortcut for save
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        handleSave();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [handleSave]);

  // Git helpers
  const [commitMessage, setCommitMessage] = useState('update via editor');
  const [gitStatus, setGitStatus] = useState<string>('');
  const [remoteUrl, setRemoteUrl] = useState('');

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

  const handlePush = useCallback(async () => {
    if (remoteUrl) {
      await fetch('/api/git/remote', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ repo_path: root, name: 'origin', url: remoteUrl })
      });
    }
    await fetch('/api/git/push', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ repo_path: root, remote: 'origin', branch: 'main', set_upstream: true })
    });
    await refreshGitStatus();
  }, [root, remoteUrl, refreshGitStatus]);

  const handlePull = useCallback(async () => {
    await fetch('/api/git/pull', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ repo_path: root, remote: 'origin', branch: 'main' })
    });
    await refreshGitStatus();
  }, [root, refreshGitStatus]);

  useEffect(() => { refreshGitStatus(); }, [refreshGitStatus]);

  const getFileName = (path: string) => path.split(/[\\/]/).pop() || path;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
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
              onChange={(e) => setCommitMessage(e.target.value)}
              placeholder="Commit message"
              title="Commit message"
              aria-label="Commit message"
            />
            <button onClick={commit} className="text-xs px-2 py-1 bg-blue-600 text-white rounded">Commit</button>
          </div>
          <div className="flex items-center gap-2 mt-2">
            <input
              className="flex-1 text-xs border rounded px-2 py-1"
              value={remoteUrl}
              onChange={(e) => setRemoteUrl(e.target.value)}
              placeholder="Remote URL (optional)"
              title="Remote URL"
              aria-label="Remote URL"
            />
            <button onClick={handlePull} className="text-xs px-2 py-1 bg-gray-600 text-white rounded">Pull</button>
            <button onClick={handlePush} className="text-xs px-2 py-1 bg-green-600 text-white rounded">Push</button>
          </div>
        </div>
        <SecretsPanel root={root} />
      </div>
      <div className="lg:col-span-2 space-y-2">
        {/* Tab Bar */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-1 overflow-x-auto">
            {openTabs.map(tab => (
              <div
                key={tab.path}
                onClick={() => setActiveTabPath(tab.path)}
                className={`flex items-center gap-1 px-3 py-1.5 rounded-t text-sm cursor-pointer border-b-2 ${tab.path === activeTabPath
                  ? 'bg-white border-blue-500 text-blue-700'
                  : 'bg-gray-100 border-transparent text-gray-600 hover:bg-gray-200'
                  }`}
              >
                <span className="truncate max-w-[120px]" title={tab.path}>{getFileName(tab.path)}</span>
                {tab.dirty && <span className="w-2 h-2 rounded-full bg-amber-500" title="Unsaved"></span>}
                <button
                  onClick={(e) => handleCloseTab(tab.path, e)}
                  className="ml-1 text-gray-400 hover:text-red-500 text-xs"
                  title="Close tab"
                >
                  ×
                </button>
              </div>
            ))}
            {openTabs.length === 0 && (
              <div className="text-sm text-gray-500 px-3 py-1.5">No files open</div>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button onClick={handleDownload} className="px-3 py-1 rounded bg-gray-700 text-white text-sm">Download</button>
            <button
              disabled={!activeTab?.dirty || loading}
              onClick={handleSave}
              className="px-3 py-1 rounded bg-blue-600 text-white text-sm disabled:opacity-50"
            >
              Save
            </button>
          </div>
        </div>
        <div className="min-h-[400px]">
          {activeTab ? (
            <CodeEditor
              language={activeTab.language}
              value={activeTab.content}
              onChange={handleContentChange}
            />
          ) : (
            <div className="h-[60vh] border rounded bg-white flex items-center justify-center text-gray-500 text-sm">
              Select a file to edit
            </div>
          )}
        </div>
        {/* Integrated terminal */}
        <TerminalPanel cwd={root} />
        {error && <div className="text-sm text-red-600">{error}</div>}
      </div>
      <div className="lg:col-span-1">
        <ChatPanel embedded hideSessionList contextRoot={root} selectedPath={activeTabPath} onSessionReady={setChatSessionId} />
        <div className="mt-3">
          <ChangesPanel sessionId={chatSessionId} contextRoot={root} selectedPath={activeTabPath} />
        </div>
      </div>
    </div>
  );
};

