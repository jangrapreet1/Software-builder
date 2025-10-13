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
  logs = [],
  tail = 100,
  autoScroll = true
}) => {
  const [localLogs, setLocalLogs] = useState<LogEntry[]>(logs);
  const [isStreaming, setIsStreaming] = useState(false);
  const logsEndRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    if (autoScroll && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  };

  useEffect(() => {
    setLocalLogs(logs);
    scrollToBottom();
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
          ? data.logs.split('\n').map((line: string, idx: number) => ({
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
    <div className="bg-white rounded-lg shadow-lg overflow-hidden">
      <div className="bg-gray-800 text-white px-4 py-3 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <i className="fas fa-terminal"></i>
          <span className="font-semibold">Console Logs</span>
          {instanceId && (
            <span className="text-xs text-gray-400">({instanceId})</span>
          )}
        </div>
        <div className="flex items-center space-x-2">
          {logsUrl && (
            <button
              onClick={fetchLogs}
              disabled={isStreaming}
              className="px-3 py-1 bg-gray-700 hover:bg-gray-600 rounded text-sm transition disabled:opacity-50"
              title="Refresh logs"
            >
              <i className={`fas fa-sync-alt ${isStreaming ? 'fa-spin' : ''}`}></i>
            </button>
          )}
          <button
            onClick={downloadLogs}
            className="px-3 py-1 bg-gray-700 hover:bg-gray-600 rounded text-sm transition"
            title="Download full logs"
          >
            <i className="fas fa-download"></i>
          </button>
        </div>
      </div>
      
      <div
        ref={containerRef}
        className="bg-gray-900 text-gray-300 p-4 font-mono text-sm overflow-y-auto max-h-96"
      >
        {localLogs.length === 0 ? (
          <div className="text-gray-500 text-center py-8">
            <i className="fas fa-inbox text-3xl mb-2"></i>
            <p>No logs available</p>
          </div>
        ) : (
          localLogs.map((log, idx) => {
            const config = levelConfig[log.level];
            return (
              <div key={idx} className="flex items-start space-x-2 mb-1 hover:bg-gray-800 px-2 py-1 rounded">
                <i className={`fas ${config.icon} ${config.color} mt-1 flex-shrink-0`}></i>
                <div className="flex-1 break-all">
                  <span className="text-gray-500 text-xs mr-2">
                    {new Date(log.timestamp).toLocaleTimeString()}
                  </span>
                  <span className={log.level === 'error' ? 'text-red-400' : 'text-gray-300'}>
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
        <div className="bg-gray-800 px-4 py-2 text-xs text-gray-400 border-t border-gray-700">
          Showing {localLogs.length} log entries (tail: {tail})
        </div>
      )}
    </div>
  );
};