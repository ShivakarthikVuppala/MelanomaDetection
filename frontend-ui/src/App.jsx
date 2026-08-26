import { useState, useCallback } from 'react';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import { ToastProvider } from './components/Toast';
import { AuthProvider, useAuth } from './components/AuthContext';
import Dashboard from './pages/Dashboard';
import Upload from './pages/Upload';
import Results from './pages/Results';
import Reports from './pages/Reports';
import Settings from './pages/Settings';
import Help from './pages/Help';
import Login from './pages/Login';
import Signup from './pages/Signup';
import Profile from './pages/Profile';
import AdminApp from './pages/admin/AdminApp';

function AuthenticatedApp() {
  const [activePage, setActivePage] = useState('dashboard');
  const [analysisResult, setAnalysisResult] = useState(null);

  const navigateTo = useCallback((page) => {
    setActivePage(page);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, []);

  const handleAnalysisComplete = useCallback((response) => {
    setAnalysisResult(response);
    setActivePage('results');
  }, []);

  const renderPage = () => {
    switch (activePage) {
      case 'dashboard':
        return <Dashboard onNavigate={navigateTo} />;
      case 'upload':
        return <Upload onAnalysisComplete={handleAnalysisComplete} />;
      case 'results':
        return <Results analysisResult={analysisResult} onNavigate={navigateTo} />;
      case 'reports':
        return <Reports onNavigate={navigateTo} onAnalysisComplete={handleAnalysisComplete} />;
      case 'settings':
        return <Settings />;
      case 'help':
        return <Help />;
      case 'profile':
        return <Profile />;
      default:
        return <Dashboard onNavigate={navigateTo} />;
    }
  };

  return (
    <div className="app">
      <Sidebar activePage={activePage} onNavigate={navigateTo} />
      <main className="main-content">
        <Header activePage={activePage} onNavigate={navigateTo} />
        {renderPage()}
      </main>
    </div>
  );
}

function UnauthenticatedApp() {
  const [page, setPage] = useState('login');

  const navigateTo = useCallback((p) => {
    setPage(p);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, []);

  if (page === 'signup') {
    return <Signup onNavigate={navigateTo} />;
  }
  return <Login onNavigate={navigateTo} />;
}

function AppGate() {
  const { user, isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="auth-loading-screen">
        <div className="auth-loading-content">
          <div className="auth-brand-icon">🔬</div>
          <h1 className="auth-brand-title">
            Mela<span>Detect</span> AI
          </h1>
          <div className="auth-spinner-large"></div>
        </div>
      </div>
    );
  }

  if (isAuthenticated) {
    return user?.role === 'admin' ? <AdminApp /> : <AuthenticatedApp />;
  }

  return <UnauthenticatedApp />;
}

export default function App() {
  return (
    <ToastProvider>
      <AuthProvider>
        <AppGate />
      </AuthProvider>
    </ToastProvider>
  );
}
