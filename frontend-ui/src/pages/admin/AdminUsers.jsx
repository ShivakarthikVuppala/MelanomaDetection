import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../../components/AuthContext';

const FONT = "'Inter', 'Segoe UI', system-ui, sans-serif";

function Avatar({ firstName, lastName, role }) {
  const initials = ((firstName?.[0] || '') + (lastName?.[0] || '')).toUpperCase() || '?';
  return (
    <div style={{
      width: '36px', height: '36px', borderRadius: '50%', flexShrink: 0,
      background: role === 'admin' ? '#fef2f2' : '#f0fdfa',
      color: role === 'admin' ? '#dc2626' : '#0F766E',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontWeight: 700, fontSize: '13px', fontFamily: FONT,
    }}>
      {initials}
    </div>
  );
}

function RoleBadge({ role }) {
  return (
    <span style={{
      padding: '3px 10px', borderRadius: '20px',
      fontSize: '11.5px', fontWeight: 700,
      textTransform: 'uppercase', letterSpacing: '0.05em',
      background: role === 'admin' ? '#fef2f2' : '#f0fdfa',
      color: role === 'admin' ? '#dc2626' : '#0F766E',
    }}>
      {role}
    </span>
  );
}

function Toast({ msg, type, onDone }) {
  useEffect(() => { const t = setTimeout(onDone, 3000); return () => clearTimeout(t); }, []);
  return (
    <div style={{
      position: 'fixed', bottom: '28px', right: '28px', zIndex: 9999,
      background: type === 'success' ? '#0F766E' : '#dc2626',
      color: '#fff', padding: '14px 22px', borderRadius: '12px',
      fontSize: '14px', fontWeight: 600,
      boxShadow: '0 8px 24px rgba(0,0,0,0.18)',
      display: 'flex', alignItems: 'center', gap: '10px', fontFamily: FONT,
    }}>
      <i className={type === 'success' ? 'fas fa-check-circle' : 'fas fa-times-circle'} />
      {msg}
    </div>
  );
}

