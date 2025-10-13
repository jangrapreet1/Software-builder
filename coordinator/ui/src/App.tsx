import React, { useState, useEffect } from 'react';
import { LivePreview } from './components/LivePreview';
import { ControlsPanel } from './components/ControlsPanel';
import { StatusIndicator } from './components/StatusIndicator';
import { LogsPanel } from './components/LogsPanel';

interface InstanceState {
  instanceId?: string;
  sessionId?: string;
  previewUrl?: string;
  sessionToken?: string;
  status: 'idle' | 'detected' | 'building' | 'running' | 'error' | 'stopped';
  progress: number;
  currentStep?: string;
  logsUrl?: string;
  expiresAt?: string;
}

const App: React.FC = () => {
  const [instance, setInstance] = useState<InstanceState>({
    status: 'idle',
    progress: 0
  });
  const [detectedCommands, setDetectedCommands] = useState<{buildCmd?: string[]; runCmd?: string[]}>({});
  const [appPath, setAppPath] = useState('./generated/my-app');

  // Poll instance status
  useEffect(() => {
    if (instance.instanceId && instance.status === 'running') {
      const interval = setInterval(async () => {
        try {
          const response = await fetch(`/api/sandbox/${instance.instanceId}/status`);
          const data = await response.json();
          
          setInstance(prev => ({
            ...prev,
            status: data.status === 'running' ? 'running' : 'error',
            currentStep: data.health
          }));
        } catch (error) {
          console.error('Status poll error:', error);
        }
      }, 5000);

      return () => clearInterval(interval);
    }
  }, [instance.instanceId, instance.status]);

  const handleDetect = async () => {
    try {
      setInstance(prev => ({ ...prev, status: 'detected', progress: 10 }));
      
      const response = await fetch('/api/repo/detect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ repo_path: appPath })
      });

      const data = await response.json();
      
      if (data.status === 'success') {
        const report = data.detection_report;
        setDetectedCommands({
          buildCmd: report.build_commands?.confident || [],
          runCmd: report.run_commands?.confident || []
        });
        setInstance(prev => ({
          ...prev,
          status: 'detected',
          progress: 20,
          currentStep: 'Repository detected'
        }));
      }
    } catch (error) {
      console.error('Detection error:', error);
      setInstance(prev => ({ ...prev, status: 'error' }));
    }
  };

  const handleLaunch = async (sessionId: string) => {
    try {
      setInstance(prev => ({ ...prev, status: 'building', progress: 30, sessionId }));

      const response = await fetch('/api/app/launch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          app_path: appPath,
          port: 3000,
          cpu_limit: 1.0,
          memory_limit: '512m',
          timeout: 3600
        })
      });

      if (response.status === 403) {
        const data = await response.json();
        alert(data.message);
        setInstance(prev => ({ ...prev, status: 'detected' }));
        return;
      }

      const data = await response.json();
      
      if (data.status === 'success') {
        setInstance({
          instanceId: data.instance_id,
          sessionId,
          previewUrl: data.preview_url,
          sessionToken: data.session_token,
          status: 'running',
          progress: 100,
          currentStep: 'Running',
          logsUrl: data.logs_url,
          expiresAt: data.expires_at
        });
      }
    } catch (error) {
      console.error('Launch error:', error);
      setInstance(prev => ({ ...prev, status: 'error' }));
    }
  };

  const handleStop = async (instanceId: string) => {
    try {
      await fetch('/api/app/stop', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ instance_id: instanceId, force: true })
      });

      setInstance({
        status: 'stopped',
        progress: 0
      });
    } catch (error) {
      console.error('Stop error:', error);
    }
  };

  const handleDownload = async () => {
    try {
      window.open(`/api/app/download?app_path=${encodeURIComponent(appPath)}`, '_blank');
    } catch (error) {
      console.error('Download error:', error);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      <nav className="bg-blue-600 text-white shadow-lg">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <i className="fas fa-robot text-3xl"></i>
              <div>
                <h1 className="text-2xl font-bold">Live Preview - Phase 1</h1>
                <p className="text-blue-100 text-sm">Sandbox Orchestration</p>
              </div>
            </div>
          </div>
        </div>
      </nav>

      <div className="container mx-auto px-4 py-8">
        {/* App Path Input */}
        <div className="bg-white rounded-lg shadow-lg p-6 mb-8">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Application Path
          </label>
          <div className="flex space-x-2">
            <input
              type="text"
              value={appPath}
              onChange={(e) => setAppPath(e.target.value)}
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              placeholder="./generated/my-app"
            />
            <button
              onClick={handleDetect}
              className="bg-blue-600 hover:bg-blue-700 text-white font-semibold px-6 py-2 rounded-lg transition"
            >
              <i className="fas fa-search mr-2"></i>
              Detect
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left Column - Controls & Status */}
          <div className="space-y-8">
            <StatusIndicator
              status={instance.status}
              progress={instance.progress}
              currentStep={instance.currentStep}
              logsUrl={instance.logsUrl}
            />

            <ControlsPanel
              instanceId={instance.instanceId}
              sessionId={instance.sessionId}
              detectedCommands={detectedCommands}
              onLaunch={handleLaunch}
              onStop={handleStop}
              onDownload={handleDownload}
              isRunning={instance.status === 'running'}
            />
          </div>

          {/* Right Column - Preview & Logs */}
          <div className="lg:col-span-2 space-y-8">
            {instance.previewUrl && instance.instanceId && (
              <LivePreview
                previewUrl={instance.previewUrl}
                sessionToken={instance.sessionToken}
                instanceId={instance.instanceId}
              />
            )}

            {instance.logsUrl && (
              <LogsPanel
                instanceId={instance.instanceId}
                logsUrl={instance.logsUrl}
                tail={100}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default App;