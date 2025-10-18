import React, { useState, useEffect } from 'react';

interface SessionContextPanelProps {
  sessionToken?: string;
}

interface SessionContext {
  session_token: string;
  instance_id: string;
  build_id?: string;
  created_at: string;
  expires_at: string;
  active: boolean;
  approved_commands: string[];
  detection_data: any;
  agent_outputs: any[];
  workflow_state?: string;
  metadata: any;
}

export const SessionContextPanel: React.FC<SessionContextPanelProps> = ({
  sessionToken
}) => {
  const [context, setContext] = useState<SessionContext | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    if (sessionToken) {
      fetchSessionContext();
    }
  }, [sessionToken]);

  const fetchSessionContext = async () => {
    if (!sessionToken) return;

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`/api/session/${sessionToken}/context`);
      
      if (!response.ok) {
        throw new Error(`Failed to fetch session context: ${response.statusText}`);
      }

      const data = await response.json();
      setContext(data.context);
    } catch (err: any) {
      console.error('Error fetching session context:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString: string) => {
    try {
      return new Date(dateString).toLocaleString();
    } catch {
      return dateString;
    }
  };

  const getTimeRemaining = (expiresAt: string) => {
    try {
      const expiry = new Date(expiresAt);
      const now = new Date();
      const diffMs = expiry.getTime() - now.getTime();
      
      if (diffMs < 0) return 'Expired';
      
      const minutes = Math.floor(diffMs / 60000);
      const hours = Math.floor(minutes / 60);
      
      if (hours > 0) {
        return `${hours}h ${minutes % 60}m remaining`;
      }
      return `${minutes}m remaining`;
    } catch {
      return 'Unknown';
    }
  };

  if (!sessionToken) {
    return null;
  }

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <i className="fas fa-info-circle text-blue-600"></i>
          <h3 className="text-lg font-semibold text-gray-800">Session Context</h3>
        </div>
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-sm text-blue-600 hover:text-blue-700 flex items-center space-x-1"
        >
          <span>{expanded ? 'Hide Details' : 'Show Details'}</span>
          <i className={`fas fa-chevron-${expanded ? 'up' : 'down'}`}></i>
        </button>
      </div>

      {loading && (
        <div className="text-sm text-gray-600 flex items-center space-x-2">
          <i className="fas fa-spinner fa-spin"></i>
          <span>Loading session context...</span>
        </div>
      )}

      {error && (
        <div className="text-sm text-red-600 flex items-center space-x-2">
          <i className="fas fa-exclamation-triangle"></i>
          <span>{error}</span>
        </div>
      )}

      {context && !loading && (
        <div className="space-y-4">
          {/* Quick Stats */}
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-blue-50 rounded-lg p-3">
              <div className="text-xs text-blue-600 font-medium mb-1">Status</div>
              <div className={`text-sm font-semibold ${context.active ? 'text-green-600' : 'text-gray-600'}`}>
                {context.active ? 'Active' : 'Inactive'}
              </div>
            </div>
            <div className="bg-purple-50 rounded-lg p-3">
              <div className="text-xs text-purple-600 font-medium mb-1">Time Remaining</div>
              <div className="text-sm font-semibold text-purple-700">
                {getTimeRemaining(context.expires_at)}
              </div>
            </div>
          </div>

          {/* Approved Commands Summary */}
          {context.approved_commands.length > 0 && (
            <div className="bg-green-50 border border-green-200 rounded-lg p-3">
              <div className="text-xs text-green-700 font-medium mb-2 flex items-center space-x-2">
                <i className="fas fa-check-circle"></i>
                <span>Approved Commands ({context.approved_commands.length})</span>
              </div>
              <div className="space-y-1">
                {context.approved_commands.slice(0, 3).map((cmd, idx) => (
                  <div key={idx} className="text-xs font-mono text-green-800 bg-white rounded px-2 py-1">
                    {cmd}
                  </div>
                ))}
                {context.approved_commands.length > 3 && (
                  <div className="text-xs text-green-600">
                    +{context.approved_commands.length - 3} more commands
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Expanded Details */}
          {expanded && (
            <div className="space-y-3 pt-3 border-t border-gray-200">
              {/* Session Info */}
              <div>
                <div className="text-xs font-medium text-gray-600 mb-2">Session Details</div>
                <div className="space-y-1 text-xs">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Session Token:</span>
                    <span className="font-mono text-gray-800">{context.session_token}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Instance ID:</span>
                    <span className="font-mono text-gray-800">{context.instance_id}</span>
                  </div>
                  {context.build_id && (
                    <div className="flex justify-between">
                      <span className="text-gray-600">Build ID:</span>
                      <span className="font-mono text-gray-800">{context.build_id}</span>
                    </div>
                  )}
                  <div className="flex justify-between">
                    <span className="text-gray-600">Created:</span>
                    <span className="text-gray-800">{formatDate(context.created_at)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Expires:</span>
                    <span className="text-gray-800">{formatDate(context.expires_at)}</span>
                  </div>
                </div>
              </div>

              {/* Detection Data */}
              {context.detection_data && Object.keys(context.detection_data).length > 0 && (
                <div>
                  <div className="text-xs font-medium text-gray-600 mb-2">Detection Data</div>
                  <div className="bg-gray-50 rounded p-2 text-xs font-mono text-gray-700 max-h-32 overflow-y-auto">
                    {context.detection_data.languages && (
                      <div>Languages: {context.detection_data.languages.confident?.map((l: any) => l.language).join(', ')}</div>
                    )}
                    {context.detection_data.frameworks && (
                      <div>Frameworks: {context.detection_data.frameworks.confident?.join(', ')}</div>
                    )}
                  </div>
                </div>
              )}

              {/* Agent Outputs */}
              {context.agent_outputs.length > 0 && (
                <div>
                  <div className="text-xs font-medium text-gray-600 mb-2">
                    Agent Interactions ({context.agent_outputs.length})
                  </div>
                  <div className="space-y-2">
                    {context.agent_outputs.map((output, idx) => (
                      <div key={idx} className="bg-indigo-50 rounded p-2">
                        <div className="text-xs font-semibold text-indigo-700">
                          {output.agent}
                        </div>
                        <div className="text-xs text-gray-600">
                          {formatDate(output.timestamp)}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Workflow State Link */}
              {context.workflow_state && (
                <div className="bg-yellow-50 border border-yellow-200 rounded p-2">
                  <div className="text-xs text-yellow-800 flex items-center space-x-2">
                    <i className="fas fa-link"></i>
                    <span>Linked to workflow state: {context.workflow_state}</span>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
