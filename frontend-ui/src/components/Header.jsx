const pageNames = {
  dashboard: 'Dashboard',
  upload: 'Upload & Analyze',
  analysis: 'Analysis',
  results: 'Results',
  reports: 'Reports',
  settings: 'Settings',
  help: 'Help',
};

export default function Header({ activePage }) {
  return (
    <header className="header">
      <div className="header-left">
        <div className="header-breadcrumb">
          <span>MelaDetect AI</span>
          <i className="fas fa-chevron-right" style={{ fontSize: '10px' }}></i>
          <span className="current">{pageNames[activePage] || activePage}</span>
        </div>
      </div>
      <div className="header-right">
        <button className="header-btn" title="Notifications">
          <i className="fas fa-bell"></i>
        </button>
        <div className="header-user">
          <div className="header-avatar">DA</div>
          <span className="header-user-name">Dr. Admin</span>
        </div>
      </div>
    </header>
  );
}
