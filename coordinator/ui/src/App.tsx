import React, { useState, useEffect, useRef } from 'react';
import { LivePreview } from './components/LivePreview';
import { StatusIndicator } from './components/StatusIndicator';
import { LogsPanel } from './components/LogsPanel';
import { EnhancedProblemResolverPanel } from './components/EnhancedProblemResolverPanel';
import { ProjectExplorer } from './components/ProjectExplorer';
import { NotificationSystem, useNotifications } from './components/NotificationSystem';
import { SessionContextPanel } from './components/SessionContextPanel';
import { EditorPanel } from './components/EditorPanel';
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
          actions: ['allow_run'],
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
        const data = await response.json().catch(()=>({message:'Permission denied'}));
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
              <button
                className={`px-4 py-2 rounded-full text-sm font-semibold transition ${
                  activePage === 'editor' ? 'bg-white text-blue-600 shadow' : 'text-white hover:bg-blue-400'
                }`}
                onClick={() => setActivePage('editor')}
              >
                Editor
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
        <ErrorBoundary>
          <ProjectExplorer
            frameworksError={null}
            onOpenEditor={(projectPath: string) => {
              setAppPath(projectPath);
              setActivePage('editor');
            }}
          />
        </ErrorBoundary>
      ) : activePage === 'problem-resolver' ? (
        <ErrorBoundary>
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
        </ErrorBoundary>
      ) : activePage === 'editor' ? (
        <ErrorBoundary>
          <div className="container mx-auto px-4 py-8">
            <div className="bg-white rounded-lg shadow-lg p-6 mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Project Root
              </label>
              <input
                type="text"
                value={appPath}
                onChange={(e) => setAppPath(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                placeholder="./generated/my-app"
              />
            </div>
            <EditorPanel root={appPath} />
          </div>
        </ErrorBoundary>
      ) : (
        <ErrorBoundary>
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
            {/* Left Column - Status & Tools */}
            <div className="space-y-8">
              <StatusIndicator
                status={instance.status}
                progress={instance.progress}
                currentStep={instance.currentStep}
                logsUrl={instance.logsUrl}
              />

              {/* Permissions Stats */}
              <PermissionsStatsPanel />

              {/* Session Context Panel */}
              {instance.sessionToken && (
                <SessionContextPanel
                  sessionToken={instance.sessionToken}
                />
              )}

              {/* Problem Resolver & Testing removed from Live Preview tab */}
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
                  <div className="flex items-center gap-2">
                    <span className={`text-xs font-semibold tracking-wide px-3 py-1 rounded-full ${previewStatusClass}`}>
                      {previewStatusLabel}
                    </span>
                    <button onClick={handleRun} disabled={resolverRunning || autoRetryActive} className="px-3 py-1 rounded bg-green-600 text-white text-sm disabled:opacity-50 hover:bg-green-700"><i className="fas fa-play mr-1"></i>Run</button>
                    <button onClick={startResolverAndRerun} disabled={resolverRunning} className="px-3 py-1 rounded bg-amber-600 text-white text-sm disabled:opacity-50 hover:bg-amber-700"><i className="fas fa-wrench mr-1"></i>Diagnose</button>
                    <button onClick={handleDeploy} disabled={!previewActive} className="px-3 py-1 rounded bg-indigo-600 text-white text-sm disabled:opacity-50 hover:bg-indigo-700"><i className="fas fa-cloud-upload-alt mr-1"></i>Deploy</button>
                    <button onClick={handleStop} disabled={!instance.instanceId} className="px-3 py-1 rounded bg-red-600 text-white text-sm disabled:opacity-50 hover:bg-red-700"><i className="fas fa-stop mr-1"></i>Stop</button>
                  </div>
                </div>
                <div className="relative p-6 bg-gradient-to-br from-slate-50 via-white to-slate-100 min-h-[360px] flex items-center justify-center">
                  {previewActive ? (
                    <div className="w-full">
                      <LivePreview
                        previewUrl={instance.previewUrl as string}
                        openUrl={(instance.rawPreviewUrl || instance.previewUrl) as string}
                        sessionToken={instance.sessionToken}
                        instanceId={instance.instanceId as string}
                      />
                    </div>
                  ) : (
                    <div className="w-full h-[360px] flex items-center justify-center">
                      <div className="text-center text-gray-600 space-y-3 opacity-90">
                        <i className="fas fa-robot text-4xl text-gray-400"></i>
                        <div className="text-sm">
                          {resolverRunning ? (
                            <>
                              <div className="font-semibold">Agents are working...</div>
                              <div className="text-xs">Status: {resolverStatus}</div>
                            </>
                          ) : (
                            <>
                              <div className="font-medium">Application is not running.</div>
                              <div className="text-xs">Click Run to start the sandbox. If issues occur, agents will attempt fixes automatically and re-run.</div>
                            </>
                          )}
                        </div>
                        {lastRunError && (
                          <div className="max-w-xl mx-auto bg-red-50 border border-red-200 text-red-700 text-xs p-3 rounded">
                            {lastRunError}
                          </div>
                        )}
                        {autoRetryActive && nextRetryAt && (
                          <div className="text-xs text-gray-500">Auto-retrying in ~{Math.max(0, Math.ceil((nextRetryAt - Date.now())/1000))}s (attempt {retryCount + 1}/{RETRY_LIMIT})</div>
                        )}
                        {(resolverRunning || autoRetryActive) && (
                          <div className="flex items-center justify-center gap-3 mt-2">
                            {resolverRunId && (
                              <>
                                <a
                                  href={`/api/agent/problem-resolver/${resolverRunId}/logs`}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-xs text-blue-600 hover:text-blue-700"
                                >
                                  View resolver logs
                                </a>
                                <span className="text-gray-300">|</span>
                                <a
                                  href={`/api/agent/problem-resolver/${resolverRunId}/artifacts`}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-xs text-blue-600 hover:text-blue-700"
                                >
                                  View resolver artifacts
                                </a>
                              </>
                            )}
                            <button onClick={cancelAutoRetry} className="px-3 py-1 rounded bg-gray-200 text-gray-700 text-xs hover:bg-gray-300">Cancel auto‑retry</button>
                          </div>
                        )}
                        {!resolverRunning && (
                          <button onClick={handleRun} disabled={autoRetryActive} className="mt-2 px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 text-sm disabled:opacity-50"><i className="fas fa-play mr-1"></i>Run</button>
                        )}
                      </div>
                    </div>
                  )}
                  {resolverRunning && (
                    <div className="absolute inset-0 bg-white/60 backdrop-blur-sm pointer-events-none" />
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
        </ErrorBoundary>
      )}
    </div>
  );
};

export default App;