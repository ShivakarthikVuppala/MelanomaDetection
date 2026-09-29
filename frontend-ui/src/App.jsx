import { useState, useCallback, useMemo } from 'react';
import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
  Outlet,
  useLocation,
  useNavigate,
} from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import SignOutModal from './components/SignOutModal';
import { ToastProvider } from './components/Toast';
import { AuthProvider, useAuth } from './components/AuthContext';
import { ThemeProvider } from './components/ThemeContext';
import { NotificationProvider } from './components/NotificationContext';
import Home from './pages/Dashboard';
import Upload from './pages/Upload';
import Results from './pages/Results';
import Reports from './pages/Reports';
import Settings from './pages/Settings';
import Help from './pages/Help';
import Login from './pages/Login';
import Signup from './pages/Signup';
import Profile from './pages/Profile';
import AdminApp from './pages/admin/AdminApp';

function getActivePage(pathname) {
  if (pathname.startsWith('/home') || pathname === '/') return 'home';
  if (pathname.startsWith('/upload') || pathname.startsWith('/new-check')) return 'upload';
  if (pathname.startsWith('/results')) return 'results';
  if (pathname.startsWith('/history') || pathname.startsWith('/reports')) return 'history';
  if (pathname.startsWith('/profile')) return 'profile';
  if (pathname.startsWith('/settings')) return 'settings';
  if (pathname.startsWith('/help')) return 'help';
  return 'home';
}

function AuthenticatedLayout() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  const [mobileOpen, setMobileOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(() => {
    return localStorage.getItem('sidebar_collapsed') === 'true';
  });
  const [showSignOutModal, setShowSignOutModal] = useState(false);

  const activePage = useMemo(() => getActivePage(location.pathname), [location.pathname]);

  const toggleDesktopCollapsed = useCallback(() => {
    setCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem('sidebar_collapsed', String(next));
      return next;
    });
  }, []);

  const handleSignOutConfirm = useCallback(() => {
    setShowSignOutModal(false);
    logout();
    navigate('/login', { replace: true });
  }, [logout, navigate]);

  if (user?.role === 'admin') {
    return <AdminApp />;
  }

  return (
    <div className={`app ${collapsed ? 'app-sidebar-collapsed' : ''}`}>
      <Sidebar
        collapsed={collapsed}
        mobileOpen={mobileOpen}
        onCloseMobile={() => setMobileOpen(false)}
        onRequestSignOut={() => setShowSignOutModal(true)}
      />
      <main className={`main-content ${collapsed ? 'main-content-collapsed' : ''}`}>
        <Header
          activePage={activePage}
          onToggleMobileSidebar={() => setMobileOpen((prev) => !prev)}
          onToggleDesktopSidebar={toggleDesktopCollapsed}
          onRequestSignOut={() => setShowSignOutModal(true)}
        />
        <div className="content-inner">
          <Outlet />
        </div>
      </main>

      <SignOutModal
        isOpen={showSignOutModal}
        onClose={() => setShowSignOutModal(false)}
        onConfirm={handleSignOutConfirm}
      />
    </div>
  );
}

function ProtectedRoute() {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="auth-page">
        <div className="card loading-gate-card">
          <div className="loading-gate-icon">
            <i className="fas fa-plus-square"></i>
          </div>
          <h2 className="loading-gate-title">
            Mela<span>Detect</span> AI
          </h2>
          <p className="loading-gate-subtitle">Initializing Workspace...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <AuthenticatedLayout />;
}

function PublicAuthRoute({ children }) {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return null;
  }

  if (isAuthenticated) {
    return <Navigate to="/home" replace />;
  }

  return children;
}

export default function App() {
  return (
    <ToastProvider>
      <ThemeProvider>
        <AuthProvider>
          <NotificationProvider>
            <BrowserRouter>
              <Routes>
                {/* Public Authentication Routes */}
                <Route
                  path="/login"
                  element={
                    <PublicAuthRoute>
                      <Login />
                    </PublicAuthRoute>
                  }
                />
                <Route
                  path="/signup"
                  element={
                    <PublicAuthRoute>
                      <Signup />
                    </PublicAuthRoute>
                  }
                />

                {/* Authenticated Workspace Routes */}
                <Route element={<ProtectedRoute />}>
                  <Route index element={<Navigate to="/home" replace />} />
                  <Route path="/home" element={<Home />} />
                  <Route path="/dashboard" element={<Navigate to="/home" replace />} />
                  <Route path="/upload" element={<Upload />} />
                  <Route path="/new-check" element={<Navigate to="/upload" replace />} />
                  <Route path="/results" element={<Results />} />
                  <Route path="/results/:reportId" element={<Results />} />
                  <Route path="/history" element={<Reports mode="history" />} />
                  <Route path="/reports" element={<Navigate to="/history" replace />} />
                  <Route path="/profile" element={<Profile />} />
                  <Route path="/settings" element={<Settings />} />
                  <Route path="/help" element={<Help />} />
                </Route>

                {/* Catch-all */}
                <Route path="*" element={<Navigate to="/home" replace />} />
              </Routes>
            </BrowserRouter>
          </NotificationProvider>
        </AuthProvider>
      </ThemeProvider>
    </ToastProvider>
  );
}
