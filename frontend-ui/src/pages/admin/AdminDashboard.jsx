import { useState, useEffect } from 'react';
import { useAuth } from '../../components/AuthContext';

export default function AdminDashboard({ onNavigate }) {
  const { token } = useAuth();
  const [stats, setStats] = useState({ total: 0, new: 0, active: 0, error: null });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetch('/api/admin/users', { headers: { Authorization: `Bearer ${token}` } }).then(res => {
        if (!res.ok) throw new Error('Failed to fetch users');
        return res.json();
      }),
      fetch('/api/health').then(res => res.json())
    ])
      .then(([users, healthData]) => {
        const now = new Date();
        const thirtyDaysAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
        
        const newUsers = users.filter(u => new Date(u.created_at) > thirtyDaysAgo).length;
        
        setStats({
          total: users.length,
          new: newUsers,
          active: users.length, // Rough proxy for now
          analysesCount: healthData.analyses_count || 0,
          error: null
        });
      })
      .catch(err => {
        setStats(s => ({ ...s, error: err.message }));
      })
      .finally(() => setLoading(false));
  }, [token]);

  return (
    <section className="page active">
      <div className="page-header">
        <h1 className="page-title">Admin Dashboard</h1>
        <p className="page-subtitle">Overview of system activity and users.</p>
      </div>

      <div className="metrics-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', display: 'grid', gap: '20px', marginBottom: '32px' }}>
        <div className="metric-card" style={{ background: 'var(--bg-card)', padding: '24px', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)' }}>
          <div className="metric-title" style={{ fontSize: '14px', color: 'var(--text-secondary)', marginBottom: '8px' }}>Total Users</div>
          <div className="metric-value" style={{ fontSize: '32px', fontWeight: '800', color: 'var(--text-primary)' }}>
            {loading ? '...' : stats.total}
          </div>
        </div>
        <div className="metric-card" style={{ background: 'var(--bg-card)', padding: '24px', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)' }}>
          <div className="metric-title" style={{ fontSize: '14px', color: 'var(--text-secondary)', marginBottom: '8px' }}>New Users (30d)</div>
          <div className="metric-value" style={{ fontSize: '32px', fontWeight: '800', color: 'var(--text-primary)' }}>
            {loading ? '...' : stats.new}
          </div>
        </div>
        <div className="metric-card" style={{ background: 'var(--bg-card)', padding: '24px', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)' }}>
          <div className="metric-title" style={{ fontSize: '14px', color: 'var(--text-secondary)', marginBottom: '8px' }}>Active Users</div>
          <div className="metric-value" style={{ fontSize: '32px', fontWeight: '800', color: 'var(--text-primary)' }}>
            {loading ? '...' : stats.active}
          </div>
        </div>
        <div className="metric-card" style={{ background: 'var(--bg-card)', padding: '24px', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)' }}>
          <div className="metric-title" style={{ fontSize: '14px', color: 'var(--text-secondary)', marginBottom: '8px' }}>Total Analyses</div>
          <div className="metric-value" style={{ fontSize: '32px', fontWeight: '800', color: 'var(--text-primary)' }}>
            {loading ? '...' : stats.analysesCount}
          </div>
        </div>
      </div>

      <div className="result-card">
        <h3>Quick Actions</h3>
        <p style={{ color: 'var(--text-secondary)', marginBottom: '16px', fontSize: '14px' }}>
          Manage the system and its users.
        </p>
        <div style={{ display: 'flex', gap: '16px' }}>
          <button className="btn btn-primary" onClick={() => onNavigate('users')}>
            <i className="fas fa-users"></i> Manage Users
          </button>
          <button className="btn btn-outline" onClick={() => onNavigate('settings')}>
            <i className="fas fa-cog"></i> System Settings
          </button>
        </div>
      </div>
    </section>
  );
}
