import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { CodeEditor } from './CodeEditor';
import { TerminalPanel } from './TerminalPanel';
import ChatPanel from './ChatPanel';

interface IDEShellProps {
    root: string;
    onRun?: () => void;
    onStop?: () => void;
    onBack?: () => void;
    isRunning?: boolean;
}

interface FileItem {
    type: 'file' | 'directory';
    name: string;
    size: number;
    modified: string;
    path: string;
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
    if (lower.endsWith('.scss')) return 'scss';
    if (lower.endsWith('.go')) return 'go';
    if (lower.endsWith('.rs')) return 'rust';
    if (lower.endsWith('.java')) return 'java';
    if (lower.endsWith('.sh')) return 'shell';
    return 'plaintext';
};

const getFileIcon = (name: string, isDir: boolean) => {
    if (isDir) return 'fa-folder';
    const ext = name.split('.').pop()?.toLowerCase() || '';
    const icons: Record<string, string> = {
        ts: 'fa-file-code text-blue-400',
        tsx: 'fa-file-code text-blue-400',
        js: 'fa-file-code text-yellow-400',
        jsx: 'fa-file-code text-yellow-400',
        py: 'fa-file-code text-green-400',
        json: 'fa-file-code text-yellow-300',
        md: 'fa-file-alt text-gray-400',
        html: 'fa-file-code text-orange-400',
        css: 'fa-file-code text-blue-300',
        scss: 'fa-file-code text-pink-400',
        yml: 'fa-file-alt text-red-300',
        yaml: 'fa-file-alt text-red-300',
        png: 'fa-file-image text-purple-400',
        jpg: 'fa-file-image text-purple-400',
        svg: 'fa-file-image text-orange-300',
        git: 'fa-git-alt text-red-400',
        lock: 'fa-lock text-gray-500',
    };
    return icons[ext] || 'fa-file text-gray-400';
};

