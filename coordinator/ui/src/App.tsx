import React, { useState, useEffect } from 'react';
import { LivePreview } from './components/LivePreview';
import { ControlsPanel } from './components/ControlsPanel';
import { StatusIndicator } from './components/StatusIndicator';
import { LogsPanel } from './components/LogsPanel';
import { ProblemResolverPanel } from './components/ProblemResolverPanel';
import { EnhancedProblemResolverPanel } from './components/EnhancedProblemResolverPanel';
import { TestingPanel } from './components/TestingPanel';
import { ProjectExplorer } from './components/ProjectExplorer';
import { NotificationSystem, useNotifications } from './components/NotificationSystem';
import { SessionContextPanel } from './components/SessionContextPanel';
import { PermissionsStatsPanel } from './components/PermissionsStatsPanel';

interface InstanceState {
  instanceId?: string;
  sessionId?: string;
  previewUrl?: string;
  sessionToken?: string;
  buildId?: string;
  status: 'idle' | 'detected' | 'building' | 'running' | 'error' | 'stopped' | 'resolving' | 'testing';
  progress: number;
  currentStep?: string;
  logsUrl?: string;
  expiresAt?: string;
}

type ActivePage = 'live-preview' | 'project-explorer' | 'problem-resolver';

const App: React.FC = () => {
  const [instance, setInstance] = useState<InstanceState>({
    status: 'idle',
    progress: 0
  });
  const [detectedCommands, setDetectedCommands] = useState<{buildCmd?: string[]; runCmd?: string[]}>({});
  const [appPath, setAppPath] = useState('./generated/my-app');
  const [activePage, setActivePage] = useState<ActivePage>('live-preview');
  const { notifications, addNotification, dismissNotification } = useNotifications();

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
          timeout: 3600,
          session_id: sessionId
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
          sessionId: data.session_id ?? sessionId,
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

  const handleResolve = () => {
    setInstance(prev => ({ ...prev, status: 'detected' }));
  };

  const handleTestComplete = () => {
    // No-op placeholder. Future enhancements can store results here.
  };

  const previewActive = Boolean(instance.previewUrl && instance.instanceId);
  const previewStatusLabel = previewActive ? 'Live' : 'Not Running';
  const previewStatusClass = previewActive
    ? 'bg-green-100 text-green-700 border border-green-200'
    : 'bg-gray-100 text-gray-600 border border-gray-200';

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      <nav className="bg-blue-600 text-white shadow-lg">
        <div className="container mx-auto px-4 py-4">
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between space-y-4 lg:space-y-0">
            <div className="flex items-center space-x-3">
              <i className="fas fa-robot text-3xl"></i>
              <div>
                <h1 className="text-2xl font-bold">Autonomous App Builder</h1>
                <p className="text-blue-100 text-sm">Live Preview & Project Explorer</p>
              </div>
            </div>
            <div className="flex items-center space-x-2 bg-blue-500 rounded-full px-2 py-1">
              <button
                className={`px-4 py-2 rounded-full text-sm font-semibold transition ${
                  activePage === 'live-preview' ? 'bg-white text-blue-600 shadow' : 'text-white hover:bg-blue-400'
                }`}
                onClick={() => setActivePage('live-preview')}
              >
                Live Preview
              </button>
              <button
                className={`px-4 py-2 rounded-full text-sm font-semibold transition ${
                  activePage === 'problem-resolver' ? 'bg-white text-blue-600 shadow' : 'text-white hover:bg-blue-400'
                }`}
                onClick={() => setActivePage('problem-resolver')}
              >
                Problem Resolver
              </button>
              <button
                className={`px-4 py-2 rounded-full text-sm font-semibold transition ${
                  activePage === 'project-explorer' ? 'bg-white text-blue-600 shadow' : 'text-white hover:bg-blue-400'
                }`}
                onClick={() => setActivePage('project-explorer')}
              >
                Project Explorer
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* Notification System */}
      <NotificationSystem
        notifications={notifications}
        onDismiss={dismissNotification}
      />

      {activePage === 'project-explorer' ? (
        <ProjectExplorer />
      ) : activePage === 'problem-resolver' ? (
        <div className="container mx-auto px-4 py-8">
          <div className="bg-white rounded-lg shadow-lg p-6 mb-8">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Application Path
            </label>
            <input
              type="text"
              value={appPath}
              onChange={(e) => setAppPath(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              placeholder="./generated/my-app"
            />
          </div>
          <EnhancedProblemResolverPanel
            appPath={appPath}
            onNotification={(type, title, message) => {
              addNotification({
                type,
                title,
                message,
                duration: 5000
              });
            }}
          />
        </div>
      ) : (
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

              {/* Permissions Stats */}
              <PermissionsStatsPanel />

              <ControlsPanel
                instanceId={instance.instanceId}
                sessionId={instance.sessionId}
                detectedCommands={detectedCommands}
                onLaunch={handleLaunch}
                onStop={handleStop}
                onDownload={handleDownload}
                isRunning={instance.status === 'running'}
              />

              {/* Session Context Panel */}
              {instance.sessionToken && (
                <SessionContextPanel
                  sessionToken={instance.sessionToken}
                />
              )}

              {/* Phase 2: Problem Resolver Panel */}
              <ProblemResolverPanel
                appPath={appPath}
                onResolve={handleResolve}
              />

              {/* Phase 2: Testing Panel */}
              <TestingPanel
                appPath={appPath}
                onTestComplete={handleTestComplete}
              />
            </div>

            {/* Right Column - Preview & Logs */}
            <div className="lg:col-span-2 space-y-8">
              <div className="bg-white/80 backdrop-blur rounded-2xl border-2 border-blue-100 shadow-xl overflow-hidden">
                <div className="flex items-center justify-between px-6 py-4 border-b border-blue-100 bg-gradient-to-r from-blue-50 to-blue-100">
                  <div className="flex items-center space-x-3">
                    <div className="w-10 h-10 rounded-xl bg-blue-500/20 text-blue-700 flex items-center justify-center">
                      <i className="fas fa-display text-lg"></i>
                    </div>
                    <div>
                      <h3 className="text-lg font-semibold text-blue-900">Live Preview</h3>
                      <p className="text-xs text-blue-700 opacity-80">Interact with the running application instance</p>
                    </div>
                  </div>
                  <span className={`text-xs font-semibold tracking-wide px-3 py-1 rounded-full ${previewStatusClass}`}>
                    {previewStatusLabel}
                  </span>
                </div>
                <div className="p-6 bg-gradient-to-br from-slate-50 via-white to-slate-100 min-h-[360px] flex items-center justify-center">
                  {previewActive ? (
                    <div className="w-full">
                      <LivePreview
                        previewUrl={instance.previewUrl as string}
                        sessionToken={instance.sessionToken}
                        instanceId={instance.instanceId as string}
                      />
                    </div>
                  ) : (
                    <div className="text-center text-gray-500 space-y-3">
                      <i className="fas fa-tv text-4xl text-gray-400"></i>
                      <div>
                        <p className="text-sm font-medium">Live preview is not running yet.</p>
                        <p className="text-xs">Launch the application to see it rendered here.</p>
                      </div>
                    </div>
                  )}
                </div>
              </div>

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
      )}
    </div>
  );
};

export default App;