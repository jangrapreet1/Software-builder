import React, { useState } from 'react';
import { ProblemsPanel, Problem } from './ProblemsPanel';
import { ProblemDetail, ProblemDetailData } from './ProblemDetail';
import { PRCard, PRInfo } from './PRCard';
import { PreviewValidation } from './PreviewValidation';

interface EnhancedProblemResolverPanelProps {
  appPath: string;
  onNotification: (type: 'success' | 'error' | 'info' | 'warning', title: string, message: string) => void;
}

export const EnhancedProblemResolverPanel: React.FC<EnhancedProblemResolverPanelProps> = ({
  appPath,
  onNotification
}) => {
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [problems, setProblems] = useState<Problem[]>([]);
  const [selectedProblemId, setSelectedProblemId] = useState<string | null>(null);
  const [problemDetails, setProblemDetails] = useState<ProblemDetailData | null>(null);
  const [isFixing, setIsFixing] = useState(false);
  const [pullRequests, setPullRequests] = useState<PRInfo[]>([]);
  const [currentRunId, setCurrentRunId] = useState<string | null>(null);
  const [buildCommands, setBuildCommands] = useState<string>('npm install && npm run build');
  const [testCommands, setTestCommands] = useState<string>('npm test');
  const [runMode, setRunMode] = useState<'diagnose-only' | 'attempt-fix'>('diagnose-only');

  const handleDiagnose = async () => {
    setIsAnalyzing(true);
    setProblems([]);
    setPullRequests([]);

    try {
      const sessionId = `session-${Date.now()}`;
      
      // Parse commands
      const buildCmd = buildCommands.trim() ? buildCommands.split('&&').map(c => c.trim()) : [];
      const testCmd = testCommands.trim() ? testCommands.split('&&').map(c => c.trim()) : [];

      const response = await fetch('/api/agent/problem-resolver', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          app_path: appPath,
          commands: {
            build: buildCmd,
            test: testCmd
          },
          run_mode: runMode
        })
      });

      const data = await response.json();
      
      if (data.status === 'success') {
        setCurrentRunId(data.runId);
        onNotification('info', 'Analysis Started', 'Problem resolver is analyzing your application...');
        
        // Poll for results
        pollForResults(data.runId);
      } else {
        onNotification('error', 'Analysis Failed', 'Could not start problem resolver');
      }
    } catch (error) {
      console.error('Diagnosis error:', error);
      onNotification('error', 'Analysis Error', String(error));
      setIsAnalyzing(false);
    }
  };

  const pollForResults = async (runId: string) => {
    let attempts = 0;
    const maxAttempts = 60; // 5 minutes with 5-second intervals

    const poll = async () => {
      try {
        const response = await fetch(`/api/agent/problem-resolver/${runId}/result`);
        const data = await response.json();

        if (data.status === 'completed' || data.status === 'failed') {
          // Analysis complete
          setIsAnalyzing(false);
          
          if (data.result) {
            processResults(data.result);
          }
          return;
        }

        // Continue polling if still running
        if (data.status === 'running' && attempts < maxAttempts) {
          attempts++;
          setTimeout(poll, 5000);
        } else if (attempts >= maxAttempts) {
          setIsAnalyzing(false);
          onNotification('warning', 'Analysis Timeout', 'The analysis is taking longer than expected');
        } else {
          // Still pending, continue polling
          attempts++;
          setTimeout(poll, 5000);
        }
      } catch (error) {
        console.error('Polling error:', error);
        setIsAnalyzing(false);
        onNotification('error', 'Polling Error', 'Could not fetch analysis results');
      }
    };

    poll();
  };

  const processResults = (result: any) => {
    // Convert issues to problems
    const detectedProblems: Problem[] = (result.issues || []).map((issue: any) => ({
      id: issue.id,
      summary: issue.message || 'Unknown issue',
      category: issue.category || 'unknown',
      severity: issue.severity || 'medium',
      confidence: issue.confidence || 0.5,
      status: result.status,
      timestamp: result.timestamp
    }));

    setProblems(detectedProblems);

    // If there's a PR, add it
    if (result.prUrl && result.branch) {
      const pr: PRInfo = {
        prUrl: result.prUrl,
        branch: result.branch,
        summary: result.summary || 'Auto-fix applied',
        validation: result.validation || { passed: false },
        repairs: result.repairs || [],
        timestamp: result.timestamp
      };
      setPullRequests([pr]);
    }

    // Notify user
    if (result.status === 'completed' && result.prUrl) {
      onNotification('success', 'Fixes Applied', `Created PR on branch ${result.branch}`);
    } else if (result.status === 'completed') {
      onNotification('success', 'Analysis Complete', `Found ${detectedProblems.length} issues`);
    } else if (result.status === 'escalation_required') {
      onNotification('warning', 'Manual Review Required', 'Some issues require manual intervention');
    }
  };

  const handleViewDetails = (problemId: string) => {
    setSelectedProblemId(problemId);
    
    // Find the problem details from current results
    if (currentRunId) {
      fetch(`/api/agent/problem-resolver/${currentRunId}/result`)
        .then(res => res.json())
        .then(data => {
          if (data.result && data.result.issues) {
            const issue = data.result.issues.find((i: any) => i.id === problemId);
            if (issue) {
              setProblemDetails(issue);
            }
          }
        })
        .catch(err => console.error('Error fetching problem details:', err));
    }
  };

  const handleAttemptFix = async (problemId: string) => {
    setIsFixing(true);

    try {
      // Start a new run in attempt-fix mode for this specific problem
      const sessionId = `fix-session-${Date.now()}`;
      const buildCmd = buildCommands.trim() ? buildCommands.split('&&').map(c => c.trim()) : [];
      const testCmd = testCommands.trim() ? testCommands.split('&&').map(c => c.trim()) : [];

      const response = await fetch('/api/agent/problem-resolver', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          app_path: appPath,
          commands: {
            build: buildCmd,
            test: testCmd
          },
          run_mode: 'attempt-fix'
        })
      });

      const data = await response.json();
      
      if (data.status === 'success') {
        onNotification('info', 'Applying Fix', 'Attempting to fix the issue...');
        setCurrentRunId(data.runId);
        pollForResults(data.runId);
      }
    } catch (error) {
      console.error('Fix error:', error);
      onNotification('error', 'Fix Failed', String(error));
    } finally {
      setIsFixing(false);
      setProblemDetails(null);
      setSelectedProblemId(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Configuration Panel */}
      <div className="bg-white rounded-lg shadow-lg p-6">
        <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center">
          <i className="fas fa-cog mr-2 text-blue-600"></i>
          Problem Resolver Configuration
        </h3>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Build Commands
            </label>
            <input
              type="text"
              value={buildCommands}
              onChange={(e) => setBuildCommands(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              placeholder="npm install && npm run build"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Test Commands (Optional)
            </label>
            <input
              type="text"
              value={testCommands}
              onChange={(e) => setTestCommands(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              placeholder="npm test"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Run Mode
            </label>
            <div className="flex space-x-4">
              <label className="flex items-center">
                <input
                  type="radio"
                  value="diagnose-only"
                  checked={runMode === 'diagnose-only'}
                  onChange={(e) => setRunMode(e.target.value as any)}
                  className="mr-2"
                />
                <span className="text-sm">Diagnose Only</span>
              </label>
              <label className="flex items-center">
                <input
                  type="radio"
                  value="attempt-fix"
                  checked={runMode === 'attempt-fix'}
                  onChange={(e) => setRunMode(e.target.value as any)}
                  className="mr-2"
                />
                <span className="text-sm">Attempt Fix</span>
              </label>
            </div>
            <p className="text-xs text-gray-500 mt-1">
              {runMode === 'diagnose-only' 
                ? 'Only detect and report issues without making changes'
                : 'Attempt to automatically fix low-risk issues'}
            </p>
          </div>

          <button
            onClick={handleDiagnose}
            disabled={isAnalyzing}
            className="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 disabled:from-gray-400 disabled:to-gray-500 text-white font-semibold py-3 px-4 rounded-lg transition flex items-center justify-center"
          >
            {isAnalyzing ? (
              <>
                <i className="fas fa-spinner fa-spin mr-2"></i>
                Analyzing...
              </>
            ) : (
              <>
                <i className="fas fa-search mr-2"></i>
                {runMode === 'diagnose-only' ? 'Analyze Application' : 'Analyze & Fix'}
              </>
            )}
          </button>
        </div>
      </div>

      {/* Problems Panel */}
      <ProblemsPanel
        problems={problems}
        onViewDetails={handleViewDetails}
        isLoading={isAnalyzing}
      />

      {/* Pull Requests */}
      {pullRequests.length > 0 && (
        <div className="space-y-4">
          <h3 className="text-lg font-semibold text-gray-800 flex items-center">
            <i className="fas fa-code-branch mr-2 text-blue-600"></i>
            Created Pull Requests
          </h3>
          {pullRequests.map((pr, idx) => (
            <PRCard
              key={idx}
              pr={pr}
              onOpenPreview={(url) => window.open(url, '_blank')}
            />
          ))}
        </div>
      )}

      {/* Preview Validation */}
      {pullRequests.length > 0 && pullRequests[0].validation?.previewUrl && (
        <PreviewValidation
          previewUrl={pullRequests[0].validation.previewUrl}
          originalError={problems[0]?.summary}
        />
      )}

      {/* Problem Detail Modal */}
      {problemDetails && (
        <ProblemDetail
          problem={problemDetails}
          onClose={() => {
            setProblemDetails(null);
            setSelectedProblemId(null);
          }}
          onAttemptFix={handleAttemptFix}
          isFixing={isFixing}
        />
      )}
    </div>
  );
};
