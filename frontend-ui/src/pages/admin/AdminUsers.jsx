import { useState, useEffect } from 'react';
import { useAuth } from '../../components/AuthContext';
import { useToast } from '../../components/Toast';

export default function AdminUsers() {
  const { token, user: currentUser } = useAuth();
  const showToast = useToast();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // Deletion state
  const [userToDelete, setUserToDelete] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const fetchUsers = () => {
    setLoading(true);
    fetch('/api/admin/users', {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then(res => res.json())
      .then(data => setUsers(data))
      .catch(err => showToast('Failed to load users', 'error'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchUsers();
  }, [token]);

  const confirmDelete = async () => {
    if (!userToDelete) return;
    setIsDeleting(true);
    try {
      const res = await fetch(`/api/admin/users/${userToDelete.id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` }
      });
      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || 'Failed to delete user');
      }
      showToast('User deleted successfully', 'success');
      setUserToDelete(null);
      fetchUsers();
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <section className="page active">
      <div className="page-header">
        <h1 className="page-title">User Management</h1>
        <p className="page-subtitle">View and manage registered users.</p>
      </div>

      <div className="result-card" style={{ padding: '0', overflow: 'hidden' }}>
        {loading ? (
          <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
            <div className="auth-spinner" style={{ margin: '0 auto 16px auto', borderTopColor: 'var(--primary)' }}></div>
            Loading users...
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '14px' }}>
              <thead>
                <tr style={{ background: 'var(--bg-main)', borderBottom: '1px solid var(--border)' }}>
                  <th style={{ padding: '16px', fontWeight: '600', color: 'var(--text-secondary)' }}>ID</th>
                  <th style={{ padding: '16px', fontWeight: '600', color: 'var(--text-secondary)' }}>Name</th>
                  <th style={{ padding: '16px', fontWeight: '600', color: 'var(--text-secondary)' }}>Email</th>
                  <th style={{ padding: '16px', fontWeight: '600', color: 'var(--text-secondary)' }}>Role</th>
                  <th style={{ padding: '16px', fontWeight: '600', color: 'var(--text-secondary)' }}>Created</th>
                  <th style={{ padding: '16px', fontWeight: '600', color: 'var(--text-secondary)' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map(u => (
                  <tr key={u.id} style={{ borderBottom: '1px solid var(--border-light)' }}>
                    <td style={{ padding: '16px', color: 'var(--text-muted)' }}>#{u.id}</td>
                    <td style={{ padding: '16px', fontWeight: '500', color: 'var(--text-primary)' }}>{u.first_name} {u.last_name}</td>
                    <td style={{ padding: '16px', color: 'var(--text-secondary)' }}>{u.email}</td>
                    <td style={{ padding: '16px' }}>
                      <span style={{ 
                        padding: '4px 8px', 
                        borderRadius: '12px', 
                        fontSize: '12px', 
                        fontWeight: '600',
                        background: u.role === 'admin' ? 'rgba(239, 68, 68, 0.1)' : 'rgba(13, 148, 136, 0.1)',
                        color: u.role === 'admin' ? 'var(--accent-red)' : 'var(--primary)'
                      }}>
                        {u.role}
                      </span>
                    </td>
                    <td style={{ padding: '16px', color: 'var(--text-muted)' }}>
                      {new Date(u.created_at).toLocaleDateString()}
                    </td>
                    <td style={{ padding: '16px' }}>
                      {u.role !== 'admin' && (
                        <button 
                          onClick={() => setUserToDelete(u)}
                          style={{ 
                            background: 'none', 
                            border: 'none', 
                            color: 'var(--accent-red)', 
                            cursor: 'pointer',
                            fontSize: '14px',
                            fontWeight: '600'
                          }}
                        >
                          Delete
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
                {users.length === 0 && (
                  <tr>
                    <td colSpan="6" style={{ padding: '32px', textAlign: 'center', color: 'var(--text-muted)' }}>
                      No users found.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Delete Confirmation Modal */}
      {userToDelete && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', zIndex: 1000,
          display: 'flex', alignItems: 'center', justifyContent: 'center'
        }}>
          <div style={{
            background: 'var(--bg-card)', padding: '32px', borderRadius: 'var(--radius-lg)',
            width: '100%', maxWidth: '400px', boxShadow: 'var(--shadow-xl)'
          }}>
            <h3 style={{ fontSize: '20px', fontWeight: '700', marginBottom: '16px', color: 'var(--text-primary)' }}>Delete User?</h3>
            <p style={{ fontSize: '15px', color: 'var(--text-secondary)', marginBottom: '24px', lineHeight: '1.5' }}>
              Are you sure you want to permanently delete <strong>{userToDelete.first_name} {userToDelete.last_name}</strong>? 
              This action cannot be undone.
            </p>
            <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
              <button 
                className="btn btn-outline" 
                onClick={() => setUserToDelete(null)}
                disabled={isDeleting}
              >
                Cancel
              </button>
              <button 
                className="btn" 
                onClick={confirmDelete}
                disabled={isDeleting}
                style={{ background: 'var(--accent-red)', color: 'white', border: 'none' }}
              >
                {isDeleting ? 'Deleting...' : 'Delete User'}
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
