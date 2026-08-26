const navItems = [
  { key: 'dashboard', label: 'Dashboard', icon: 'fa-th-large' },
  { key: 'upload', label: 'Upload & Analyze', icon: 'fa-cloud-upload-alt' },
  { key: 'results', label: 'Results', icon: 'fa-chart-bar' },
  { key: 'reports', label: 'History', icon: 'fa-history' },
  { key: 'settings', label: 'Settings', icon: 'fa-cog' },
  { key: 'help', label: 'Help', icon: 'fa-question-circle' },
];

export default function Sidebar({ activePage, onNavigate }) {
  return (
    <aside className="sidebar" id="sidebar">
      <div className="sidebar-brand">
        <div className="sidebar-brand-icon">🔬</div>
        <div className="sidebar-brand-text">
          Mela<span>Detect</span> AI
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
        <a className="nav-item" onClick={() => {}}>
          <span className="nav-icon">
            <i className="fas fa-sign-out-alt"></i>
          </span>
          <span>Log Out</span>
        </a>
      </div>
    </aside>
  );
}
