import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from './AuthContext';
import { useNotification } from './NotificationContext';

const pageTitles = {
  home: 'Home',
  upload: 'New Skin Check',
  'new-check': 'New Skin Check',
  results: 'My Results',
  history: 'History',
  reports: 'History',
  profile: 'Profile',
  settings: 'Settings',
  help: 'Help',
};

export default function Header({
  activePage = 'home',
  onToggleMobileSidebar,
  onToggleDesktopSidebar,
  onRequestSignOut,
}) {
  const { user } = useAuth();
  const { notification, markAsRead, clearNotification } = useNotification();
  const navigate = useNavigate();

  const [profileDropdownOpen, setProfileDropdownOpen] = useState(false);
  const [notificationDropdownOpen, setNotificationDropdownOpen] = useState(false);

  const profileRef = useRef(null);
  const notifRef = useRef(null);

  const initials =
    ((user?.first_name?.[0] || '') + (user?.last_name?.[0] || '')).toUpperCase() || 'MD';

  const displayName = user ? `${user.first_name} ${user.last_name}` : 'User';

  const currentTitle = pageTitles[activePage] || 'Home';

  // Close dropdowns when clicking outside
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (profileRef.current && !profileRef.current.contains(e.target)) {
        setProfileDropdownOpen(false);
      }
      if (notifRef.current && !notifRef.current.contains(e.target)) {
        setNotificationDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const toggleNotifications = () => {
    setProfileDropdownOpen(false);
    setNotificationDropdownOpen((prev) => {
      if (!prev) {
        markAsRead();
      }
      return !prev;
    });
  };

  const handleViewResults = () => {
    setNotificationDropdownOpen(false);
    if (notification.reportId) {
      navigate(`/results/${notification.reportId}`);
    } else {
      navigate('/results');
    }
  };

  const handleNavClick = (path) => {
    setProfileDropdownOpen(false);
    navigate(path);
  };

  const handleSignOutClick = () => {
    setProfileDropdownOpen(false);
    if (onRequestSignOut) {
      onRequestSignOut();
    }
  };

  const hasUnread = notification.unread || notification.status === 'running';

  return (
    <header className="header">
      <div className="header-left">
        {/* Mobile toggle */}
        <button
          type="button"
          className="header-mobile-toggle"
          onClick={onToggleMobileSidebar}
          aria-label="Toggle mobile navigation menu"
        >
          <i className="fas fa-bars"></i>
        </button>

        {/* Desktop collapse toggle */}
        <button
          type="button"
          className="header-desktop-toggle btn-icon-subtle"
          onClick={onToggleDesktopSidebar}
          aria-label="Toggle sidebar width"
          title="Toggle sidebar"
        >
          <i className="fas fa-bars"></i>
        </button>

        <div className="header-breadcrumb" aria-label="Breadcrumb">
          <span className="breadcrumb-brand">MelaDetect AI</span>
          <i className="fas fa-chevron-right breadcrumb-separator"></i>
          <span className="current">{currentTitle}</span>
        </div>
      </div>

      <div className="header-right">
        {/* Notifications Popover */}
        <div className="header-notif-menu" ref={notifRef} style={{ position: 'relative' }}>
          <button
            type="button"
            className="header-btn"
            title="Notifications"
            aria-label="View notifications"
            aria-expanded={notificationDropdownOpen}
            onClick={toggleNotifications}
          >
            <i className="far fa-bell"></i>
            {hasUnread && <span className="notification-dot"></span>}
          </button>

          {notificationDropdownOpen && (
            <div
              className="notification-dropdown card"
              role="region"
              aria-label="Notifications popover"
              style={{
                position: 'absolute',
                top: 'calc(100% + 8px)',
                right: 0,
                width: '320px',
                borderRadius: '12px',
                border: '1px solid var(--border)',
                backgroundColor: 'var(--surface)',
                boxShadow: 'var(--shadow-lg)',
                zIndex: 200,
                overflow: 'hidden',
                animation: 'dropdownFadeIn 0.15s ease-out',
              }}
            >
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '14px 16px',
                  borderBottom: '1px solid var(--border)',
                  backgroundColor: 'var(--bg-subtle)',
                }}
              >
                <div style={{ fontWeight: 600, fontSize: '14px', color: 'var(--text-primary)' }}>
                  Notifications
                </div>
                {notification.status !== 'none' && (
                  <button
                    type="button"
                    style={{
                      background: 'none',
                      border: 'none',
                      color: 'var(--text-muted)',
                      fontSize: '11.5px',
                      cursor: 'pointer',
                      fontWeight: 500,
                    }}
                    onClick={clearNotification}
                  >
                    Clear
                  </button>
                )}
              </div>

              <div style={{ padding: '16px' }}>
                {notification.status === 'running' && (
                  <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
                    <div
                      style={{
                        width: '34px',
                        height: '34px',
                        borderRadius: '50%',
                        backgroundColor: 'var(--primary-light)',
                        color: 'var(--primary)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        flexShrink: 0,
                        fontSize: '15px',
                      }}
                    >
                      <i className="fas fa-spinner fa-spin"></i>
                    </div>
                    <div style={{ flex: 1 }}>
                      <div
                        style={{
                          fontWeight: 600,
                          fontSize: '13.5px',
                          color: 'var(--text-primary)',
                          marginBottom: '3px',
                        }}
                      >
                        Report Running
                      </div>
                      <p
                        style={{
                          fontSize: '12.5px',
                          color: 'var(--text-secondary)',
                          lineHeight: 1.4,
                          margin: 0,
                        }}
                      >
                        Your analysis report is currently being generated.
                      </p>
                    </div>
                  </div>
                )}

                {notification.status === 'completed' && (
                  <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
                    <div
                      style={{
                        width: '34px',
                        height: '34px',
                        borderRadius: '50%',
                        backgroundColor: 'var(--success-bg)',
                        color: 'var(--success)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        flexShrink: 0,
                        fontSize: '15px',
                      }}
                    >
                      <i className="fas fa-check"></i>
                    </div>
                    <div style={{ flex: 1 }}>
                      <div
                        style={{
                          fontWeight: 600,
                          fontSize: '13.5px',
                          color: 'var(--text-primary)',
                          marginBottom: '3px',
                        }}
                      >
                        Report Generated
                      </div>
                      <p
                        style={{
                          fontSize: '12.5px',
                          color: 'var(--text-secondary)',
                          lineHeight: 1.4,
                          marginBottom: '10px',
                        }}
                      >
                        Your skin analysis report is ready to view.
                      </p>
                      <button
                        type="button"
                        className="btn btn-primary"
                        style={{
                          padding: '6px 14px',
                          fontSize: '12px',
                          height: '30px',
                          borderRadius: '6px',
                        }}
                        onClick={handleViewResults}
                      >
                        View Results
                      </button>
                    </div>
                  </div>
                )}

                {notification.status === 'failed' && (
                  <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
                    <div
                      style={{
                        width: '34px',
                        height: '34px',
                        borderRadius: '50%',
                        backgroundColor: 'var(--danger-bg)',
                        color: 'var(--danger)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        flexShrink: 0,
                        fontSize: '15px',
                      }}
                    >
                      <i className="fas fa-exclamation-triangle"></i>
                    </div>
                    <div style={{ flex: 1 }}>
                      <div
                        style={{
                          fontWeight: 600,
                          fontSize: '13.5px',
                          color: 'var(--text-primary)',
                          marginBottom: '3px',
                        }}
                      >
                        Report Generation Failed
                      </div>
                      <p
                        style={{
                          fontSize: '12.5px',
                          color: 'var(--text-secondary)',
                          lineHeight: 1.4,
                          margin: 0,
                        }}
                      >
                        Something went wrong while generating your report.
                      </p>
                    </div>
                  </div>
                )}

                {notification.status === 'none' && (
                  <div style={{ textAlign: 'center', padding: '12px 0' }}>
                    <div
                      style={{
                        fontSize: '24px',
                        color: 'var(--text-muted)',
                        marginBottom: '8px',
                      }}
                    >
                      <i className="far fa-bell-slash"></i>
                    </div>
                    <div
                      style={{
                        fontWeight: 600,
                        fontSize: '13.5px',
                        color: 'var(--text-primary)',
                        marginBottom: '3px',
                      }}
                    >
                      No New Notifications
                    </div>
                    <p
                      style={{
                        fontSize: '12.5px',
                        color: 'var(--text-secondary)',
                        margin: 0,
                      }}
                    >
                      There are no new notifications.
                    </p>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* User Profile Menu */}
        <div className="header-user-menu" ref={profileRef} style={{ position: 'relative' }}>
          <button
            type="button"
            className="header-user"
            onClick={() => {
              setNotificationDropdownOpen(false);
              setProfileDropdownOpen(!profileDropdownOpen);
            }}
            aria-expanded={profileDropdownOpen}
            aria-haspopup="true"
            aria-label="User account menu"
          >
            <div className="header-avatar">{initials}</div>
            <span className="header-user-name">{displayName}</span>
            <i
              className={`fas fa-chevron-down header-chevron ${profileDropdownOpen ? 'rotated' : ''}`}
            ></i>
          </button>

          {profileDropdownOpen && (
            <div
              className="header-dropdown"
              role="menu"
              style={{
                position: 'absolute',
                top: 'calc(100% + 8px)',
                right: 0,
                borderRadius: '12px',
                border: '1px solid var(--border)',
                backgroundColor: 'var(--surface)',
                boxShadow: 'var(--shadow-lg)',
                zIndex: 200,
                overflow: 'hidden',
                animation: 'dropdownFadeIn 0.15s ease-out',
              }}
            >
              <div className="header-dropdown-user">
                <div className="header-dropdown-avatar">{initials}</div>
                <div className="header-dropdown-info">
                  <div className="header-dropdown-name">{displayName}</div>
                  <div className="header-dropdown-email">
                    {user?.email || 'user@meladetect.ai'}
                  </div>
                </div>
              </div>
              <div className="header-dropdown-divider"></div>
              <button
                type="button"
                className="header-dropdown-item"
                role="menuitem"
                onClick={() => handleNavClick('/profile')}
              >
                <i className="far fa-user-circle"></i>
                <span>Profile</span>
              </button>
              <button
                type="button"
                className="header-dropdown-item"
                role="menuitem"
                onClick={() => handleNavClick('/settings')}
              >
                <i className="fas fa-cog"></i>
                <span>Settings</span>
              </button>
              <button
                type="button"
                className="header-dropdown-item"
                role="menuitem"
                onClick={() => handleNavClick('/help')}
              >
                <i className="far fa-question-circle"></i>
                <span>Help & Guide</span>
              </button>
              <div className="header-dropdown-divider"></div>
              <button
                type="button"
                className="header-dropdown-item header-dropdown-logout"
                role="menuitem"
                onClick={handleSignOutClick}
              >
                <i className="fas fa-sign-out-alt"></i>
                <span>Sign Out</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
