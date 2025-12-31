import React, { useState, useEffect, useRef } from 'react';

interface LogEntry {
  timestamp: string;
  level: 'info' | 'success' | 'warning' | 'error';
  message: string;
}

interface LogsPanelProps {
  instanceId?: string;
  logsUrl?: string;
  logs?: LogEntry[];
  tail?: number;
  autoScroll?: boolean;
}

export const LogsPanel: React.FC<LogsPanelProps> = ({
  instanceId,
  logsUrl,
  logs,
  tail = 100,
  autoScroll = true
}) => {
  const [localLogs, setLocalLogs] = useState<LogEntry[]>(logs ?? []);
  const [isStreaming, setIsStreaming] = useState(false);
  const logsEndRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    if (autoScroll && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  };

  useEffect(() => {
    if (logs) {
      setLocalLogs(logs);
    }
  }, [logs]);

  useEffect(() => {
    scrollToBottom();
  }, [localLogs]);

  const fetchLogs = async () => {
    if (!logsUrl) return;

    setIsStreaming(true);
    try {
      const response = await fetch(`${logsUrl}?tail=${tail}`);
      const data = await response.json();
      if (data.logs) {
        // Parse logs if they're strings
        const parsedLogs = typeof data.logs === 'string'
          ? data.logs.split('\n').map((line: string) => ({
            timestamp: new Date().toISOString(),
            level: 'info' as const,
            message: line
          }))
          : data.logs;
        setLocalLogs(parsedLogs);
      }
    } catch (error) {
      console.error('Failed to fetch logs:', error);
    } finally {
      setIsStreaming(false);
    }
  };

  const downloadLogs = () => {
    const logText = localLogs.map(log => `[${log.timestamp}] [${log.level.toUpperCase()}] ${log.message}`).join('\n');
    const blob = new Blob([logText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `logs-${instanceId || 'instance'}-${Date.now()}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const levelConfig = {
    info: { icon: 'fa-info-circle', color: 'text-blue-500' },
    success: { icon: 'fa-check-circle', color: 'text-green-500' },
    warning: { icon: 'fa-exclamation-triangle', color: 'text-yellow-500' },
    error: { icon: 'fa-times-circle', color: 'text-red-500' }
  };

  return (
    <div className="glass-panel rounded-2xl overflow-hidden border border-white/10 shadow-lg">
      <div className="bg-black/40 border-b border-white/5 px-6 py-4 flex items-center justify-between backdrop-blur-md">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 rounded-lg bg-gray-800 flex items-center justify-center border border-white/5">
            <i className="fas fa-terminal text-gray-400 text-sm"></i>
          </div>
          <div>
            <span className="font-bold text-gray-200 text-sm tracking-wide uppercase">Console Logs</span>
            {instanceId && (
              <div className="text-[10px] text-gray-500 font-mono mt-0.5">{instanceId}</div>
            )}
          </div>
        </div>
        <div className="flex items-center space-x-2">
          {logsUrl && (
            <button
              onClick={fetchLogs}
              disabled={isStreaming}
              className="glass-button w-8 h-8 rounded-lg flex items-center justify-center text-gray-400 hover:text-white transition-colors"
              title="Refresh logs"
            >
              <i className={`fas fa-sync-alt ${isStreaming ? 'fa-spin' : ''}`}></i>
            </button>
          )}
          <button
            onClick={downloadLogs}
            className="glass-button w-8 h-8 rounded-lg flex items-center justify-center text-gray-400 hover:text-white transition-colors"
            title="Download full logs"
          >
            <i className="fas fa-download"></i>
          </button>
        </div>
      </div>

      <div
        ref={containerRef}
        className="bg-[#0c0c0e]/80 text-gray-300 p-6 font-mono text-xs overflow-y-auto max-h-[500px] custom-scrollbar"
      >
        {localLogs.length === 0 ? (
          <div className="text-gray-600 text-center py-16 flex flex-col items-center">
            <div className="w-12 h-12 rounded-full bg-white/5 flex items-center justify-center mb-3">
              <i className="fas fa-inbox text-xl opacity-50"></i>
            </div>
            <p>No logs available</p>
          </div>
        ) : (
          localLogs.map((log, idx) => {
            const config = levelConfig[log.level];
            return (
              <div key={idx} className="flex items-start space-x-3 mb-1.5 hover:bg-white/5 px-2 py-1 rounded transition-colors group">
                <i className={`fas ${config.icon} ${config.color} mt-0.5 flex-shrink-0 opacity-70 group-hover:opacity-100 transition-opacity`}></i>
                <div className="flex-1 break-all leading-relaxed">
                  <span className="text-gray-600 text-[10px] mr-3 select-none inline-block min-w-[60px]">
                    {new Date(log.timestamp).toLocaleTimeString()}
                  </span>
                  <span className={`${log.level === 'error' ? 'text-red-400' : log.level === 'warning' ? 'text-amber-400' : 'text-gray-300'} font-medium`}>
                    {log.message}
                  </span>
                </div>
              </div>
            );
          })
        )}
        <div ref={logsEndRef} />
      </div>

      {localLogs.length > 0 && (
        <div className="bg-black/60 px-6 py-2 text-[10px] text-gray-500 uppercase tracking-wider font-semibold border-t border-white/5 flex justify-between">
          <span>Total Entries: {localLogs.length}</span>
          <span>Tail: {tail}</span>
        </div>
      )}
    </div>
  );
};