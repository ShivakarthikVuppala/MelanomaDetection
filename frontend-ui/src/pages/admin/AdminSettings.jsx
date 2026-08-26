import { useState, useEffect } from 'react';
import { useAuth } from '../../components/AuthContext';
import { useToast } from '../../components/Toast';

export default function AdminSettings() {
  const { token, logout } = useAuth();
  const showToast = useToast();
  
  // Theme state
  const [isDarkMode, setIsDarkMode] = useState(() => {
    const saved = localStorage.getItem('theme');
    if (saved) return saved === 'dark';
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  });

  // Password state
  const [passwordForm, setPasswordForm] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: ''
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [passwordError, setPasswordError] = useState('');

  useEffect(() => {
    if (isDarkMode) {
      document.body.classList.add('dark-theme');
      localStorage.setItem('theme', 'dark');
    } else {
      document.body.classList.remove('dark-theme');
      localStorage.setItem('theme', 'light');
    }
  }, [isDarkMode]);

  const toggleTheme = (theme) => {
    const isDark = theme === 'dark';
    setIsDarkMode(isDark);
    showToast(`Theme changed to ${theme} mode`, 'success');
  };

  const handlePasswordChange = async (e) => {
    e.preventDefault();
    setPasswordError('');

    if (passwordForm.newPassword.length < 6) {
      setPasswordError('New password must be at least 6 characters long.');
      return;
    }
    if (passwordForm.newPassword !== passwordForm.confirmPassword) {
      setPasswordError('New passwords do not match.');
      return;
    }

    setIsSubmitting(true);
    try {
      const res = await fetch('/api/admin/password', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          current_password: passwordForm.currentPassword,
          new_password: passwordForm.newPassword
        })
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Failed to change password.');
      }

      showToast('Password changed successfully. Please log in again.', 'success');
      setPasswordForm({ currentPassword: '', newPassword: '', confirmPassword: '' });
      setTimeout(() => logout(), 1500); // Invalidate session
    } catch (err) {
      setPasswordError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <section className="page active">
      <div className="page-header">
        <h1 className="page-title">Admin Settings</h1>
        <p className="page-subtitle">Manage system appearance and security.</p>
      </div>

      <div className="settings-layout">
        <div className="settings-form" style={{ maxWidth: '600px' }}>
          
          {/* Appearance Section */}
          <div className="result-card" style={{ marginBottom: '24px' }}>
            <h3 style={{ fontSize: '18px', fontWeight: '700', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <i className="fas fa-palette" style={{ color: 'var(--primary)' }}></i> Appearance
            </h3>
            <p style={{ fontSize: '14px', color: 'var(--text-secondary)', marginBottom: '20px' }}>
              Customize the look and feel of the Admin Dashboard.
            </p>
            
            <div className="theme-toggles" style={{ display: 'flex', gap: '16px' }}>
              <button 
                className={`btn ${!isDarkMode ? 'btn-primary' : 'btn-outline'}`}
                onClick={() => toggleTheme('light')}
                style={{ flex: 1, padding: '16px' }}
              >
                <i className="fas fa-sun" style={{ fontSize: '18px' }}></i> Light Mode
              </button>
              
              <button 
                className={`btn ${isDarkMode ? 'btn-primary' : 'btn-outline'}`}
                onClick={() => toggleTheme('dark')}
                style={{ flex: 1, padding: '16px' }}
              >
                <i className="fas fa-moon" style={{ fontSize: '18px' }}></i> Dark Mode
              </button>
            </div>
          </div>

          {/* Security Section */}
          <div className="result-card" style={{ marginBottom: '24px' }}>
            <h3 style={{ fontSize: '18px', fontWeight: '700', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--accent-red)' }}>
              <i className="fas fa-shield-alt"></i> Security
            </h3>
            <p style={{ fontSize: '14px', color: 'var(--text-secondary)', marginBottom: '20px' }}>
              Change your administrative password. You will be logged out after a successful change.
            </p>

            {passwordError && (
              <div className="auth-error-banner" style={{ marginBottom: '16px' }}>
                <i className="fas fa-exclamation-circle"></i>
                <span>{passwordError}</span>
              </div>
            )}

            <form onSubmit={handlePasswordChange} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div className="auth-field">
                <label>Current Password</label>
                <div className="auth-input-wrap">
                  <i className="fas fa-lock auth-input-icon"></i>
                  <input 
                    type="password" 
                    placeholder="Enter current password"
                    value={passwordForm.currentPassword}
                    onChange={e => setPasswordForm(prev => ({ ...prev, currentPassword: e.target.value }))}
                    required
                  />
                </div>
              </div>
              
              <div className="auth-field">
                <label>New Password</label>
                <div className="auth-input-wrap">
                  <i className="fas fa-key auth-input-icon"></i>
                  <input 
                    type="password" 
                    placeholder="Enter new password (min. 6 characters)"
                    value={passwordForm.newPassword}
                    onChange={e => setPasswordForm(prev => ({ ...prev, newPassword: e.target.value }))}
                    required
                  />
                </div>
              </div>

              <div className="auth-field">
                <label>Confirm New Password</label>
                <div className="auth-input-wrap">
                  <i className="fas fa-check-circle auth-input-icon"></i>
                  <input 
                    type="password" 
                    placeholder="Confirm new password"
                    value={passwordForm.confirmPassword}
                    onChange={e => setPasswordForm(prev => ({ ...prev, confirmPassword: e.target.value }))}
                    required
                  />
                </div>
              </div>

              <button 
                type="submit" 
                className="btn" 
                disabled={isSubmitting}
                style={{ 
                  background: 'var(--accent-red)', 
                  color: 'white', 
                  border: 'none', 
                  marginTop: '8px',
                  justifyContent: 'center',
                  padding: '12px'
                }}
              >
                {isSubmitting ? (
                  <div className="auth-spinner" style={{ width: '16px', height: '16px' }}></div>
                ) : (
                  'Change Password'
                )}
              </button>
            </form>
          </div>

        </div>
      </div>
    </section>
  );
}