function DeleteModal({ user, onCancel, onConfirm, loading }) {
  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(15,23,42,0.6)',
      zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontFamily: FONT,
    }}>
      <div style={{
        background: 'var(--adm-surface)',
        border: '1px solid var(--adm-border)',
        borderRadius: '18px', padding: '32px',
        width: '100%', maxWidth: '420px',
        boxShadow: '0 20px 60px rgba(15,23,42,0.2)',
      }}>
        <div style={{
          width: '52px', height: '52px', borderRadius: '14px',
          background: '#fef2f2', color: '#dc2626',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: '22px', marginBottom: '20px',
        }}>
          <i className="fas fa-trash-alt" />
        </div>
        <h3 style={{ fontSize: '19px', fontWeight: 800, color: 'var(--adm-text)', margin: '0 0 8px' }}>
          Delete User?
        </h3>
        <p style={{ fontSize: '14.5px', color: 'var(--adm-text-3)', lineHeight: 1.6, margin: '0 0 24px' }}>
          Permanently remove <strong style={{ color: 'var(--adm-text)' }}>{user.first_name} {user.last_name}</strong>{' '}
          ({user.email}) from MongoDB? This action cannot be undone.
        </p>
        <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
          <button onClick={onCancel} disabled={loading} style={{
            padding: '10px 20px', borderRadius: '9px',
            border: '1px solid var(--adm-border)',
            background: 'var(--adm-surface)',
            fontSize: '14px', fontWeight: 600, color: 'var(--adm-text-3)',
            cursor: 'pointer', fontFamily: FONT,
          }}>
            Cancel
          </button>
          <button onClick={onConfirm} disabled={loading} style={{
            padding: '10px 20px', borderRadius: '9px',
            border: 'none', background: '#dc2626', color: '#fff',
            fontSize: '14px', fontWeight: 600, cursor: 'pointer',
            opacity: loading ? 0.7 : 1, fontFamily: FONT,
          }}>
            {loading ? 'Deleting…' : 'Delete User'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function AdminUsers() {
  const { token } = useAuth();
  const [users, setUsers]           = useState([]);
  const [loading, setLoading]       = useState(true);
  const [search, setSearch]         = useState('');
  const [roleFilter, setRoleFilter] = useState('all');
  const [userToDelete, setUserToDelete] = useState(null);
  const [deleting, setDeleting]     = useState(false);
  const [toast, setToast]           = useState(null);

  const showToast = (msg, type = 'success') => setToast({ msg, type });

  const fetchUsers = useCallback(() => {
    setLoading(true);
    fetch('/api/admin/users', { headers: { Authorization: `Bearer ${token}` } })
      .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); })
      .then(data => setUsers(data))
      .catch(err => showToast(`Failed to load users: ${err.message}`, 'error'))
      .finally(() => setLoading(false));
  }, [token]);

  useEffect(fetchUsers, [fetchUsers]);

  const handleDelete = async () => {
    if (!userToDelete) return;
    setDeleting(true);
    try {
      const res = await fetch(`/api/admin/users/${userToDelete.id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) { const b = await res.json(); throw new Error(b.detail || 'Delete failed'); }
      showToast('User deleted successfully.', 'success');
      setUserToDelete(null);
      fetchUsers();
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setDeleting(false);
    }
  };

  const visible = users.filter(u => {
    const q = search.toLowerCase();
    const matchSearch = !q || `${u.first_name} ${u.last_name}`.toLowerCase().includes(q) || u.email.toLowerCase().includes(q);
    const matchRole   = roleFilter === 'all' || u.role === roleFilter;
    return matchSearch && matchRole;
  });

  const inputBase = {
    border: '1px solid var(--adm-border)',
    background: 'var(--adm-surface)',
    color: 'var(--adm-text)',
    borderRadius: '10px', fontSize: '14px',
    fontFamily: FONT, outline: 'none',
  };

  return (
    <div style={{ padding: '36px 40px', fontFamily: FONT, maxWidth: '1120px', color: 'var(--adm-text)', background: 'var(--adm-bg)', minHeight: '100%' }}>
      {/* Header */}
      <div style={{ marginBottom: '28px' }}>
        <h1 style={{ fontSize: '26px', fontWeight: 800, margin: 0, color: 'var(--adm-text)' }}>User Management</h1>
        <p style={{ color: 'var(--adm-text-3)', margin: '6px 0 0', fontSize: '14.5px' }}>
          All users stored in MongoDB · {users.length} total
        </p>
      </div>

      {/* Toolbar */}
      <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', alignItems: 'center', marginBottom: '20px' }}>
        <div style={{ position: 'relative', flex: '1 1 260px' }}>
          <i className="fas fa-search" style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)', color: 'var(--adm-text-muted)', fontSize: '14px' }} />
          <input
            value={search} onChange={e => setSearch(e.target.value)}
            placeholder="Search by name or email…"
            style={{ ...inputBase, width: '100%', padding: '10px 14px 10px 40px', boxSizing: 'border-box' }}
          />
        </div>
        <select value={roleFilter} onChange={e => setRoleFilter(e.target.value)}
          style={{ ...inputBase, padding: '10px 14px', cursor: 'pointer' }}>
          <option value="all">All Roles</option>
          <option value="user">Users</option>
          <option value="admin">Admins</option>
        </select>
        <button onClick={fetchUsers} style={{
          ...inputBase, padding: '10px 16px', color: '#0F766E',
          fontWeight: 600, cursor: 'pointer',
          display: 'flex', alignItems: 'center', gap: '7px',
        }}>
          <i className="fas fa-sync-alt" /> Refresh
        </button>
      </div>

      {/* Table */}
      <div style={{
        background: 'var(--adm-surface)',
        border: '1px solid var(--adm-border)',
        borderRadius: '16px', overflow: 'hidden',
        boxShadow: 'var(--adm-shadow)',
      }}>
        {loading ? (
          <div style={{ padding: '60px', textAlign: 'center', color: 'var(--adm-text-muted)', fontSize: '15px' }}>
            <i className="fas fa-circle-notch fa-spin" style={{ fontSize: '28px', marginBottom: '14px', display: 'block', color: '#0F766E' }} />
            Loading users from MongoDB…
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '14px' }}>
              <thead>
                <tr style={{ background: 'var(--adm-bg)', borderBottom: '1px solid var(--adm-border)' }}>
                  {['User', 'Email', 'Phone', 'Role', 'Joined', 'Actions'].map(h => (
                    <th key={h} style={{
                      padding: '13px 16px', textAlign: 'left',
                      fontWeight: 700, fontSize: '11.5px',
                      color: 'var(--adm-text-3)',
                      textTransform: 'uppercase', letterSpacing: '0.06em', whiteSpace: 'nowrap',
                    }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {visible.map((u, i) => (
                  <tr key={u.id}
                    style={{ borderBottom: i < visible.length - 1 ? `1px solid var(--adm-border-light)` : 'none', transition: 'background .12s' }}
                    onMouseEnter={e => e.currentTarget.style.background = 'var(--adm-row-hover)'}
                    onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                  >
                    <td style={{ padding: '14px 16px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <Avatar firstName={u.first_name} lastName={u.last_name} role={u.role} />
                        <div>
                          <div style={{ fontWeight: 600, color: 'var(--adm-text)' }}>{u.first_name} {u.last_name}</div>
                          <div style={{ fontSize: '11.5px', color: 'var(--adm-text-muted)', fontFamily: 'monospace' }}>…{u.id.slice(-8)}</div>
                        </div>
                      </div>
                    </td>
                    <td style={{ padding: '14px 16px', color: 'var(--adm-text-2)' }}>{u.email}</td>
                    <td style={{ padding: '14px 16px', color: 'var(--adm-text-3)' }}>{u.phone || '—'}</td>
                    <td style={{ padding: '14px 16px' }}><RoleBadge role={u.role} /></td>
                    <td style={{ padding: '14px 16px', color: 'var(--adm-text-muted)', whiteSpace: 'nowrap' }}>
                      {new Date(u.created_at).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })}
                    </td>
                    <td style={{ padding: '14px 16px' }}>
                      {u.role !== 'admin' && (
                        <button onClick={() => setUserToDelete(u)} style={{
                          background: 'none', border: '1px solid #fecaca',
                          borderRadius: '8px', padding: '6px 14px',
                          color: '#dc2626', fontSize: '13px', fontWeight: 600,
                          cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: '6px',
                          fontFamily: FONT,
                        }}
                          onMouseEnter={e => e.currentTarget.style.background = '#fef2f2'}
                          onMouseLeave={e => e.currentTarget.style.background = 'none'}
                        >
                          <i className="fas fa-trash-alt" /> Delete
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
                {visible.length === 0 && (
                  <tr>
                    <td colSpan={6} style={{ padding: '60px', textAlign: 'center', color: 'var(--adm-text-muted)' }}>
                      <i className="fas fa-search" style={{ fontSize: '28px', display: 'block', marginBottom: '12px' }} />
                      No users match your filter.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {!loading && (
        <div style={{ marginTop: '12px', fontSize: '13px', color: 'var(--adm-text-muted)', textAlign: 'right' }}>
          Showing {visible.length} of {users.length} users
        </div>
      )}

      {userToDelete && (
        <DeleteModal user={userToDelete} onCancel={() => setUserToDelete(null)} onConfirm={handleDelete} loading={deleting} />
      )}
      {toast && <Toast msg={toast.msg} type={toast.type} onDone={() => setToast(null)} />}
    </div>
  );
}
