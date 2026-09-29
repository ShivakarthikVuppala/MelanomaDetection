import { useState, useCallback } from 'react';
import AdminSidebar from '../../components/admin/AdminSidebar';
import AdminHeader  from '../../components/admin/AdminHeader';
import AdminDashboard from './AdminDashboard';
import AdminUsers    from './AdminUsers';
import AdminSettings from './AdminSettings';

export default function AdminApp() {
  const [activePage, setActivePage] = useState('dashboard');

  const navigateTo = useCallback((page) => {
    setActivePage(page);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, []);

  const renderPage = () => {
    switch (activePage) {
      case 'dashboard': return <AdminDashboard onNavigate={navigateTo} />;
      case 'users':     return <AdminUsers />;
      case 'settings':  return <AdminSettings />;
      default:          return <AdminDashboard onNavigate={navigateTo} />;
    }
  };

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: 'var(--adm-bg)' }}>
      <AdminSidebar activePage={activePage} onNavigate={navigateTo} />
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        <AdminHeader activePage={activePage} onNavigate={navigateTo} />
        <main style={{ flex: 1, overflowY: 'auto' }}>
          {renderPage()}
        </main>
      </div>
    </div>
  );
}
