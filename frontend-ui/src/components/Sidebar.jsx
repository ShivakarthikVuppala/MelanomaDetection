import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from './AuthContext';

const navSections = [
  {
    title: 'HOME',
    items: [
      { path: '/home', label: 'Home', icon: 'fas fa-home', altPaths: ['/', '/dashboard'] },
    ],
  },
  {
    title: 'SKIN HEALTH',
    items: [
      { path: '/upload', label: 'New Skin Check', icon: 'fas fa-camera', altPaths: ['/new-check'] },
      { path: '/results', label: 'My Results', icon: 'fas fa-clipboard-check', altPaths: [] },
      { path: '/history', label: 'History', icon: 'fas fa-history', altPaths: ['/reports'] },
    ],
  },
  {
    title: 'ACCOUNT',
    items: [
      { path: '/profile', label: 'Profile', icon: 'fas fa-user', altPaths: [] },
      { path: '/settings', label: 'Settings', icon: 'fas fa-cog', altPaths: [] },
      { path: '/help', label: 'Help', icon: 'fas fa-question-circle', altPaths: [] },
    ],
  },
];

export default function Sidebar({
  mobileOpen = false,
  onCloseMobile,
  collapsed = false,
  onRequestSignOut,
}) {
  const { user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const initials =
    ((user?.first_name?.[0] || '') + (user?.last_name?.[0] || '')).toUpperCase() || 'MD';

  const displayName = user ? `${user.first_name} ${user.last_name}` : 'User';

  const handleNavClick = (path) => {
    navigate(path);
    if (onCloseMobile) onCloseMobile();
  };

  const isItemActive = (item) => {
    const current = location.pathname;
    if (current === item.path) return true;
    if (item.path === '/results' && current.startsWith('/results')) return true;
    return item.altPaths && item.altPaths.includes(current);
  };

  return (
    <>
      {mobileOpen && (
        <div
          className="modal-backdrop sidebar-backdrop"
          onClick={onCloseMobile}
          aria-hidden="true"
        />
      )}
      <aside
        className={`sidebar ${mobileOpen ? 'mobile-open' : ''} ${collapsed ? 'sidebar-collapsed' : ''}`}
        id="sidebar"
        aria-label="Application Sidebar"
      >
        <div className="sidebar-brand" onClick={() => handleNavClick('/home')} style={{ cursor: 'pointer' }}>
          <div className="sidebar-brand-icon" aria-hidden="true">
            <i className="fas fa-plus-square"></i>
          </div>
          {!collapsed && (
            <div className="sidebar-brand-text">
              Mela<span>Detect</span> AI
            </div>
          )}
        </div>

        <nav className="sidebar-nav" aria-label="Main Navigation">
          {navSections.map((section) => (
            <div key={section.title} className="nav-section-group">
              {!collapsed && <div className="nav-section-title">{section.title}</div>}
              {section.items.map((item) => {
                const active = isItemActive(item);
                return (
                  <button
                    key={item.path}
                    type="button"
                    className={`nav-item ${active ? 'active' : ''}`}
                    onClick={() => handleNavClick(item.path)}
                    aria-current={active ? 'page' : undefined}
                    title={collapsed ? item.label : undefined}
                  >
                    <span className="nav-icon" aria-hidden="true">
                      <i className={item.icon}></i>
                    </span>
                    {!collapsed && <span className="nav-label">{item.label}</span>}
                  </button>
                );
              })}
            </div>
          ))}
        </nav>

        <div className="sidebar-footer">
          {user && (
            <div
              className="sidebar-user-info"
              onClick={() => handleNavClick('/profile')}
              role="button"
              tabIndex={0}
              title={collapsed ? displayName : undefined}
            >
              <div className="sidebar-user-avatar" aria-hidden="true">
                {initials}
              </div>
              {!collapsed && (
                <div className="sidebar-user-details">
                  <span className="sidebar-user-name">{displayName}</span>
                </div>
              )}
            </div>
          )}
          <button
            type="button"
            className="nav-item sidebar-signout-btn"
            onClick={onRequestSignOut}
            aria-label="Sign out of your account"
            title={collapsed ? 'Sign Out' : undefined}
          >
            <span className="nav-icon" aria-hidden="true">
              <i className="fas fa-sign-out-alt"></i>
            </span>
            {!collapsed && <span className="nav-label">Sign Out</span>}
          </button>
        </div>
      </aside>
    </>
  );
}
