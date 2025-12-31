import React, { useEffect, useRef } from 'react';

interface LivePreviewProps {
  previewUrl: string;
  openUrl?: string;
  sessionToken?: string;
  instanceId: string;
  useSandbox?: boolean;
}

export const LivePreview: React.FC<LivePreviewProps> = ({
  previewUrl,
  openUrl,
  sessionToken,
  instanceId,
  useSandbox = true
}) => {
  const iframeRef = useRef<HTMLIFrameElement>(null);

  // Compute frame URL
  const alreadyHasSession = /[?&]session=/.test(previewUrl);
  const isBridge = previewUrl.includes('/preview/bridge');
  const frameUrl = (sessionToken && !alreadyHasSession && !isBridge)
    ? `${previewUrl}${previewUrl.includes('?') ? '&' : '?'}session=${sessionToken}`
    : previewUrl;
  const newTabUrl = openUrl || previewUrl;

  // Determine if we can safely iframe this (bridge or same-origin or localhost)
  const sameOrigin = previewUrl.startsWith('/') || previewUrl.startsWith(window.location.origin);
  const canIframe = useSandbox && (isBridge || sameOrigin || previewUrl.includes('localhost'));

  useEffect(() => {
    // Apply CSP and security attributes
    if (iframeRef.current && canIframe) {
      iframeRef.current.setAttribute('sandbox', 'allow-scripts allow-same-origin allow-forms allow-popups allow-modals allow-popups-to-escape-sandbox');
    }
  }, [canIframe]);

  if (!canIframe) {
    // Open in new tab for non-localhost or when iframe is not safe
    return (
      <div className="flex items-center justify-center h-[500px]">
        <div className="glass-panel rounded-2xl p-10 text-center max-w-lg mx-auto border border-white/10 bg-white/5">
          <div className="mb-6 relative">
            <div className="absolute inset-0 bg-blue-500/20 blur-xl rounded-full"></div>
            <div className="relative w-20 h-20 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-2xl flex items-center justify-center mx-auto shadow-lg shadow-blue-500/25">
              <i className="fas fa-external-link-alt text-3xl text-white"></i>
            </div>
          </div>
          <h3 className="text-2xl font-bold mb-3 text-white">Preview Available</h3>
          <p className="text-gray-400 mb-8 leading-relaxed">
            For security reasons, this application preview must be opened in a new separate window.
          </p>
          <a
            href={newTabUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="group inline-flex items-center bg-white text-gray-900 hover:bg-gray-100 font-bold py-3 px-8 rounded-xl transition-all shadow-lg shadow-white/10 hover:shadow-white/20 transform hover:-translate-y-0.5"
          >
            <span>Open Preview</span>
            <i className="fas fa-arrow-right ml-2 group-hover:translate-x-1 transition-transform"></i>
          </a>
          <div className="mt-6 text-xs text-gray-500 font-mono">
            Instance ID: {instanceId}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full h-full bg-white">
      <iframe
        ref={iframeRef}
        src={frameUrl}
        className="w-full h-[600px] border-none"
        title="Application Preview"
        sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-modals allow-popups-to-escape-sandbox"
      />
    </div>
  );
};