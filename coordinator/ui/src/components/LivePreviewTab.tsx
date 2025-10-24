import React, { useState, useEffect } from 'react';

interface Project {
  name: string;
  path: string;
  status: string;
  has_backend: boolean;
  has_frontend: boolean;
}

interface LivePreviewTabProps {
  selectedProject: Project | null;
  onProjectSelect: (project: Project) => void;
  projects: Project[];
  addNotification: (notification: any) => void;
}

interface PreviewState {
  isRunning: boolean;
  url: string | null;
  urls: {
    frontend_url?: string;
    api_url?: string;
    docs_url?: string;
  };
  errors: any[];
  autoFixing: boolean;
}

export const LivePreviewTab: React.FC<LivePreviewTabProps> = ({
  selectedProject,
  onProjectSelect,
  projects,
  addNotification
}) => {
  const [previewState, setPreviewState] = useState<PreviewState>({
    isRunning: false,
    url: null,
    urls: {},
    errors: [],
    autoFixing: false
  });
  const [healthCheckInterval, setHealthCheckInterval] = useState<ReturnType<typeof setInterval> | null>(null);

  // Monitor preview health
  useEffect(() => {
    if (previewState.isRunning && selectedProject) {
      const interval = setInterval(async () => {
        await checkPreviewHealth();
      }, 5000);
      
      setHealthCheckInterval(interval);
      
      return () => {
        if (interval) clearInterval(interval);
      };
    }
  }, [previewState.isRunning, selectedProject]);

  const checkPreviewHealth = async () => {
    if (!selectedProject) return;

    try {
      const response = await fetch(`/api/preview/health/${selectedProject.name}`);
      const health = await response.json();

      if (!health.healthy && health.errors && health.errors.length > 0) {
        setPreviewState(prev => ({ ...prev, errors: health.errors }));
        
        // Auto-resolve errors
        for (const error of health.errors) {
          await autoResolveError(error);
        }
      }
    } catch (error) {
      console.error('Health check failed:', error);
    }
  };

  const autoResolveError = async (error: any) => {
    if (!selectedProject) return;

    try {
      setPreviewState(prev => ({ ...prev, autoFixing: true }));
      
      const response = await fetch('/api/preview/resolve-error', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_name: selectedProject.name,
          error: error
        })
      });

      const result = await response.json();

      if (result.status === 'fixed') {
        addNotification({
          type: 'success',
          title: 'Error Auto-Fixed',
          message: result.message,
          duration: 5000
        });
        
        // Remove resolved error
        setPreviewState(prev => ({
          ...prev,
          errors: prev.errors.filter(e => e !== error)
        }));
      } else if (result.status === 'manual_intervention_required') {
        addNotification({
          type: 'warning',
          title: 'Manual Fix Required',
          message: result.message,
          duration: 7000
        });
      }
    } catch (error) {
      console.error('Auto-fix failed:', error);
    } finally {
      setPreviewState(prev => ({ ...prev, autoFixing: false }));
    }
  };

  const handleStartPreview = async () => {
    if (!selectedProject) {
      addNotification({
        type: 'warning',
        title: 'No Project Selected',
        message: 'Please select a project first',
        duration: 3000
      });
      return;
    }

    try {
      const response = await fetch('/api/preview/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_name: selectedProject.name,
          project_path: selectedProject.path
        })
      });

      const result = await response.json();

      if (result.status === 'success' || result.status === 'running') {
        setPreviewState({
          isRunning: true,
          url: result.url,
          urls: result.urls || {},
          errors: [],
          autoFixing: false
        });

        addNotification({
          type: 'success',
          title: 'Preview Started',
          message: `Preview is running at ${result.url}`,
          duration: 5000
        });
      } else {
        addNotification({
          type: 'error',
          title: 'Preview Failed',
          message: result.message || 'Failed to start preview',
          duration: 5000
        });
      }
    } catch (error) {
      console.error('Failed to start preview:', error);
      addNotification({
        type: 'error',
        title: 'Error',
        message: 'Failed to start live preview',
        duration: 5000
      });
    }
  };

  const handleStopPreview = async () => {
    if (!selectedProject) return;

    try {
      const response = await fetch('/api/preview/stop', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_name: selectedProject.name
        })
      });

      const result = await response.json();

      if (result.status === 'success') {
        setPreviewState({
          isRunning: false,
          url: null,
          urls: {},
          errors: [],
          autoFixing: false
        });

        if (healthCheckInterval) {
          clearInterval(healthCheckInterval);
          setHealthCheckInterval(null);
        }

        addNotification({
          type: 'info',
          title: 'Preview Stopped',
          message: 'Live preview has been stopped',
          duration: 3000
        });
      }
    } catch (error) {
      console.error('Failed to stop preview:', error);
    }
  };

  return (
    <div className="space-y-6">
      {/* Project Selector */}
      <div className="bg-white rounded-2xl shadow-xl p-6">
        <h2 className="text-xl font-bold text-gray-800 mb-4 flex items-center">
          <i className="fas fa-folder-tree mr-3 text-blue-600"></i>
          Select Project
        </h2>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {projects.length === 0 ? (
            <div className="col-span-full text-center py-8 text-gray-500">
              <i className="fas fa-inbox text-4xl mb-3"></i>
              <p>No projects available. Create one in the Project Builder tab.</p>
            </div>
          ) : (
            projects.map((project) => (
              <div
                key={project.name}
                onClick={() => onProjectSelect(project)}
                className={`cursor-pointer p-4 rounded-xl border-2 transition-all duration-200 ${
                  selectedProject?.name === project.name
                    ? 'border-blue-500 bg-blue-50 shadow-lg scale-105'
                    : 'border-gray-200 hover:border-blue-300 hover:shadow-md'
                }`}
              >
                <div className="flex items-start justify-between mb-2">
                  <h3 className="font-semibold text-gray-800">{project.name}</h3>
                  <span className={`text-xs px-2 py-1 rounded-full ${
                    project.status === 'ready' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'
                  }`}>
                    {project.status}
                  </span>
                </div>
                <div className="flex items-center space-x-2 text-xs text-gray-600">
                  {project.has_backend && (
                    <span className="flex items-center">
                      <i className="fas fa-server mr-1"></i>
                      Backend
                    </span>
                  )}
                  {project.has_frontend && (
                    <span className="flex items-center">
                      <i className="fas fa-desktop mr-1"></i>
                      Frontend
                    </span>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Preview Controls */}
      {selectedProject && (
        <div className="bg-white rounded-2xl shadow-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold text-gray-800 flex items-center">
              <i className="fas fa-play-circle mr-3 text-green-600"></i>
              Preview Controls
            </h2>
            
            <div className="flex items-center space-x-3">
              {previewState.autoFixing && (
                <span className="flex items-center text-sm text-orange-600">
                  <i className="fas fa-spinner fa-spin mr-2"></i>
                  Auto-fixing errors...
                </span>
              )}
              
              {!previewState.isRunning ? (
                <button
                  onClick={handleStartPreview}
                  className="bg-green-600 hover:bg-green-700 text-white px-6 py-2 rounded-lg font-semibold transition flex items-center shadow-lg"
                >
                  <i className="fas fa-play mr-2"></i>
                  Start Preview
                </button>
              ) : (
                <button
                  onClick={handleStopPreview}
                  className="bg-red-600 hover:bg-red-700 text-white px-6 py-2 rounded-lg font-semibold transition flex items-center shadow-lg"
                >
                  <i className="fas fa-stop mr-2"></i>
                  Stop Preview
                </button>
              )}
            </div>
          </div>

          {/* Error Display */}
          {previewState.errors.length > 0 && (
            <div className="bg-red-50 border-l-4 border-red-500 p-4 mb-4 rounded">
              <h3 className="font-semibold text-red-800 mb-2">
                <i className="fas fa-exclamation-triangle mr-2"></i>
                Detected Errors ({previewState.errors.length})
              </h3>
              {previewState.errors.map((error, index) => (
                <div key={index} className="text-sm text-red-700 mb-1">
                  • {error.service}: {error.message}
                </div>
              ))}
              <p className="text-xs text-red-600 mt-2">
                <i className="fas fa-magic mr-1"></i>
                AI Agent is attempting to auto-resolve these errors...
              </p>
            </div>
          )}
        </div>
      )}

      {/* Preview Window */}
      {previewState.isRunning && (
        <div className="bg-white rounded-2xl shadow-xl overflow-hidden">
          <div className="bg-gradient-to-r from-blue-500 to-indigo-600 px-6 py-4 flex items-center justify-between">
            <div className="flex items-center space-x-3 text-white">
              <i className="fas fa-globe text-2xl"></i>
              <div>
                <h3 className="font-bold">Live Preview</h3>
                <p className="text-xs text-blue-100">Real-time application view</p>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              {previewState.urls.frontend_url && (
                <a
                  href={previewState.urls.frontend_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-white hover:bg-white/20 px-3 py-1 rounded text-sm transition"
                >
                  <i className="fas fa-external-link-alt mr-1"></i>
                  Frontend
                </a>
              )}
              {previewState.urls.docs_url && (
                <a
                  href={previewState.urls.docs_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-white hover:bg-white/20 px-3 py-1 rounded text-sm transition"
                >
                  <i className="fas fa-book mr-1"></i>
                  API Docs
                </a>
              )}
            </div>
          </div>
          
          <div className="p-6 bg-gray-50">
            {previewState.url ? (
              <iframe
                src={previewState.url}
                className="w-full h-[600px] border-4 border-gray-300 rounded-xl shadow-inner bg-white"
                title="Live Preview"
              />
            ) : (
              <div className="flex items-center justify-center h-[600px] text-gray-500">
                <div className="text-center">
                  <i className="fas fa-spinner fa-spin text-4xl mb-3"></i>
                  <p>Loading preview...</p>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* No Project Selected State */}
      {!selectedProject && (
        <div className="bg-white rounded-2xl shadow-xl p-12 text-center">
          <i className="fas fa-hand-pointer text-6xl text-gray-300 mb-4"></i>
          <h3 className="text-xl font-bold text-gray-700 mb-2">No Project Selected</h3>
          <p className="text-gray-500">Select a project above to start live preview</p>
        </div>
      )}
    </div>
  );
};
