import React, { useState, useEffect } from 'react';
import { EnhancedProblemResolverPanel } from './components/EnhancedProblemResolverPanel';
import { ProjectExplorer } from './components/ProjectExplorer';
import { NotificationSystem, useNotifications } from './components/NotificationSystem';
import { IDEShell } from './components/IDEShell';
import { ErrorBoundary } from './components/ErrorBoundary';
import { apiClient } from './utils/apiClient';
import { BuilderPage } from './components/BuilderPage';

type NotifType = 'success' | 'error' | 'info' | 'warning';

type ActivePage = 'builder' | 'project-explorer' | 'problem-resolver' | 'editor';

const App: React.FC = () => {
  const [appPath, setAppPath] = useState('./generated/my-app');
  const [activePage, setActivePage] = useState<ActivePage>('builder');
  const { notifications, addNotification, dismissNotification } = useNotifications();
  const [apiLatency, setApiLatency] = useState<number | null>(null);
  const [apiOnline, setApiOnline] = useState<boolean | null>(null);
  const [projectCount, setProjectCount] = useState<number>(0);

  // Set up API client notification handler
  useEffect(() => {
    apiClient.setNotificationHandler(addNotification);
  }, [addNotification]);

  // Backend health ping every 15 seconds
  useEffect(() => {
    const ping = async () => {
      const t0 = performance.now();
      try {
        const res = await fetch('/health', { signal: AbortSignal.timeout(5000) });
        const latency = Math.round(performance.now() - t0);
        setApiOnline(res.ok);
        setApiLatency(latency);
      } catch {
        setApiOnline(false);
        setApiLatency(null);
      }
    };
    ping();
    const id = setInterval(ping, 15000);
    return () => clearInterval(id);
  }, []);

  // Fetch project count for Explorer badge
  useEffect(() => {
    const loadCount = () => {
      fetch('/api/builds')
        .then(r => r.json())
        .then(d => setProjectCount(Array.isArray(d.builds) ? d.builds.length : 0))
        .catch(() => {});
    };
    loadCount();
    const intervalId = setInterval(loadCount, 30000);
    return () => clearInterval(intervalId);
  }, []);

  return (
    <div className="min-h-screen text-foreground font-sans selection:bg-primary/30">
      {/* Navbar - Hidden in Editor mode */}
      {activePage !== 'editor' && (
        <nav className="fixed top-0 left-0 right-0 z-50 glass-panel border-b border-white/5 mx-4 mt-4 rounded-2xl">
          <div className="container mx-auto px-6 py-3">
            <div className="flex items-center justify-between gap-4">

              {/* Logo + title */}
              <div className="flex items-center space-x-3 shrink-0">
                <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/30 animate-pulse-glow">
                  <i className="fas fa-robot text-white"></i>
                </div>
                <div>
                  <h1 className="text-lg font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-gray-400 leading-tight">
                    Autonomous Builder
                  </h1>
                  <p className="text-[10px] text-gray-500 font-semibold tracking-widest uppercase">COORDINATOR</p>
                </div>
              </div>

              {/* Tab switcher */}
              <div className="flex items-center p-1 bg-white/5 rounded-xl border border-white/5 backdrop-blur-sm gap-0.5">
                {/* Builder tab */}
                <button
                  className={`relative px-4 py-1.5 rounded-lg text-sm font-medium transition-all duration-300 flex items-center gap-2 ${
                    activePage === 'builder'
                      ? 'bg-primary text-white shadow-lg shadow-primary/25'
                      : 'text-gray-400 hover:text-white hover:bg-white/5'
                  }`}
                  onClick={() => setActivePage('builder')}
                >
                  <i className="fas fa-wand-magic-sparkles"></i>
                  Builder
                </button>

                {/* Resolver tab */}
                <button
                  className={`relative px-4 py-1.5 rounded-lg text-sm font-medium transition-all duration-300 flex items-center gap-2 ${
                    activePage === 'problem-resolver'
                      ? 'bg-primary text-white shadow-lg shadow-primary/25'
                      : 'text-gray-400 hover:text-white hover:bg-white/5'
                  }`}
                  onClick={() => setActivePage('problem-resolver')}
                >
                  <i className="fas fa-wrench"></i>
                  Resolver
                </button>

                {/* Explorer tab */}
                <button
                  className={`relative px-4 py-1.5 rounded-lg text-sm font-medium transition-all duration-300 flex items-center gap-2 ${
                    activePage === 'project-explorer'
                      ? 'bg-primary text-white shadow-lg shadow-primary/25'
                      : 'text-gray-400 hover:text-white hover:bg-white/5'
                  }`}
                  onClick={() => setActivePage('project-explorer')}
                >
                  <i className="fas fa-folder-open"></i>
                  Explorer
                  {projectCount > 0 && (
                    <span className="tab-badge bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                      {projectCount}
                    </span>
                  )}
                </button>

                {/* Editor tab */}
                <button
                  className="px-4 py-1.5 rounded-lg text-sm font-medium transition-all duration-300 text-gray-400 hover:text-white hover:bg-white/5 flex items-center gap-2"
                  onClick={() => setActivePage('editor')}
                >
                  <i className="fas fa-code"></i>
                  Editor
                </button>
              </div>

              {/* Backend health pill */}
              <div className={`health-pill shrink-0 ${
                apiOnline === null
                  ? 'border-white/10 text-gray-500'
                  : apiOnline
                  ? 'border-emerald-500/30 text-emerald-400 bg-emerald-500/5'
                  : 'border-red-500/30 text-red-400 bg-red-500/5'
              }`}>
                <span className={`w-1.5 h-1.5 rounded-full ${
                  apiOnline === null ? 'bg-gray-500' : apiOnline ? 'bg-emerald-400 animate-pulse' : 'bg-red-400'
                }`}></span>
                {apiOnline === null ? 'Connecting…' : apiOnline ? `API Online` : 'API Offline'}
                {apiOnline && apiLatency !== null && (
                  <span className="opacity-60 ml-0.5">· {apiLatency}ms</span>
                )}
              </div>

            </div>
          </div>
        </nav>
      )}

      {/* Main Content */}
      <main className={activePage === 'editor' ? '' : 'container mx-auto px-4 pt-28 pb-12'}>
        <NotificationSystem
          notifications={notifications}
          onDismiss={dismissNotification}
        />

        {/* Builder Tab */}
        <div className={activePage === 'builder' ? 'block' : 'hidden'}>
          <ErrorBoundary>
            <BuilderPage addNotification={(n) => addNotification({ ...n, type: n.type as NotifType })} />
          </ErrorBoundary>
        </div>

        {/* Project Explorer Tab */}
        <div className={activePage === 'project-explorer' ? 'block animate-fade-in' : 'hidden'}>
          <ErrorBoundary>
            <ProjectExplorer
              frameworksError={null}
              onOpenEditor={(projectPath: string) => {
                setAppPath(projectPath);
                setActivePage('editor');
              }}
              onGoToBuilder={() => setActivePage('builder')}
            />
          </ErrorBoundary>
        </div>

        {/* Problem Resolver Tab */}
        <div className={activePage === 'problem-resolver' ? 'block animate-fade-in max-w-5xl mx-auto' : 'hidden'}>
          <ErrorBoundary>
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
          </ErrorBoundary>
        </div>

        {/* Editor Tab */}
        <div className={activePage === 'editor' ? 'block' : 'hidden'}>
          <ErrorBoundary>
            <IDEShell
              root={appPath}
              onRun={() => {}}
              onStop={() => {}}
              onBack={() => setActivePage('builder')}
              isRunning={false}
            />
          </ErrorBoundary>
        </div>
      </main>
    </div>
  );
};


export default App;