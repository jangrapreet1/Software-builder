import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { ControlsPanel } from './ControlsPanel';
import { FrameworkOption } from '../types';

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

type DetectedCommands = {
  buildCmd?: string[];
  runCmd?: string[];
};

interface ProjectExplorerProps {
  detectedCommands?: DetectedCommands;
  backendOptions: FrameworkOption[];
  frontendOptions: FrameworkOption[];
  selectedBackend?: string;
  selectedFrontend?: string;
  onBackendChange: (frameworkId: string) => void;
  onFrontendChange: (frameworkId: string) => void;
  onLaunch: (sessionId: string) => void;
  onStop: (instanceId: string) => void;
  onDownload: () => void;
  isRunning?: boolean;
  instanceId?: string;
  sessionId?: string;
  frameworksError?: string | null;
  isLoadingFrameworks?: boolean;
  onRequestTests?: () => void;
  onOpenPR?: () => void;
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
  detectedCommands,
  backendOptions,
  frontendOptions,
  selectedBackend,
  selectedFrontend,
  onBackendChange,
  onFrontendChange,
  onLaunch,
  onStop,
  onDownload,
  isRunning = false,
  instanceId,
  sessionId,
  frameworksError,
  isLoadingFrameworks = false,
  onRequestTests,
  onOpenPR,
}) => {
  const [description, setDescription] = useState('');
  const [projectName, setProjectName] = useState('');
  const [requirementsText, setRequirementsText] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [buildResult, setBuildResult] = useState<BuildResult | null>(null);
  const [submissionError, setSubmissionError] = useState<string | null>(null);

  const [projects, setProjects] = useState<ProjectItem[]>([]);
  const [isLoadingProjects, setIsLoadingProjects] = useState(false);
  const [projectsError, setProjectsError] = useState<string | null>(null);

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
      fetchProjects();
    } catch (error: any) {
      setSubmissionError(error?.message ?? 'Failed to submit build request');
    } finally {
      setIsSubmitting(false);
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
            {frameworksError && (
              <div className="rounded-md bg-red-50 px-4 py-3 text-sm text-red-700">
                {frameworksError}
              </div>
            )}

            <ControlsPanel
              instanceId={instanceId}
              sessionId={sessionId}
              detectedCommands={detectedCommands}
              backendOptions={backendOptions}
              frontendOptions={frontendOptions}
              selectedBackend={selectedBackend}
              selectedFrontend={selectedFrontend}
              onBackendChange={onBackendChange}
              onFrontendChange={onFrontendChange}
              onLaunch={onLaunch}
              onStop={onStop}
              onDownload={onDownload}
              onRequestTests={onRequestTests}
              onOpenPR={onOpenPR}
              isRunning={isRunning}
              isLoadingFrameworks={isLoadingFrameworks}
            />
          </div>
        </div>
      </section>

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
            <div key={project.path} className="border border-gray-200 rounded-lg p-5 space-y-3">
              <div>
                <h3 className="text-lg font-semibold text-gray-900">{project.name}</h3>
                <p className="text-sm text-gray-500 break-all">{project.path}</p>
              </div>
              <div className="text-sm text-gray-600 space-y-1">
                <p>Created: {formatTimestamp(project.created_at)}</p>
                <p>Updated: {formatTimestamp(project.updated_at)}</p>
              </div>
              <div className="flex items-center space-x-2 text-sm">
                <span className={`px-3 py-1 rounded-full ${project.has_backend ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                  Backend
                </span>
                <span className={`px-3 py-1 rounded-full ${project.has_frontend ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                  Frontend
                </span>
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
