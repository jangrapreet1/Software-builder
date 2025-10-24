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
    try { if (selectedBackend) localStorage.setItem('sb_pref_backend', selectedBackend); } catch {}
  }, [selectedBackend]);
  useEffect(() => {
    try { if (selectedFrontend) localStorage.setItem('sb_pref_frontend', selectedFrontend); } catch {}
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
          try { ws.close(); } catch {}
          setWsConnection(null);
          try { localStorage.removeItem('sb_active_build_id'); } catch {}
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
        try { localStorage.setItem('sb_active_build_id', result.build_id); } catch {}
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
      try { localStorage.setItem('sb_active_build_id', buildId); } catch {}
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
        try { localStorage.removeItem('sb_active_build_id'); } catch {}
      }
      await refreshInProgress();
    } catch (e) {
      // no-op; UI will refresh list
    }
  };

  return (
    <div className="container mx-auto px-4 py-8 space-y-8">
      <section className="bg-white rounded-lg shadow-lg p-6">
        <div className="grid gap-8 xl:grid-cols-[minmax(0,_2fr)_minmax(0,_1fr)]">
          <div className="space-y-6">
            <div>
              <h2 className="text-2xl font-bold text-gray-900">Request a New Project</h2>
              <p className="text-gray-600">Describe the project you want and let the enhanced workflow build it for you.</p>
            </div>

            <form className="space-y-6" onSubmit={handleSubmit}>
              <div className="space-y-2">
                <label className="block text-sm font-medium text-gray-700">Project Description</label>
                <textarea
                  value={description}
                  onChange={(event) => setDescription(event.target.value)}
                  className="w-full min-h-[120px] px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="Build a task management app with authentication and a dashboard..."
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-gray-700">Project Name (optional)</label>
                  <input
                    type="text"
                    value={projectName}
                    onChange={(event) => setProjectName(event.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    placeholder="my-awesome-project"
                  />
                </div>

                <div className="space-y-2">
                  <label className="block text-sm font-medium text-gray-700">Requirements (optional)</label>
                  <textarea
                    value={requirementsText}
                    onChange={(event) => setRequirementsText(event.target.value)}
                    className="w-full min-h-[80px] px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    placeholder="authentication, dashboard, notifications"
                  />
                  <p className="text-xs text-gray-500">Separate requirements with commas or new lines.</p>
                </div>
              </div>

              {submissionError && (
                <div className="rounded-md bg-red-50 px-4 py-3 text-sm text-red-700">
                  {submissionError}
                </div>
              )}

              {buildResult && (
                <div className="rounded-md bg-green-50 px-4 py-3 text-sm text-green-800 space-y-1">
                  <p className="font-semibold">Build request submitted successfully.</p>
                  {buildResult.build_id && <p>Build ID: {buildResult.build_id}</p>}
                  {buildResult.message && <p>{buildResult.message}</p>}
                  {buildResult.source_path && <p>Source: {buildResult.source_path}</p>}
                </div>
              )}

              <div className="flex justify-end">
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="bg-blue-600 hover:bg-blue-700 disabled:hover:bg-blue-600 disabled:opacity-60 text-white font-semibold px-6 py-2 rounded-lg transition"
                >
                  {isSubmitting ? 'Submitting...' : 'Submit Build Request'}
                </button>
              </div>
            </form>
          </div>

          <div className="space-y-4">
            <div className="rounded-md border border-gray-200 p-4">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-sm font-semibold text-gray-800">Tech Stack</h3>
                {loadingStack && (<span className="text-xs text-gray-500">Loading...</span>)}
              </div>
              {stackError && (
                <div className="rounded bg-red-50 text-red-700 text-xs px-2 py-1 mb-2">{stackError}</div>
              )}
              <div className="space-y-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Backend</label>
                  <select
                    value={selectedBackend}
                    onChange={(e) => setSelectedBackend(e.target.value)}
                    className="w-full px-2 py-2 border border-gray-300 rounded-md"
                    title="Select backend framework"
                  >
                    {backendOptions.map((fw) => (
                      <option key={fw.id} value={fw.id}>{fw.name} · {fw.language.toUpperCase()}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Frontend</label>
                  <select
                    value={selectedFrontend}
                    onChange={(e) => setSelectedFrontend(e.target.value)}
                    className="w-full px-2 py-2 border border-gray-300 rounded-md"
                    title="Select frontend framework"
                  >
                    {frontendOptions.map((fw) => (
                      <option key={fw.id} value={fw.id}>{fw.name} · {fw.language.toUpperCase()}</option>
                    ))}
                  </select>
                </div>
              </div>
            </div>
            <div className="space-y-3">
              {inProgressError && (
                <div className="rounded-md bg-yellow-50 px-4 py-3 text-sm text-yellow-800">{inProgressError}</div>
              )}
              {(!loadingInProgress && inProgressBuilds.length > 0) && (
                <div className="rounded-md border border-gray-200 p-4">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="text-sm font-semibold text-gray-800">In-Progress Builds</h3>
                    <button onClick={refreshInProgress} className="text-sm text-blue-600 hover:text-blue-700">Refresh</button>
                  </div>
                  <div className="space-y-2">
                    {inProgressBuilds.map((b) => (
                      <div key={b.build_id} className="flex items-center justify-between text-sm">
                        <div className="truncate mr-2">
                          <span className="text-gray-900 font-medium">{inProgressLabels[b.build_id] || b.build_id}</span>
                          <span className="ml-2 font-mono text-gray-500">({b.build_id})</span>
                          <span className="ml-2 px-2 py-0.5 rounded-full text-xs bg-yellow-100 text-yellow-700">{b.status}</span>
                        </div>
                        <div className="flex items-center gap-3">
                          <button onClick={() => handleResume(b.build_id)} className="text-blue-600 hover:text-blue-800">Show Progress</button>
                          <button onClick={() => handleStopBuild(b.build_id)} className="text-red-600 hover:text-red-700">Stop</button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
            {frameworksError && (
              <div className="rounded-md bg-red-50 px-4 py-3 text-sm text-red-700">
                {frameworksError}
              </div>
            )}
            {/* Controls removed as requested */}
          </div>
        </div>
      </section>

      {buildProgress && (
        <section className="bg-white rounded-lg shadow-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-lg font-bold text-gray-900">Build Progress</h3>
              <div className="text-xs text-gray-600 mt-0.5">
                {(inProgressLabels[buildProgress.build_id] || buildProgress.build_id)}
                <span className="ml-1 text-gray-400">({buildProgress.build_id})</span>
              </div>
            </div>
            <span className="text-sm text-gray-600">{buildProgress.progress}%</span>
          </div>
          <p className="text-sm text-gray-600 mb-4">{buildProgress.current_step}</p>
          <div className="mb-6">
            <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
              <div
                ref={progressBarRef}
                className={`h-full ${getProgressColor(buildProgress.progress)} transition-all duration-500`}
              />
            </div>
          </div>
          {Array.isArray(buildProgress.logs) && buildProgress.logs.length > 0 && (
            <div className="bg-gray-900 rounded-lg p-4 max-h-56 overflow-y-auto">
              {buildProgress.logs.slice(-10).map((log, idx) => (
                <div key={idx} className="text-sm font-mono">
                  <span className="text-gray-500 text-xs">{new Date(log.timestamp).toLocaleTimeString()}</span>
                  <span className={`ml-2 ${
                    log.level === 'error' ? 'text-red-400' :
                    log.level === 'warning' ? 'text-yellow-400' :
                    'text-green-400'
                  }`}>
                    [{(log.level || 'info').toUpperCase()}]
                  </span>
                  <span className="text-gray-300 ml-2">{log.message}</span>
                </div>
              ))}
            </div>
          )}
        </section>
      )}

      <section className="bg-white rounded-lg shadow-lg p-6 space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Generated Projects</h2>
            <p className="text-gray-600">Projects stored under the generated directory.</p>
          </div>
          <button
            onClick={fetchProjects}
            disabled={isLoadingProjects}
            className="bg-gray-900 hover:bg-gray-700 disabled:opacity-60 text-white font-semibold px-4 py-2 rounded-lg transition"
          >
            {isLoadingProjects ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>

        {projectsError && (
          <div className="rounded-md bg-red-50 px-4 py-3 text-sm text-red-700">
            {projectsError}
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
          {projects.map((project) => (
            <div
              key={project.path}
              className="border border-gray-200 rounded-lg p-5 space-y-3 hover:shadow-md hover:border-blue-300 cursor-pointer transition"
              onClick={() => onOpenEditor(project.path)}
              title="Open in Editor"
            >
              <div>
                <h3 className="text-lg font-semibold text-gray-900">{project.name}</h3>
                <p className="text-sm text-gray-500 break-all">{project.path}</p>
              </div>
              <div className="text-sm text-gray-600 space-y-1">
                <p>Created: {formatTimestamp(project.created_at)}</p>
                <p>Updated: {formatTimestamp(project.updated_at)}</p>
              </div>
              <div className="flex items-center space-x-2 text-sm">
                <span className={`${project.has_backend ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'} px-3 py-1 rounded-full`}>
                  Backend
                </span>
                <span className={`${project.has_frontend ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'} px-3 py-1 rounded-full`}>
                  Frontend
                </span>
              </div>
              <div className="pt-2">
                <button
                  onClick={(e) => { e.stopPropagation(); onOpenEditor(project.path); }}
                  className="text-blue-600 hover:text-blue-800 text-sm"
                >
                  Open in Editor
                </button>
              </div>
            </div>
          ))}
        </div>

        {!isLoadingProjects && projects.length === 0 && !projectsError && (
          <div className="text-center text-gray-500 text-sm">
            No generated projects found. Submit a build request to create one.
          </div>
        )}
      </section>
    </div>
  );
};
