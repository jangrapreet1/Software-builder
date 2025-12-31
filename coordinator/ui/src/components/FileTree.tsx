import React, { useEffect, useState } from 'react';

interface FileItem {
  type: 'file' | 'directory';
  name: string;
  size: number;
  modified: string;
  path: string;
}

interface ListResponse {
  root: string;
  path: string;
  items: FileItem[];
}

interface FileTreeProps {
  root: string;
  onSelectFile: (relPath: string) => void;
}

export const FileTree: React.FC<FileTreeProps> = ({ root, onSelectFile }) => {
  const [tree, setTree] = useState<Record<string, FileItem[]>>({});
  const [expanded, setExpanded] = useState<Record<string, boolean>>({ '.': true });
  const [loading, setLoading] = useState<Record<string, boolean>>({});
  const [error, setError] = useState<string | null>(null);

  const loadDir = async (rel: string) => {
    try {
      setLoading((p) => ({ ...p, [rel]: true }));
      const res = await fetch(`/api/fs/list?root=${encodeURIComponent(root)}&path=${encodeURIComponent(rel)}`);
      const data: ListResponse | FileItem = await res.json();
      if ('items' in data) {
        setTree((prev) => ({ ...prev, [rel]: data.items }));
      } else {
        // Fallback for file response
        setTree((prev) => ({ ...prev, [rel]: [] }));
      }
    } catch (e: any) {
      setError(e?.message ?? 'Failed to load directory');
    } finally {
      setLoading((p) => ({ ...p, [rel]: false }));
    }
  };

  useEffect(() => {
    loadDir('.');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [root]);

  const toggle = async (rel: string) => {
    const now = !expanded[rel];
    setExpanded((p) => ({ ...p, [rel]: now }));
    if (now && !tree[rel]) {
      await loadDir(rel);
    }
  };

  const renderDir = (rel: string) => {
    const items = tree[rel] || [];
    return (
      <ul className="pl-3 border-l border-white/5 ml-1.5">
        {items.map((item) => (
          <li key={item.path} className="py-0.5">
            {item.type === 'directory' ? (
              <div>
                <button
                  className="text-left w-full hover:bg-white/5 rounded-lg px-2 py-1 flex items-center group transition-colors"
                  onClick={() => toggle(item.path)}
                  title={item.path}
                >
                  <span className="mr-2 text-primary/80 group-hover:text-primary transition-colors text-xs">
                    {expanded[item.path] ? <i className="fas fa-folder-open"></i> : <i className="fas fa-folder"></i>}
                  </span>
                  <span className="text-gray-300 group-hover:text-white text-xs truncate transition-colors">{item.name}</span>
                </button>
                {expanded[item.path] && renderDir(item.path)}
              </div>
            ) : (
              <button
                className="text-left w-full hover:bg-white/5 rounded-lg px-2 py-1 flex items-center group transition-colors"
                onClick={() => onSelectFile(item.path)}
                title={item.path}
                draggable
                onDragStart={(e) => {
                  const mention = `@${item.path.replace(/\\/g, '/')}`;
                  e.dataTransfer.setData('text/plain', mention);
                  e.dataTransfer.effectAllowed = 'copy';
                }}
                onContextMenu={(e) => {
                  e.preventDefault();
                  const mention = `@${item.path.replace(/\\/g, '/')}`;
                  if (navigator.clipboard && navigator.clipboard.writeText) {
                    navigator.clipboard.writeText(mention).catch(() => { });
                  }
                }}
              >
                <span className="mr-2 text-gray-500 group-hover:text-accent transition-colors text-xs">
                  <i className="far fa-file-code"></i>
                </span>
                <span className="text-gray-400 group-hover:text-white text-xs truncate transition-colors font-mono">{item.name}</span>
              </button>
            )}
          </li>
        ))}
        {loading[rel] && (
          <li className="text-[10px] text-gray-500 py-1 flex items-center pl-2">
            <i className="fas fa-circle-notch fa-spin mr-2"></i> Loading...
          </li>
        )}
      </ul>
    );
  };

  return (
    <div className="glass-panel flex-1 min-h-[300px] flex flex-col overflow-hidden rounded-xl">
      <div className="flex items-center justify-between p-3 border-b border-white/10 bg-black/20">
        <div className="font-bold text-xs text-white tracking-wide uppercase flex items-center">
          <i className="fas fa-project-diagram mr-2 text-primary"></i>
          Explorer
        </div>
        <button
          onClick={() => loadDir('.')}
          className="text-[10px] px-2 py-1 bg-white/5 hover:bg-white/10 text-gray-300 hover:text-white rounded-lg transition-colors border border-white/5"
        >
          <i className="fas fa-sync-alt mr-1"></i> Refresh
        </button>
      </div>
      <div className="flex-1 overflow-auto p-2 custom-scrollbar">
        {error && <div className="text-xs text-red-300 bg-red-500/10 p-2 rounded mb-2 border border-red-500/20">{error}</div>}
        {renderDir('.')}
      </div>
    </div>
  );
};
