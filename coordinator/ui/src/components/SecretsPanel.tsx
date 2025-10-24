import React, { useCallback, useEffect, useMemo, useState } from 'react';

interface SecretsPanelProps {
  root: string;
}

interface SecretsResponse {
  path: string;
  secrets: Record<string, string>;
}

export const SecretsPanel: React.FC<SecretsPanelProps> = ({ root }) => {
  const [secrets, setSecrets] = useState<Record<string, string>>({});
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
    setValueInput(secrets[key] ?? '');
  };

  return (
    <div className="mt-3 p-3 border rounded bg-white space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-xs font-semibold">Secrets</div>
          <div className="text-[10px] text-gray-500">{filename}</div>
        </div>
        <button
          type="button"
          onClick={loadSecrets}
          disabled={loading}
          className="text-xs px-2 py-1 bg-gray-100 hover:bg-gray-200 rounded disabled:opacity-60"
        >
          {loading ? 'Loading...' : 'Refresh'}
        </button>
      </div>

      {error && <div className="text-xs text-red-600">{error}</div>}
      {message && <div className="text-xs text-green-600">{message}</div>}

      <div className="max-h-40 overflow-auto border rounded">
        {sortedKeys.length === 0 ? (
          <div className="text-xs text-gray-500 p-2">No secrets stored.</div>
        ) : (
          <table className="w-full text-xs">
            <thead className="bg-gray-100 text-gray-600">
              <tr>
                <th className="text-left px-2 py-1 font-medium">Key</th>
                <th className="text-left px-2 py-1 font-medium">Value</th>
                <th className="px-2 py-1"></th>
              </tr>
            </thead>
            <tbody>
              {sortedKeys.map((key) => (
                <tr key={key} className="border-t">
                  <td className="px-2 py-1 font-mono break-all align-top">{key}</td>
                  <td className="px-2 py-1 break-all align-top">{secrets[key]}</td>
                  <td className="px-2 py-1 text-right align-top">
                    <button
                      type="button"
                      onClick={() => populateForm(key)}
                      className="px-2 py-1 bg-blue-50 text-blue-600 rounded text-[10px]"
                    >
                      Edit
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <form className="space-y-2" onSubmit={handleSubmit}>
        <div className="space-y-1">
          <label className="block text-[11px] font-medium text-gray-700" htmlFor="secret-key-input">
            Key
          </label>
          <input
            id="secret-key-input"
            className="w-full text-xs border rounded px-2 py-1"
            value={keyInput}
            onChange={(event) => setKeyInput(event.target.value)}
            placeholder="API_TOKEN"
            title="Secret key"
            aria-label="Secret key"
          />
        </div>
        <div className="space-y-1">
          <label className="block text-[11px] font-medium text-gray-700" htmlFor="secret-value-input">
            Value
          </label>
          <textarea
            id="secret-value-input"
            className="w-full text-xs border rounded px-2 py-1 min-h-[64px]"
            value={valueInput}
            onChange={(event) => setValueInput(event.target.value)}
            placeholder="my-secret-value"
            title="Secret value"
            aria-label="Secret value"
          />
        </div>
        <div className="flex justify-end">
          <button
            type="submit"
            disabled={submitting}
            className="px-3 py-1 bg-blue-600 text-white rounded text-xs disabled:opacity-60"
          >
            {submitting ? 'Saving…' : 'Save Secret'}
          </button>
        </div>
      </form>
    </div>
  );
};
