import React from 'react';

export interface Problem {
  id: string;
  summary: string;
  category: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  confidence: number;
  status: string;
  timestamp?: string;
}

interface ProblemsPanelProps {
  problems: Problem[];
  onViewDetails: (problemId: string) => void;
  isLoading?: boolean;
}

export const ProblemsPanel: React.FC<ProblemsPanelProps> = ({
  problems,
  onViewDetails,
  isLoading = false
}) => {
  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'bg-red-500/10 border-red-500/30 text-red-200 hover:bg-red-500/20';
      case 'high':
        return 'bg-orange-500/10 border-orange-500/30 text-orange-200 hover:bg-orange-500/20';
      case 'medium':
        return 'bg-amber-500/10 border-amber-500/30 text-amber-200 hover:bg-amber-500/20';
      case 'low':
        return 'bg-blue-500/10 border-blue-500/30 text-blue-200 hover:bg-blue-500/20';
      default:
        return 'bg-gray-500/10 border-gray-500/30 text-gray-200 hover:bg-gray-500/20';
    }
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'fa-exclamation-circle text-red-400';
      case 'high':
        return 'fa-exclamation-triangle text-orange-400';
      case 'medium':
        return 'fa-info-circle text-amber-400';
      case 'low':
        return 'fa-check-circle text-blue-400';
      default:
        return 'fa-circle text-gray-400';
    }
  };

  if (isLoading) {
    return (
      <div className="glass-panel rounded-2xl p-8 text-center min-h-[300px] flex flex-col items-center justify-center">
        <div className="relative">
          <div className="absolute inset-0 bg-primary/20 blur-xl rounded-full"></div>
          <i className="fas fa-circle-notch fa-spin text-4xl text-primary relative z-10"></i>
        </div>
        <h3 className="text-xl font-bold text-white mt-6 mb-2">Analyzing Application</h3>
        <p className="text-gray-400 animate-pulse">Scanning for issues and vulnerabilities...</p>
      </div>
    );
  }

  if (problems.length === 0) {
    return (
      <div className="glass-panel rounded-2xl p-8 text-center min-h-[200px] flex flex-col items-center justify-center border border-emerald-500/20 shadow-[0_0_30px_rgba(16,185,129,0.1)]">
        <div className="w-16 h-16 rounded-full bg-emerald-500/10 flex items-center justify-center mb-4 border border-emerald-500/20">
          <i className="fas fa-check text-3xl text-emerald-400"></i>
        </div>
        <h3 className="text-xl font-bold text-white mb-2">All Clear</h3>
        <p className="text-gray-400">No issues detected in your application.</p>
      </div>
    );
  }

  return (
    <div className="glass-panel rounded-2xl p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-xl font-bold text-white flex items-center">
          <i className="fas fa-bug mr-3 text-red-400"></i>
          Detected Problems
        </h3>
        <span className="bg-white/5 border border-white/10 text-white text-xs font-bold px-3 py-1.5 rounded-full">
          {problems.length} {problems.length === 1 ? 'Issue' : 'Issues'} Found
        </span>
      </div>

      <div className="space-y-4 max-h-[500px] overflow-y-auto custom-scrollbar pr-2">
        {problems.map((problem) => (
          <div
            key={problem.id}
            className={`border rounded-xl p-5 cursor-pointer transition-all duration-300 group ${getSeverityColor(
              problem.severity
            )}`}
            onClick={() => onViewDetails(problem.id)}
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center space-x-3 mb-3">
                  <i className={`fas ${getSeverityIcon(problem.severity)} text-lg`}></i>
                  <span className="text-[10px] font-bold uppercase tracking-wider opacity-80 border border-current px-2 py-0.5 rounded-full">{problem.severity}</span>
                  <span className="text-[10px] bg-black/20 px-2 py-0.5 rounded text-white/70">
                    {problem.category}
                  </span>
                </div>
                <p className="text-base font-medium mb-3 text-white/90 group-hover:text-white">{problem.summary}</p>
                <div className="flex items-center space-x-4 text-xs opacity-60">
                  <span>
                    <i className="fas fa-crosshairs mr-1.5"></i>
                    Confidence: {Math.round(problem.confidence * 100)}%
                  </span>
                  {problem.timestamp && (
                    <span>
                      <i className="far fa-clock mr-1.5"></i>
                      {new Date(problem.timestamp).toLocaleTimeString()}
                    </span>
                  )}
                </div>
              </div>
              <button
                className="ml-4 w-8 h-8 rounded-full bg-white/10 flex items-center justify-center group-hover:bg-white/20 transition-colors"
                onClick={(e) => {
                  e.stopPropagation();
                  onViewDetails(problem.id);
                }}
              >
                <i className="fas fa-chevron-right text-white/50 group-hover:text-white"></i>
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
