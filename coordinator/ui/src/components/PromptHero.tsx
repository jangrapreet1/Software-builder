import React, { useState, useEffect, KeyboardEvent } from 'react';

interface PromptHeroProps {
  onSubmit: (brief: {
    description: string;
    name?: string;
    requirements?: string[];
    preferred_backend?: string;
    preferred_frontend?: string;
  }) => void;
  isBuilding: boolean;
}

interface Framework {
  id: string;
  name: string;
}

const TEMPLATES = [
  {
    title: 'Todo App',
    icon: 'fa-check-square',
    colorClass: 'text-emerald-400',
    prompt: 'Build a task management app where users can create, edit, delete, and mark tasks as complete. Include user authentication and a real-time dashboard showing completion stats.'
  },
  {
    title: 'E-commerce Store',
    icon: 'fa-shopping-cart',
    colorClass: 'text-amber-400',
    prompt: 'Create a full-stack e-commerce store with product listings, a shopping cart, and a checkout flow. Include an admin panel to manage products and view orders.'
  },
  {
    title: 'Admin Dashboard',
    icon: 'fa-chart-bar',
    colorClass: 'text-blue-400',
    prompt: 'Build a generic admin dashboard with charts, data tables, and user management. Use a sidebar navigation and a top bar with user profile settings.'
  },
  {
    title: 'Blog Platform',
    icon: 'fa-pen-nib',
    colorClass: 'text-purple-400',
    prompt: 'Develop a modern blogging platform where authors can write posts using markdown, and readers can leave comments. Include categories, tags, and a search feature.'
  }
];

export const PromptHero: React.FC<PromptHeroProps> = ({ onSubmit, isBuilding }) => {
  const [description, setDescription] = useState('');
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [projectName, setProjectName] = useState('');
  const [preferredBackend, setPreferredBackend] = useState('');
  const [preferredFrontend, setPreferredFrontend] = useState('');
  
  const [backendFrameworks, setBackendFrameworks] = useState<Framework[]>([]);
  const [frontendFrameworks, setFrontendFrameworks] = useState<Framework[]>([]);

  useEffect(() => {
    const fetchFrameworks = async () => {
      try {
        const [backendRes, frontendRes] = await Promise.all([
          fetch('/api/v2/frameworks?framework_type=backend'),
          fetch('/api/v2/frameworks?framework_type=frontend')
        ]);
        
        if (backendRes.ok) {
          const backendData = await backendRes.json();
          const list = Array.isArray(backendData?.frameworks)
            ? backendData.frameworks
            : (Array.isArray(backendData) ? backendData : []);
          setBackendFrameworks(list);
        }
        
        if (frontendRes.ok) {
          const frontendData = await frontendRes.json();
          const list = Array.isArray(frontendData?.frameworks)
            ? frontendData.frameworks
            : (Array.isArray(frontendData) ? frontendData : []);
          setFrontendFrameworks(list);
        }
      } catch (error) {
        console.error('Failed to fetch frameworks', error);
      }
    };
    
    fetchFrameworks();
  }, []);

  const handleSubmit = () => {
    if (!description.trim()) return;
    
    onSubmit({
      description: description.trim(),
      name: projectName.trim() || undefined,
      preferred_backend: preferredBackend || undefined,
      preferred_frontend: preferredFrontend || undefined,
    });
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="w-full max-w-5xl mx-auto py-12 px-4 animate-fade-in flex flex-col items-center">
      <div className="text-center mb-8">
        <h1 className="text-4xl md:text-5xl font-bold mb-4 bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-indigo-500">
          What do you want to build?
        </h1>
        <p className="text-lg text-slate-400">
          Describe your app and our agents will handle the rest.
        </p>
      </div>

      <div className="w-full glass-panel p-6 mb-8 flex flex-col gap-4">
        <textarea
          className="w-full h-40 bg-slate-800/50 text-slate-100 placeholder-slate-500 rounded-lg p-4 resize-none focus:outline-none focus:ring-2 focus:ring-indigo-500 border border-slate-700/50"
          placeholder="Build a task management app with authentication and a real-time dashboard..."
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isBuilding}
        />
        
        <div className="flex flex-col items-end w-full">
          <button
            onClick={handleSubmit}
            disabled={isBuilding || !description.trim()}
            className="glass-button bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-400 hover:to-purple-500 text-white font-semibold py-3 px-8 rounded-lg flex items-center gap-2 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isBuilding ? (
              <i className="fas fa-spinner fa-spin"></i>
            ) : (
              <i className="fas fa-sparkles"></i>
            )}
            Build It
          </button>
          <span className="text-xs text-slate-500 mt-2 mr-2">⌘+Enter to submit</span>
        </div>
      </div>

      <div className="w-full mb-8">
        <button 
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="flex items-center gap-2 text-slate-400 hover:text-slate-200 transition-colors mb-4 text-sm font-medium"
        >
          <i className={`fas fa-chevron-${showAdvanced ? 'up' : 'down'} text-xs`}></i>
          Advanced Options
        </button>
        
        {showAdvanced && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 glass-panel p-6 animate-fade-in">
            <div className="flex flex-col gap-2">
              <label className="text-sm text-slate-400 font-medium">Project Name</label>
              <input
                type="text"
                className="bg-slate-800/50 text-slate-200 border border-slate-700/50 rounded-md p-2 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                placeholder="my-awesome-app"
                value={projectName}
                onChange={(e) => setProjectName(e.target.value)}
                disabled={isBuilding}
              />
            </div>
            
            <div className="flex flex-col gap-2">
              <label className="text-sm text-slate-400 font-medium">Frontend Framework</label>
              <select
                className="bg-slate-800/50 text-slate-200 border border-slate-700/50 rounded-md p-2 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                value={preferredFrontend}
                onChange={(e) => setPreferredFrontend(e.target.value)}
                disabled={isBuilding}
              >
                <option value="">Auto-detect</option>
                {Array.isArray(frontendFrameworks) && frontendFrameworks.map(fw => (
                  <option key={fw.id} value={fw.id}>{fw.name}</option>
                ))}
              </select>
            </div>
            
            <div className="flex flex-col gap-2">
              <label className="text-sm text-slate-400 font-medium">Backend Framework</label>
              <select
                className="bg-slate-800/50 text-slate-200 border border-slate-700/50 rounded-md p-2 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                value={preferredBackend}
                onChange={(e) => setPreferredBackend(e.target.value)}
                disabled={isBuilding}
              >
                <option value="">Auto-detect</option>
                {Array.isArray(backendFrameworks) && backendFrameworks.map(fw => (
                  <option key={fw.id} value={fw.id}>{fw.name}</option>
                ))}
              </select>
            </div>
          </div>
        )}
      </div>

      <div className="w-full">
        <h3 className="text-lg font-medium text-slate-300 mb-4">Quick Start</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {TEMPLATES.map((template, idx) => (
            <div 
              key={idx}
              className="template-card cursor-pointer p-4 rounded-xl border border-slate-700/50 bg-slate-800/30 hover:bg-slate-800/70 transition-all flex flex-col gap-3"
              onClick={() => setDescription(template.prompt)}
            >
              <div className={`w-10 h-10 rounded-lg flex items-center justify-center bg-slate-900 ${template.colorClass}`}>
                <i className={`fas ${template.icon}`}></i>
              </div>
              <h4 className="font-semibold text-slate-200">{template.title}</h4>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
