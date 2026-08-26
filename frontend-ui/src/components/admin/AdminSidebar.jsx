import { useAuth } from '../AuthContext';

const navItems = [
  { key: 'dashboard', label: 'Dashboard', icon: 'fa-chart-pie' },
  { key: 'users', label: 'Users', icon: 'fa-users' },
  { key: 'settings', label: 'Settings', icon: 'fa-cog' },
];

export default function AdminSidebar({ activePage, onNavigate }) {
  const { user, logout } = useAuth();

  const initials =
    ((user?.first_name?.[0] || '') + (user?.last_name?.[0] || '')).toUpperCase() || 'A';

  return (
    <aside className="sidebar" id="sidebar">
      <div className="sidebar-brand">
        <div className="sidebar-brand-icon">🔬</div>
        <div className="sidebar-brand-text">
          Mela<span>Detect</span> AI <span style={{fontSize: '11px', color: 'var(--accent-red)', marginLeft: '4px', verticalAlign: 'top', textTransform: 'uppercase', fontWeight: 800}}>Admin</span>
        </div>
      </div>

      <nav className="sidebar-nav">
        {navItems.map((item) => (
          <a
            key={item.key}
            className={`nav-item ${activePage === item.key ? 'active' : ''}`}
            onClick={() => onNavigate(item.key)}
          >
            <span className="nav-icon">
              <i className={`fas ${item.icon}`}></i>
            </span>
            <span>{item.label}</span>
          </a>
        ))}
      </nav>

      <div className="sidebar-footer">
        {user && (
          <div className="sidebar-user-info">
            <div className="sidebar-user-avatar" style={{background: 'var(--accent-red)'}}>{initials}</div>
            <div className="sidebar-user-details">
              <span className="sidebar-user-name">{user.first_name} {user.last_name}</span>
              <span className="sidebar-user-email">{user.email}</span>
            </div>
          </div>
        )}
        <a className="nav-item" onClick={() => logout()}>
          <span className="nav-icon">
            <i className="fas fa-sign-out-alt"></i>
          </span>
          <span>Log Out</span>
        </a>
      </div>
    </aside>
  );
}
