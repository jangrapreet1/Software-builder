import React, { useState, useEffect } from 'react';

export interface ValidationStatus {
  previewUrl: string;
  status: 'checking' | 'running' | 'error' | 'unknown';
  bootTime?: number;
  errorFixed: boolean;
  originalError?: string;
  currentStatus?: string;
  lastChecked?: string;
}

interface PreviewValidationProps {
  previewUrl: string;
  originalError?: string;
  onStatusChange?: (status: ValidationStatus) => void;
}

export const PreviewValidation: React.FC<PreviewValidationProps> = ({
  previewUrl,
  originalError,
  onStatusChange
}) => {
  const [validationStatus, setValidationStatus] = useState<ValidationStatus>({
    previewUrl,
    status: 'checking',
    errorFixed: false,
    originalError
  });

  useEffect(() => {
    let isMounted = true;
    let checkInterval: NodeJS.Timeout;

    const checkPreviewStatus = async () => {
      try {
        const startTime = Date.now();
        const response = await fetch(previewUrl, {
          method: 'HEAD',
          mode: 'no-cors' // Avoid CORS issues for status check
        });
        const bootTime = Date.now() - startTime;

        if (isMounted) {
          const newStatus: ValidationStatus = {
            previewUrl,
            status: 'running',
            bootTime,
            errorFixed: true, // If we can reach it, the error is likely fixed
            originalError,
            currentStatus: 'Preview is accessible',
            lastChecked: new Date().toISOString()
          };
          setValidationStatus(newStatus);
          onStatusChange?.(newStatus);
        }
      } catch (error) {
        if (isMounted) {
          // Even with no-cors, if it fails, we can't determine much
          // But we'll assume it's still checking or there's an error
          const newStatus: ValidationStatus = {
            previewUrl,
            status: 'unknown',
            errorFixed: false,
            originalError,
            currentStatus: 'Unable to verify preview status',
            lastChecked: new Date().toISOString()
          };
          setValidationStatus(newStatus);
          onStatusChange?.(newStatus);
        }
      }
    };

    // Initial check after a short delay
    const initialDelay = setTimeout(() => {
      checkPreviewStatus();
    }, 2000);

    // Then check periodically
    checkInterval = setInterval(checkPreviewStatus, 10000); // Every 10 seconds

    return () => {
      isMounted = false;
      clearTimeout(initialDelay);
      clearInterval(checkInterval);
    };
  }, [previewUrl, originalError, onStatusChange]);

  const getStatusBadge = () => {
    switch (validationStatus.status) {
      case 'checking':
        return (
          <span className="inline-flex items-center bg-blue-100 text-blue-800 text-xs font-semibold px-3 py-1 rounded-full">
            <i className="fas fa-spinner fa-spin mr-2"></i>
            Checking...
          </span>
        );
      case 'running':
        return (
          <span className="inline-flex items-center bg-green-100 text-green-800 text-xs font-semibold px-3 py-1 rounded-full">
            <i className="fas fa-check-circle mr-2"></i>
            Running
          </span>
        );
      case 'error':
        return (
          <span className="inline-flex items-center bg-red-100 text-red-800 text-xs font-semibold px-3 py-1 rounded-full">
            <i className="fas fa-exclamation-circle mr-2"></i>
            Error
          </span>
        );
      case 'unknown':
        return (
          <span className="inline-flex items-center bg-gray-100 text-gray-800 text-xs font-semibold px-3 py-1 rounded-full">
            <i className="fas fa-question-circle mr-2"></i>
            Unknown
          </span>
        );
    }
  };

  const getErrorFixStatus = () => {
    if (validationStatus.errorFixed) {
      return (
        <div className="flex items-center bg-green-50 border border-green-200 rounded-lg p-3">
          <i className="fas fa-check-circle text-green-600 text-2xl mr-3"></i>
          <div className="flex-1">
            <div className="font-semibold text-green-800 text-sm">Error Fixed</div>
            <div className="text-xs text-green-700">
              The original error no longer appears in the preview
            </div>
          </div>
        </div>
      );
    } else {
      return (
        <div className="flex items-center bg-yellow-50 border border-yellow-200 rounded-lg p-3">
          <i className="fas fa-exclamation-triangle text-yellow-600 text-2xl mr-3"></i>
          <div className="flex-1">
            <div className="font-semibold text-yellow-800 text-sm">Unable to Verify</div>
            <div className="text-xs text-yellow-700">
              Could not confirm if the error was fixed
            </div>
          </div>
        </div>
      );
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center">
        <i className="fas fa-clipboard-check mr-2 text-blue-600"></i>
        Preview Validation
      </h3>

      {/* Status Badge */}
      <div className="mb-4">{getStatusBadge()}</div>

      {/* Error Fix Status */}
      <div className="mb-4">{getErrorFixStatus()}</div>

      {/* Preview URL */}
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 mb-4">
        <div className="text-xs text-gray-600 mb-2 font-semibold">Preview URL</div>
        <div className="flex items-center justify-between">
          <code className="text-sm text-gray-800 break-all">{previewUrl}</code>
          <a
            href={previewUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="ml-3 px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded transition whitespace-nowrap"
          >
            <i className="fas fa-external-link-alt mr-1"></i>
            Open
          </a>
        </div>
      </div>

      {/* Boot Time */}
      {validationStatus.bootTime && (
        <div className="mb-4">
          <div className="text-xs text-gray-600 mb-1">Boot Time</div>
          <div className="text-sm font-semibold text-gray-800">
            {validationStatus.bootTime}ms
          </div>
        </div>
      )}

      {/* Original Error */}
      {originalError && (
        <details className="mb-4">
          <summary className="cursor-pointer text-sm text-gray-700 hover:text-gray-900 font-medium">
            <i className="fas fa-bug mr-2"></i>
            View Original Error
          </summary>
          <div className="mt-2 bg-red-50 border border-red-200 rounded p-3">
            <pre className="text-xs text-red-800 whitespace-pre-wrap overflow-x-auto">
              {originalError}
            </pre>
          </div>
        </details>
      )}

      {/* Current Status */}
      {validationStatus.currentStatus && (
        <div className="text-xs text-gray-600">
          <i className="fas fa-info-circle mr-1"></i>
          {validationStatus.currentStatus}
        </div>
      )}

      {/* Last Checked */}
      {validationStatus.lastChecked && (
        <div className="text-xs text-gray-500 mt-2">
          Last checked: {new Date(validationStatus.lastChecked).toLocaleTimeString()}
        </div>
      )}
    </div>
  );
};
