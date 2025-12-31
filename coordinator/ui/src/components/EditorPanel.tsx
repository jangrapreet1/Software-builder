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
    <div className="flex h-[calc(100vh-64px)] overflow-hidden bg-[#0c0c0e]">
      {/* LEFT SIDEBAR - Files, Git, Secrets */}
      <div className="w-72 flex-shrink-0 flex flex-col border-r border-white/5 bg-black/20">
        <div className="flex-1 overflow-y-auto custom-scrollbar p-3 space-y-4">
          <FileTree root={root} onSelectFile={loadFile} />

          <div className="glass-panel rounded-xl p-3 flex-shrink-0">
            <div className="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-2 flex items-center">
              <i className="fab fa-git-alt mr-2 text-red-400"></i>
              Git Controls
            </div>
            <pre className="text-[10px] whitespace-pre-wrap bg-black/40 p-2 rounded-lg border border-white/5 max-h-24 overflow-auto text-gray-300 font-mono mb-2 custom-scrollbar">{gitStatus || 'No status'}</pre>

            <div className="flex items-center gap-1.5 mb-2">
              <button onClick={ensureRepo} className="glass-button px-2 py-1 text-[10px] text-gray-300 hover:text-white rounded" title="Initialize Repo">Init</button>
              <input
                className="flex-1 text-[10px] bg-black/20 border border-white/10 rounded px-2 py-1 text-white placeholder-gray-600 focus:ring-1 focus:ring-primary/50 outline-none"
                value={commitMessage}
                onChange={(e) => setCommitMessage(e.target.value)}
                placeholder="Message"
              />
              <button onClick={commit} className="px-2 py-1 bg-primary/20 hover:bg-primary/30 text-primary hover:text-white rounded text-[10px] font-bold border border-primary/20">Commit</button>
            </div>

            <div className="flex items-center gap-1.5">
              <input
                className="flex-1 text-[10px] bg-black/20 border border-white/10 rounded px-2 py-1 text-white placeholder-gray-600 focus:ring-1 focus:ring-primary/50 outline-none"
                value={remoteUrl}
                onChange={(e) => setRemoteUrl(e.target.value)}
                placeholder="Remote URL"
              />
              <button onClick={handlePull} className="glass-button px-2 py-1 text-[10px] text-blue-300 hover:text-white rounded" title="Pull">
                <i className="fas fa-arrow-down"></i>
              </button>
              <button onClick={handlePush} className="glass-button px-2 py-1 text-[10px] text-green-300 hover:text-white rounded" title="Push">
                <i className="fas fa-arrow-up"></i>
              </button>
            </div>
          </div>

          <SecretsPanel root={root} />
        </div>
      </div>

      {/* MIDDLE CONTENT - Editor & Terminal */}
      <div className="flex-1 flex flex-col min-w-0 bg-[#1e1e1e]">
        {/* Tab Bar */}
        <div className="h-10 border-b border-white/5 bg-[#18181b] flex items-center justify-between px-2 flex-shrink-0">
          <div className="flex items-center space-x-1 overflow-x-auto custom-scrollbar h-full no-scrollbar">
            {openTabs.map(tab => (
              <div
                key={tab.path}
                onClick={() => setActiveTabPath(tab.path)}
                className={`flex items-center gap-2 px-3 h-full text-xs cursor-pointer border-r border-white/5 transition-colors ${tab.path === activeTabPath
                    ? 'bg-[#1e1e1e] text-white font-medium border-t-2 border-t-primary'
                    : 'bg-transparent text-gray-400 hover:bg-[#1e1e1e]/50 hover:text-gray-200 border-t-2 border-t-transparent'
                  }`}
              >
                <span className="truncate max-w-[150px]" title={tab.path}>{getFileName(tab.path)}</span>
                {tab.dirty && <span className="w-1.5 h-1.5 rounded-full bg-amber-500" title="Unsaved"></span>}
                <button
                  onClick={(e) => handleCloseTab(tab.path, e)}
                  className="w-4 h-4 flex items-center justify-center rounded hover:bg-white/10 text-gray-400 hover:text-white text-[10px] ml-1"
                  title="Close tab"
                >
                  <i className="fas fa-times"></i>
                </button>
              </div>
            ))}
          </div>
          <div className="flex items-center gap-2 pl-2 border-l border-white/10 ml-2">
            <button onClick={handleDownload} className="text-gray-400 hover:text-white text-xs px-2 py-1 hover:bg-white/5 rounded">
              <i className="fas fa-download"></i>
            </button>
            <button
              disabled={!activeTab?.dirty || loading}
              onClick={handleSave}
              className="px-3 py-1 rounded bg-primary text-white text-xs font-medium hover:bg-primary-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Save
            </button>
          </div>
        </div>

        {/* Editor Area */}
        <div className="flex-1 relative min-h-0">
          {activeTab ? (
            <CodeEditor
              language={activeTab.language}
              value={activeTab.content}
              onChange={handleContentChange}
            />
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-gray-500 bg-[#1e1e1e]">
              <div className="w-16 h-16 rounded-full bg-white/5 flex items-center justify-center mb-4 border border-white/5">
                <i className="fas fa-code text-3xl opacity-30"></i>
              </div>
              <p className="text-sm">Select a file to edit</p>
              <p className="text-xs text-gray-600 mt-2">Ctrl+S to save</p>
            </div>
          )}
        </div>

        {/* Terminal Area - Fixed height at bottom */}
        <div className="h-64 border-t border-white/10 bg-black flex-shrink-0 overflow-hidden">
          <TerminalPanel cwd={root} />
        </div>
      </div>

      {/* RIGHT SIDEBAR - Chat & Changes */}
      <div className="w-80 flex-shrink-0 flex flex-col border-l border-white/5 bg-black/20">
        <div className="flex-1 flex flex-col min-h-0">
          <div className="flex-1 min-h-0 overflow-hidden">
            <ChatPanel embedded hideSessionList contextRoot={root} selectedPath={activeTabPath} onSessionReady={setChatSessionId} />
          </div>
          <div className="flex-shrink-0 border-t border-white/5 max-h-[300px] overflow-y-auto custom-scrollbar">
            <ChangesPanel sessionId={chatSessionId} contextRoot={root} selectedPath={activeTabPath} />
          </div>
        </div>
      </div>

      {/* Toast Error */}
      {error && (
        <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 bg-red-500/90 text-white px-4 py-2 rounded-lg shadow-xl text-xs flex items-center backdrop-blur-md border border-red-400/50 z-50">
          <i className="fas fa-exclamation-circle mr-2"></i>
          {error}
        </div>
      )}
    </div>
  );
};

