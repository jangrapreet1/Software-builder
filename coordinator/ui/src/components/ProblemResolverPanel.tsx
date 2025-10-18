import React, { useState } from 'react';

interface ProblemResolverPanelProps {
  appPath: string;
  onResolve: (result: any) => void;
}

export const ProblemResolverPanel: React.FC<ProblemResolverPanelProps> = ({
  appPath,
  onResolve
}) => {
  const [isResolving, setIsResolving] = useState(false);
  const [resolutionResult, setResolutionResult] = useState<any>(null);
  const [errorLogs, setErrorLogs] = useState('');

  const handleResolve = async () => {
    setIsResolving(true);
    setResolutionResult(null);

    try {
      const response = await fetch('/api/resolve/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          app_path: appPath,
          error_logs: errorLogs || null,
          auto_fix: true
        })
      });

      const data = await response.json();
      setResolutionResult(data.result);
      
      if (onResolve) {
        onResolve(data.result);
      }
    } catch (error) {
      console.error('Resolution error:', error);
      setResolutionResult({
        status: 'error',
        error: String(error)
      });
    } finally {
      setIsResolving(false);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center">
        <i className="fas fa-tools mr-2 text-blue-600"></i>
        Problem Resolver
      </h3>

      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Error Logs (Optional)
        </label>
        <textarea
          value={errorLogs}
          onChange={(e) => setErrorLogs(e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 font-mono text-sm"
          rows={4}
          placeholder="Paste error logs here for better analysis..."
        />
      </div>

      <button
        onClick={handleResolve}
        disabled={isResolving}
        className="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 disabled:from-gray-400 disabled:to-gray-500 text-white font-semibold py-3 px-4 rounded-lg transition flex items-center justify-center space-x-2"
      >
        {isResolving ? (
          <>
            <i className="fas fa-spinner fa-spin"></i>
            <span>Analyzing & Resolving...</span>
          </>
        ) : (
          <>
            <i className="fas fa-magic"></i>
            <span>Auto-Resolve Issues</span>
          </>
        )}
      </button>

      {resolutionResult && (
        <div className="mt-6">
          <div className={`p-4 rounded-lg mb-4 ${
            resolutionResult.status === 'success' 
              ? 'bg-green-50 border border-green-200' 
              : resolutionResult.status === 'partial'
              ? 'bg-yellow-50 border border-yellow-200'
              : 'bg-red-50 border border-red-200'
          }`}>
            <div className="flex items-start space-x-2">
              <i className={`fas mt-1 ${
                resolutionResult.status === 'success'
                  ? 'fa-check-circle text-green-600'
                  : resolutionResult.status === 'partial'
                  ? 'fa-exclamation-triangle text-yellow-600'
                  : 'fa-times-circle text-red-600'
              }`}></i>
              <div className="flex-1">
                <div className="font-semibold mb-1">
                  {resolutionResult.status === 'success' && 'All Issues Resolved'}
                  {resolutionResult.status === 'partial' && 'Partially Resolved'}
                  {resolutionResult.status === 'failed' && 'Resolution Failed'}
                </div>
                <div className="text-sm space-y-1">
                  <div>Issues Found: <span className="font-semibold">{resolutionResult.issues_found || 0}</span></div>
                  <div>Issues Resolved: <span className="font-semibold">{resolutionResult.issues_resolved || 0}</span></div>
                  {resolutionResult.modified_files && resolutionResult.modified_files.length > 0 && (
                    <div>Modified Files: <span className="font-semibold">{resolutionResult.modified_files.length}</span></div>
                  )}
                </div>
              </div>
            </div>
          </div>

          {resolutionResult.resolution_log && resolutionResult.resolution_log.length > 0 && (
            <div className="space-y-2">
              <h4 className="font-semibold text-gray-700 text-sm">Resolution Actions:</h4>
              <div className="max-h-64 overflow-y-auto space-y-2">
                {resolutionResult.resolution_log.map((action: any, idx: number) => (
                  <div
                    key={idx}
                    className={`p-3 rounded-lg text-sm ${
                      action.success
                        ? 'bg-green-50 border-l-4 border-green-500'
                        : 'bg-red-50 border-l-4 border-red-500'
                    }`}
                  >
                    <div className="flex items-start space-x-2">
                      <i className={`fas mt-0.5 ${
                        action.success ? 'fa-check text-green-600' : 'fa-times text-red-600'
                      }`}></i>
                      <div className="flex-1">
                        <div className="font-medium">{action.category}</div>
                        <div className="text-gray-600 text-xs mt-1">{action.action}</div>
                        {action.issue && (
                          <div className="text-gray-500 text-xs mt-1 italic">Issue: {action.issue}</div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {resolutionResult.remaining_issues && resolutionResult.remaining_issues.length > 0 && (
            <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
              <div className="font-semibold text-yellow-800 text-sm mb-2">
                Remaining Issues ({resolutionResult.remaining_issues.length}):
              </div>
              <ul className="list-disc list-inside text-sm text-yellow-700 space-y-1">
                {resolutionResult.remaining_issues.map((issue: any, idx: number) => (
                  <li key={idx}>{issue.issue || issue.message || 'Unknown issue'}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
