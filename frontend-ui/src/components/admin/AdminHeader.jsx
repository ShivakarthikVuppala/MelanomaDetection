import { useState, useEffect, useRef } from 'react';
import { useAuth } from '../AuthContext';

const pageNames = {
  dashboard: 'Admin Dashboard',
  users: 'User Management',
  settings: 'Admin Settings',
};

export default function AdminHeader({ activePage, onNavigate }) {
  const { user, logout } = useAuth();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef(null);

  const initials =
    ((user?.first_name?.[0] || '') + (user?.last_name?.[0] || '')).toUpperCase() || 'A';
  const displayName = user ? `${user.first_name} ${user.last_name}` : 'Admin';

  // Close dropdown on outside click
  useEffect(() => {
    if (!dropdownOpen) return;
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [dropdownOpen]);

  const handleDropdownAction = (action) => {
    setDropdownOpen(false);
    if (action === 'logout') {
      logout();
    } else if (onNavigate) {
      onNavigate(action);
    }
  };

  return (
    <header className="header" style={{ borderBottomColor: 'var(--accent-red-bg)' }}>
      <div className="header-left">
        <div className="header-breadcrumb">
          <span>MelaDetect AI Admin</span>
          <i className="fas fa-chevron-right" style={{ fontSize: '10px' }}></i>
          <span className="current">{pageNames[activePage] || activePage}</span>
        </div>
      </div>
      <div className="header-right">
        <div className="header-user-menu" ref={dropdownRef}>
          <button
            className="header-user"
            onClick={() => setDropdownOpen(!dropdownOpen)}
            aria-expanded={dropdownOpen}
            aria-haspopup="true"
          >
            <div className="header-avatar" style={{background: 'var(--accent-red)'}}>{initials}</div>
            <span className="header-user-name">{displayName}</span>
            <i className={`fas fa-chevron-down header-chevron ${dropdownOpen ? 'rotated' : ''}`}></i>
          </button>

          {dropdownOpen && (
            <div className="header-dropdown">
              <div className="header-dropdown-user">
                <div className="header-dropdown-avatar" style={{background: 'var(--accent-red)'}}>{initials}</div>
                <div>
                  <div className="header-dropdown-name">{displayName}</div>
                  <div className="header-dropdown-email">{user?.email}</div>
                </div>
              </div>
              <div className="header-dropdown-divider"></div>
              <button className="header-dropdown-item" onClick={() => handleDropdownAction('settings')}>
                <i className="fas fa-cog"></i>
                <span>Settings</span>
              </button>
              <div className="header-dropdown-divider"></div>
              <button className="header-dropdown-item header-dropdown-logout" onClick={() => handleDropdownAction('logout')}>
                <i className="fas fa-sign-out-alt"></i>
                <span>Log Out</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
