import React from 'react';

type Status = 'detected' | 'building' | 'running' | 'error' | 'stopped' | 'idle';

interface StatusIndicatorProps {
  status: Status;
  progress?: number;
  currentStep?: string;
  logsUrl?: string;
}

const statusConfig: Record<Status, { icon: string; color: string; bgColor: string; label: string }> = {
  detected: {
    icon: 'fa-search',
    color: 'text-blue-600',
    bgColor: 'bg-blue-100',
    label: 'Detected'
  },
  building: {
    icon: 'fa-cog fa-spin',
    color: 'text-yellow-600',
    bgColor: 'bg-yellow-100',
    label: 'Building'
  },
  running: {
    icon: 'fa-play-circle',
    color: 'text-green-600',
    bgColor: 'bg-green-100',
    label: 'Running'
  },
  error: {
    icon: 'fa-exclamation-circle',
    color: 'text-red-600',
    bgColor: 'bg-red-100',
    label: 'Error'
  },
  stopped: {
    icon: 'fa-stop-circle',
    color: 'text-gray-600',
    bgColor: 'bg-gray-100',
    label: 'Stopped'
  },
  idle: {
    icon: 'fa-pause-circle',
    color: 'text-gray-400',
    bgColor: 'bg-gray-50',
    label: 'Idle'
  }
};

export const StatusIndicator: React.FC<StatusIndicatorProps> = ({
  status,
  progress,
  currentStep,
  logsUrl
}) => {
  const config = statusConfig[status];

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-3">
          <div className={`${config.bgColor} p-3 rounded-full`}>
            <i className={`fas ${config.icon} ${config.color} text-xl`}></i>
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-800">{config.label}</h3>
            {currentStep && (
              <p className="text-sm text-gray-600">{currentStep}</p>
            )}
          </div>
        </div>
        {logsUrl && (
          <a
            href={logsUrl}
            className="text-sm text-blue-600 hover:text-blue-700 font-medium"
            title="View Logs"
          >
            <i className="fas fa-file-alt mr-1"></i> Logs
          </a>
        )}
      </div>

      {progress !== undefined && (
        <div className="mt-4">
          <div className="flex justify-between items-center mb-2">
            <span className="text-sm font-medium text-gray-700">Progress</span>
            <span className="text-sm font-medium text-gray-700">{progress}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className={`h-2 rounded-full transition-all duration-500 ${
                status === 'error' ? 'bg-red-500' :
                status === 'running' ? 'bg-green-500' :
                'bg-blue-500'
              }`}
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}

      {status === 'building' && (
        <div className="mt-4 flex items-center space-x-2 text-sm text-gray-600">
          <div className="animate-pulse flex space-x-1">
            <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
            <div className="w-2 h-2 bg-blue-500 rounded-full animation-delay-200"></div>
            <div className="w-2 h-2 bg-blue-500 rounded-full animation-delay-400"></div>
          </div>
          <span>In progress...</span>
        </div>
      )}
    </div>
  );
};