import React, { useState, useRef, useEffect } from 'react';

export interface ChatEntry {
  id: string;
  role: 'user' | 'agent' | 'system' | 'build-progress';
  content: string;
  timestamp: Date;
  progress?: number;
  step?: string;
  status?: string;
}

export interface BuilderChatProps {
  messages: ChatEntry[];
  isBuilding: boolean;
  buildProgress: number;
  currentStep: string;
  buildStatus: string;
  onSendMessage: (text: string) => void;
  inputEnabled: boolean;
  compact?: boolean;
}

export const BuilderChat: React.FC<BuilderChatProps> = ({
  messages,
  isBuilding,
  buildProgress,
  currentStep,
  buildStatus,
  onSendMessage,
  inputEnabled,
  compact = false,
}) => {
  const [inputValue, setInputValue] = useState('');
  const endOfMessagesRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endOfMessagesRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isBuilding, buildProgress, currentStep, buildStatus]);

  const handleSend = () => {
    if (inputValue.trim() && inputEnabled) {
      onSendMessage(inputValue.trim());
      setInputValue('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleSend();
    }
  };

  return (
    <div className={`flex flex-col h-full w-full ${compact ? 'max-w-[350px] text-sm' : 'text-base'}`}>
      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar">
        {(messages || []).map((msg) => {
          if (msg.role === 'user') {
            return (
              <div key={msg.id} className="flex justify-end animate-fade-in">
                <div className="bg-indigo-600 text-white rounded-2xl rounded-tr-sm px-4 py-2 max-w-[85%] shadow-md">
                  {msg.content}
                </div>
              </div>
            );
          }
          if (msg.role === 'agent') {
            return (
              <div key={msg.id} className="flex justify-start items-end gap-2 animate-fade-in">
                <div className="w-8 h-8 rounded-full bg-slate-800 flex items-center justify-center text-indigo-400 shrink-0">
                  <i className="fas fa-robot"></i>
                </div>
                <div className="glass-panel rounded-2xl rounded-bl-sm px-4 py-2 max-w-[85%]">
                  {msg.content}
                </div>
              </div>
            );
          }
          if (msg.role === 'system') {
            return (
              <div key={msg.id} className="text-center text-xs text-slate-500 animate-fade-in">
                {msg.content}
              </div>
            );
          }
          if (msg.role === 'build-progress') {
            return (
              <div key={msg.id} className="glass-panel p-3 rounded-xl border border-indigo-500/30 animate-slide-in-r shadow-[0_0_15px_rgba(99,102,241,0.1)]">
                <div className="flex justify-between items-center mb-2">
                  <span className="font-medium text-slate-200 text-sm">
                    {msg.step || 'Building...'}
                  </span>
                  <span className="text-xs text-indigo-400 font-mono">
                    {msg.progress || 0}%
                  </span>
                </div>
                <div className="w-full bg-slate-800/50 rounded-full h-1.5 overflow-hidden">
                  <div 
                    className="bg-indigo-500 h-1.5 rounded-full transition-all duration-300 ease-out shadow-[0_0_8px_rgba(99,102,241,0.6)]"
                    style={{ width: `${msg.progress || 0}%` }}
                  ></div>
                </div>
                {msg.status && (
                  <div className="mt-2 text-xs text-slate-400">
                    {msg.status}
                  </div>
                )}
              </div>
            );
          }
          return null;
        })}
        <div ref={endOfMessagesRef} />
      </div>

      {/* Input Area */}
      <div className="p-3 border-t border-slate-700/50 bg-slate-900/50 backdrop-blur-md">
        <div className="relative flex items-center">
          <input
            type="text"
            className="w-full bg-slate-800 border border-slate-700 rounded-full pl-4 pr-12 py-2 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            placeholder={inputEnabled ? "Ask the agent anything..." : "Agent is working..."}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={!inputEnabled}
          />
          <button
            className="absolute right-1 w-8 h-8 rounded-full flex items-center justify-center text-indigo-400 hover:text-indigo-300 hover:bg-slate-700/50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            onClick={handleSend}
            disabled={!inputEnabled || !inputValue.trim()}
            title="Send message"
          >
            <i className="fas fa-paper-plane"></i>
          </button>
        </div>
      </div>
    </div>
  );
};
