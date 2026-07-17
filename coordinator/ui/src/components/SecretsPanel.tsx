import React, { useCallback, useEffect, useMemo, useState } from 'react';

interface SecretsPanelProps {
  root: string;
}

interface SecretMetadata {
  set: boolean;
  length?: number;
}

interface SecretsResponse {
  path: string;
  secrets: Record<string, SecretMetadata | string>;
}

export const SecretsPanel: React.FC<SecretsPanelProps> = ({ root }) => {
  const [secrets, setSecrets] = useState<Record<string, SecretMetadata | string>>({});
  const [filename, setFilename] = useState('.env');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [keyInput, setKeyInput] = useState('');
  const [valueInput, setValueInput] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const sortedKeys = useMemo(() => Object.keys(secrets).sort(), [secrets]);

  const loadSecrets = useCallback(async () => {
    setLoading(true);
    setMessage(null);
    try {
      const trimmedRoot = root.trim();
      if (!trimmedRoot) {
        setSecrets({});
        setFilename('.env');
        setError('Enter a project root to load secrets.');
        return;
      }

      const response = await fetch(`/api/secrets/list?root=${encodeURIComponent(trimmedRoot)}`);
      if (!response.ok) {
        throw new Error(`Failed to load secrets (${response.status})`);
      }
      const data: SecretsResponse = await response.json();
      setSecrets(data.secrets || {});
      setFilename(data.path || '.env');
      setError(null);
    } catch (err: any) {
      setError(err?.message ?? 'Unable to load secrets');
      setSecrets({});
    } finally {
      setLoading(false);
    }
  }, [root]);

  useEffect(() => {
    loadSecrets();
  }, [loadSecrets]);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmedKey = keyInput.trim();
    if (!trimmedKey) {
      setError('Secret key cannot be empty.');
      return;
    }

    setSubmitting(true);
    setError(null);
    setMessage(null);
    try {
      const response = await fetch('/api/secrets/set', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ root: root.trim(), key: trimmedKey, value: valueInput })
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const msg = errorData?.detail || `Failed to save secret (${response.status})`;
        throw new Error(msg);
      }

      setMessage('Secret saved.');
      setKeyInput('');
      setValueInput('');
      await loadSecrets();
    } catch (err: any) {
      setError(err?.message ?? 'Unable to save secret');
    } finally {
      setSubmitting(false);
    }
  };

  const populateForm = (key: string) => {
    setKeyInput(key);
    setValueInput('');
  };

  const secretLabel = (secret: SecretMetadata | string) => {
    const length = typeof secret === 'string' ? secret.length : secret.length;
    return typeof length === 'number' ? `Set (${length} chars)` : 'Set';
  };

  return (
    <div className="glass-panel rounded-xl p-4 mt-4 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-[10px] font-bold text-gray-400 uppercase tracking-wider flex items-center">
            <i className="fas fa-key mr-2 text-accent"></i>
            Secrets
          </div>
          <div className="text-[10px] text-gray-500 font-mono mt-0.5">{filename}</div>
        </div>
        <button
          type="button"
          onClick={loadSecrets}
          disabled={loading}
          className="text-xs px-2 py-1 glass-button text-gray-400 hover:text-white rounded-lg disabled:opacity-50"
          title="Refresh secrets"
        >
          <i className={`fas fa-sync-alt ${loading ? 'fa-spin' : ''}`}></i>
        </button>
      </div>

      {error && <div className="text-xs text-red-200 bg-red-500/10 p-2 rounded border border-red-500/20">{error}</div>}
      {message && <div className="text-xs text-green-200 bg-green-500/10 p-2 rounded border border-green-500/20">{message}</div>}

      <div className="max-h-40 overflow-auto border border-white/5 rounded-lg bg-black/20 custom-scrollbar">
        {sortedKeys.length === 0 ? (
          <div className="text-xs text-gray-500 p-4 text-center italic">No secrets stored.</div>
        ) : (
          <table className="w-full text-xs">
            <thead className="bg-white/5 text-gray-400 sticky top-0 backdrop-blur-sm">
              <tr>
                <th className="text-left px-3 py-2 font-medium">Key</th>
                <th className="text-left px-3 py-2 font-medium">Value</th>
                <th className="px-3 py-2"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {sortedKeys.map((key) => (
                <tr key={key} className="hover:bg-white/5 transition-colors group">
                  <td className="px-3 py-2 font-mono text-primary/90 break-all align-top">{key}</td>
                  <td className="px-3 py-2 break-all align-top text-gray-400 group-hover:text-gray-200">
                    <span>{secretLabel(secrets[key])}</span>
                  </td>
                  <td className="px-3 py-2 text-right align-top">
                    <button
                      type="button"
                      onClick={() => populateForm(key)}
                      className="px-2 py-1 text-primary hover:text-white transition-colors text-[10px] opacity-0 group-hover:opacity-100"
                      title="Replace secret value"
                    >
                      <i className="fas fa-pen"></i>
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <form className="space-y-3 pt-2 border-t border-white/5" onSubmit={handleSubmit}>
        <div className="space-y-1">
          <label className="block text-[10px] font-bold text-gray-500 uppercase tracking-wider" htmlFor="secret-key-input">
            New Secret Key
          </label>
          <input
            id="secret-key-input"
            className="w-full text-xs bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-white placeholder-gray-600 focus:ring-1 focus:ring-primary/50 outline-none font-mono"
            value={keyInput}
            onChange={(event) => setKeyInput(event.target.value)}
            placeholder="API_TOKEN"
          />
        </div>
        <div className="space-y-1">
          <label className="block text-[10px] font-bold text-gray-500 uppercase tracking-wider" htmlFor="secret-value-input">
            Safe Value
          </label>
          <textarea
            id="secret-value-input"
            className="w-full text-xs bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-white placeholder-gray-600 focus:ring-1 focus:ring-primary/50 outline-none font-mono min-h-[60px]"
            value={valueInput}
            onChange={(event) => setValueInput(event.target.value)}
            placeholder="my-secret-value"
          />
        </div>
        <div className="flex justify-end">
          <button
            type="submit"
            disabled={submitting}
            className="px-4 py-2 bg-primary/20 hover:bg-primary/30 text-primary hover:text-white rounded-lg text-xs font-bold border border-primary/20 transition-all shadow-lg hover:shadow-primary/10 disabled:opacity-50"
          >
            {submitting ? (
              <><i className="fas fa-circle-notch fa-spin mr-2"></i>Saving...</>
            ) : (
              <><i className="fas fa-save mr-2"></i>Save Secret</>
            )}
          </button>
        </div>
      </form>
    </div>
  );
};
