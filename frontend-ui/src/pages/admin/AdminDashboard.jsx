import { useState, useEffect } from 'react';
import { useAuth } from '../../components/AuthContext';

const FONT = "'Inter', 'Segoe UI', system-ui, sans-serif";

const StatCard = ({ label, value, icon, color, loading, subtitle }) => (
  <div style={{
    background: 'var(--adm-surface)',
    border: '1px solid var(--adm-border)',
    borderRadius: '16px',
    padding: '24px',
    display: 'flex',
    alignItems: 'center',
    gap: '18px',
    boxShadow: 'var(--adm-shadow)',
    flex: '1 1 180px',
    minWidth: '0',
    fontFamily: FONT,
  }}>
    <div style={{
      width: '54px', height: '54px', borderRadius: '14px',
      background: color + '18',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontSize: '22px', color, flexShrink: 0,
    }}>
      <i className={`fas ${icon}`} />
    </div>
    <div style={{ minWidth: 0 }}>
      <div style={{ fontSize: '12.5px', color: 'var(--adm-text-3)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '4px' }}>
        {label}
      </div>
      <div style={{ fontSize: '32px', fontWeight: 800, color: 'var(--adm-text)', lineHeight: 1 }}>
        {loading ? <span style={{ fontSize: '18px', color: 'var(--adm-text-muted)' }}>—</span> : value}
      </div>
      {subtitle && (
        <div style={{ fontSize: '12px', color: 'var(--adm-text-muted)', marginTop: '4px' }}>{subtitle}</div>
      )}
    </div>
  </div>
);

export default function AdminDashboard({ onNavigate }) {
  const { token } = useAuth();
  const [stats, setStats] = useState({ total_users: 0, new_users_30d: 0, total_analyses: 0 });
  const [recentUsers, setRecentUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const headers = { Authorization: `Bearer ${token}` };
    Promise.all([
      fetch('/api/admin/stats', { headers }).then(r => { if (!r.ok) throw new Error(`Stats ${r.status}`); return r.json(); }),
      fetch('/api/admin/users', { headers }).then(r => { if (!r.ok) throw new Error(`Users ${r.status}`); return r.json(); }),
    ])
      .then(([s, users]) => {
        setStats(s);
        setRecentUsers(users.slice(0, 5));
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, [token]);

  return (
    <div style={{
      padding: '36px 40px',
      fontFamily: FONT,
      maxWidth: '1120px',
      color: 'var(--adm-text)',
      background: 'var(--adm-bg)',
      minHeight: '100%',
    }}>
      {/* Header */}
      <div style={{ marginBottom: '32px' }}>
        <h1 style={{ fontSize: '26px', fontWeight: 800, margin: 0, color: 'var(--adm-text)' }}>
          Admin Dashboard
        </h1>
        <p style={{ color: 'var(--adm-text-3)', margin: '6px 0 0', fontSize: '14.5px' }}>
          MongoDB-backed system overview — users, activity, and analytics.
        </p>
      </div>

      {/* Error */}
      {error && (
        <div style={{
          background: '#fef2f2', border: '1px solid #fecaca', borderRadius: '12px',
          padding: '14px 18px', marginBottom: '24px',
          color: '#b91c1c', fontSize: '14px',
          display: 'flex', alignItems: 'center', gap: '10px',
        }}>
          <i className="fas fa-exclamation-circle" />
          <strong>Error:</strong>&nbsp;{error}
        </div>
      )}

      {/* Stats */}
      <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap', marginBottom: '32px' }}>
        <StatCard label="Total Users"     icon="fa-users"      color="#0F766E" value={stats.total_users}    loading={loading} subtitle="All registered accounts" />
        <StatCard label="New (30 days)"   icon="fa-user-plus"  color="#7c3aed" value={stats.new_users_30d}  loading={loading} subtitle="Joined in the last month" />
        <StatCard label="Total Analyses"  icon="fa-microscope" color="#d97706" value={stats.total_analyses} loading={loading} subtitle="AI scans performed" />
      </div>

      {/* Recent Users */}
      <div style={{
        background: 'var(--adm-surface)',
        border: '1px solid var(--adm-border)',
        borderRadius: '16px', overflow: 'hidden',
        boxShadow: 'var(--adm-shadow)',
        marginBottom: '24px',
      }}>
        <div style={{
          padding: '20px 24px',
          borderBottom: '1px solid var(--adm-border-light)',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        }}>
          <div>
            <div style={{ fontSize: '15px', fontWeight: 700, color: 'var(--adm-text)' }}>Recent Users</div>
            <div style={{ fontSize: '13px', color: 'var(--adm-text-3)', marginTop: '2px' }}>Latest 5 registrations from MongoDB</div>
          </div>
          <button
            onClick={() => onNavigate('users')}
            style={{
              background: 'none', border: '1px solid var(--adm-border)',
              borderRadius: '8px', padding: '7px 14px',
              fontSize: '13px', fontWeight: 600, color: '#0F766E',
              cursor: 'pointer', fontFamily: FONT,
            }}
          >
            View All <i className="fas fa-arrow-right" style={{ marginLeft: '6px' }} />
          </button>
        </div>
        <div>
          {loading ? (
            <div style={{ padding: '32px', textAlign: 'center', color: 'var(--adm-text-muted)', fontSize: '14px' }}>
              <i className="fas fa-circle-notch fa-spin" style={{ marginRight: '8px' }} />
              Loading from MongoDB…
            </div>
          ) : recentUsers.length === 0 ? (
            <div style={{ padding: '40px', textAlign: 'center', color: 'var(--adm-text-muted)' }}>
              <i className="fas fa-users" style={{ fontSize: '28px', marginBottom: '12px', display: 'block' }} />
              No users found in MongoDB.
            </div>
          ) : (
            recentUsers.map((u, i) => (
              <div key={u.id} style={{
                display: 'flex', alignItems: 'center', gap: '14px',
                padding: '14px 24px',
                borderBottom: i < recentUsers.length - 1 ? '1px solid var(--adm-border-light)' : 'none',
              }}>
                <div style={{
                  width: '38px', height: '38px', borderRadius: '50%',
                  background: u.role === 'admin' ? '#fef2f2' : '#f0fdfa',
                  color: u.role === 'admin' ? '#dc2626' : '#0F766E',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontWeight: 700, fontSize: '14px', flexShrink: 0,
                }}>
                  {(u.first_name[0] + u.last_name[0]).toUpperCase()}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--adm-text)' }}>
                    {u.first_name} {u.last_name}
                  </div>
                  <div style={{ fontSize: '13px', color: 'var(--adm-text-3)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {u.email}
                  </div>
                </div>
                <span style={{
                  padding: '3px 10px', borderRadius: '20px', fontSize: '11.5px', fontWeight: 700,
                  background: u.role === 'admin' ? '#fef2f2' : '#f0fdfa',
                  color: u.role === 'admin' ? '#dc2626' : '#0F766E',
                  textTransform: 'uppercase', letterSpacing: '0.04em',
                }}>
                  {u.role}
                </span>
                <div style={{ fontSize: '12px', color: 'var(--adm-text-muted)', whiteSpace: 'nowrap', marginLeft: '8px' }}>
                  {new Date(u.created_at).toLocaleDateString()}
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Quick Actions */}
      <div style={{
        background: 'var(--adm-surface)',
        border: '1px solid var(--adm-border)',
        borderRadius: '16px', padding: '24px',
        boxShadow: 'var(--adm-shadow)',
      }}>
        <div style={{ fontSize: '15px', fontWeight: 700, color: 'var(--adm-text)', marginBottom: '6px' }}>Quick Actions</div>
        <div style={{ fontSize: '13px', color: 'var(--adm-text-3)', marginBottom: '18px' }}>Jump to key admin tasks</div>
        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
          {[
            { label: 'Manage Users',    icon: 'fa-users', page: 'users',    color: '#0F766E' },
            { label: 'System Settings', icon: 'fa-cog',   page: 'settings', color: '#7c3aed' },
          ].map(a => (
            <button
              key={a.page}
              onClick={() => onNavigate(a.page)}
              style={{
                display: 'inline-flex', alignItems: 'center', gap: '8px',
                padding: '11px 22px', borderRadius: '10px',
                background: a.color, color: '#fff', border: 'none',
                fontSize: '14px', fontWeight: 600, cursor: 'pointer',
                boxShadow: `0 2px 8px ${a.color}40`,
                transition: 'opacity .15s, transform .15s', fontFamily: FONT,
              }}
              onMouseEnter={e => { e.currentTarget.style.opacity = '.85'; e.currentTarget.style.transform = 'translateY(-1px)'; }}
              onMouseLeave={e => { e.currentTarget.style.opacity = '1';   e.currentTarget.style.transform = 'translateY(0)'; }}
            >
              <i className={`fas ${a.icon}`} />{a.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
