import React, { useEffect, useRef } from 'react';

interface LivePreviewProps {
  previewUrl: string;
  sessionToken?: string;
  instanceId: string;
  useSandbox?: boolean;
}

export const LivePreview: React.FC<LivePreviewProps> = ({
  previewUrl,
  sessionToken,
  instanceId,
  useSandbox = true
}) => {
  const iframeRef = useRef<HTMLIFrameElement>(null);

  // Build secure URL with session token
  const secureUrl = sessionToken 
    ? `${previewUrl}?session=${sessionToken}`
    : previewUrl;

  // Determine if we can safely iframe this
  const canIframe = useSandbox && previewUrl.includes('localhost');

  useEffect(() => {
    // Apply CSP and security attributes
    if (iframeRef.current && canIframe) {
      iframeRef.current.setAttribute('sandbox', 'allow-scripts allow-same-origin allow-forms');
    }
  }, [canIframe]);

  if (!canIframe) {
    // Open in new tab for non-localhost or when iframe is not safe
    return (
      <div className="bg-white rounded-lg shadow-lg p-8 text-center">
        <div className="mb-4">
          <i className="fas fa-external-link-alt text-4xl text-blue-500"></i>
        </div>
        <h3 className="text-xl font-semibold mb-4">Preview Available</h3>
        <p className="text-gray-600 mb-6">
          For security reasons, this preview will open in a new tab.
        </p>
        <a
          href={secureUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-block bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-6 rounded-lg transition"
        >
          Open Preview <i className="fas fa-arrow-right ml-2"></i>
        </a>
        <div className="mt-4 text-sm text-gray-500">
          Instance ID: {instanceId}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-lg overflow-hidden">
      <div className="bg-gray-100 px-4 py-2 flex items-center justify-between border-b">
        <div className="flex items-center space-x-2">
          <i className="fas fa-globe text-blue-500"></i>
          <span className="text-sm font-medium text-gray-700">Live Preview</span>
        </div>
        <div className="flex items-center space-x-4">
          <span className="text-xs text-gray-500">Instance: {instanceId}</span>
          <a
            href={secureUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-blue-600 hover:text-blue-700"
          >
            <i className="fas fa-external-link-alt"></i>
          </a>
        </div>
      </div>
      <iframe
        ref={iframeRef}
        src={secureUrl}
        className="w-full h-[600px]"
        title="Application Preview"
        sandbox="allow-scripts allow-same-origin allow-forms"
      />
    </div>
  );
};