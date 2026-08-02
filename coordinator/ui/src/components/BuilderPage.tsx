import React, { useState, useEffect, useRef, useCallback } from 'react';
import { PromptHero } from './PromptHero';
import { BuilderChat, ChatEntry } from './BuilderChat';
import BuildWorkflowStepper from './BuildWorkflowStepper';
import { LivePreview } from './LivePreview';
import { IDEShell } from './IDEShell';

type Phase = 'idle' | 'building' | 'running';
type DeviceViewport = 'desktop' | 'tablet' | 'mobile';

const DEVICE_WIDTHS: Record<DeviceViewport, string> = {
  desktop: '100%',
  tablet: '768px',
  mobile: '375px',
};

interface BuilderPageProps {
  addNotification: (n: { type: string; title: string; message: string; duration: number }) => void;
}

function chatId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
}

function addMsg(role: ChatEntry['role'], content: string, extra?: Partial<ChatEntry>): ChatEntry {
  return { id: chatId(), role, content, timestamp: new Date(), ...extra };
}

export const BuilderPage: React.FC<BuilderPageProps> = ({ addNotification }) => {
  // ─── State ───
  const [phase, setPhase] = useState<Phase>('idle');
  const [messages, setMessages] = useState<ChatEntry[]>([]);
  const [buildProgress, setBuildProgress] = useState(0);
  const [buildStep, setBuildStep] = useState('');
  const [buildStatus, setBuildStatus] = useState('idle');
  const [sourcePath, setSourcePath] = useState('');

  // Running state
  const [instanceId, setInstanceId] = useState<string | null>(null);
  const [previewUrl, setPreviewUrl] = useState('');
  const [rawPreviewUrl, setRawPreviewUrl] = useState('');
  const [sessionToken, setSessionToken] = useState('');
  const [isRunning, setIsRunning] = useState(false);
  const [viewport, setViewport] = useState<DeviceViewport>('desktop');
  const [sidebarExpanded, setSidebarExpanded] = useState(true);

  const wsRef = useRef<WebSocket | null>(null);
  const retryCountRef = useRef(0);
  const MAX_RETRIES = 2;

  // ─── Helpers ───
  const pushMsg = useCallback((role: ChatEntry['role'], content: string, extra?: Partial<ChatEntry>) => {
    setMessages(prev => [...prev, addMsg(role, content, extra)]);
  }, []);

  // ─── Sandbox Launch ───
  const launchSandbox = useCallback(async (appPath: string) => {
    pushMsg('system', '🚀 Launching sandbox preview...');
    try {
      const sessionId = `session-${Date.now()}`;
      // Grant permissions
      await fetch('/api/session/permissions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          actions: ['allow_run', 'allow_agent_auto_fix'],
          commands: [],
          duration: 3600
        })
      });

      const res = await fetch('/api/app/launch', {
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

      const data = await res.json();
      if (res.ok && data.status === 'success') {
        setInstanceId(data.instance_id);
        setPreviewUrl(data.secure_preview_url || data.preview_url || '');
        setRawPreviewUrl(data.preview_url || '');
        setSessionToken(data.session_token || '');
        setIsRunning(true);
        setPhase('running');
        setBuildStatus('running');
        retryCountRef.current = 0;
        pushMsg('agent', '✅ Your app is live! Preview is ready above. Use the chat to request changes.');
        addNotification({ type: 'success', title: 'App Running', message: 'Sandbox preview is live', duration: 3000 });
      } else {
        throw new Error(data?.detail || data?.message || 'Launch failed');
      }
    } catch (e: unknown) {
      const errMsg = e instanceof Error ? e.message : String(e);
      pushMsg('system', `⚠️ Launch failed: ${errMsg}`);

      // Auto-fix attempt
      if (retryCountRef.current < MAX_RETRIES) {
        retryCountRef.current++;
        pushMsg('agent', `🔧 Attempting auto-fix (attempt ${retryCountRef.current}/${MAX_RETRIES})...`);
        try {
          const fixRes = await fetch('/api/agent/problem-resolver', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              session_id: `session-${Date.now()}`,
              app_path: appPath,
              commands: { build: [], test: [] },
              run_mode: 'attempt-fix'
            })
          });
          const fixData = await fixRes.json();
          if (fixRes.ok && fixData.runId) {
            pushMsg('agent', '🔍 Problem resolver is analyzing issues...');
            // Wait a bit for fixes to apply, then retry launch
            await new Promise(r => setTimeout(r, 10000));
            pushMsg('agent', '🔄 Retrying launch after auto-fix...');
            await launchSandbox(appPath);
          } else {
            pushMsg('system', '❌ Auto-fix could not start. Please check the Resolver tab.');
          }
        } catch {
          pushMsg('system', '❌ Auto-fix request failed.');
        }
      } else {
        pushMsg('system', '❌ Retries exhausted. Please check the Resolver tab for manual fixes.');
        addNotification({ type: 'error', title: 'Launch Failed', message: 'Could not start the app after auto-fix attempts', duration: 5000 });
      }
    }
  }, [pushMsg, addNotification]);

  // ─── Build WebSocket ───
  const connectBuildWs = useCallback((id: string) => {
    if (wsRef.current) { try { wsRef.current.close(); } catch {} }

    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(`${proto}//${window.location.host}/ws/build/${id}`);

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        const status = (data.status || '').toLowerCase();
        const progress = data.progress ?? 0;
        const step = data.current_step || '';

        setBuildProgress(progress);
        setBuildStep(step);
        setBuildStatus(status === 'building' ? 'building' : status);

        // Post agent messages for key milestones
        if (step && progress > 0) {
          const stepLower = step.toLowerCase();
          if (stepLower.includes('analyz')) pushMsg('agent', `🔍 ${step}`);
          else if (stepLower.includes('generat') && progress >= 40 && progress < 50) pushMsg('agent', `⚡ ${step}`);
          else if (stepLower.includes('valid')) pushMsg('agent', `✓ ${step}`);
          else if (stepLower.includes('build') && progress >= 80) pushMsg('agent', `🏗️ ${step}`);
        }

        // Build complete
        if (status === 'success' || progress >= 100) {
          const path = data.source_path || '';
          if (path) setSourcePath(path);
          pushMsg('agent', '🎉 Build complete! Starting your app...');
          setBuildStatus('success');
          try { ws.close(); } catch {}
          try { localStorage.removeItem('sb_active_build_id'); } catch {}
          if (path) {
            launchSandbox(path);
          }
        }

        // Build failed
        if (status === 'failed' || status === 'error') {
          const errMsg = data.error || data.message || 'Build failed';
          pushMsg('system', `❌ Build error: ${errMsg}`);
          setBuildStatus('error');
          try { ws.close(); } catch {}
          try { localStorage.removeItem('sb_active_build_id'); } catch {}
          addNotification({ type: 'error', title: 'Build Failed', message: errMsg, duration: 5000 });
        }
      } catch (e) {
        console.error('WS parse error:', e);
      }
    };

    ws.onerror = () => {
      pushMsg('system', '⚠️ Build connection interrupted. Retrying...');
    };

    ws.onclose = () => {
      wsRef.current = null;
    };

    wsRef.current = ws;
  }, [pushMsg, launchSandbox, addNotification]);

  // ─── Rehydrate from localStorage ───
  useEffect(() => {
    const saved = localStorage.getItem('sb_active_build_id');
    if (saved && phase === 'idle') {
      (async () => {
        try {
          const res = await fetch(`/api/build/${saved}/status`);
          if (!res.ok) { localStorage.removeItem('sb_active_build_id'); return; }
          const data = await res.json();
          const st = (data.status || '').toLowerCase();
          const prog = data.progress ?? 0;
          if (st === 'success' || prog >= 100) {
            localStorage.removeItem('sb_active_build_id');
            if (data.source_path) {
              setSourcePath(data.source_path);
              launchSandbox(data.source_path);
            }
            return;
          }
          if (st === 'failed' || st === 'error') {
            localStorage.removeItem('sb_active_build_id');
            return;
          }
          setBuildProgress(data.progress || 0);
          setBuildStep(data.current_step || '');
          setBuildStatus('building');
          setPhase('building');
          pushMsg('system', 'Resuming build in progress...');
          connectBuildWs(saved);
        } catch {
          localStorage.removeItem('sb_active_build_id');
        }
      })();
    }
    return () => { if (wsRef.current) { try { wsRef.current.close(); } catch {} } };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ─── Start Build ───
  const handleStartBuild = useCallback(async (brief: {
    description: string;
    name?: string;
    requirements?: string[];
    preferred_backend?: string;
    preferred_frontend?: string;
  }) => {
    setPhase('building');
    setBuildProgress(0);
    setBuildStep('Submitting...');
    setBuildStatus('building');
    retryCountRef.current = 0;

    setMessages([addMsg('user', brief.description)]);
    pushMsg('agent', '🧠 Analyzing your requirements...');

    try {
      const res = await fetch('/api/build', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          description: brief.description,
          name: brief.name || undefined,
          requirements: brief.requirements || undefined,
          preferred_backend: brief.preferred_backend || undefined,
          preferred_frontend: brief.preferred_frontend || undefined,
        })
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err?.detail || `Build request failed (${res.status})`);
      }

      const data = await res.json();
      const newId = data.build_id;
      try { localStorage.setItem('sb_active_build_id', newId); } catch {}
      pushMsg('agent', `📋 Build started (ID: ${newId.substring(0, 8)}…). Generating your app…`);
      connectBuildWs(newId);
    } catch (e: unknown) {
      const errMsg = e instanceof Error ? e.message : String(e);
      pushMsg('system', `❌ Failed to start build: ${errMsg}`);
      setBuildStatus('error');
      addNotification({ type: 'error', title: 'Build Error', message: errMsg, duration: 5000 });
    }
  }, [connectBuildWs, pushMsg, addNotification]);

  // ─── Stop sandbox ───
  const handleStop = useCallback(async () => {
    if (!instanceId) return;
    try {
      await fetch('/api/app/stop', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ instance_id: instanceId, force: true })
      });
      setIsRunning(false);
      setPhase('idle');
      setInstanceId(null);
      setMessages([]);
      setBuildProgress(0);
      setBuildStatus('idle');
      addNotification({ type: 'info', title: 'Stopped', message: 'Sandbox stopped', duration: 2500 });
    } catch {
      addNotification({ type: 'error', title: 'Stop Failed', message: 'Could not stop instance', duration: 3000 });
    }
  }, [instanceId, addNotification]);

  // ─── Chat message handler ───
  const handleChatMessage = useCallback((text: string) => {
    pushMsg('user', text);
    // For now, messages are logged. A future version will send to /api/chat/ws for real LLM reasoning.
    pushMsg('agent', 'I heard you! Real-time chat editing will be available soon. For now, use the Editor panel below to make changes.');
  }, [pushMsg]);

  // ══════════════════════════════════════════════════════════
  //  RENDER
  // ══════════════════════════════════════════════════════════

  // ─── Phase 1: Idle / Prompt ───
  if (phase === 'idle') {
    return (
      <div className="animate-fade-in max-w-4xl mx-auto pt-8 px-4">
        <PromptHero onSubmit={handleStartBuild} isBuilding={false} />
      </div>
    );
  }

  // ─── Phase 2: Building ───
  if (phase === 'building') {
    return (
      <div className="animate-fade-in max-w-4xl mx-auto pt-4 px-4 flex flex-col gap-6" style={{ height: 'calc(100vh - 120px)' }}>
        {/* Stepper */}
        <BuildWorkflowStepper status={buildStatus} currentStep={buildStep} />

        {/* Chat thread */}
        <div className="flex-1 min-h-0">
          <BuilderChat
            messages={messages}
            isBuilding={true}
            buildProgress={buildProgress}
            currentStep={buildStep}
            buildStatus={buildStatus}
            onSendMessage={handleChatMessage}
            inputEnabled={false}
          />
        </div>
      </div>
    );
  }

  // ─── Phase 3: Running (split view) ───
  return (
    <div className="animate-fade-in builder-split" style={{ height: 'calc(100vh - 80px)' }}>
      {/* Left Sidebar — Chat */}
      <div className={`builder-sidebar ${sidebarExpanded ? 'expanded' : 'collapsed'} flex flex-col`}>
        <div className="flex items-center justify-between px-3 py-2 border-b border-white/5 shrink-0">
          {sidebarExpanded && <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Chat</span>}
          <button
            onClick={() => setSidebarExpanded(!sidebarExpanded)}
            className="glass-button w-7 h-7 rounded-lg text-xs p-0"
            title={sidebarExpanded ? 'Collapse' : 'Expand'}
          >
            <i className={`fas fa-${sidebarExpanded ? 'chevron-left' : 'comments'} text-[10px]`}></i>
          </button>
        </div>
        {sidebarExpanded && (
          <div className="flex-1 min-h-0">
            <BuilderChat
              messages={messages}
              isBuilding={false}
              buildProgress={100}
              currentStep="Running"
              buildStatus="running"
              onSendMessage={handleChatMessage}
              inputEnabled={true}
              compact
            />
          </div>
        )}
      </div>

      {/* Main Area */}
      <div className="builder-main">
        {/* Toolbar */}
        <div className="flex items-center justify-between px-4 py-2 border-b border-white/5 bg-white/3 shrink-0">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></div>
            <span className="text-xs text-gray-400 font-medium">Live Preview</span>
          </div>

          <div className="flex items-center gap-1.5">
            {(['desktop', 'tablet', 'mobile'] as const).map(d => (
              <button
                key={d}
                onClick={() => setViewport(d)}
                className={`device-toggle ${viewport === d ? 'active' : ''}`}
              >
                <i className={`fas fa-${d === 'desktop' ? 'desktop' : d === 'tablet' ? 'tablet-alt' : 'mobile-alt'} text-xs`}></i>
              </button>
            ))}
          </div>

          <div className="flex items-center gap-1.5">
            <button onClick={handleStop} className="glass-button text-xs px-3 py-1.5 rounded-lg text-red-400 hover:bg-red-500/10">
              <i className="fas fa-square mr-1.5"></i>Stop
            </button>
            {rawPreviewUrl && (
              <a href={rawPreviewUrl} target="_blank" rel="noopener noreferrer" className="glass-button text-xs px-2.5 py-1.5 rounded-lg text-gray-400 hover:text-white">
                <i className="fas fa-external-link-alt"></i>
              </a>
            )}
          </div>
        </div>

        {/* Preview iframe */}
        <div className="builder-preview-area flex items-start justify-center p-2">
          <div
            className="h-full bg-white rounded-lg overflow-hidden transition-all duration-500 shadow-2xl"
            style={{ width: DEVICE_WIDTHS[viewport], maxWidth: '100%' }}
          >
            <LivePreview
              previewUrl={previewUrl}
              openUrl={rawPreviewUrl || previewUrl}
              sessionToken={sessionToken}
              instanceId={instanceId || ''}
            />
          </div>
        </div>

        {/* Editor */}
        <div className="builder-editor-area">
          <IDEShell
            root={sourcePath}
            onRun={() => {}}
            onStop={handleStop}
            onBack={() => { setPhase('idle'); setIsRunning(false); }}
            isRunning={isRunning}
          />
        </div>
      </div>
    </div>
  );
};
