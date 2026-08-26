import { useState, useEffect } from 'react';
import { useToast } from '../components/Toast';

export default function Reports({ onNavigate, onAnalysisComplete }) {
  const [analyses, setAnalyses] = useState([]);
  const [loading, setLoading] = useState(true);
  const showToast = useToast();

  useEffect(() => {
    const fetchAnalyses = async () => {
      try {
        const response = await fetch('/api/analyses');
        if (!response.ok) throw new Error('Failed to fetch history');
        const data = await response.json();
        setAnalyses(data);
    } catch (err) {
      showToast('Could not load analysis history.', 'error');
      console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchAnalyses();
  }, [showToast]);

  const viewAnalysis = async (analysisId) => {
    try {
      const response = await fetch(`/api/analyses/${analysisId}`);
      if (!response.ok) throw new Error('Failed to load analysis');
      const data = await response.json();
      onAnalysisComplete(data);
      showToast('Loaded analysis from history', 'info');
    } catch {
      showToast('Failed to load analysis details', 'error');
    }
  };

  if (loading) {
    return (
      <section className="page active" id="page-reports">
        <div className="empty-state">
          <h2>Loading History...</h2>
        </div>
      </section>
    );
  }

  return (
    <section className="page active" id="page-reports">
      <div className="page-header">
        <h1 className="page-title">Analysis History</h1>
        <p className="page-subtitle">View past melanoma pipeline analyses and download reports.</p>
      </div>

      <div className="report-container">
        {analyses.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon"><i className="fas fa-history"></i></div>
            <h2>No History Found</h2>
            <p>You haven't run any analyses yet.</p>
            <button className="btn btn-primary" onClick={() => onNavigate('upload')}>
              <i className="fas fa-upload"></i> Upload Image
            </button>
          </div>
        ) : (
          <div className="history-table-container" style={{ background: 'var(--surface)', borderRadius: '12px', overflow: 'hidden' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
              <thead style={{ background: 'var(--surface-light)' }}>
                <tr>
                  <th style={{ padding: '16px' }}>Date</th>
                  <th style={{ padding: '16px' }}>Image Name</th>
                  <th style={{ padding: '16px' }}>Prediction</th>
                  <th style={{ padding: '16px' }}>Confidence</th>
                  <th style={{ padding: '16px' }}>Status</th>
                  <th style={{ padding: '16px' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {analyses.map((item) => (
                  <tr key={item.analysis_id} style={{ borderBottom: '1px solid var(--border)' }}>
                    <td style={{ padding: '16px' }}>{new Date(item.timestamp).toLocaleDateString()}</td>
                    <td style={{ padding: '16px' }}>{item.image_name}</td>
                    <td style={{ padding: '16px' }}>
                      <span style={{ 
                        color: item.prediction === 'Melanoma' ? 'var(--danger)' : 'var(--success)',
                        fontWeight: 'bold'
                      }}>
                        {item.prediction}
                      </span>
                    </td>
                    <td style={{ padding: '16px' }}>{item.confidence.toFixed(1)}%</td>
                    <td style={{ padding: '16px' }}>
                      <span className={`badge ${item.status === 'completed' ? 'badge-success' : 'badge-warning'}`} style={{ padding: '4px 8px', borderRadius: '4px', fontSize: '12px', background: 'var(--surface-light)' }}>
                        {item.status}
                      </span>
                    </td>
                    <td style={{ padding: '16px' }}>
                      <button 
                        className="btn btn-sm btn-white"
                        onClick={() => viewAnalysis(item.analysis_id)}
                      >
                         View Results
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  );
}
