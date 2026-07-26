import React, { useState, useEffect, useRef } from 'react';
import { LivePreview } from './components/LivePreview';
import { StatusIndicator } from './components/StatusIndicator';
import { LogsPanel } from './components/LogsPanel';
import { EnhancedProblemResolverPanel } from './components/EnhancedProblemResolverPanel';
import { ProjectExplorer } from './components/ProjectExplorer';
import { NotificationSystem, useNotifications } from './components/NotificationSystem';
import { SessionContextPanel } from './components/SessionContextPanel';
import { IDEShell } from './components/IDEShell';
import { PermissionsStatsPanel } from './components/PermissionsStatsPanel';
import { ErrorBoundary } from './components/ErrorBoundary';
import { apiClient } from './utils/apiClient';

interface InstanceState {
  instanceId?: string;
  sessionId?: string;
  previewUrl?: string;
  rawPreviewUrl?: string;
  sessionToken?: string;
  buildId?: string;
  status: 'idle' | 'detected' | 'building' | 'running' | 'error' | 'stopped' | 'resolving' | 'testing';
  progress: number;
  currentStep?: string;
  logsUrl?: string;
  expiresAt?: string;
}

type ActivePage = 'live-preview' | 'project-explorer' | 'problem-resolver' | 'editor';

const App: React.FC = () => {
  const [instance, setInstance] = useState<InstanceState>({
    status: 'idle',
    progress: 0
  });
  const [appPath, setAppPath] = useState('./generated/my-app');
  const [activePage, setActivePage] = useState<ActivePage>('live-preview');
  const { notifications, addNotification, dismissNotification } = useNotifications();
  const [resolverRunId, setResolverRunId] = useState<string | null>(null);
  const [resolverRunning, setResolverRunning] = useState(false);
  const [resolverStatus, setResolverStatus] = useState<string>('idle');
  const [retryCount, setRetryCount] = useState(0);
  const [autoRetryActive, setAutoRetryActive] = useState(false);
  const [lastRunError, setLastRunError] = useState<string | null>(null);
  const [nextRetryAt, setNextRetryAt] = useState<number | null>(null);
  const RETRY_LIMIT = 2;
  const retryTimeoutRef = useRef<number | null>(null);

  // Set up API client notification handler
  useEffect(() => {
    apiClient.setNotificationHandler(addNotification);
  }, [addNotification]);

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

  // Removed frameworks fetch and selection (controls removed from Project Explorer)

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

  // Removed launch/stop/download controls from Project Explorer

  const ensurePermission = async (sessionId: string) => {
    try {
      const res = await fetch('/api/session/permissions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          actions: ['allow_run', 'allow_agent_auto_fix'],
          commands: [],
          duration: 3600
        })
      });
      return res.ok;
    } catch {
      return false;
    }
  };

  const handleRun = async () => {
    try {
      const sessionId = instance.sessionId || `session-${Date.now()}`;
      const permitted = await ensurePermission(sessionId);
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
          session_id: sessionId,
          environment: {}
        })
      });

      if (response.status === 403 && !permitted) {
        const data = await response.json().catch(() => ({ message: 'Permission denied' }));
        addNotification({ type: 'warning', title: 'Permission Required', message: data.message || 'Grant permission to run', duration: 4000 });
        setInstance(prev => ({ ...prev, status: 'detected' }));
        return;
      }

      const data = await response.json().catch(() => ({} as any));
      if (!response.ok) {
        const errMsg = (data?.detail || data?.message || 'Launch failed');
        setLastRunError(errMsg);
        throw new Error(errMsg);
      }
      if (data.status === 'success') {
        setInstance({
          instanceId: data.instance_id,
          sessionId: data.session_id ?? sessionId,
          previewUrl: data.secure_preview_url,
          rawPreviewUrl: data.preview_url,
          sessionToken: data.session_token,
          status: 'running',
          progress: 100,
          currentStep: 'Running',
          logsUrl: data.logs_url,
          expiresAt: data.expires_at
        });
        setLastRunError(null);
        setRetryCount(0);
        setAutoRetryActive(false);
        setNextRetryAt(null);
        addNotification({ type: 'success', title: 'App Running', message: 'Sandbox preview started', duration: 3000 });
      } else {
        const errMsg = (data?.message || 'Launch failed');
        setLastRunError(errMsg);
        throw new Error(errMsg);
      }
    } catch (error: any) {
      addNotification({ type: 'error', title: 'Run Failed', message: String(error?.message || error), duration: 4000 });
      await startResolverAndRerun();
    }
  };

  const handleStop = async () => {
    try {
      if (!instance.instanceId) return;
      await fetch('/api/app/stop', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ instance_id: instance.instanceId, force: true })
      });
      setInstance({ status: 'stopped', progress: 0 });
      setAutoRetryActive(false);
      setNextRetryAt(null);
      setResolverRunning(false);
      addNotification({ type: 'info', title: 'Stopped', message: 'Sandbox instance stopped', duration: 2500 });
    } catch (e) {
      addNotification({ type: 'error', title: 'Stop Failed', message: 'Could not stop instance', duration: 3000 });
    }
  };

  const handleDeploy = async () => {
    try {
      const name = appPath.split(/[\\\/]/).filter(Boolean).slice(-1)[0] || 'app';
      const res = await fetch('/api/v2/deployment/configure', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_path: appPath, platform: 'docker', project_name: name })
      });
      const data = await res.json();
      if (res.ok) {
        addNotification({ type: 'success', title: 'Deploy Configured', message: 'Generated deployment config (docker)', duration: 4000 });
      } else {
        throw new Error(data?.detail || 'Deploy configure failed');
      }
    } catch (e: any) {
      addNotification({ type: 'error', title: 'Deploy Failed', message: e?.message || 'Failed to generate deployment config', duration: 4000 });
    }
  };

  const startResolverAndRerun = async () => {
    try {
      if (retryCount >= RETRY_LIMIT) {
        setAutoRetryActive(false);
        addNotification({ type: 'warning', title: 'Retries Exhausted', message: 'Reached auto-retry limit. Please fix the error or run manually.', duration: 6000 });
        return;
      }
      setResolverRunning(true);
      setResolverStatus('starting');
      const sessionId = instance.sessionId || `session-${Date.now()}`;
      const res = await fetch('/api/agent/problem-resolver', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          app_path: appPath,
          commands: { build: [], test: [] },
          run_mode: 'attempt-fix'
        })
      });
      const data = await res.json();
      if (data.status === 'success' && data.runId) {
        setResolverRunId(data.runId);
        setResolverStatus('running');
        setAutoRetryActive(true);
        addNotification({ type: 'info', title: 'Agents Working', message: 'Problem resolver is fixing issues...', duration: 4000 });
      } else {
        throw new Error('Could not start resolver');
      }
    } catch (e: any) {
      setResolverRunning(false);
      setResolverStatus('error');
      addNotification({ type: 'error', title: 'Resolver Failed', message: e?.message || 'Failed to start resolver', duration: 4000 });
    }
  };

  // Poll resolver status and auto re-run (with retry guard and cooldown)
  useEffect(() => {
    if (!resolverRunId) return;
    let cancelled = false;
    const poll = async () => {
      try {
        const res = await fetch(`/api/agent/problem-resolver/${resolverRunId}/result`);
        const data = await res.json();
        if (cancelled) return;
        if (data.status === 'completed') {
          setResolverStatus('completed');
          setResolverRunning(false);
          setResolverRunId(null);
          if (retryCount >= RETRY_LIMIT) {
            setAutoRetryActive(false);
            addNotification({ type: 'warning', title: 'Retries Exhausted', message: 'Reached auto-retry limit. Please review the error and run manually.', duration: 6000 });
            return;
          }
          const cooldown = 15000;
          const when = Date.now() + cooldown;
          setNextRetryAt(when);
          if (retryTimeoutRef.current) {
            clearTimeout(retryTimeoutRef.current);
            retryTimeoutRef.current = null;
          }
          retryTimeoutRef.current = window.setTimeout(async () => {
            setNextRetryAt(null);
            setRetryCount((c) => c + 1);
            await handleRun();
          }, cooldown);
        } else if (data.status === 'failed') {
          setResolverStatus('failed');
          setResolverRunning(false);
          setResolverRunId(null);
          addNotification({ type: 'warning', title: 'Agent Could Not Fix', message: 'Manual intervention may be required', duration: 5000 });
        } else {
          setResolverStatus('running');
          setTimeout(poll, 5000);
        }
      } catch {
        if (!cancelled) setTimeout(poll, 5000);
      }
    };
    poll();
    return () => { cancelled = true; };
  }, [resolverRunId]);

  const cancelAutoRetry = () => {
    setAutoRetryActive(false);
    setResolverRunning(false);
    setNextRetryAt(null);
    if (retryTimeoutRef.current) {
      clearTimeout(retryTimeoutRef.current);
      retryTimeoutRef.current = null;
    }
    addNotification({ type: 'info', title: 'Auto-Retry Cancelled', message: 'Stopped automatic retries.', duration: 3000 });
  };

  const previewActive = Boolean(instance.previewUrl && instance.instanceId);
  const previewStatusLabel = previewActive ? 'Live' : 'Not Running';

  return (
    <div className="min-h-screen text-foreground font-sans selection:bg-primary/30">
      {/* Navbar - Hidden in Editor mode */}
      {activePage !== 'editor' && (
        <nav className="fixed top-0 left-0 right-0 z-50 glass-panel border-b border-white/5 mx-4 mt-4 rounded-2xl">
          <div className="container mx-auto px-6 py-4">
            <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between space-y-4 lg:space-y-0">
              <div className="flex items-center space-x-4">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/30">
                  <i className="fas fa-robot text-white text-xl"></i>
                </div>
                <div>
                  <h1 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-gray-400">
                    Autonomous Builder
                  </h1>
                  <p className="text-xs text-gray-400 font-medium tracking-wide">COORDINATOR DASHBOARD</p>
                </div>
              </div>

              <div className="flex items-center p-1 bg-white/5 rounded-xl border border-white/5 backdrop-blur-sm">
                <button
                  className={`px-5 py-2 rounded-lg text-sm font-medium transition-all duration-300 ${activePage === 'live-preview'
                    ? 'bg-primary text-white shadow-lg shadow-primary/25'
                    : 'text-gray-400 hover:text-white hover:bg-white/5'
                    }`}
                  onClick={() => setActivePage('live-preview')}
                >
                  <i className="fas fa-play-circle mr-2"></i>Live Preview
                </button>
                <button
                  className={`px-5 py-2 rounded-lg text-sm font-medium transition-all duration-300 ${activePage === 'problem-resolver'
                    ? 'bg-primary text-white shadow-lg shadow-primary/25'
                    : 'text-gray-400 hover:text-white hover:bg-white/5'
                    }`}
                  onClick={() => setActivePage('problem-resolver')}
                >
                  <i className="fas fa-wrench mr-2"></i>Resolver
                </button>
                <button
                  className={`px-5 py-2 rounded-lg text-sm font-medium transition-all duration-300 ${activePage === 'project-explorer'
                    ? 'bg-primary text-white shadow-lg shadow-primary/25'
                    : 'text-gray-400 hover:text-white hover:bg-white/5'
                    }`}
                  onClick={() => setActivePage('project-explorer')}
                >
                  <i className="fas fa-folder-open mr-2"></i>Explorer
                </button>
                <button
                  className="px-5 py-2 rounded-lg text-sm font-medium transition-all duration-300 text-gray-400 hover:text-white hover:bg-white/5"
                  onClick={() => setActivePage('editor')}
                >
                  <i className="fas fa-code mr-2"></i>Editor
                </button>
              </div>
            </div>
          </div>
        </nav>
      )}

      {/* Main Content */}
      <main className="container mx-auto px-4 pt-32 pb-12">
        <NotificationSystem
          notifications={notifications}
          onDismiss={dismissNotification}
        />

        {activePage === 'project-explorer' ? (
          <ErrorBoundary>
            <div className="animate-fade-in text-gray-800">
              {/* Wrapper div to give some context if ProjectExplorer uses white background internally, usually it does, but we will fix that next */}
              <ProjectExplorer
                frameworksError={null}
                onOpenEditor={(projectPath: string) => {
                  setAppPath(projectPath);
                  setActivePage('editor');
                }}
              />
            </div>
          </ErrorBoundary>
        ) : activePage === 'problem-resolver' ? (
          <ErrorBoundary>
            <div className="animate-fade-in max-w-5xl mx-auto">
              <div className="glass-panel rounded-2xl p-8 mb-8">
                <label className="block text-sm font-medium text-gray-300 mb-3">
                  Application Path
                </label>
                <div className="relative">
                  <input
                    type="text"
                    value={appPath}
                    onChange={(e) => setAppPath(e.target.value)}
                    className="w-full pl-10 pr-4 py-3 bg-black/20 border border-white/10 rounded-xl focus:ring-2 focus:ring-primary/50 text-white placeholder-gray-500 outline-none transition-all"
                    placeholder="./generated/my-app"
                  />
                  <i className="fas fa-folder absolute left-3.5 top-3.5 text-gray-500"></i>
                </div>
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
          </ErrorBoundary>
        ) : activePage === 'editor' ? (
          <ErrorBoundary>
            <IDEShell
              root={appPath}
              onRun={handleRun}
              onStop={handleStop}
              onBack={() => setActivePage('live-preview')}
              isRunning={instance.status === 'running'}
            />
          </ErrorBoundary>
        ) : (
          <ErrorBoundary>
            <div className="animate-fade-in space-y-8">
              {/* Controls Bar */}
              <div className="glass-panel rounded-2xl p-6 flex flex-col md:flex-row md:items-center gap-6">
                <div className="flex-1">
                  <label className="block text-xs font-semibold text-gray-400 mb-2 uppercase tracking-wider">
                    Target Application
                  </label>
                  <div className="flex space-x-2">
                    <div className="relative flex-1">
                      <input
                        type="text"
                        value={appPath}
                        onChange={(e) => setAppPath(e.target.value)}
                        className="w-full pl-10 pr-4 py-2.5 bg-black/20 border border-white/10 rounded-xl focus:ring-2 focus:ring-primary/50 text-white placeholder-gray-500 outline-none transition-all font-mono text-sm"
                        placeholder="./generated/my-app"
                      />
                      <i className="fas fa-search absolute left-3.5 top-3 text-gray-500"></i>
                    </div>
                  </div>
                </div>
                <div className="flex items-end">
                  <button
                    onClick={handleDetect}
                    className="glass-button bg-primary/20 hover:bg-primary/30 text-white px-8 py-2.5 rounded-xl font-medium flex items-center space-x-2"
                  >
                    <i className="fas fa-radar"></i>
                    <span>Detect Config</span>
                  </button>
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
                {/* Left Sidebar */}
                <div className="lg:col-span-4 space-y-6">
                  <StatusIndicator
                    status={instance.status}
                    progress={instance.progress}
                    currentStep={instance.currentStep}
                    logsUrl={instance.logsUrl}
                  />

                  <PermissionsStatsPanel />

                  {instance.sessionToken && (
                    <SessionContextPanel
                      sessionToken={instance.sessionToken}
                    />
                  )}
                </div>

                {/* Main Preview Area */}
                <div className="lg:col-span-8 space-y-6">
                  <div className="glass-panel rounded-2xl overflow-hidden border border-white/10 shadow-2xl shadow-black/20">
                    {/* Preview Header */}
                    <div className="px-6 py-4 border-b border-white/5 bg-white/5 flex items-center justify-between">
                      <div className="flex items-center space-x-3">
                        <div className={`w-2.5 h-2.5 rounded-full ${previewActive ? 'bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.5)]' : 'bg-red-500 opacity-50'}`}></div>
                        <span className="text-sm font-medium text-gray-200">Live Preview</span>
                        {previewStatusLabel && (
                          <span className="text-xs bg-white/10 px-2 py-0.5 rounded text-gray-400">{previewStatusLabel}</span>
                        )}
                      </div>

                      <div className="flex items-center space-x-2">
                        <button
                          onClick={handleRun}
                          disabled={resolverRunning || autoRetryActive}
                          className="glass-button text-xs px-3 py-1.5 rounded-lg text-emerald-400 hover:text-emerald-300 hover:bg-emerald-500/10 border-emerald-500/20 disabled:hidden"
                        >
                          <i className="fas fa-play mr-1.5"></i>Run
                        </button>
                        <button
                          onClick={startResolverAndRerun}
                          disabled={resolverRunning}
                          className="glass-button text-xs px-3 py-1.5 rounded-lg text-amber-400 hover:text-amber-300 hover:bg-amber-500/10 border-amber-500/20 disabled:hidden"
                        >
                          <i className="fas fa-bug mr-1.5"></i>Diagnose
                        </button>
                        <button
                          onClick={handleDeploy}
                          disabled={!previewActive}
                          className="glass-button text-xs px-3 py-1.5 rounded-lg text-indigo-400 hover:text-indigo-300 hover:bg-indigo-500/10 border-indigo-500/20 disabled:hidden"
                        >
                          <i className="fas fa-rocket mr-1.5"></i>Deploy
                        </button>
                        <button
                          onClick={handleStop}
                          disabled={!instance.instanceId}
                          className="glass-button text-xs px-3 py-1.5 rounded-lg text-red-400 hover:text-red-300 hover:bg-red-500/10 border-red-500/20 disabled:hidden"
                        >
                          <i className="fas fa-square mr-1.5"></i>Stop
                        </button>
                      </div>
                    </div>

                    {/* Preview Body */}
                    <div className="bg-[#0c0c0e] min-h-[500px] relative">
                      {previewActive ? (
                        <LivePreview
                          previewUrl={instance.previewUrl as string}
                          openUrl={(instance.rawPreviewUrl || instance.previewUrl) as string}
                          sessionToken={instance.sessionToken}
                          instanceId={instance.instanceId as string}
                        />
                      ) : (
                        <div className="absolute inset-0 flex items-center justify-center">
                          <div className="text-center space-y-4 max-w-md px-6">
                            <div className="w-20 h-20 bg-white/5 rounded-full flex items-center justify-center mx-auto mb-6">
                              <i className="fas fa-cube text-3xl text-gray-600"></i>
                            </div>

                            {resolverRunning ? (
                              <div className="space-y-2">
                                <h3 className="text-lg font-medium text-white">Auto-fixing Issues</h3>
                                <div className="flex items-center justify-center space-x-2 text-primary">
                                  <i className="fas fa-circle-notch fa-spin"></i>
                                  <span>{resolverStatus}...</span>
                                </div>
                              </div>
                            ) : (
                              <div className="space-y-2">
                                <h3 className="text-lg font-medium text-white">Ready to Launch</h3>
                                <p className="text-gray-500 text-sm">
                                  Start the sandbox to preview your application. Our agents will automatically detect and fix build errors if they occur.
                                </p>
                              </div>
                            )}

                            {lastRunError && (
                              <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4 text-left">
                                <div className="flex items-start space-x-3">
                                  <i className="fas fa-exclamation-triangle text-red-500 mt-0.5"></i>
                                  <p className="text-sm text-red-200">{lastRunError}</p>
                                </div>
                              </div>
                            )}

                            {!resolverRunning && (
                              <button
                                onClick={handleRun}
                                className="mt-4 px-8 py-3 bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-white font-bold rounded-xl shadow-lg shadow-emerald-500/25 transition-all transform hover:scale-105"
                              >
                                <i className="fas fa-power-off mr-2"></i>Launch Sandbox
                              </button>
                            )}

                            {autoRetryActive && nextRetryAt && (
                              <div className="text-xs text-gray-500 pt-4">
                                Auto-retrying in <span className="text-white font-mono">{Math.max(0, Math.ceil((nextRetryAt - Date.now()) / 1000))}s</span>
                                <br />
                                <button onClick={cancelAutoRetry} className="text-gray-400 hover:text-white underline mt-1">Cancel</button>
                              </div>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>

                  {instance.logsUrl && (
                    <div className="glass-panel rounded-2xl p-1 overflow-hidden">
                      <div className="bg-black/50 rounded-xl overflow-hidden">
                        <LogsPanel
                          instanceId={instance.instanceId}
                          logsUrl={instance.logsUrl}
                          tail={100}
                        />
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </ErrorBoundary>
        )}
      </main>
    </div>
  );
};


export default App;