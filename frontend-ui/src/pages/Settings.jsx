import { useState, useEffect } from 'react';
import { useToast } from '../components/Toast';

export default function Settings() {
  const showToast = useToast();
  
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
