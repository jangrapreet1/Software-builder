import React, { useState } from 'react';

interface TestingPanelProps {
  appPath: string;
  onTestComplete: (result: any) => void;
}

export const TestingPanel: React.FC<TestingPanelProps> = ({
  appPath,
  onTestComplete
}) => {
  const [isRunning, setIsRunning] = useState(false);
  const [testResult, setTestResult] = useState<any>(null);
  const [testType, setTestType] = useState('all');
  const [generateMissing, setGenerateMissing] = useState(true);

  const handleRunTests = async () => {
    setIsRunning(true);
    setTestResult(null);

    try {
      const response = await fetch('/api/test/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          app_path: appPath,
          test_type: testType,
          specific_tests: [],
          generate_missing: generateMissing
        })
      });

      const data = await response.json();
      setTestResult(data);
      
      if (onTestComplete) {
        onTestComplete(data);
      }
    } catch (error) {
      console.error('Test execution error:', error);
      setTestResult({
        status: 'error',
        error: String(error)
      });
    } finally {
      setIsRunning(false);
    }
  };

  const getStatusBgClass = (status: string) => {
    switch (status) {
      case 'passed': return 'bg-green-50 border-green-200';
      case 'failed': return 'bg-red-50 border-red-200';
      case 'no_tests': return 'bg-yellow-50 border-yellow-200';
      default: return 'bg-gray-50 border-gray-200';
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center">
        <i className="fas fa-vial mr-2 text-purple-600"></i>
        Testing Agent
      </h3>

      <div className="space-y-4 mb-4">
        <div>
          <label
            htmlFor="testTypeSelect"
            className="block text-sm font-medium text-gray-700 mb-2"
          >
            Test Type
          </label>
          <select
            id="testTypeSelect"
            value={testType}
            onChange={(e) => setTestType(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500"
          >
            <option value="all">All Tests</option>
            <option value="unit">Unit Tests</option>
            <option value="integration">Integration Tests</option>
            <option value="e2e">End-to-End Tests</option>
          </select>
        </div>

        <div className="flex items-center space-x-2">
          <input
            type="checkbox"
            id="generateMissing"
            checked={generateMissing}
            onChange={(e) => setGenerateMissing(e.target.checked)}
            className="rounded text-purple-600 focus:ring-purple-500"
          />
          <label htmlFor="generateMissing" className="text-sm text-gray-700">
            Generate missing tests automatically
          </label>
        </div>
      </div>

      <button
        onClick={handleRunTests}
        disabled={isRunning}
        className="w-full bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 disabled:from-gray-400 disabled:to-gray-500 text-white font-semibold py-3 px-4 rounded-lg transition flex items-center justify-center space-x-2"
      >
        {isRunning ? (
          <>
            <i className="fas fa-spinner fa-spin"></i>
            <span>Running Tests...</span>
          </>
        ) : (
          <>
            <i className="fas fa-play"></i>
            <span>Run Tests</span>
          </>
        )}
      </button>

      {testResult && (
        <div className="mt-6">
          {/* Status Badge */}
          <div className={`p-4 rounded-lg mb-4 border ${getStatusBgClass(testResult.status)}`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <i className={`fas ${
                  testResult.status === 'passed' ? 'fa-check-circle text-green-600' :
                  testResult.status === 'failed' ? 'fa-times-circle text-red-600' :
                  'fa-exclamation-circle text-yellow-600'
                }`}></i>
                <span className="font-semibold">
                  {testResult.status === 'passed' && 'All Tests Passed'}
                  {testResult.status === 'failed' && 'Some Tests Failed'}
                  {testResult.status === 'no_tests' && 'No Tests Found'}
                  {testResult.status === 'error' && 'Test Error'}
                </span>
              </div>
              {testResult.summary && (
                <div className="text-sm font-semibold">
                  {testResult.summary.success_rate}% Success
                </div>
              )}
            </div>
          </div>

          {/* Test Summary */}
          {testResult.summary && (
            <div className="grid grid-cols-2 gap-4 mb-4">
              <div className="bg-gray-50 p-3 rounded-lg">
                <div className="text-xs text-gray-500 mb-1">Total Tests</div>
                <div className="text-2xl font-bold text-gray-800">{testResult.summary.total_tests}</div>
              </div>
              <div className="bg-green-50 p-3 rounded-lg">
                <div className="text-xs text-green-600 mb-1">Passed</div>
                <div className="text-2xl font-bold text-green-700">{testResult.summary.passed}</div>
              </div>
              <div className="bg-red-50 p-3 rounded-lg">
                <div className="text-xs text-red-600 mb-1">Failed</div>
                <div className="text-2xl font-bold text-red-700">{testResult.summary.failed}</div>
              </div>
              <div className="bg-yellow-50 p-3 rounded-lg">
                <div className="text-xs text-yellow-600 mb-1">Skipped</div>
                <div className="text-2xl font-bold text-yellow-700">{testResult.summary.skipped}</div>
              </div>
            </div>
          )}

          {/* Execution Time */}
          {testResult.summary?.execution_time && (
            <div className="mb-4 text-sm text-gray-600">
              <i className="fas fa-clock mr-2"></i>
              Execution Time: {testResult.summary.execution_time.toFixed(2)}s
            </div>
          )}

          {/* Failures */}
          {testResult.failures && testResult.failures.length > 0 && (
            <div className="mb-4">
              <h4 className="font-semibold text-gray-700 text-sm mb-2">
                Failed Tests ({testResult.failures.length}):
              </h4>
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {testResult.failures.map((failure: any, idx: number) => (
                  <div key={idx} className="bg-red-50 border-l-4 border-red-500 p-3 rounded">
                    <div className="font-mono text-xs text-red-800 font-semibold">
                      {failure.test}
                    </div>
                    <div className="text-xs text-red-600 mt-1">
                      {failure.message}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Coverage */}
          {testResult.coverage && (
            <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-blue-800">Code Coverage</span>
                <span className="text-lg font-bold text-blue-600">{testResult.coverage.total}%</span>
              </div>
              <progress
                value={Math.min(Math.max(testResult.coverage.total, 0), 100)}
                max={100}
                className="mt-2 w-full h-2 overflow-hidden rounded-full bg-blue-200 [&::-webkit-progress-bar]:bg-blue-200 [&::-webkit-progress-value]:bg-blue-600 [&::-moz-progress-bar]:bg-blue-600"
              />
            </div>
          )}

          {/* Recommendations */}
          {testResult.recommendations && testResult.recommendations.length > 0 && (
            <div className="p-3 bg-indigo-50 border border-indigo-200 rounded-lg">
              <div className="font-semibold text-indigo-800 text-sm mb-2">
                <i className="fas fa-lightbulb mr-2"></i>
                Recommendations:
              </div>
              <ul className="list-disc list-inside text-sm text-indigo-700 space-y-1">
                {testResult.recommendations.map((rec: string, idx: number) => (
                  <li key={idx}>{rec}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Generated Tests Info */}
          {testResult.generated_tests?.success && (
            <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded-lg">
              <div className="flex items-start space-x-2">
                <i className="fas fa-magic text-green-600 mt-1"></i>
                <div className="flex-1">
                  <div className="font-semibold text-green-800 text-sm">
                    Generated {testResult.generated_tests.files_created?.length || 0} Test Files
                  </div>
                  {testResult.generated_tests.files_created && (
                    <ul className="text-xs text-green-700 mt-1 space-y-1">
                      {testResult.generated_tests.files_created.map((file: string, idx: number) => (
                        <li key={idx} className="font-mono">{file}</li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Framework Info */}
          {testResult.framework && (
            <div className="mt-4 text-xs text-gray-500">
              Framework: <span className="font-semibold">{testResult.framework}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
