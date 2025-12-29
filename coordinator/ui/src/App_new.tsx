import React, { useState, useEffect } from 'react';
import { LivePreviewTab } from './components/LivePreviewTab';
import { TesterTab } from './components/TesterTab';
import { ProjectBuilderTab } from './components/ProjectBuilderTab';
import { NotificationSystem, useNotifications } from './components/NotificationSystem';
import { ErrorBoundary } from './components/ErrorBoundary';
import { apiClient } from './utils/apiClient';

type ActiveTab = 'live-preview' | 'tester' | 'project-builder';

interface Project {
  name: string;
  path: string;
  created_at?: string;
  description?: string;
  status: string;
  has_backend: boolean;
  has_frontend: boolean;
}

const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<ActiveTab>('project-builder');
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [, setLoading] = useState(true);
  const { notifications, addNotification, dismissNotification } = useNotifications();

  // Set up API client notification handler
  useEffect(() => {
    apiClient.setNotificationHandler(addNotification);
  }, [addNotification]);

  // Load projects on mount
  useEffect(() => {
    loadProjects();
  }, []);

  const loadProjects = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/projects');
      const data = await response.json();
      setProjects(data.projects || []);
    } catch (error) {
      console.error('Failed to load projects:', error);
      addNotification({
        type: 'error',
        title: 'Error',
        message: 'Failed to load projects',
        duration: 5000
      });
    } finally {
      setLoading(false);
    }
  };

  // Sync selected project across all tabs
  const handleProjectSelect = (project: Project) => {
    setSelectedProject(project);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-blue-50 to-gray-100">
      {/* Header */}
      <nav className="bg-gradient-to-r from-blue-600 to-indigo-700 text-white shadow-2xl">
        <div className="container mx-auto px-6 py-4">
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between space-y-4 lg:space-y-0">
            <div className="flex items-center space-x-4">
              <div className="w-12 h-12 bg-white/20 rounded-xl flex items-center justify-center backdrop-blur">
                <i className="fas fa-robot text-3xl"></i>
              </div>
              <div>
                <h1 className="text-2xl font-bold tracking-tight">Autonomous App Builder</h1>
                <p className="text-blue-100 text-sm">AI-Powered Development Platform</p>
              </div>
            </div>

            {/* Tab Navigation */}
            <div className="flex items-center space-x-2 bg-white/10 backdrop-blur rounded-2xl px-2 py-2">
              <button
                className={`px-6 py-2.5 rounded-xl text-sm font-semibold transition-all duration-200 ${activeTab === 'project-builder'
                    ? 'bg-white text-blue-600 shadow-lg scale-105'
                    : 'text-white hover:bg-white/20'
                  }`}
                onClick={() => setActiveTab('project-builder')}
              >
                <i className="fas fa-hammer mr-2"></i>
                Project Builder
              </button>
              <button
                className={`px-6 py-2.5 rounded-xl text-sm font-semibold transition-all duration-200 ${activeTab === 'live-preview'
                    ? 'bg-white text-blue-600 shadow-lg scale-105'
                    : 'text-white hover:bg-white/20'
                  }`}
                onClick={() => setActiveTab('live-preview')}
              >
                <i className="fas fa-eye mr-2"></i>
                Live Preview
              </button>
              <button
                className={`px-6 py-2.5 rounded-xl text-sm font-semibold transition-all duration-200 ${activeTab === 'tester'
                    ? 'bg-white text-blue-600 shadow-lg scale-105'
                    : 'text-white hover:bg-white/20'
                  }`}
                onClick={() => setActiveTab('tester')}
              >
                <i className="fas fa-vial mr-2"></i>
                Tester
              </button>
            </div>
          </div>

          {/* Selected Project Indicator */}
          {selectedProject && (
            <div className="mt-4 bg-white/10 backdrop-blur rounded-xl px-4 py-2 flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <i className="fas fa-folder-open text-yellow-300"></i>
                <span className="text-sm font-medium">
                  Selected: <span className="font-bold">{selectedProject.name}</span>
                </span>
              </div>
              <button
                onClick={() => setSelectedProject(null)}
                className="text-xs text-white/70 hover:text-white"
              >
                <i className="fas fa-times mr-1"></i>
                Clear
              </button>
            </div>
          )}
        </div>
      </nav>

      {/* Notification System */}
      <NotificationSystem
        notifications={notifications}
        onDismiss={dismissNotification}
      />

      {/* Main Content Area */}
      <div className="container mx-auto px-6 py-8">
        <ErrorBoundary>
          {activeTab === 'project-builder' && (
            <ProjectBuilderTab
              selectedProject={selectedProject}
              onProjectSelect={handleProjectSelect}
              projects={projects}
              onProjectsUpdate={loadProjects}
              addNotification={addNotification}
            />
          )}

          {activeTab === 'live-preview' && (
            <LivePreviewTab
              selectedProject={selectedProject}
              onProjectSelect={handleProjectSelect}
              projects={projects}
              addNotification={addNotification}
            />
          )}

          {activeTab === 'tester' && (
            <TesterTab
              selectedProject={selectedProject}
              onProjectSelect={handleProjectSelect}
              projects={projects}
              addNotification={addNotification}
            />
          )}
        </ErrorBoundary>
      </div>
    </div>
  );
};

export default App;
