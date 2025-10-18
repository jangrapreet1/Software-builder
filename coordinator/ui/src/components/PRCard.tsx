import React from 'react';

export interface PRInfo {
  prUrl: string;
  branch: string;
  commitHash?: string;
  summary: string;
  validation: {
    passed: boolean;
    previewUrl?: string;
    buildOutput?: string;
    errors?: string;
  };
  repairs: Array<{
    success: boolean;
    action: string;
  }>;
  timestamp?: string;
}

interface PRCardProps {
  pr: PRInfo;
  onOpenPreview?: (previewUrl: string) => void;
}

export const PRCard: React.FC<PRCardProps> = ({ pr, onOpenPreview }) => {
  const successfulRepairs = pr.repairs.filter((r) => r.success);
  const failedRepairs = pr.repairs.filter((r) => !r.success);

  return (
    <div className="bg-white rounded-lg shadow-lg border-l-4 border-blue-500 overflow-hidden">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-50 to-purple-50 p-4 border-b">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center space-x-2 mb-2">
              <i className="fas fa-code-branch text-blue-600"></i>
              <h3 className="font-semibold text-gray-800">Pull Request Created</h3>
              {pr.validation.passed && (
                <span className="bg-green-100 text-green-800 text-xs font-semibold px-2 py-1 rounded">
                  <i className="fas fa-check-circle mr-1"></i>
                  Validated
                </span>
              )}
              {!pr.validation.passed && (
                <span className="bg-red-100 text-red-800 text-xs font-semibold px-2 py-1 rounded">
                  <i className="fas fa-times-circle mr-1"></i>
                  Failed
                </span>
              )}
            </div>
            <p className="text-sm text-gray-600">{pr.summary}</p>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="p-4">
        {/* Branch & Commit Info */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-4">
          <div className="bg-gray-50 rounded p-3">
            <div className="text-xs text-gray-600 mb-1">Branch</div>
            <div className="flex items-center">
              <i className="fas fa-code-branch text-gray-500 mr-2"></i>
              <code className="text-sm font-mono text-gray-800">{pr.branch}</code>
            </div>
          </div>

          {pr.commitHash && (
            <div className="bg-gray-50 rounded p-3">
              <div className="text-xs text-gray-600 mb-1">Commit</div>
              <div className="flex items-center">
                <i className="fas fa-hashtag text-gray-500 mr-2"></i>
                <code className="text-sm font-mono text-gray-800">
                  {pr.commitHash.substring(0, 8)}
                </code>
              </div>
            </div>
          )}
        </div>

        {/* Repairs Summary */}
        <div className="mb-4">
          <h4 className="text-sm font-semibold text-gray-700 mb-2">
            <i className="fas fa-wrench mr-2"></i>
            Changes Applied
          </h4>
          <div className="space-y-2">
            {successfulRepairs.map((repair, idx) => (
              <div
                key={idx}
                className="flex items-start bg-green-50 border border-green-200 rounded p-2"
              >
                <i className="fas fa-check text-green-600 mt-1 mr-2"></i>
                <span className="text-sm text-green-800 flex-1">{repair.action}</span>
              </div>
            ))}
            {failedRepairs.map((repair, idx) => (
              <div
                key={idx}
                className="flex items-start bg-red-50 border border-red-200 rounded p-2"
              >
                <i className="fas fa-times text-red-600 mt-1 mr-2"></i>
                <span className="text-sm text-red-800 flex-1">{repair.action}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Validation Result */}
        <div className="mb-4">
          <h4 className="text-sm font-semibold text-gray-700 mb-2">
            <i className="fas fa-clipboard-check mr-2"></i>
            Validation Result
          </h4>
          <div
            className={`rounded-lg p-3 ${
              pr.validation.passed
                ? 'bg-green-50 border border-green-200'
                : 'bg-red-50 border border-red-200'
            }`}
          >
            <div className="flex items-center mb-2">
              <i
                className={`fas ${
                  pr.validation.passed ? 'fa-check-circle text-green-600' : 'fa-times-circle text-red-600'
                } mr-2`}
              ></i>
              <span
                className={`text-sm font-semibold ${
                  pr.validation.passed ? 'text-green-800' : 'text-red-800'
                }`}
              >
                {pr.validation.passed ? 'Build Successful' : 'Build Failed'}
              </span>
            </div>

            {pr.validation.buildOutput && (
              <details className="text-xs">
                <summary className="cursor-pointer text-gray-600 hover:text-gray-800">
                  View build output
                </summary>
                <pre className="mt-2 bg-white p-2 rounded border overflow-x-auto max-h-32">
                  {pr.validation.buildOutput}
                </pre>
              </details>
            )}

            {pr.validation.errors && (
              <div className="mt-2 text-xs text-red-700 bg-white p-2 rounded border border-red-300">
                <strong>Errors:</strong>
                <pre className="mt-1 overflow-x-auto">{pr.validation.errors}</pre>
              </div>
            )}
          </div>
        </div>

        {/* Preview URL */}
        {pr.validation.previewUrl && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-4">
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <div className="text-xs text-blue-600 font-semibold mb-1">Preview URL</div>
                <code className="text-sm text-blue-800">{pr.validation.previewUrl}</code>
              </div>
              <button
                onClick={() => onOpenPreview?.(pr.validation.previewUrl!)}
                className="ml-3 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded transition"
              >
                <i className="fas fa-external-link-alt mr-2"></i>
                Open Preview
              </button>
            </div>
          </div>
        )}

        {/* Timestamp */}
        {pr.timestamp && (
          <div className="text-xs text-gray-500">
            <i className="fas fa-clock mr-1"></i>
            Created {new Date(pr.timestamp).toLocaleString()}
          </div>
        )}
      </div>

      {/* Footer Actions */}
      <div className="bg-gray-50 px-4 py-3 border-t flex items-center justify-between">
        <div className="flex items-center space-x-2 text-sm">
          <span className="text-gray-600">
            {successfulRepairs.length} / {pr.repairs.length} fixes applied
          </span>
        </div>
        <div className="flex items-center space-x-2">
          <a
            href={pr.prUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="px-4 py-2 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white text-sm font-semibold rounded transition flex items-center"
          >
            <i className="fab fa-github mr-2"></i>
            View PR
          </a>
        </div>
      </div>
    </div>
  );
};
