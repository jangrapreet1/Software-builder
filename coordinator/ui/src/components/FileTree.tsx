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
      <ul className="pl-3">
        {items.map((item) => (
          <li key={item.path} className="py-0.5">
            {item.type === 'directory' ? (
              <div>
                <button
                  className="text-left w-full hover:bg-gray-100 rounded px-1"
                  onClick={() => toggle(item.path)}
                  title={item.path}
                >
                  <span className="mr-1">{expanded[item.path] ? '📂' : '📁'}</span>
                  {item.name}
                </button>
                {expanded[item.path] && renderDir(item.path)}
              </div>
            ) : (
              <button
                className="text-left w-full hover:bg-blue-50 rounded px-1"
                onClick={() => onSelectFile(item.path)}
                title={item.path}
              >
                <span className="mr-1">📄</span>
                {item.name}
              </button>
            )}
          </li>
        ))}
        {loading[rel] && <li className="text-xs text-gray-500">Loading...</li>}
      </ul>
    );
  };

  return (
    <div className="h-full overflow-auto border rounded-lg p-2 bg-white">
      <div className="flex items-center justify-between mb-2">
        <div className="font-semibold text-sm">Files</div>
        <button
          onClick={() => loadDir('.')}
          className="text-xs px-2 py-1 bg-gray-100 hover:bg-gray-200 rounded"
        >
          Refresh
        </button>
      </div>
      {error && <div className="text-xs text-red-600 mb-2">{error}</div>}
      {renderDir('.')}
    </div>
  );
};
