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
        return 'bg-red-100 border-red-500 text-red-800';
      case 'high':
        return 'bg-orange-100 border-orange-500 text-orange-800';
      case 'medium':
        return 'bg-yellow-100 border-yellow-500 text-yellow-800';
      case 'low':
        return 'bg-blue-100 border-blue-500 text-blue-800';
      default:
        return 'bg-gray-100 border-gray-500 text-gray-800';
    }
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'fa-exclamation-circle';
      case 'high':
        return 'fa-exclamation-triangle';
      case 'medium':
        return 'fa-info-circle';
      case 'low':
        return 'fa-check-circle';
      default:
        return 'fa-circle';
    }
  };

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow-lg p-6">
        <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center">
          <i className="fas fa-list-ul mr-2 text-blue-600"></i>
          Detected Problems
        </h3>
        <div className="flex items-center justify-center py-8">
          <i className="fas fa-spinner fa-spin text-3xl text-blue-600"></i>
          <span className="ml-3 text-gray-600">Loading problems...</span>
        </div>
      </div>
    );
  }

  if (problems.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-lg p-6">
        <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center">
          <i className="fas fa-list-ul mr-2 text-blue-600"></i>
          Detected Problems
        </h3>
        <div className="text-center py-8">
          <i className="fas fa-check-circle text-5xl text-green-500 mb-3"></i>
          <p className="text-gray-600">No problems detected</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-800 flex items-center">
          <i className="fas fa-list-ul mr-2 text-blue-600"></i>
          Detected Problems
        </h3>
        <span className="bg-blue-100 text-blue-800 text-xs font-semibold px-3 py-1 rounded-full">
          {problems.length} {problems.length === 1 ? 'issue' : 'issues'}
        </span>
      </div>

      <div className="space-y-3 max-h-96 overflow-y-auto">
        {problems.map((problem) => (
          <div
            key={problem.id}
            className={`border-l-4 rounded-lg p-4 cursor-pointer hover:shadow-md transition ${getSeverityColor(
              problem.severity
            )}`}
            onClick={() => onViewDetails(problem.id)}
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center space-x-2 mb-2">
                  <i className={`fas ${getSeverityIcon(problem.severity)}`}></i>
                  <span className="text-xs font-semibold uppercase">{problem.severity}</span>
                  <span className="text-xs bg-white bg-opacity-50 px-2 py-0.5 rounded">
                    {problem.category}
                  </span>
                </div>
                <p className="text-sm font-medium mb-1">{problem.summary}</p>
                <div className="flex items-center space-x-3 text-xs">
                  <span>
                    <i className="fas fa-certificate mr-1"></i>
                    Confidence: {Math.round(problem.confidence * 100)}%
                  </span>
                  {problem.timestamp && (
                    <span>
                      <i className="fas fa-clock mr-1"></i>
                      {new Date(problem.timestamp).toLocaleTimeString()}
                    </span>
                  )}
                </div>
              </div>
              <button
                className="ml-4 text-sm font-semibold hover:underline"
                onClick={(e) => {
                  e.stopPropagation();
                  onViewDetails(problem.id);
                }}
              >
                View Details →
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
