import React, { useState, useEffect } from 'react';

interface Project {
  name: string;
  path: string;
  status: string;
  has_backend: boolean;
  has_frontend: boolean;
}

interface TesterTabProps {
  selectedProject: Project | null;
  onProjectSelect: (project: Project) => void;
  projects: Project[];
  addNotification: (notification: any) => void;
}

interface TestResult {
  status: string;
  timestamp: string;
  framework: string;
  summary: {
    total_tests: number;
    passed: number;
    failed: number;
    skipped: number;
    success_rate: number;
    execution_time: number;
  };
  failures: Array<{
    test: string;
    message: string;
  }>;
  recommendations: string[];
  output: {
    stdout: string;
    stderr: string;
  };
}

export const TesterTab: React.FC<TesterTabProps> = ({
  selectedProject,
  onProjectSelect,
  projects,
  addNotification
}) => {
  const [testResult, setTestResult] = useState<TestResult | null>(null);
  const [testing, setTesting] = useState(false);
  const [autoFixing, setAutoFixing] = useState(false);
  const [testType, setTestType] = useState<'all' | 'unit' | 'integration' | 'e2e'>('all');
  const [generateMissing, setGenerateMissing] = useState(true);
  const [testHistory, setTestHistory] = useState<TestResult[]>([]);

  // Load test history on mount
  useEffect(() => {
    loadTestHistory();
  }, []);

  const loadTestHistory = async () => {
    try {
      const response = await fetch('/api/test/history');
      const data = await response.json();
      setTestHistory(data.history || []);
    } catch (error) {
      console.error('Failed to load test history:', error);
    }
  };

  const handleRunTests = async () => {
    if (!selectedProject) {
      addNotification({
        type: 'warning',
        title: 'No Project Selected',
        message: 'Please select a project first',
        duration: 3000
      });
      return;
    }

    try {
      setTesting(true);
      setTestResult(null);

      const response = await fetch('/api/test/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_path: selectedProject.path,
          test_type: testType,
          generate_missing: generateMissing
        })
      });

      const result = await response.json();
      setTestResult(result);

      // Auto-fix if tests failed
      if (result.status === 'failed' && result.summary.failed > 0) {
        addNotification({
          type: 'warning',
          title: 'Tests Failed',
          message: `${result.summary.failed} test(s) failed. Attempting auto-fix...`,
          duration: 5000
        });
        
        await triggerAutoFix(result);
      } else if (result.status === 'passed') {
        addNotification({
          type: 'success',
          title: 'All Tests Passed!',
          message: `${result.summary.passed} test(s) passed successfully`,
          duration: 5000
        });
      } else if (result.status === 'no_tests') {
        addNotification({
          type: 'info',
          title: 'No Tests Found',
          message: generateMissing ? 'Generated basic tests automatically' : 'No tests available',
          duration: 5000
        });
      }

      // Reload history
      await loadTestHistory();
    } catch (error) {
      console.error('Failed to run tests:', error);
      addNotification({
        type: 'error',
        title: 'Testing Failed',
        message: 'Failed to run tests',
        duration: 5000
      });
    } finally {
      setTesting(false);
    }
  };

  const triggerAutoFix = async (result: TestResult) => {
    setAutoFixing(true);
    
    try {
      // Route failures to appropriate agents
      for (const failure of result.failures) {
        addNotification({
          type: 'info',
          title: 'Auto-Fixing',
          message: `Routing ${failure.test} to appropriate agent for fixing...`,
          duration: 3000
        });
      }

      // Wait a moment then re-run tests
      setTimeout(async () => {
        addNotification({
          type: 'info',
          title: 'Retesting',
          message: 'Running tests again after fixes...',
          duration: 3000
        });
        
        await handleRunTests();
      }, 5000);
    } finally {
      setAutoFixing(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'passed': return 'text-green-600 bg-green-50 border-green-200';
      case 'failed': return 'text-red-600 bg-red-50 border-red-200';
      case 'no_tests': return 'text-gray-600 bg-gray-50 border-gray-200';
      default: return 'text-blue-600 bg-blue-50 border-blue-200';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'passed': return 'fa-check-circle';
      case 'failed': return 'fa-times-circle';
      case 'no_tests': return 'fa-info-circle';
      default: return 'fa-question-circle';
    }
  };

  return (
    <div className="space-y-6">
      {/* Project Selector */}
      <div className="bg-white rounded-2xl shadow-xl p-6">
        <h2 className="text-xl font-bold text-gray-800 mb-4 flex items-center">
          <i className="fas fa-folder-tree mr-3 text-purple-600"></i>
          Select Project to Test
        </h2>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {projects.length === 0 ? (
            <div className="col-span-full text-center py-8 text-gray-500">
              <i className="fas fa-inbox text-4xl mb-3"></i>
              <p>No projects available. Create one in the Project Builder tab.</p>
            </div>
          ) : (
            projects.map((project) => (
              <div
                key={project.name}
                onClick={() => onProjectSelect(project)}
                className={`cursor-pointer p-4 rounded-xl border-2 transition-all duration-200 ${
                  selectedProject?.name === project.name
                    ? 'border-purple-500 bg-purple-50 shadow-lg scale-105'
                    : 'border-gray-200 hover:border-purple-300 hover:shadow-md'
                }`}
              >
                <div className="flex items-start justify-between mb-2">
                  <h3 className="font-semibold text-gray-800">{project.name}</h3>
                  <span className={`text-xs px-2 py-1 rounded-full ${
                    project.status === 'ready' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'
                  }`}>
                    {project.status}
                  </span>
                </div>
                <div className="flex items-center space-x-2 text-xs text-gray-600">
                  {project.has_backend && (
                    <span className="flex items-center">
                      <i className="fas fa-server mr-1"></i>
                      Backend
                    </span>
                  )}
                  {project.has_frontend && (
                    <span className="flex items-center">
                      <i className="fas fa-desktop mr-1"></i>
                      Frontend
                    </span>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Test Controls */}
      {selectedProject && (
        <div className="bg-white rounded-2xl shadow-xl p-6">
          <h2 className="text-xl font-bold text-gray-800 mb-4 flex items-center">
            <i className="fas fa-cog mr-3 text-purple-600"></i>
            Test Configuration
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Test Type
              </label>
              <select
                value={testType}
                onChange={(e) => setTestType(e.target.value as any)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500"
                aria-label="Select test type"
              >
                <option value="all">All Tests</option>
                <option value="unit">Unit Tests</option>
                <option value="integration">Integration Tests</option>
                <option value="e2e">End-to-End Tests</option>
              </select>
            </div>

            <div className="flex items-center">
              <label className="flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={generateMissing}
                  onChange={(e) => setGenerateMissing(e.target.checked)}
                  className="w-5 h-5 text-purple-600 rounded focus:ring-2 focus:ring-purple-500"
                />
                <span className="ml-3 text-sm font-medium text-gray-700">
                  Auto-generate missing tests
                </span>
              </label>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <button
              onClick={handleRunTests}
              disabled={testing || autoFixing}
              className="bg-purple-600 hover:bg-purple-700 disabled:bg-gray-400 text-white px-8 py-3 rounded-lg font-semibold transition flex items-center shadow-lg"
            >
              {testing ? (
                <>
                  <i className="fas fa-spinner fa-spin mr-2"></i>
                  Running Tests...
                </>
              ) : (
                <>
                  <i className="fas fa-vial mr-2"></i>
                  Run Tests
                </>
              )}
            </button>

            {autoFixing && (
              <span className="flex items-center text-orange-600 font-medium">
                <i className="fas fa-magic fa-spin mr-2"></i>
                AI Agent is fixing issues...
              </span>
            )}
          </div>
        </div>
      )}

      {/* Test Results */}
      {testResult && (
        <div className="bg-white rounded-2xl shadow-xl overflow-hidden">
          <div className={`px-6 py-4 border-b-2 ${getStatusColor(testResult.status)}`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <i className={`fas ${getStatusIcon(testResult.status)} text-2xl`}></i>
                <div>
                  <h3 className="font-bold text-lg">Test Results</h3>
                  <p className="text-sm opacity-80">
                    Framework: {testResult.framework} | 
                    Execution time: {testResult.summary.execution_time.toFixed(2)}s
                  </p>
                </div>
              </div>
              <span className="text-3xl font-bold">
                {testResult.summary.success_rate.toFixed(1)}%
              </span>
            </div>
          </div>

          <div className="p-6">
            {/* Summary Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              <div className="bg-blue-50 rounded-lg p-4 text-center">
                <div className="text-3xl font-bold text-blue-600">{testResult.summary.total_tests}</div>
                <div className="text-sm text-gray-600">Total Tests</div>
              </div>
              <div className="bg-green-50 rounded-lg p-4 text-center">
                <div className="text-3xl font-bold text-green-600">{testResult.summary.passed}</div>
                <div className="text-sm text-gray-600">Passed</div>
              </div>
              <div className="bg-red-50 rounded-lg p-4 text-center">
                <div className="text-3xl font-bold text-red-600">{testResult.summary.failed}</div>
                <div className="text-sm text-gray-600">Failed</div>
              </div>
              <div className="bg-gray-50 rounded-lg p-4 text-center">
                <div className="text-3xl font-bold text-gray-600">{testResult.summary.skipped}</div>
                <div className="text-sm text-gray-600">Skipped</div>
              </div>
            </div>

            {/* Failures */}
            {testResult.failures.length > 0 && (
              <div className="mb-6">
                <h4 className="font-bold text-red-600 mb-3 flex items-center">
                  <i className="fas fa-exclamation-triangle mr-2"></i>
                  Failed Tests ({testResult.failures.length})
                </h4>
                <div className="space-y-2">
                  {testResult.failures.map((failure, index) => (
                    <div key={index} className="bg-red-50 border-l-4 border-red-500 p-3 rounded">
                      <div className="font-medium text-red-800">{failure.test}</div>
                      <div className="text-sm text-red-700 mt-1">{failure.message}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Recommendations */}
            {testResult.recommendations.length > 0 && (
              <div className="mb-6">
                <h4 className="font-bold text-blue-600 mb-3 flex items-center">
                  <i className="fas fa-lightbulb mr-2"></i>
                  Recommendations
                </h4>
                <ul className="space-y-2">
                  {testResult.recommendations.map((rec, index) => (
                    <li key={index} className="flex items-start space-x-2">
                      <i className="fas fa-check text-blue-500 mt-1"></i>
                      <span className="text-gray-700">{rec}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Output Logs */}
            <details className="bg-gray-50 rounded-lg p-4">
              <summary className="font-semibold text-gray-700 cursor-pointer flex items-center">
                <i className="fas fa-terminal mr-2"></i>
                View Test Output
              </summary>
              <pre className="mt-3 text-xs bg-gray-900 text-green-400 p-4 rounded overflow-x-auto max-h-64">
                {testResult.output.stdout || 'No output available'}
              </pre>
              {testResult.output.stderr && (
                <pre className="mt-2 text-xs bg-red-900 text-red-200 p-4 rounded overflow-x-auto max-h-64">
                  {testResult.output.stderr}
                </pre>
              )}
            </details>
          </div>
        </div>
      )}

      {/* Test History */}
      {testHistory.length > 0 && (
        <div className="bg-white rounded-2xl shadow-xl p-6">
          <h2 className="text-xl font-bold text-gray-800 mb-4 flex items-center">
            <i className="fas fa-history mr-3 text-purple-600"></i>
            Test History
          </h2>
          
          <div className="space-y-3">
            {testHistory.slice(0, 5).map((result, index) => (
              <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition">
                <div className="flex items-center space-x-3">
                  <i className={`fas ${getStatusIcon(result.status)} ${getStatusColor(result.status)}`}></i>
                  <div>
                    <div className="font-medium text-gray-800">{result.framework}</div>
                    <div className="text-xs text-gray-500">
                      {new Date(result.timestamp).toLocaleString()}
                    </div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="font-bold text-gray-800">{result.summary.success_rate.toFixed(1)}%</div>
                  <div className="text-xs text-gray-600">
                    {result.summary.passed}/{result.summary.total_tests} passed
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* No Project Selected State */}
      {!selectedProject && (
        <div className="bg-white rounded-2xl shadow-xl p-12 text-center">
          <i className="fas fa-hand-pointer text-6xl text-gray-300 mb-4"></i>
          <h3 className="text-xl font-bold text-gray-700 mb-2">No Project Selected</h3>
          <p className="text-gray-500">Select a project above to run tests</p>
        </div>
      )}
    </div>
  );
};
