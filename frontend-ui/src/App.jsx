import { useState, useCallback } from 'react';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import { ToastProvider } from './components/Toast';
import Dashboard from './pages/Dashboard';
import Upload from './pages/Upload';
import Results from './pages/Results';
import Reports from './pages/Reports';
import Settings from './pages/Settings';
import Help from './pages/Help';

function AppContent() {
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
      default:
        return <Dashboard onNavigate={navigateTo} />;
    }
  };

  return (
    <div className="app">
      <Sidebar activePage={activePage} onNavigate={navigateTo} />
      <main className="main-content">
        <Header activePage={activePage} />
        {renderPage()}
      </main>
    </div>
  );
}

export default function App() {
  return (
    <ToastProvider>
      <AppContent />
    </ToastProvider>
  );
}
