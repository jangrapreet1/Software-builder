import React, { useState } from 'react';

export interface ProblemDetailData {
  id: string;
  category: string;
  severity: string;
  message: string;
  stage?: string;
  risk_level: string;
  suggested_fix: string;
  confidence: number;
  details?: string;
}

interface ProblemDetailProps {
  problem: ProblemDetailData | null;
  onClose: () => void;
  onAttemptFix: (problemId: string) => void;
  isFixing?: boolean;
}

export const ProblemDetail: React.FC<ProblemDetailProps> = ({
  problem,
  onClose,
  onAttemptFix,
  isFixing = false
}) => {
  const [showPermissionModal, setShowPermissionModal] = useState(false);

  if (!problem) return null;

  const getRiskColor = (risk: string) => {
    switch (risk) {
      case 'critical':
        return 'text-red-600 bg-red-50';
      case 'high':
        return 'text-orange-600 bg-orange-50';
      case 'medium':
        return 'text-yellow-600 bg-yellow-50';
      case 'low':
        return 'text-green-600 bg-green-50';
      default:
        return 'text-gray-600 bg-gray-50';
    }
  };

  const handleFixClick = () => {
    if (problem.risk_level === 'low') {
      // Show permission modal for low-risk fixes
      setShowPermissionModal(true);
    } else {
      // High-risk fixes require manual review
      alert('This issue requires manual review due to high risk level.');
    }
  };

  const handleConfirmFix = () => {
    setShowPermissionModal(false);
    onAttemptFix(problem.id);
  };

  return (
    <>
      {/* Main Detail Modal */}
      <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-lg shadow-2xl max-w-3xl w-full max-h-[90vh] overflow-hidden flex flex-col">
          {/* Header */}
          <div className="bg-gradient-to-r from-blue-600 to-purple-600 text-white p-6">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <h2 className="text-2xl font-bold mb-2">Problem Details</h2>
                <div className="flex items-center space-x-3 text-sm">
                  <span className="bg-white bg-opacity-20 px-3 py-1 rounded-full">
                    {problem.category}
                  </span>
                  <span className={`px-3 py-1 rounded-full ${getRiskColor(problem.risk_level)}`}>
                    {problem.risk_level} risk
                  </span>
                </div>
              </div>
              <button
                onClick={onClose}
                className="text-white hover:bg-white hover:bg-opacity-20 rounded-full p-2 transition"
              >
                <i className="fas fa-times text-xl"></i>
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="p-6 overflow-y-auto flex-1">
            {/* Problem Message */}
            <div className="mb-6">
              <h3 className="text-sm font-semibold text-gray-700 mb-2 flex items-center">
                <i className="fas fa-exclamation-circle mr-2 text-red-500"></i>
                Error Message
              </h3>
              <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                <pre className="text-sm text-red-800 whitespace-pre-wrap font-mono">
                  {problem.message}
                </pre>
              </div>
            </div>

            {/* Stage Info */}
            {problem.stage && (
              <div className="mb-6">
                <h3 className="text-sm font-semibold text-gray-700 mb-2">
                  <i className="fas fa-layer-group mr-2"></i>
                  Detection Stage
                </h3>
                <span className="inline-block bg-blue-100 text-blue-800 px-3 py-1 rounded text-sm">
                  {problem.stage}
                </span>
              </div>
            )}

            {/* Suggested Fix */}
            <div className="mb-6">
              <h3 className="text-sm font-semibold text-gray-700 mb-2 flex items-center">
                <i className="fas fa-tools mr-2 text-green-500"></i>
                Suggested Fix
              </h3>
              <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                <p className="text-sm text-green-800">{problem.suggested_fix}</p>
              </div>
            </div>

            {/* Additional Details */}
            {problem.details && (
              <div className="mb-6">
                <h3 className="text-sm font-semibold text-gray-700 mb-2">
                  <i className="fas fa-info-circle mr-2"></i>
                  Additional Details
                </h3>
                <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                  <p className="text-sm text-gray-700">{problem.details}</p>
                </div>
              </div>
            )}

            {/* Confidence & Risk Assessment */}
            <div className="grid grid-cols-2 gap-4 mb-6">
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <div className="text-xs text-blue-600 font-semibold mb-1">Confidence</div>
                <div className="flex items-center">
                  <div className="flex-1 bg-blue-200 rounded-full h-2 mr-2">
                    <div
                      className="bg-blue-600 h-2 rounded-full"
                      style={{ width: `${problem.confidence * 100}%` }}
                    ></div>
                  </div>
                  <span className="text-sm font-semibold text-blue-800">
                    {Math.round(problem.confidence * 100)}%
                  </span>
                </div>
              </div>

              <div className={`border rounded-lg p-4 ${getRiskColor(problem.risk_level)}`}>
                <div className="text-xs font-semibold mb-1">Risk Level</div>
                <div className="text-lg font-bold capitalize">{problem.risk_level}</div>
              </div>
            </div>

            {/* Auto-fix availability */}
            {problem.risk_level === 'low' && (
              <div className="bg-green-50 border border-green-300 rounded-lg p-4 mb-4">
                <div className="flex items-start">
                  <i className="fas fa-magic text-green-600 mt-1 mr-3"></i>
                  <div className="flex-1">
                    <p className="text-sm text-green-800 font-medium">
                      Auto-fix available for this low-risk issue
                    </p>
                    <p className="text-xs text-green-700 mt-1">
                      This fix will be applied in a separate branch for your review
                    </p>
                  </div>
                </div>
              </div>
            )}

            {problem.risk_level !== 'low' && (
              <div className="bg-yellow-50 border border-yellow-300 rounded-lg p-4 mb-4">
                <div className="flex items-start">
                  <i className="fas fa-hand-paper text-yellow-600 mt-1 mr-3"></i>
                  <div className="flex-1">
                    <p className="text-sm text-yellow-800 font-medium">
                      Manual review required
                    </p>
                    <p className="text-xs text-yellow-700 mt-1">
                      This issue has {problem.risk_level} risk and requires manual intervention
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Footer Actions */}
          <div className="bg-gray-50 px-6 py-4 flex items-center justify-end space-x-3 border-t">
            <button
              onClick={onClose}
              className="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition"
            >
              Close
            </button>
            {problem.risk_level === 'low' && (
              <button
                onClick={handleFixClick}
                disabled={isFixing}
                className="px-6 py-2 bg-gradient-to-r from-green-600 to-green-700 hover:from-green-700 hover:to-green-800 disabled:from-gray-400 disabled:to-gray-500 text-white font-semibold rounded-lg transition flex items-center"
              >
                {isFixing ? (
                  <>
                    <i className="fas fa-spinner fa-spin mr-2"></i>
                    Fixing...
                  </>
                ) : (
                  <>
                    <i className="fas fa-magic mr-2"></i>
                    Attempt Auto-Fix
                  </>
                )}
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Permission Modal */}
      {showPermissionModal && (
        <div className="fixed inset-0 bg-black bg-opacity-70 z-[60] flex items-center justify-center p-4">
          <div className="bg-white rounded-lg shadow-2xl max-w-md w-full">
            <div className="bg-blue-600 text-white p-4 rounded-t-lg">
              <h3 className="text-lg font-bold flex items-center">
                <i className="fas fa-shield-alt mr-2"></i>
                Confirm Auto-Fix
              </h3>
            </div>

            <div className="p-6">
              <p className="text-gray-700 mb-4">
                This will attempt to automatically fix the issue:
              </p>
              <div className="bg-gray-50 border border-gray-200 rounded p-3 mb-4">
                <p className="text-sm font-mono text-gray-800">{problem.suggested_fix}</p>
              </div>
              <div className="bg-blue-50 border border-blue-200 rounded p-3 mb-4">
                <p className="text-xs text-blue-800">
                  <i className="fas fa-info-circle mr-1"></i>
                  Changes will be made in a new branch: <code>auto/fix-{problem.category}-*</code>
                </p>
              </div>

              <p className="text-sm text-gray-600">
                Do you want to proceed with this automated fix?
              </p>
            </div>

            <div className="bg-gray-50 px-6 py-4 flex justify-end space-x-3 rounded-b-lg">
              <button
                onClick={() => setShowPermissionModal(false)}
                className="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded hover:bg-gray-50 transition"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmFix}
                className="px-6 py-2 bg-green-600 hover:bg-green-700 text-white font-semibold rounded transition"
              >
                <i className="fas fa-check mr-2"></i>
                Confirm Fix
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
