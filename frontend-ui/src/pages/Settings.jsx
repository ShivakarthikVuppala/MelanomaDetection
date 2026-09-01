import { useState, useEffect } from 'react';
import { useToast } from '../components/Toast';
import { useAuth } from '../components/AuthContext';

export default function Settings({ onNavigate }) {
  const showToast = useToast();
  const { user } = useAuth();
  
  // Initialize theme from localStorage or system preference
  const [isDarkMode, setIsDarkMode] = useState(() => {
    const saved = localStorage.getItem('theme');
    if (saved) return saved === 'dark';
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  });

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

  return (
    <section className="page active" id="page-settings">
      <div className="page-header">
        <h1 className="page-title">Settings</h1>
        <p className="page-subtitle">Manage your application preferences.</p>
      </div>

      <div className="settings-layout">
        <div className="settings-form" style={{ maxWidth: '600px' }}>
          {/* Account Section */}
          <div className="result-card" style={{ marginBottom: '24px' }}>
            <h3 style={{ fontSize: '18px', fontWeight: '700', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <i className="fas fa-user-circle" style={{ color: 'var(--primary)' }}></i> Account
            </h3>
            {user && (
              <div className="settings-account-info">
                <div className="settings-account-row">
                  <span className="settings-account-label">Name</span>
                  <span className="settings-account-value">{user.first_name} {user.last_name}</span>
                </div>
                <div className="settings-account-row">
                  <span className="settings-account-label">Email</span>
                  <span className="settings-account-value">{user.email}</span>
                </div>
                <div className="settings-account-row">
                  <span className="settings-account-label">Phone</span>
                  <span className="settings-account-value">{user.phone}</span>
                </div>
              </div>
            )}
            <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '16px' }}>
              To edit your profile information, visit the <strong>Profile</strong> page.
            </p>
          </div>

          {/* Appearance Section */}
          <div className="result-card" style={{ marginBottom: '24px' }}>
            <h3 style={{ fontSize: '18px', fontWeight: '700', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <i className="fas fa-palette" style={{ color: 'var(--primary)' }}></i> Appearance
            </h3>
            <p style={{ fontSize: '14px', color: 'var(--text-secondary)', marginBottom: '20px' }}>
              Customize the look and feel of MelaDetect AI by switching between Light and Dark mode.
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
        </div>
      </div>
    </section>
  );
}