export const IDEShell: React.FC<IDEShellProps> = ({ root, onRun, onStop, onBack, isRunning }) => {
    // State
    const [openTabs, setOpenTabs] = useState<OpenTab[]>([]);
    const [activeTabPath, setActiveTabPath] = useState<string>('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Sidebar state
    const [sidebarWidth, setSidebarWidth] = useState(240);
    const [isResizingSidebar, setIsResizingSidebar] = useState(false);

    // Right sidebar (Chat) state
    const [rightSidebarWidth, setRightSidebarWidth] = useState(320);
    const [isResizingRightSidebar, setIsResizingRightSidebar] = useState(false);
    const [showChatPanel, setShowChatPanel] = useState(true);
    const [_chatSessionId, setChatSessionId] = useState<string>('');

    // Agent status & live streaming state
    const [agentStatus, setAgentStatus] = useState<{
        isThinking: boolean;
        isWriting: boolean;
        targetFile?: string;
        toolName?: string;
    }>({ isThinking: false, isWriting: false });

    const [streamedEdit, setStreamedEdit] = useState<{
        path: string;
        originalContent: string;
        newContent: string;
        isDone: boolean;
    } | null>(null);

    const handleLiveCodeStream = useCallback((filePath: string, code: string, isDone: boolean) => {
        if (!filePath) return;

        setOpenTabs(prev => {
            const normTarget = filePath.replace(/\\/g, '/');
            const existingIndex = prev.findIndex(t => {
                const p = t.path.replace(/\\/g, '/');
                return p.endsWith(normTarget) || normTarget.endsWith(p);
            });

            if (existingIndex >= 0) {
                const copy = [...prev];
                const targetTab = copy[existingIndex];
                setStreamedEdit(curr => {
                    if (!curr || curr.path !== targetTab.path) {
                        return { path: targetTab.path, originalContent: targetTab.content, newContent: code, isDone };
                    }
                    return { ...curr, newContent: code, isDone };
                });

                copy[existingIndex] = {
                    ...targetTab,
                    content: code,
                    dirty: true,
                };
                setActiveTabPath(targetTab.path);
                return copy;
            } else {
                const newTab: OpenTab = {
                    path: filePath,
                    content: code,
                    dirty: true,
                    language: guessLanguage(filePath),
                };
                setActiveTabPath(filePath);
                setStreamedEdit({ path: filePath, originalContent: '', newContent: code, isDone });
                return [...prev, newTab];
            }
        });
    }, []);

    // Bottom panel state
    const [bottomPanelHeight, setBottomPanelHeight] = useState(180);
    const [isResizingBottom, setIsResizingBottom] = useState(false);

    // File tree state
    const [tree, setTree] = useState<Record<string, FileItem[]>>({});
    const [expanded, setExpanded] = useState<Record<string, boolean>>({ '.': true });
    const [treeLoading, setTreeLoading] = useState<Record<string, boolean>>({});

    const activeTab = useMemo(() => openTabs.find(t => t.path === activeTabPath), [openTabs, activeTabPath]);

    // File tree loading
    const loadDir = useCallback(async (rel: string) => {
        try {
            setTreeLoading((p) => ({ ...p, [rel]: true }));
            const res = await fetch(`/api/fs/list?root=${encodeURIComponent(root)}&path=${encodeURIComponent(rel)}`);
            const data = await res.json();
            if ('items' in data) {
                setTree((prev) => ({ ...prev, [rel]: data.items }));
            }
        } catch (e: any) {
            console.error('Failed to load directory:', e);
        } finally {
            setTreeLoading((p) => ({ ...p, [rel]: false }));
        }
    }, [root]);

    useEffect(() => {
        loadDir('.');
    }, [loadDir]);

    const toggleDir = useCallback(async (rel: string) => {
        const now = !expanded[rel];
        setExpanded((p) => ({ ...p, [rel]: now }));
        if (now && !tree[rel]) {
            await loadDir(rel);
        }
    }, [expanded, tree, loadDir]);

    // File loading
    const loadFile = useCallback(async (relPath: string) => {
        const existing = openTabs.find(t => t.path === relPath);
        if (existing) {
            setActiveTabPath(relPath);
            return;
        }

        setError(null);
        setLoading(true);
        try {
            const res = await fetch(`/api/fs/read?root=${encodeURIComponent(root)}&path=${encodeURIComponent(relPath)}`);
            if (!res.ok) throw new Error(`Failed to read file: ${res.status}`);
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

    // Editor handlers
    const handleContentChange = useCallback((newContent: string) => {
        setOpenTabs(prev => prev.map(tab =>
            tab.path === activeTabPath ? { ...tab, content: newContent, dirty: true } : tab
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
        if (tab?.dirty && !window.confirm(`"${pathToClose}" has unsaved changes. Close anyway?`)) {
            return;
        }
        setOpenTabs(prev => prev.filter(t => t.path !== pathToClose));
        if (activeTabPath === pathToClose) {
            const remaining = openTabs.filter(t => t.path !== pathToClose);
            setActiveTabPath(remaining.length > 0 ? remaining[remaining.length - 1].path : '');
        }
    }, [openTabs, activeTabPath]);

    // Keyboard shortcuts
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

    // Listen for file updates from ChatPanel (when AI applies changes)
    useEffect(() => {
        const handleFileUpdated = async (e: CustomEvent<{ path: string; root: string }>) => {
            const { path, root: eventRoot } = e.detail;
            // Only refresh if it's for our root and we have this file open
            if (eventRoot !== root) return;

            const tab = openTabs.find(t => t.path === path);
            if (tab) {
                // Re-fetch the file content
                try {
                    setLoading(true);
                    const res = await fetch(`/api/fs/read?root=${encodeURIComponent(root)}&path=${encodeURIComponent(path)}`);
                    const data = await res.json();
                    if (data.content !== undefined) {
                        setOpenTabs(prev => prev.map(t =>
                            t.path === path
                                ? { ...t, content: data.content, dirty: false }
                                : t
                        ));
                    }
                } catch (err) {
                    console.error('[IDEShell] Failed to refresh file:', err);
                } finally {
                    setLoading(false);
                }
            }
        };

        window.addEventListener('sb:file-updated', handleFileUpdated as unknown as EventListener);
        return () => window.removeEventListener('sb:file-updated', handleFileUpdated as unknown as EventListener);
    }, [root, openTabs]);

    // Resize handlers
    const handleSidebarMouseDown = useCallback(() => {
        setIsResizingSidebar(true);
    }, []);

    const handleBottomMouseDown = useCallback(() => {
        setIsResizingBottom(true);
    }, []);

    const handleRightSidebarMouseDown = useCallback(() => {
        setIsResizingRightSidebar(true);
    }, []);

    useEffect(() => {
        const handleMouseMove = (e: MouseEvent) => {
            if (isResizingSidebar) {
                const newWidth = Math.max(160, Math.min(400, e.clientX));
                setSidebarWidth(newWidth);
            }
            if (isResizingBottom) {
                const newHeight = Math.max(100, Math.min(500, window.innerHeight - e.clientY - 40));
                setBottomPanelHeight(newHeight);
            }
            if (isResizingRightSidebar) {
                const newWidth = Math.max(280, Math.min(500, window.innerWidth - e.clientX));
                setRightSidebarWidth(newWidth);
            }
        };
        const handleMouseUp = () => {
            setIsResizingSidebar(false);
            setIsResizingBottom(false);
            setIsResizingRightSidebar(false);
        };
        if (isResizingSidebar || isResizingBottom || isResizingRightSidebar) {
            document.addEventListener('mousemove', handleMouseMove);
            document.addEventListener('mouseup', handleMouseUp);
            document.body.style.cursor = isResizingSidebar || isResizingRightSidebar ? 'col-resize' : 'row-resize';
            document.body.style.userSelect = 'none';
        }
        return () => {
            document.removeEventListener('mousemove', handleMouseMove);
            document.removeEventListener('mouseup', handleMouseUp);
            document.body.style.cursor = '';
            document.body.style.userSelect = '';
        };
    }, [isResizingSidebar, isResizingBottom, isResizingRightSidebar]);

    const getFileName = (path: string) => path.split(/[\\/]/).pop() || path;
    const projectName = root.split(/[\\/]/).pop() || 'Project';

    // Render file tree
    const renderTree = (rel: string, depth: number = 0) => {
        const items = tree[rel] || [];
        return (
            <div style={{ paddingLeft: depth > 0 ? 12 : 0 }}>
                {items.map((item) => (
                    <div key={item.path}>
                        {item.type === 'directory' ? (
                            <>
                                <button
                                    onClick={() => toggleDir(item.path)}
                                    className="w-full text-left px-2 py-[3px] flex items-center gap-2 hover:bg-[#2a2d2e] text-[13px] text-[#cccccc]"
                                >
                                    <i className={`fas ${expanded[item.path] ? 'fa-chevron-down' : 'fa-chevron-right'} text-[10px] text-[#858585] w-3`}></i>
                                    <i className={`fas ${expanded[item.path] ? 'fa-folder-open text-[#dcb67a]' : 'fa-folder text-[#dcb67a]'} text-[14px]`}></i>
                                    <span className="truncate">{item.name}</span>
                                </button>
                                {expanded[item.path] && renderTree(item.path, depth + 1)}
                            </>
                        ) : (
                            <button
                                onClick={() => loadFile(item.path)}
                                className={`w-full text-left px-2 py-[3px] flex items-center gap-2 hover:bg-[#2a2d2e] text-[13px] ${activeTabPath === item.path ? 'bg-[#37373d] text-white' : 'text-[#cccccc]'}`}
                                style={{ paddingLeft: 20 }}
                            >
                                <i className={`fas ${getFileIcon(item.name, false)} text-[14px]`}></i>
                                <span className="truncate">{item.name}</span>
                            </button>
                        )}
                    </div>
                ))}
                {treeLoading[rel] && (
                    <div className="px-4 py-1 text-[11px] text-[#858585]">
                        <i className="fas fa-circle-notch fa-spin mr-2"></i>Loading...
                    </div>
                )}
            </div>
        );
    };

    return (
        <div className="fixed inset-0 flex flex-col bg-[#1e1e1e] text-[#cccccc] overflow-hidden" style={{ fontFamily: "'Segoe UI', sans-serif" }}>
            {/* TOP BAR */}
            <div className="h-10 flex items-center justify-between px-3 bg-[#3c3c3c] border-b border-[#252526] flex-shrink-0">
                <div className="flex items-center gap-3">
                    {/* Back Button */}
                    <button
                        onClick={onBack}
                        className="w-8 h-8 flex items-center justify-center hover:bg-[#505050] rounded text-[#cccccc]"
                        title="Back to Dashboard"
                    >
                        <i className="fas fa-arrow-left text-[12px]"></i>
                    </button>

                    {/* Run Button */}
                    <button
                        onClick={isRunning ? onStop : onRun}
                        className={`px-4 py-1.5 rounded text-[13px] font-medium flex items-center gap-2 transition-colors ${isRunning
                            ? 'bg-[#f14c4c] hover:bg-[#d93f3f] text-white'
                            : 'bg-[#4ec9b0] hover:bg-[#3dbfa6] text-[#1e1e1e]'
                            }`}
                    >
                        <i className={`fas ${isRunning ? 'fa-stop' : 'fa-play'} text-[11px]`}></i>
                        {isRunning ? 'Stop' : 'Run'}
                    </button>
                </div>

                {/* Project Name */}
                <div className="text-[13px] font-medium text-[#cccccc]">
                    {projectName}
                </div>

                {/* Right icons */}
                <div className="flex items-center gap-2">
                    <button
                        onClick={() => setShowChatPanel(!showChatPanel)}
                        className={`w-7 h-7 flex items-center justify-center hover:bg-[#505050] rounded ${showChatPanel ? 'text-[#007acc]' : 'text-[#cccccc]'}`}
                        title="Toggle AI Assistant"
                    >
                        <i className="fas fa-robot text-[14px]"></i>
                    </button>
                    <button className="w-7 h-7 flex items-center justify-center hover:bg-[#505050] rounded text-[#cccccc]">
                        <i className="fas fa-cog text-[14px]"></i>
                    </button>
                </div>
            </div>

            {/* MAIN AREA */}
            <div className="flex-1 flex overflow-hidden">
                {/* LEFT SIDEBAR */}
                <div
                    className="flex-shrink-0 bg-[#252526] border-r border-[#3c3c3c] flex flex-col overflow-hidden"
                    style={{ width: sidebarWidth }}
                >
                    {/* Sidebar Header */}
                    <div className="h-9 flex items-center justify-between px-4 border-b border-[#3c3c3c] flex-shrink-0">
                        <span className="text-[11px] font-semibold tracking-wide text-[#bbbbbb] uppercase">Explorer</span>
                        <button
                            onClick={() => loadDir('.')}
                            className="w-5 h-5 flex items-center justify-center hover:bg-[#3c3c3c] rounded text-[#858585] hover:text-[#cccccc]"
                        >
                            <i className="fas fa-sync-alt text-[10px]"></i>
                        </button>
                    </div>

                    {/* File Tree */}
                    <div className="flex-1 overflow-y-auto overflow-x-hidden py-1">
                        {renderTree('.')}
                    </div>
                </div>

                {/* Sidebar Resize Handle */}
                <div
                    className="w-1 cursor-col-resize hover:bg-[#007acc] active:bg-[#007acc] transition-colors flex-shrink-0"
                    onMouseDown={handleSidebarMouseDown}
                />

                {/* CENTER AREA (Editor + Bottom Panel) */}
                <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
                    {/* Tab Bar */}
                    <div className="h-[35px] bg-[#252526] flex items-end overflow-x-auto flex-shrink-0" style={{ scrollbarWidth: 'none' }}>
                        {openTabs.map(tab => (
                            <div
                                key={tab.path}
                                onClick={() => setActiveTabPath(tab.path)}
                                className={`h-[35px] flex items-center gap-2 px-3 cursor-pointer border-r border-[#252526] transition-colors ${tab.path === activeTabPath
                                    ? 'bg-[#1e1e1e] text-white'
                                    : 'bg-[#2d2d2d] text-[#969696] hover:bg-[#2d2d2d]'
                                    }`}
                                style={{ minWidth: 'fit-content' }}
                            >
                                <i className={`fas ${getFileIcon(tab.path, false)} text-[13px]`}></i>
                                <span className="text-[13px] whitespace-nowrap">{getFileName(tab.path)}</span>
                                {tab.dirty && <span className="w-2 h-2 rounded-full bg-white"></span>}
                                <button
                                    onClick={(e) => handleCloseTab(tab.path, e)}
                                    className="w-5 h-5 flex items-center justify-center hover:bg-[#3c3c3c] rounded ml-1 text-[#969696] hover:text-white"
                                >
                                    <i className="fas fa-times text-[11px]"></i>
                                </button>
                            </div>
                        ))}
                    </div>

                    {/* Editor Surface */}
                    <div className="flex-1 min-h-0 bg-[#1e1e1e] flex flex-col relative" style={{ height: `calc(100% - 35px - ${bottomPanelHeight}px)` }}>
                        {/* Live Agent Status Banner */}
                        {(agentStatus.isWriting || agentStatus.isThinking) && (
                            <div className="bg-[#007acc]/20 border-b border-[#007acc]/40 px-4 py-1.5 flex items-center justify-between text-xs text-[#007acc] animate-pulse shrink-0 z-10">
                                <div className="flex items-center gap-2 font-medium">
                                    <i className={`fas ${agentStatus.isWriting ? 'fa-pen-nib' : 'fa-brain'} fa-spin`}></i>
                                    <span>
                                        {agentStatus.isWriting
                                            ? `AI Agent writing to ${agentStatus.targetFile || getFileName(activeTabPath)}...`
                                            : `AI Agent thinking... (${agentStatus.toolName || 'analyzing codebase'})`}
                                    </span>
                                </div>
                                <span className="text-[10px] bg-[#007acc]/30 text-white font-mono px-2 py-0.5 rounded tracking-wider uppercase font-semibold">
                                    LIVE AI STREAM
                                </span>
                            </div>
                        )}

                        {/* Cursor/Antigravity Floating Accept/Revert Action Bar */}
                        {streamedEdit && streamedEdit.isDone && streamedEdit.path === activeTabPath && (
                            <div className="bg-[#252526] border-b border-[#3c3c3c] px-4 py-2 flex items-center justify-between text-xs shrink-0 z-10 shadow-lg animate-fade-in">
                                <div className="flex items-center gap-2 text-emerald-400 font-medium">
                                    <i className="fas fa-sparkles text-amber-400"></i>
                                    <span>AI generated code edits for <strong>{getFileName(streamedEdit.path)}</strong></span>
                                </div>
                                <div className="flex items-center gap-2">
                                    <button
                                        onClick={() => {
                                            handleSave();
                                            setStreamedEdit(null);
                                        }}
                                        className="px-3 py-1 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold rounded flex items-center gap-1.5 transition-all shadow-md"
                                    >
                                        <i className="fas fa-check"></i> Accept Changes (Ctrl+S)
                                    </button>
                                    <button
                                        onClick={() => {
                                            if (streamedEdit) {
                                                setOpenTabs(prev => prev.map(t => t.path === streamedEdit.path ? { ...t, content: streamedEdit.originalContent, dirty: false } : t));
                                            }
                                            setStreamedEdit(null);
                                        }}
                                        className="px-3 py-1 bg-[#3c3c3c] hover:bg-[#4c4c4c] text-gray-300 rounded flex items-center gap-1.5 transition-all"
                                    >
                                        <i className="fas fa-undo"></i> Revert
                                    </button>
                                </div>
                            </div>
                        )}

                        <div className="flex-1 min-h-0 relative">
                            {activeTab ? (
                                <CodeEditor
                                    language={activeTab.language}
                                    value={activeTab.content}
                                    onChange={handleContentChange}
                                />
                            ) : (
                                <div className="h-full flex flex-col items-center justify-center text-[#5a5a5a]">
                                    <i className="fas fa-file-code text-[48px] mb-4 opacity-30"></i>
                                    <p className="text-[14px]">Select a file to open</p>
                                    <p className="text-[12px] mt-1 text-[#4a4a4a]">Ctrl+S to save</p>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Bottom Panel Resize Handle */}
                    <div
                        className="h-1 cursor-row-resize hover:bg-[#007acc] active:bg-[#007acc] transition-colors flex-shrink-0 bg-[#3c3c3c]"
                        onMouseDown={handleBottomMouseDown}
                    />

                    {/* Bottom Panel (Terminal) */}
                    <div
                        className="flex-shrink-0 bg-[#1e1e1e] border-t border-[#3c3c3c] overflow-hidden"
                        style={{ height: bottomPanelHeight }}
                    >
                        <TerminalPanel cwd={root} />
                    </div>
                </div>

                {/* RIGHT SIDEBAR - Chat Panel */}
                {showChatPanel && (
                    <>
                        {/* Right Sidebar Resize Handle */}
                        <div
                            className="w-1 cursor-col-resize hover:bg-[#007acc] active:bg-[#007acc] transition-colors flex-shrink-0"
                            onMouseDown={handleRightSidebarMouseDown}
                        />
                        <div
                            className="flex-shrink-0 bg-[#252526] border-l border-[#3c3c3c] flex flex-col overflow-hidden"
                            style={{ width: rightSidebarWidth }}
                        >
                            {/* Chat Header */}
                            <div className="h-9 flex items-center justify-between px-4 border-b border-[#3c3c3c] flex-shrink-0">
                                <span className="text-[11px] font-semibold tracking-wide text-[#bbbbbb] uppercase flex items-center gap-2">
                                    <i className="fas fa-robot text-[#007acc]"></i>
                                    AI Assistant
                                </span>
                                <button
                                    onClick={() => setShowChatPanel(false)}
                                    className="w-5 h-5 flex items-center justify-center hover:bg-[#3c3c3c] rounded text-[#858585] hover:text-[#cccccc]"
                                >
                                    <i className="fas fa-times text-[10px]"></i>
                                </button>
                            </div>

                            {/* Chat Panel */}
                            <div className="flex-1 overflow-hidden">
                                <ChatPanel
                                    embedded
                                    hideSessionList
                                    contextRoot={root}
                                    selectedPath={activeTabPath}
                                    onSessionReady={setChatSessionId}
                                    onLiveCodeStream={handleLiveCodeStream}
                                    onAgentStatusChange={setAgentStatus}
                                />
                            </div>
                        </div>
                    </>
                )}
            </div>

            {/* Loading Indicator */}
            {loading && (
                <div className="fixed top-12 right-4 bg-[#252526] text-[#cccccc] px-3 py-2 rounded text-[12px] flex items-center gap-2 shadow-lg z-50 border border-[#3c3c3c]">
                    <i className="fas fa-circle-notch fa-spin text-[#007acc]"></i>
                    Loading...
                </div>
            )}

            {/* Error Toast */}
            {error && (
                <div className="fixed bottom-4 left-1/2 transform -translate-x-1/2 bg-[#f14c4c] text-white px-4 py-2 rounded text-[13px] flex items-center gap-2 shadow-lg z-50">
                    <i className="fas fa-exclamation-circle"></i>
                    {error}
                    <button onClick={() => setError(null)} className="ml-2 hover:text-[#cccccc]">
                        <i className="fas fa-times"></i>
                    </button>
                </div>
            )}
        </div>
    );
};
