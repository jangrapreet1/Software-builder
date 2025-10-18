import React, { useState, useEffect } from 'react';

interface PermissionsStats {
  total_permissions: number;
  active_permissions: number;
  total_executions: number;
}

export const PermissionsStatsPanel: React.FC = () => {
  const [stats, setStats] = useState<PermissionsStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchStats = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/permissions/stats');
      
      if (!response.ok) {
        throw new Error(`Failed to fetch permissions stats: ${response.statusText}`);
      }

      const data = await response.json();
      setStats(data.stats);
    } catch (err: any) {
      console.error('Error fetching permissions stats:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
    
    // Refresh every 30 seconds
    const interval = setInterval(fetchStats, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="bg-gradient-to-br from-purple-50 to-indigo-50 rounded-lg p-4 border border-purple-200">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-2">
          <i className="fas fa-shield-alt text-purple-600"></i>
          <h4 className="text-sm font-semibold text-purple-900">Permission Stats</h4>
        </div>
        <button
          onClick={fetchStats}
          className="text-xs text-purple-600 hover:text-purple-700"
          disabled={loading}
          title="Refresh permissions stats"
          aria-label="Refresh permissions stats"
        >
          <i className={`fas fa-sync-alt ${loading ? 'fa-spin' : ''}`}></i>
        </button>
      </div>

      {error && (
        <div className="text-xs text-red-600 flex items-center space-x-1">
          <i className="fas fa-exclamation-triangle"></i>
          <span>{error}</span>
        </div>
      )}

      {stats && !loading && (
        <div className="grid grid-cols-3 gap-2">
          <div className="bg-white rounded p-2 text-center">
            <div className="text-xs text-gray-600 mb-1">Total</div>
            <div className="text-lg font-bold text-purple-700">{stats.total_permissions}</div>
          </div>
          <div className="bg-white rounded p-2 text-center">
            <div className="text-xs text-gray-600 mb-1">Active</div>
            <div className="text-lg font-bold text-green-600">{stats.active_permissions}</div>
          </div>
          <div className="bg-white rounded p-2 text-center">
            <div className="text-xs text-gray-600 mb-1">Executions</div>
            <div className="text-lg font-bold text-blue-600">{stats.total_executions}</div>
          </div>
        </div>
      )}
    </div>
  );
};
