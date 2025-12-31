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
    <div className="glass-panel rounded-2xl overflow-hidden border border-primary/30 shadow-[0_0_20px_rgba(99,102,241,0.15)] relative">
      <div className="absolute top-0 right-0 w-64 h-64 bg-primary/10 rounded-full blur-3xl -z-10 pointer-events-none"></div>

      {/* Header */}
      <div className="bg-primary/10 p-5 border-b border-white/10">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center space-x-3 mb-2">
              <div className="w-8 h-8 rounded-lg bg-primary/20 flex items-center justify-center border border-primary/30">
                <i className="fas fa-code-branch text-primary text-sm"></i>
              </div>
              <h3 className="text-lg font-bold text-white">Pull Request Created</h3>
              {pr.validation.passed ? (
                <span className="bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full">
                  <i className="fas fa-check mr-1"></i>Validated
                </span>
              ) : (
                <span className="bg-red-500/10 text-red-300 border border-red-500/20 text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full">
                  <i className="fas fa-times mr-1"></i>Failed
                </span>
              )}
            </div>
            <p className="text-gray-300 text-sm pl-11">{pr.summary}</p>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="p-6 space-y-6">
        {/* Branch & Commit Info */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-black/20 rounded-xl p-4 border border-white/5">
            <div className="text-[10px] uppercase tracking-wider text-gray-500 font-bold mb-1.5">Branch</div>
            <div className="flex items-center group cursor-pointer hover:bg-white/5 p-1 -ml-1 rounded transition-colors">
              <i className="fas fa-code-branch text-gray-500 mr-2 group-hover:text-primary transition-colors"></i>
              <code className="text-sm font-mono text-primary group-hover:text-white transition-colors">{pr.branch}</code>
            </div>
          </div>

          {pr.commitHash && (
            <div className="bg-black/20 rounded-xl p-4 border border-white/5">
              <div className="text-[10px] uppercase tracking-wider text-gray-500 font-bold mb-1.5">Commit</div>
              <div className="flex items-center group cursor-pointer hover:bg-white/5 p-1 -ml-1 rounded transition-colors">
                <i className="fas fa-hashtag text-gray-500 mr-2 group-hover:text-primary transition-colors"></i>
                <code className="text-sm font-mono text-primary group-hover:text-white transition-colors">
                  {pr.commitHash.substring(0, 8)}
                </code>
              </div>
            </div>
          )}
        </div>

        {/* Repairs Summary */}
        <div>
          <h4 className="text-sm font-bold text-white mb-3 flex items-center">
            <i className="fas fa-wrench mr-2 text-gray-400"></i>
            Changes Applied
          </h4>
          <div className="space-y-2">
            {successfulRepairs.map((repair, idx) => (
              <div
                key={idx}
                className="flex items-start bg-emerald-500/5 border border-emerald-500/10 rounded-xl p-3"
              >
                <div className="w-5 h-5 rounded-full bg-emerald-500/20 flex items-center justify-center mr-3 mt-0.5 flex-shrink-0">
                  <i className="fas fa-check text-emerald-400 text-xs"></i>
                </div>
                <span className="text-sm text-emerald-100/80 flex-1">{repair.action}</span>
              </div>
            ))}
            {failedRepairs.map((repair, idx) => (
              <div
                key={idx}
                className="flex items-start bg-red-500/5 border border-red-500/10 rounded-xl p-3"
              >
                <div className="w-5 h-5 rounded-full bg-red-500/20 flex items-center justify-center mr-3 mt-0.5 flex-shrink-0">
                  <i className="fas fa-times text-red-400 text-xs"></i>
                </div>
                <span className="text-sm text-red-100/80 flex-1">{repair.action}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Validation Result */}
        <div>
          <h4 className="text-sm font-bold text-white mb-3 flex items-center">
            <i className="fas fa-clipboard-check mr-2 text-gray-400"></i>
            Validation Result
          </h4>
          <div
            className={`rounded-xl p-4 border ${pr.validation.passed
                ? 'bg-emerald-500/5 border-emerald-500/20'
                : 'bg-red-500/5 border-red-500/20'
              }`}
          >
            <div className="flex items-center mb-2">
              <i
                className={`fas ${pr.validation.passed ? 'fa-check-circle text-emerald-400' : 'fa-times-circle text-red-400'
                  } mr-2 text-lg`}
              ></i>
              <span
                className={`text-sm font-bold ${pr.validation.passed ? 'text-emerald-100' : 'text-red-100'
                  }`}
              >
                {pr.validation.passed ? 'Build Successful' : 'Build Failed'}
              </span>
            </div>

            {pr.validation.buildOutput && (
              <details className="text-xs group mt-2">
                <summary className="cursor-pointer text-gray-400 hover:text-white transition-colors font-medium select-none">
                  View build output
                  <i className="fas fa-chevron-down ml-1 group-open:rotate-180 transition-transform"></i>
                </summary>
                <pre className="mt-2 bg-black/40 p-3 rounded-lg border border-white/5 overflow-x-auto max-h-32 text-gray-300 font-mono scrollbar-thin">
                  {pr.validation.buildOutput}
                </pre>
              </details>
            )}

            {pr.validation.errors && (
              <div className="mt-3 text-xs text-red-200 bg-red-500/10 p-3 rounded-lg border border-red-500/20">
                <strong className="block mb-1 text-red-100">Errors:</strong>
                <pre className="overflow-x-auto font-mono opacity-80 whitespace-pre-wrap">{pr.validation.errors}</pre>
              </div>
            )}
          </div>
        </div>

        {/* Preview URL */}
        {pr.validation.previewUrl && (
          <div className="glass-panel p-4 rounded-xl border border-blue-500/20 relative overflow-hidden group">
            <div className="absolute inset-0 bg-blue-500/5 group-hover:bg-blue-500/10 transition-colors"></div>
            <div className="flex items-center justify-between relative z-10">
              <div className="flex-1 min-w-0 mr-4">
                <div className="text-[10px] text-blue-300 font-bold uppercase tracking-wider mb-1">Preview URL</div>
                <code className="text-sm text-blue-100 truncate block opacity-80 group-hover:opacity-100 transition-opacity">{pr.validation.previewUrl}</code>
              </div>
              <button
                onClick={() => onOpenPreview?.(pr.validation.previewUrl!)}
                className="glass-button bg-blue-500/20 hover:bg-blue-500/30 text-blue-200 hover:text-white px-4 py-2 rounded-lg flex items-center space-x-2 transition-all"
              >
                <span>Open</span>
                <i className="fas fa-external-link-alt text-xs"></i>
              </button>
            </div>
          </div>
        )}

        {/* Timestamp */}
        {pr.timestamp && (
          <div className="pt-4 border-t border-white/5 text-xs text-gray-500 flex items-center justify-end">
            <i className="far fa-clock mr-1.5 opacity-70"></i>
            Created {new Date(pr.timestamp).toLocaleString()}
          </div>
        )}
      </div>

      {/* Footer Actions */}
      <div className="bg-black/20 px-6 py-4 border-t border-white/5 flex items-center justify-between backdrop-blur-sm">
        <div className="flex items-center text-sm">
          <span className="text-gray-400">
            <span className="text-white font-bold">{successfulRepairs.length}</span> <span className="opacity-50">/</span> <span className="opacity-70">{pr.repairs.length} fixes applied</span>
          </span>
        </div>
        <div className="flex items-center">
          <a
            href={pr.prUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="group px-5 py-2.5 bg-gradient-to-r from-primary to-accent hover:from-primary/90 hover:to-accent/90 text-white text-sm font-bold rounded-xl shadow-lg shadow-primary/20 transition-all transform hover:scale-105 flex items-center"
          >
            <i className="fab fa-github mr-2 group-hover:rotate-12 transition-transform"></i>
            View Pull Request
          </a>
        </div>
      </div>
    </div>
  );
};
