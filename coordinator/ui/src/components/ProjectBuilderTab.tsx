import React, { useState, useEffect, useMemo, useRef } from 'react';

interface Project {
  name: string;
  path: string;
  created_at?: string;
  description?: string;
  status: string;
  has_backend: boolean;
  has_frontend: boolean;
}

interface ProjectBuilderTabProps {
  selectedProject: Project | null;
  onProjectSelect: (project: Project) => void;
  projects: Project[];
  onProjectsUpdate: () => void;
  addNotification: (notification: any) => void;
}

interface BuildProgress {
  build_id: string;
  status: string;
  progress: number;
  current_step: string;
  logs: Array<{
    level: string;
    message: string;
    timestamp: string;
  }>;
}

export const ProjectBuilderTab: React.FC<ProjectBuilderTabProps> = ({
  selectedProject,
  onProjectSelect,
  projects,
  onProjectsUpdate,
  addNotification
}) => {
  const [description, setDescription] = useState('');
  const [projectName, setProjectName] = useState('');
  const [requirements, setRequirements] = useState<string[]>([]);
  const [newRequirement, setNewRequirement] = useState('');
  const [building, setBuilding] = useState(false);
  const [buildProgress, setBuildProgress] = useState<BuildProgress | null>(null);
  const [wsConnection, setWsConnection] = useState<WebSocket | null>(null);
  const lastConnectAtRef = useRef<number>(0);

  const isFinished = useMemo(() => {
    const st = (buildProgress?.status || '').toLowerCase();
    const prog = buildProgress?.progress ?? 0;
    return st === 'success' || st === 'failed' || st === 'error' || prog >= 100;
  }, [buildProgress?.status, buildProgress?.progress]);

  // WebSocket connection for real-time progress
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
        console.log('WebSocket connected');
        setWsConnection(ws);
      };

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        setBuildProgress(data);

        if (data.status === 'success' || data.status === 'failed' || data.status === 'error' || (data.progress ?? 0) >= 100) {
          ws.close();
          setWsConnection(null);
          setBuilding(false);
          try { localStorage.removeItem('sb_active_build_id'); } catch {}

          if (data.status === 'success') {
            addNotification({
              type: 'success',
              title: 'Build Complete!',
              message: 'Your application has been built successfully',
              duration: 5000
            });
            onProjectsUpdate();
          } else {
            addNotification({
              type: 'error',
              title: 'Build Failed',
              message: 'Failed to build application. Check logs for details.',
              duration: 5000
            });
          }
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setWsConnection(null);
      };

      ws.onclose = () => {
        console.log('WebSocket disconnected');
        setWsConnection(null);
      };

      return () => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.close();
        }
      };
    }
  }, [buildProgress?.build_id, isFinished]);

  // Rehydrate from localStorage on mount
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
          setBuilding(true);
        } catch {
          try { localStorage.removeItem('sb_active_build_id'); } catch {}
        }
      })();
    }
  }, []);

  const handleAddRequirement = () => {
    if (newRequirement.trim()) {
      setRequirements([...requirements, newRequirement.trim()]);
      setNewRequirement('');
    }
  };

  const handleRemoveRequirement = (index: number) => {
    setRequirements(requirements.filter((_, i) => i !== index));
  };

  const handleBuildProject = async () => {
    if (!description.trim()) {
      addNotification({
        type: 'warning',
        title: 'Description Required',
        message: 'Please describe your application',
        duration: 3000
      });
      return;
    }

    try {
      setBuilding(true);
      setBuildProgress(null);

      const response = await fetch('/api/build', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          description: description,
          name: projectName || undefined,
          requirements: requirements.length > 0 ? requirements : undefined
        })
      });

      const result = await response.json();

      if (result.status === 'success' || result.build_id) {
        setBuildProgress({
          build_id: result.build_id,
          status: 'building',
          progress: 10,
          current_step: 'Starting build...',
          logs: []
        });
        try { localStorage.setItem('sb_active_build_id', result.build_id); } catch {}

        addNotification({
          type: 'info',
          title: 'Build Started',
          message: 'Your application is being built...',
          duration: 3000
        });
      } else {
        throw new Error(result.message || 'Build failed');
      }
    } catch (error: any) {
      console.error('Build failed:', error);
      addNotification({
        type: 'error',
        title: 'Build Failed',
        message: error.message || 'Failed to start build',
        duration: 5000
      });
      setBuilding(false);
    }
  };

  const getProgressColor = (progress: number) => {
    if (progress < 30) return 'bg-blue-500';
    if (progress < 70) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  return (
    <div className="space-y-6">
      {/* Build New Project Section */}
      <div className="bg-gradient-to-br from-blue-50 to-indigo-100 rounded-2xl shadow-2xl p-8 border-2 border-blue-200">
        <div className="flex items-center mb-6">
          <div className="w-12 h-12 bg-blue-600 rounded-xl flex items-center justify-center mr-4">
            <i className="fas fa-hammer text-white text-2xl"></i>
          </div>
          <div>
            <h2 className="text-2xl font-bold text-gray-800">Build New Application</h2>
            <p className="text-gray-600 text-sm">Describe your app and let AI build it for you</p>
          </div>
        </div>

        <div className="space-y-4">
          {/* Project Name */}
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              Project Name (Optional)
            </label>
            <input
              type="text"
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              placeholder="my-awesome-app"
              className="w-full px-4 py-3 border-2 border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition"
              disabled={building}
            />
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              Application Description *
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe your application in detail. For example: 'A task management app with user authentication, real-time updates, file uploads, and email notifications. Users can create projects, assign tasks to team members, set deadlines, and track progress with a dashboard.'"
              rows={6}
              className="w-full px-4 py-3 border-2 border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition resize-none"
              disabled={building}
            />
            <p className="text-xs text-gray-500 mt-2">
              <i className="fas fa-lightbulb mr-1"></i>
              Tip: Be specific about features, user flows, and technical requirements for best results
            </p>
          </div>

          {/* Requirements */}
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              Additional Requirements (Optional)
            </label>
            <div className="flex space-x-2 mb-3">
              <input
                type="text"
                value={newRequirement}
                onChange={(e) => setNewRequirement(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleAddRequirement()}
                placeholder="e.g., authentication, real-time updates, file upload"
                className="flex-1 px-4 py-2 border-2 border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                disabled={building}
              />
              <button
                onClick={handleAddRequirement}
                disabled={building}
                className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg font-semibold transition disabled:bg-gray-400"
                aria-label="Add requirement"
              >
                <i className="fas fa-plus"></i>
              </button>
            </div>

            {requirements.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {requirements.map((req, index) => (
                  <span
                    key={index}
                    className="bg-blue-100 text-blue-700 px-3 py-1 rounded-full text-sm flex items-center space-x-2"
                  >
                    <span>{req}</span>
                    <button
                      onClick={() => handleRemoveRequirement(index)}
                      disabled={building}
                      className="hover:text-blue-900"
                      aria-label="Remove requirement"
                    >
                      <i className="fas fa-times"></i>
                    </button>
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* Build Button */}
          <button
            onClick={handleBuildProject}
            disabled={building || !description.trim()}
            className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-bold py-4 rounded-xl transition-all duration-200 disabled:from-gray-400 disabled:to-gray-500 shadow-lg flex items-center justify-center space-x-2"
          >
            {building ? (
              <>
                <i className="fas fa-spinner fa-spin"></i>
                <span>Building Application...</span>
              </>
            ) : (
              <>
                <i className="fas fa-rocket"></i>
                <span>Build Application</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Build Progress */}
      {buildProgress && (
        <div className="bg-white rounded-2xl shadow-xl overflow-hidden border-2 border-blue-200">
          <div className="bg-gradient-to-r from-blue-600 to-indigo-600 px-6 py-4 text-white">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-lg font-bold">Build in Progress</h3>
              <span className="text-sm bg-white/20 px-3 py-1 rounded-full">
                {buildProgress.progress}%
              </span>
            </div>
            <p className="text-sm text-blue-100">{buildProgress.current_step}</p>
          </div>

          <div className="p-6">
            {/* Progress Bar */}
            <div className="mb-6">
              <div className="w-full bg-gray-200 rounded-full h-4 overflow-hidden">
                <div
                  className={`h-full ${getProgressColor(buildProgress.progress)} transition-all duration-500 flex items-center justify-end pr-2`}
                  style={{ width: `${buildProgress.progress}%` }}
                >
                  {buildProgress.progress > 10 && (
                    <span className="text-xs text-white font-bold">{buildProgress.progress}%</span>
                  )}
                </div>
              </div>
            </div>

            {/* Build Logs */}
            {buildProgress.logs && buildProgress.logs.length > 0 && (
              <div className="bg-gray-900 rounded-lg p-4 max-h-64 overflow-y-auto">
                <div className="space-y-1">
                  {buildProgress.logs.slice(-10).map((log, index) => (
                    <div key={index} className="text-sm font-mono">
                      <span className="text-gray-500 text-xs">
                        {new Date(log.timestamp).toLocaleTimeString()}
                      </span>
                      <span className={`ml-2 ${
                        log.level === 'error' ? 'text-red-400' :
                        log.level === 'warning' ? 'text-yellow-400' :
                        'text-green-400'
                      }`}>
                        [{log.level.toUpperCase()}]
                      </span>
                      <span className="text-gray-300 ml-2">{log.message}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Existing Projects */}
      <div className="bg-white rounded-2xl shadow-xl p-6">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center">
            <div className="w-10 h-10 bg-green-600 rounded-lg flex items-center justify-center mr-3">
              <i className="fas fa-folder-open text-white text-xl"></i>
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-800">Your Projects</h2>
              <p className="text-sm text-gray-600">{projects.length} project(s) available</p>
            </div>
          </div>
          <button
            onClick={onProjectsUpdate}
            className="text-blue-600 hover:text-blue-700 font-semibold text-sm flex items-center"
          >
            <i className="fas fa-sync-alt mr-2"></i>
            Refresh
          </button>
        </div>

        {projects.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <i className="fas fa-inbox text-6xl mb-4 text-gray-300"></i>
            <h3 className="text-lg font-semibold mb-2">No Projects Yet</h3>
            <p className="text-sm">Build your first application above to get started</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {projects.map((project) => (
              <div
                key={project.name}
                onClick={() => onProjectSelect(project)}
                className={`cursor-pointer p-5 rounded-xl border-2 transition-all duration-200 ${
                  selectedProject?.name === project.name
                    ? 'border-blue-500 bg-blue-50 shadow-lg scale-105'
                    : 'border-gray-200 hover:border-blue-300 hover:shadow-md bg-white'
                }`}
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center space-x-2">
                    <i className="fas fa-cube text-2xl text-blue-600"></i>
                    <h3 className="font-bold text-gray-800">{project.name}</h3>
                  </div>
                  <span className={`text-xs px-2 py-1 rounded-full font-semibold ${
                    project.status === 'ready' 
                      ? 'bg-green-100 text-green-700' 
                      : project.status === 'building'
                      ? 'bg-yellow-100 text-yellow-700'
                      : 'bg-gray-100 text-gray-600'
                  }`}>
                    {project.status}
                  </span>
                </div>

                {project.description && (
                  <p className="text-xs text-gray-600 mb-3 line-clamp-2">
                    {project.description}
                  </p>
                )}

                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2 text-xs text-gray-600">
                    {project.has_backend && (
                      <span className="flex items-center bg-purple-100 text-purple-700 px-2 py-1 rounded">
                        <i className="fas fa-server mr-1"></i>
                        Backend
                      </span>
                    )}
                    {project.has_frontend && (
                      <span className="flex items-center bg-blue-100 text-blue-700 px-2 py-1 rounded">
                        <i className="fas fa-desktop mr-1"></i>
                        Frontend
                      </span>
                    )}
                  </div>
                </div>

                {project.created_at && (
                  <div className="text-xs text-gray-500 mt-3 pt-3 border-t border-gray-200">
                    <i className="fas fa-clock mr-1"></i>
                    Created {new Date(project.created_at).toLocaleDateString()}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
