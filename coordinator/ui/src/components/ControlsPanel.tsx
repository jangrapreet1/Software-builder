import React, { useState } from 'react';

interface ControlsPanelProps {
  instanceId?: string;
  sessionId?: string;
  detectedCommands?: {
    buildCmd?: string[];
    runCmd?: string[];
  };
  onLaunch: (sessionId: string) => void;
  onStop: (instanceId: string) => void;
  onDownload: () => void;
  onRequestTests?: () => void;
  onOpenPR?: () => void;
  isRunning?: boolean;
}

export const ControlsPanel: React.FC<ControlsPanelProps> = ({
  instanceId,
  sessionId,
  detectedCommands,
  onLaunch,
  onStop,
  onDownload,
  onRequestTests,
  onOpenPR,
  isRunning = false
}) => {
  const [showPermissionModal, setShowPermissionModal] = useState(false);
  const [permissionGranted, setPermissionGranted] = useState(false);
  const [localSessionId, setLocalSessionId] = useState<string | null>(null);

  const handleLaunchClick = () => {
    const effectiveSessionId = sessionId ?? localSessionId ?? `session-${Date.now()}`;
    setLocalSessionId(effectiveSessionId);

    if (!permissionGranted) {
      setShowPermissionModal(true);
    } else {
      onLaunch(effectiveSessionId);
    }
  };

  const handleGrantPermission = async () => {
    // Call permission API
    try {
      const commands = [
        ...(detectedCommands?.buildCmd || []),
        ...(detectedCommands?.runCmd || [])
      ];

      const effectiveSessionId = sessionId ?? localSessionId ?? `session-${Date.now()}`;
      setLocalSessionId(effectiveSessionId);

      const response = await fetch('/api/session/permissions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: effectiveSessionId,
          actions: ['allow_build', 'allow_run'],
          commands: commands,
          duration: 3600
        })
      });

      if (response.ok) {
        setPermissionGranted(true);
        setShowPermissionModal(false);
        onLaunch(effectiveSessionId);
      } else {
        alert('Failed to grant permission');
      }
    } catch (error) {
      console.error('Permission error:', error);
      alert('Error granting permission');
    }
  };

  return (
    <>
      <div className="bg-white rounded-lg shadow-lg p-6">
        <h3 className="text-lg font-semibold text-gray-800 mb-4">
          <i className="fas fa-sliders-h mr-2"></i>
          Controls
        </h3>
        
        <div className="grid grid-cols-2 gap-3">
          <button
            onClick={handleLaunchClick}
            disabled={isRunning}
            className="bg-green-600 hover:bg-green-700 disabled:bg-gray-400 text-white font-semibold py-3 px-4 rounded-lg transition flex items-center justify-center space-x-2"
            title="Launch application"
          >
            <i className="fas fa-rocket"></i>
            <span>Launch App</span>
          </button>

          <button
            onClick={() => instanceId && onStop(instanceId)}
            disabled={!isRunning || !instanceId}
            className="bg-red-600 hover:bg-red-700 disabled:bg-gray-400 text-white font-semibold py-3 px-4 rounded-lg transition flex items-center justify-center space-x-2"
            title="Stop application"
          >
            <i className="fas fa-stop"></i>
            <span>Stop</span>
          </button>

          <button
            onClick={onDownload}
            className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-4 rounded-lg transition flex items-center justify-center space-x-2"
            title="Download source code"
          >
            <i className="fas fa-download"></i>
            <span>Download Code</span>
          </button>

          {onRequestTests && (
            <button
              onClick={onRequestTests}
              disabled={!isRunning}
              className="bg-purple-600 hover:bg-purple-700 disabled:bg-gray-400 text-white font-semibold py-3 px-4 rounded-lg transition flex items-center justify-center space-x-2"
              title="Request automated tests"
            >
              <i className="fas fa-vial"></i>
              <span>Request Tests</span>
            </button>
          )}

          {onOpenPR && (
            <button
              onClick={onOpenPR}
              className="bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-3 px-4 rounded-lg transition flex items-center justify-center space-x-2 col-span-2"
              title="Open pull request"
            >
              <i className="fas fa-code-branch"></i>
              <span>Open PR</span>
            </button>
          )}
        </div>

        {!permissionGranted && (
          <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
            <div className="flex items-start space-x-2">
              <i className="fas fa-exclamation-triangle text-yellow-600 mt-1"></i>
              <div className="text-sm text-yellow-800">
                <strong>Permission Required:</strong> You must explicitly approve commands before launching.
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Permission Modal */}
      {showPermissionModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-2xl max-w-2xl w-full max-h-[80vh] overflow-hidden">
            <div className="bg-gradient-to-r from-blue-600 to-purple-600 text-white px-6 py-4">
              <h2 className="text-2xl font-bold flex items-center">
                <i className="fas fa-shield-alt mr-3"></i>
                Permission Required
              </h2>
            </div>
            
            <div className="p-6 overflow-y-auto max-h-96">
              <div className="mb-4">
                <p className="text-gray-700 mb-4">
                  The following commands will be executed in a sandboxed container:
                </p>
              </div>

              <div className="bg-gray-900 rounded-lg p-4 mb-4">
                <div className="text-green-400 font-mono text-sm space-y-2">
                  {detectedCommands?.buildCmd && detectedCommands.buildCmd.length > 0 && (
                    <>
                      <div className="text-gray-400 mb-2">Build Commands:</div>
                      {detectedCommands.buildCmd.map((cmd, idx) => (
                        <div key={idx} className="pl-4">
                          <span className="text-blue-400">$</span> {cmd}
                        </div>
                      ))}
                    </>
                  )}
                  
                  {detectedCommands?.runCmd && detectedCommands.runCmd.length > 0 && (
                    <>
                      <div className="text-gray-400 mt-4 mb-2">Run Commands:</div>
                      {detectedCommands.runCmd.map((cmd, idx) => (
                        <div key={idx} className="pl-4">
                          <span className="text-blue-400">$</span> {cmd}
                        </div>
                      ))}
                    </>
                  )}
                </div>
              </div>

              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
                <div className="flex items-start space-x-2">
                  <i className="fas fa-info-circle text-blue-600 mt-1"></i>
                  <div className="text-sm text-blue-800">
                    <strong>Security Notice:</strong>
                    <ul className="list-disc list-inside mt-2 space-y-1">
                      <li>Commands run in isolated Docker containers</li>
                      <li>CPU & memory limits enforced</li>
                      <li>Network access restricted</li>
                      <li>Secrets are automatically masked in logs</li>
                      <li>Containers auto-cleanup after timeout</li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-gray-50 px-6 py-4 flex justify-end space-x-3 border-t">
              <button
                onClick={() => setShowPermissionModal(false)}
                className="px-4 py-2 bg-gray-200 hover:bg-gray-300 text-gray-700 font-semibold rounded-lg transition"
              >
                Cancel
              </button>
              <button
                onClick={handleGrantPermission}
                className="px-6 py-2 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-lg transition flex items-center space-x-2"
              >
                <i className="fas fa-check"></i>
                <span>Approve & Launch</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};