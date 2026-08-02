import React, { useCallback, useEffect, useState } from 'react';

type ProjectItem = {
  name: string;
  path: string;
  created_at: string;
  updated_at: string;
  has_backend: boolean;
  has_frontend: boolean;
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
  onGoToBuilder?: () => void;
}

const formatTimestamp = (value: string) => {
  try {
    const date = new Date(value);
    return date.toLocaleString();
  } catch {
    return value;
  }
};

export const ProjectExplorer: React.FC<ProjectExplorerProps> = ({
  frameworksError,
  onOpenEditor,
  onGoToBuilder,
}) => {
  const [projects, setProjects] = useState<ProjectItem[]>([]);
  const [isLoadingProjects, setIsLoadingProjects] = useState(false);
  const [projectsError, setProjectsError] = useState<string | null>(null);
  const [inProgressBuilds, setInProgressBuilds] = useState<BuildSummary[]>([]);

  const fetchProjects = useCallback(async () => {
    setIsLoadingProjects(true);
    setProjectsError(null);
    try {
      const response = await fetch('/api/generated/projects');
      if (!response.ok) throw new Error(`Request failed with status ${response.status}`);
      const data = await response.json();
      setProjects(Array.isArray(data.projects) ? data.projects : []);
    } catch (error: unknown) {
      setProjectsError(error instanceof Error ? error.message : 'Failed to load projects');
    } finally {
      setIsLoadingProjects(false);
    }
  }, []);

  useEffect(() => { fetchProjects(); }, [fetchProjects]);

  // Check for in-progress builds (for the badge)
  useEffect(() => {
    fetch('/api/builds')
      .then(r => r.json())
      .then(d => {
        const builds: BuildSummary[] = Array.isArray(d?.builds) ? d.builds : [];
        const active = builds.filter(b => {
          const st = (b.status || '').toLowerCase();
          return st !== 'success' && st !== 'failed' && st !== 'error';
        });
        setInProgressBuilds(active);
      })
      .catch(() => {});
  }, []);

  return (
    <div className="space-y-6 py-2">
      {/* In-progress builds banner */}
      {inProgressBuilds.length > 0 && (
        <div
          className="glass-panel rounded-2xl p-4 border-l-4 border-amber-500 cursor-pointer hover:bg-white/5 transition-all"
          onClick={onGoToBuilder}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-amber-500/10 flex items-center justify-center">
                <i className="fas fa-hard-hat text-amber-400 animate-pulse"></i>
              </div>
              <div>
                <h3 className="text-sm font-bold text-white">
                  {inProgressBuilds.length} Build{inProgressBuilds.length > 1 ? 's' : ''} in Progress
                </h3>
                <p className="text-xs text-gray-400">Click to view in the Builder tab</p>
              </div>
            </div>
            <i className="fas fa-arrow-right text-amber-400"></i>
          </div>
        </div>
      )}

      {frameworksError && (
        <div className="rounded-xl bg-red-500/10 px-4 py-3 text-sm text-red-300 border border-red-500/20">
          {frameworksError}
        </div>
      )}

      {/* Generated Projects */}
      <section className="glass-panel rounded-2xl p-8 space-y-8">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-white">Generated Projects</h2>
            <p className="text-gray-400">Projects built by the autonomous agents.</p>
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
          <div className="text-center py-16 bg-white/5 rounded-2xl border border-dashed border-white/10">
            <div className="w-16 h-16 bg-white/5 rounded-full flex items-center justify-center mx-auto mb-4">
              <i className="fas fa-folder-open text-2xl text-gray-500"></i>
            </div>
            <p className="text-gray-400 mb-2">No generated projects found.</p>
            <p className="text-sm text-gray-600 mb-6">Go to the Builder tab to create your first app.</p>
            {onGoToBuilder && (
              <button
                onClick={onGoToBuilder}
                className="px-6 py-2.5 bg-gradient-to-r from-indigo-500 to-purple-600 text-white font-semibold rounded-xl hover:scale-105 transition-transform shadow-lg shadow-indigo-500/25"
              >
                <i className="fas fa-wand-magic-sparkles mr-2"></i>Go to Builder
              </button>
            )}
          </div>
        )}
      </section>
    </div>
  );
};
