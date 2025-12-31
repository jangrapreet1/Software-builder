import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';

type ProjectItem = {
  name: string;
  path: string;
  created_at: string;
  updated_at: string;
  has_backend: boolean;
  has_frontend: boolean;
};

type BuildResult = {
  status: string;
  build_id?: string;
  message?: string;
  app_url?: string;
  source_path?: string;
};


type BuildProgress = {
  build_id: string;
  status: string;
  progress: number;
  current_step: string;
  logs: Array<{
    level: string;
    message: string;
    timestamp: string;
  }>;
};

type BuildSummary = {
  build_id: string;
  status: string;
  last_updated?: string;
  version?: number;
};

interface ProjectExplorerProps {
  onOpenEditor: (projectPath: string) => void;
  frameworksError?: string | null;
}

const formatTimestamp = (value: string) => {
  try {
    const date = new Date(value);
    return date.toLocaleString();
  } catch (error) {
    return value;
  }
};

export const ProjectExplorer: React.FC<ProjectExplorerProps> = ({
  frameworksError,
  onOpenEditor,
}) => {
  const [description, setDescription] = useState('');
  const [projectName, setProjectName] = useState('');
  const [requirementsText, setRequirementsText] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [buildResult, setBuildResult] = useState<BuildResult | null>(null);
  const [submissionError, setSubmissionError] = useState<string | null>(null);

  const [buildProgress, setBuildProgress] = useState<BuildProgress | null>(null);
  const [wsConnection, setWsConnection] = useState<WebSocket | null>(null);
  const progressBarRef = useRef<HTMLDivElement | null>(null);
  const lastConnectAtRef = useRef<number>(0);

  const getProgressColor = (progress: number) => {
    if (progress < 30) return 'bg-blue-500';
    if (progress < 70) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  const [projects, setProjects] = useState<ProjectItem[]>([]);
  const [isLoadingProjects, setIsLoadingProjects] = useState(false);
  const [projectsError, setProjectsError] = useState<string | null>(null);
  const [inProgressBuilds, setInProgressBuilds] = useState<BuildSummary[]>([]);
  const [inProgressError, setInProgressError] = useState<string | null>(null);
  const [loadingInProgress, setLoadingInProgress] = useState(false);
  const [inProgressLabels, setInProgressLabels] = useState<Record<string, string>>({});
  const [backendOptions, setBackendOptions] = useState<Array<{ id: string; name: string; language: string; description?: string }>>([]);
  const [frontendOptions, setFrontendOptions] = useState<Array<{ id: string; name: string; language: string; description?: string }>>([]);
  const [selectedBackend, setSelectedBackend] = useState<string>('');
  const [selectedFrontend, setSelectedFrontend] = useState<string>('');
  const [stackError, setStackError] = useState<string | null>(null);
  const [loadingStack, setLoadingStack] = useState(false);

  const parsedRequirements = useMemo(() => {
    if (!requirementsText.trim()) {
      return [] as string[];
    }

    return requirementsText
      .split(/\r?\n|,/)
      .map((item) => item.trim())
      .filter((item) => item.length > 0);
  }, [requirementsText]);

  const fetchProjects = useCallback(async () => {
    setIsLoadingProjects(true);
    setProjectsError(null);

    try {
      const response = await fetch('/api/generated/projects');

      if (!response.ok) {
        throw new Error(`Request failed with status ${response.status}`);
      }

      const data = await response.json();
      setProjects(Array.isArray(data.projects) ? data.projects : []);
    } catch (error: any) {
      setProjectsError(error?.message ?? 'Failed to load projects');
    } finally {
      setIsLoadingProjects(false);
    }
  }, []);

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  // Fetch available frameworks
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        setLoadingStack(true);
        setStackError(null);
        const [beRes, feRes] = await Promise.all([
          fetch('/api/v2/frameworks?framework_type=backend'),
          fetch('/api/v2/frameworks?framework_type=frontend')
        ]);
        if (!beRes.ok || !feRes.ok) throw new Error('Failed to load framework options');
        const beData = await beRes.json();
        const feData = await feRes.json();
        const beList = Array.isArray(beData.frameworks) ? beData.frameworks : [];
        const feList = Array.isArray(feData.frameworks) ? feData.frameworks : [];
        if (!cancelled) {
          setBackendOptions(beList);
          setFrontendOptions(feList);
          const savedBE = localStorage.getItem('sb_pref_backend') || '';
          const savedFE = localStorage.getItem('sb_pref_frontend') || '';
          setSelectedBackend(savedBE || (beList[0]?.id || ''));
          setSelectedFrontend(savedFE || (feList[0]?.id || ''));
        }
      } catch (e: any) {
        if (!cancelled) setStackError(e?.message ?? 'Unable to load tech stack options');
      } finally {
        if (!cancelled) setLoadingStack(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    try { if (selectedBackend) localStorage.setItem('sb_pref_backend', selectedBackend); } catch { }
  }, [selectedBackend]);
  useEffect(() => {
    try { if (selectedFrontend) localStorage.setItem('sb_pref_frontend', selectedFrontend); } catch { }
  }, [selectedFrontend]);

  const refreshInProgress = useCallback(async () => {
    setLoadingInProgress(true);
    setInProgressError(null);
    try {
      const res = await fetch('/api/builds');
      if (!res.ok) throw new Error(`Request failed with status ${res.status}`);
      const data = await res.json();
      const builds: BuildSummary[] = Array.isArray(data?.builds) ? data.builds : [];
      const active = builds.filter(b => {
        const st = (b.status || '').toLowerCase();
        return st !== 'success' && st !== 'failed' && st !== 'error';
      });
      setInProgressBuilds(active);
    } catch (e: any) {
      setInProgressError(e?.message ?? 'Failed to load in-progress builds');
    } finally {
      setLoadingInProgress(false);
    }
  }, []);

  useEffect(() => {
    const savedId = typeof window !== 'undefined' ? localStorage.getItem('sb_active_build_id') : null;
    if (savedId && !buildProgress) {
      (async () => {
        try {
          const res = await fetch(`/api/build/${savedId}/status`);
          if (!res.ok) throw new Error(`status ${res.status}`);
          const data = await res.json();
          if (!data || data.error) {
            localStorage.removeItem('sb_active_build_id');
            return;
          }
          setBuildProgress({
            build_id: savedId,
            status: data.status || 'building',
            progress: data.progress ?? 0,
            current_step: data.current_step || '',
            logs: Array.isArray(data.logs) ? data.logs : []
          });
        } catch {
          localStorage.removeItem('sb_active_build_id');
        }
      })();
    }
    refreshInProgress();
  }, []);

  const isFinished = useMemo(() => {
    const st = (buildProgress?.status || '').toLowerCase();
    const prog = buildProgress?.progress ?? 0;
    return st === 'success' || st === 'failed' || st === 'error' || prog >= 100;
  }, [buildProgress?.status, buildProgress?.progress]);

  useEffect(() => {
    if (buildProgress?.build_id && !wsConnection && !isFinished) {
      const now = Date.now();
      if (now - lastConnectAtRef.current < 800) {
        return; // throttle reconnects
      }
      lastConnectAtRef.current = now;
      const wsProtocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
      const ws = new WebSocket(`${wsProtocol}://${window.location.host}/ws/build/${buildProgress.build_id}`);

      ws.onopen = () => {
        setWsConnection(ws);
      };

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        setBuildProgress(data);

        const st = (data?.status ?? '').toLowerCase();
        if (st === 'success' || st === 'failed' || st === 'error' || (data?.progress ?? 0) >= 100) {
          try { ws.close(); } catch { }
          setWsConnection(null);
          try { localStorage.removeItem('sb_active_build_id'); } catch { }
          refreshInProgress();
        }
      };

      ws.onerror = () => {
        setWsConnection(null);
      };

      ws.onclose = () => {
        setWsConnection(null);
      };

      return () => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.close();
        }
      };
    }
  }, [buildProgress?.build_id, isFinished]);

  useEffect(() => {
    const width = Math.max(0, Math.min(100, buildProgress?.progress ?? 0));
    if (progressBarRef.current) {
      progressBarRef.current.style.width = `${width}%`;
    }
  }, [buildProgress?.progress]);

  // Load friendly labels (project name) for in-progress builds
  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (!inProgressBuilds.length) {
        setInProgressLabels({});
        return;
      }
      try {
        const entries = await Promise.all(
          inProgressBuilds.map(async (b) => {
            try {
              const res = await fetch(`/api/build/${b.build_id}/status`);
              const data = await res.json();
              const sp: string = data?.source_path || '';
              const name = sp ? sp.split(/[\\\/]/).filter(Boolean).slice(-1)[0] : '';
              return [b.build_id, name || b.build_id] as const;
            } catch {
              return [b.build_id, b.build_id] as const;
            }
          })
        );
        if (!cancelled) {
          const map: Record<string, string> = {};
          for (const [id, label] of entries) map[id] = label;
          setInProgressLabels(map);
        }
      } catch {
        if (!cancelled) setInProgressLabels({});
      }
    })();
    return () => { cancelled = true; };
  }, [inProgressBuilds]);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!description.trim()) {
      setSubmissionError('Please provide a project description.');
      return;
    }

    setSubmissionError(null);
    setIsSubmitting(true);
    setBuildResult(null);

    try {
      const payload = {
        description: description.trim(),
        name: projectName.trim() || undefined,
        requirements: parsedRequirements,
        preferred_backend: selectedBackend || undefined,
        preferred_frontend: selectedFrontend || undefined,
      };

      const response = await fetch('/api/build', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const message = errorData?.detail ?? `Build request failed with status ${response.status}`;
        throw new Error(message);
      }

      const result = (await response.json()) as BuildResult;
      setBuildResult(result);
      if (result.build_id) {
        setBuildProgress({
          build_id: result.build_id,
          status: 'building',
          progress: 10,
          current_step: 'Starting build...',
          logs: []
        });
        try { localStorage.setItem('sb_active_build_id', result.build_id); } catch { }
      }
      fetchProjects();
      refreshInProgress();
    } catch (error: any) {
      setSubmissionError(error?.message ?? 'Failed to submit build request');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleResume = async (buildId: string) => {
    try {
      const res = await fetch(`/api/build/${buildId}/status`);
      if (!res.ok) throw new Error(`Request failed with status ${res.status}`);
      const data = await res.json();
      if (!data || data.error) throw new Error('Build not found');
      setBuildProgress({
        build_id: buildId,
        status: data.status || 'building',
        progress: data.progress ?? 0,
        current_step: data.current_step || '',
        logs: Array.isArray(data.logs) ? data.logs : []
      });
      try { localStorage.setItem('sb_active_build_id', buildId); } catch { }
    } catch (e) {
      await refreshInProgress();
    }
  };

  const handleStopBuild = async (buildId: string) => {
    try {
      const confirmed = window.confirm('Stop and remove this build?');
      if (!confirmed) return;
      const res = await fetch(`/api/build/${buildId}`, { method: 'DELETE' });
      if (!res.ok) throw new Error(`Failed to stop build (status ${res.status})`);
      if (buildProgress?.build_id === buildId) {
        setBuildProgress(null);
        try { localStorage.removeItem('sb_active_build_id'); } catch { }
      }
      await refreshInProgress();
    } catch (e) {
      // no-op; UI will refresh list
    }
  };

  return (
    <div className="space-y-8 py-2">
      <section className="glass-panel rounded-2xl p-8 relative overflow-hidden">
        {/* Decorative background element */}
        <div className="absolute top-0 right-0 -mt-10 -mr-10 w-64 h-64 bg-primary/10 rounded-full blur-3xl pointer-events-none"></div>

        <div className="grid gap-12 xl:grid-cols-[minmax(0,_2fr)_minmax(0,_1fr)] relative">
          <div className="space-y-8">
            <div>
              <h2 className="text-3xl font-bold text-white mb-2">Request a New Project</h2>
              <p className="text-gray-400 text-lg">Describe the project you want and let the enhanced workflow build it for you.</p>
            </div>

            <form className="space-y-8" onSubmit={handleSubmit}>
              <div className="space-y-3">
                <label className="block text-sm font-medium text-gray-300 uppercase tracking-wide">Project Description</label>
                <textarea
                  value={description}
                  onChange={(event) => setDescription(event.target.value)}
                  className="w-full min-h-[160px] px-6 py-4 bg-black/20 border border-white/10 rounded-xl focus:ring-2 focus:ring-primary/50 text-white placeholder-gray-500 outline-none transition-all text-base leading-relaxed resize-none"
                  placeholder="Build a task management app with authentication and a dashboard..."
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                <div className="space-y-3">
                  <label className="block text-sm font-medium text-gray-300 uppercase tracking-wide">Project Name (optional)</label>
                  <input
                    type="text"
                    value={projectName}
                    onChange={(event) => setProjectName(event.target.value)}
                    className="w-full px-5 py-3 bg-black/20 border border-white/10 rounded-xl focus:ring-2 focus:ring-primary/50 text-white placeholder-gray-500 outline-none transition-all"
                    placeholder="my-awesome-project"
                  />
                </div>

                <div className="space-y-3">
                  <label className="block text-sm font-medium text-gray-300 uppercase tracking-wide">Requirements (optional)</label>
                  <textarea
                    value={requirementsText}
                    onChange={(event) => setRequirementsText(event.target.value)}
                    className="w-full min-h-[50px] px-5 py-3 bg-black/20 border border-white/10 rounded-xl focus:ring-2 focus:ring-primary/50 text-white placeholder-gray-500 outline-none transition-all"
                    placeholder="authentication, dashboard, notifications"
                  />
                  <p className="text-xs text-gray-500">Separate requirements with commas or new lines.</p>
                </div>
              </div>

              {submissionError && (
                <div className="rounded-xl bg-red-500/10 border border-red-500/20 px-6 py-4 text-sm text-red-200">
                  <div className="flex items-center space-x-2">
                    <i className="fas fa-exclamation-circle text-red-400"></i>
                    <span>{submissionError}</span>
                  </div>
                </div>
              )}

              {buildResult && (
                <div className="rounded-xl bg-emerald-500/10 border border-emerald-500/20 px-6 py-4 text-sm text-emerald-100 space-y-2">
                  <div className="flex items-center space-x-2 font-semibold text-emerald-400">
                    <i className="fas fa-check-circle"></i>
                    <p>Build request submitted successfully.</p>
                  </div>
                  {buildResult.build_id && <p className="pl-6 opacity-80">Build ID: <span className="font-mono">{buildResult.build_id}</span></p>}
                  {buildResult.message && <p className="pl-6 opacity-80">{buildResult.message}</p>}
                  {buildResult.source_path && <p className="pl-6 opacity-80">Source: {buildResult.source_path}</p>}
                </div>
              )}

              <div className="flex justify-end pt-2">
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="bg-gradient-to-r from-primary to-accent hover:from-primary/90 hover:to-accent/90 disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold px-8 py-3 rounded-xl shadow-lg shadow-primary/25 transition-all transform hover:scale-105 flex items-center space-x-2"
                >
                  {isSubmitting ? (
                    <>
                      <i className="fas fa-circle-notch fa-spin"></i>
                      <span>Submitting...</span>
                    </>
                  ) : (
                    <>
                      <i className="fas fa-magic"></i>
                      <span>Generate Project</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>

          <div className="space-y-6">
            <div className="rounded-2xl border border-white/10 bg-white/5 p-6 backdrop-blur-sm">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-bold text-gray-200 uppercase tracking-wider">Tech Stack</h3>
                {loadingStack && (<span className="text-xs text-gray-500 animate-pulse">Loading...</span>)}
              </div>
              {stackError && (
                <div className="rounded bg-red-500/20 text-red-200 text-xs px-3 py-2 mb-4">{stackError}</div>
              )}
              <div className="space-y-5">
                <div>
                  <label className="block text-xs font-medium text-gray-400 mb-2">Backend Framework</label>
                  <div className="relative">
                    <select
                      value={selectedBackend}
                      onChange={(e) => setSelectedBackend(e.target.value)}
                      className="w-full px-4 py-3 bg-black/40 border border-white/10 rounded-xl appearance-none text-white focus:ring-2 focus:ring-primary/50 outline-none"
                    >
                      {backendOptions.map((fw) => (
                        <option key={fw.id} value={fw.id} className="bg-slate-900">{fw.name} ({fw.language})</option>
                      ))}
                    </select>
                    <i className="fas fa-chevron-down absolute right-4 top-4 text-gray-500 pointer-events-none"></i>
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-400 mb-2">Frontend Framework</label>
                  <div className="relative">
                    <select
                      value={selectedFrontend}
                      onChange={(e) => setSelectedFrontend(e.target.value)}
                      className="w-full px-4 py-3 bg-black/40 border border-white/10 rounded-xl appearance-none text-white focus:ring-2 focus:ring-primary/50 outline-none"
                    >
                      {frontendOptions.map((fw) => (
                        <option key={fw.id} value={fw.id} className="bg-slate-900">{fw.name} ({fw.language})</option>
                      ))}
                    </select>
                    <i className="fas fa-chevron-down absolute right-4 top-4 text-gray-500 pointer-events-none"></i>
                  </div>
                </div>
              </div>
            </div>

            <div className="space-y-4">
              {inProgressError && (
                <div className="rounded-xl bg-amber-500/10 border border-amber-500/20 px-4 py-3 text-sm text-amber-200">{inProgressError}</div>
              )}
              {(!loadingInProgress && inProgressBuilds.length > 0) && (
                <div className="rounded-2xl border border-white/10 p-6 bg-white/5 backdrop-blur-sm">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-sm font-bold text-gray-200 uppercase tracking-wider">In-Progress Builds</h3>
                    <button onClick={refreshInProgress} className="text-xs text-primary hover:text-primary-foreground transition-colors"><i className="fas fa-sync-alt mr-1"></i>Refresh</button>
                  </div>
                  <div className="space-y-3">
                    {inProgressBuilds.map((b) => (
                      <div key={b.build_id} className="flex items-center justify-between text-sm bg-black/20 p-3 rounded-lg border border-white/5">
                        <div className="truncate mr-2 flex-1">
                          <div className="text-white font-medium truncate">{inProgressLabels[b.build_id] || b.build_id}</div>
                          <div className="flex items-center text-xs text-gray-500 mt-1">
                            <span className="font-mono bg-white/10 px-1.5 rounded mr-2">{b.build_id.substring(0, 8)}...</span>
                            <span className={`px-2 py-0.5 rounded-full text-[10px] uppercase font-bold tracking-wider ${b.status === 'building' ? 'bg-amber-500/20 text-amber-300' : 'bg-gray-500/20 text-gray-400'
                              }`}>{b.status}</span>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <button onClick={() => handleResume(b.build_id)} className="glass-button w-8 h-8 rounded-full text-blue-400 flex items-center justify-center p-0" title="View"><i className="fas fa-eye"></i></button>
                          <button onClick={() => handleStopBuild(b.build_id)} className="glass-button w-8 h-8 rounded-full text-red-400 flex items-center justify-center p-0" title="Stop"><i className="fas fa-trash"></i></button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
            {frameworksError && (
              <div className="rounded-xl bg-red-500/10 px-4 py-3 text-sm text-red-300 border border-red-500/20">
                {frameworksError}
              </div>
            )}
          </div>
        </div>
      </section>

      {buildProgress && (
        <section className="glass-panel rounded-2xl p-8 animate-fade-in border border-primary/20 shadow-lg shadow-primary/5">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h3 className="text-xl font-bold text-white flex items-center gap-3">
                <i className="fas fa-hard-hat text-amber-400 animate-pulse"></i>
                Build Progress
              </h3>
              <div className="text-sm text-gray-400 mt-1 pl-8">
                {(inProgressLabels[buildProgress.build_id] || buildProgress.build_id)}
                <span className="ml-2 font-mono text-gray-600">({buildProgress.build_id})</span>
              </div>
            </div>
            <span className="text-2xl font-bold text-primary">{buildProgress.progress}%</span>
          </div>
          <p className="text-sm text-gray-300 mb-4 font-mono pl-1"><i className="fas fa-terminal mr-2 text-gray-500"></i>{buildProgress.current_step}</p>
          <div className="mb-8 p-1 bg-black/30 rounded-full border border-white/5">
            <div className="w-full bg-gray-800 rounded-full h-3 overflow-hidden">
              <div
                ref={progressBarRef}
                className={`h-full ${getProgressColor(buildProgress.progress)} transition-all duration-500 shadow-[0_0_10px_rgba(99,102,241,0.5)]`}
              />
            </div>
          </div>
          {Array.isArray(buildProgress.logs) && buildProgress.logs.length > 0 && (
            <div className="bg-black/80 rounded-xl p-6 max-h-[300px] overflow-y-auto border border-white/10 font-mono text-xs custom-scrollbar">
              {buildProgress.logs.slice(-15).map((log, idx) => (
                <div key={idx} className="mb-1.5 last:mb-0 break-all">
                  <span className="text-gray-600 mr-3 select-none">{new Date(log.timestamp).toLocaleTimeString()}</span>
                  <span className={`font-bold mr-3 ${log.level === 'error' ? 'text-red-400' :
                    log.level === 'warning' ? 'text-yellow-400' :
                      'text-emerald-400'
                    }`}>
                    [{(log.level || 'info').toUpperCase()}]
                  </span>
                  <span className="text-gray-300">{log.message}</span>
                </div>
              ))}
            </div>
          )}
        </section>
      )}

      <section className="glass-panel rounded-2xl p-8 space-y-8">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-white">Generated Projects</h2>
            <p className="text-gray-400">Projects stored under the generated directory.</p>
          </div>
          <button
            onClick={fetchProjects}
            disabled={isLoadingProjects}
            className="glass-button bg-white/5 hover:bg-white/10 text-white font-semibold px-6 py-2.5 rounded-xl flex items-center space-x-2"
          >
            <i className={`fas fa-sync-alt ${isLoadingProjects ? 'fa-spin' : ''}`}></i>
            <span>{isLoadingProjects ? 'Refreshing...' : 'Refresh'}</span>
          </button>
        </div>

        {projectsError && (
          <div className="rounded-xl bg-red-500/10 border border-red-500/20 px-6 py-4 text-sm text-red-200">
            {projectsError}
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
          {projects.map((project) => (
            <div
              key={project.path}
              className="group bg-white/5 hover:bg-white/10 border border-white/5 hover:border-primary/30 rounded-2xl p-6 space-y-4 cursor-pointer transition-all duration-300 hover:shadow-xl hover:shadow-primary/10 relative overflow-hidden"
              onClick={() => onOpenEditor(project.path)}
              title="Open in Editor"
            >
              <div className="absolute top-0 right-0 p-4 opacity-0 group-hover:opacity-100 transition-opacity">
                <i className="fas fa-external-link-alt text-gray-400"></i>
              </div>

              <div>
                <h3 className="text-xl font-bold text-white mb-1 group-hover:text-primary transition-colors">{project.name}</h3>
                <p className="text-xs text-gray-500 font-mono break-all truncate">{project.path}</p>
              </div>

              <div className="py-2 flex items-center space-x-2">
                <span className={`text-xs px-3 py-1 rounded-full border ${project.has_backend ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/20' : 'bg-gray-500/10 text-gray-500 border-gray-500/20'}`}>
                  {project.has_backend ? <><i className="fas fa-check mr-1"></i>Backend</> : 'No Backend'}
                </span>
                <span className={`text-xs px-3 py-1 rounded-full border ${project.has_frontend ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/20' : 'bg-gray-500/10 text-gray-500 border-gray-500/20'}`}>
                  {project.has_frontend ? <><i className="fas fa-check mr-1"></i>Frontend</> : 'No Frontend'}
                </span>
              </div>

              <div className="pt-3 border-t border-white/5 flex items-center justify-between text-xs text-gray-500">
                <span><i className="far fa-clock mr-1"></i>{formatTimestamp(project.created_at)}</span>
                <span className="text-primary font-medium opacity-0 group-hover:opacity-100 transition-opacity">Open Project &rarr;</span>
              </div>
            </div>
          ))}
        </div>

        {!isLoadingProjects && projects.length === 0 && !projectsError && (
          <div className="text-center py-12 bg-white/5 rounded-2xl border border-dashed border-white/10">
            <div className="w-16 h-16 bg-white/5 rounded-full flex items-center justify-center mx-auto mb-4">
              <i className="fas fa-folder-open text-2xl text-gray-500"></i>
            </div>
            <p className="text-gray-400">No generated projects found.</p>
            <p className="text-sm text-gray-600 mt-1">Submit a build request above to create one.</p>
          </div>
        )}
      </section>
    </div>
  );
};
