import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useToast } from '../components/Toast';
import { useAuth } from '../components/AuthContext';

export default function Reports({ onNavigate, onAnalysisComplete, mode = 'history' }) {
  const navigate = useNavigate();
  const [analyses, setAnalyses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [riskFilter, setRiskFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [downloadingId, setDownloadingId] = useState(null);
  const showToast = useToast();
  const { token } = useAuth();

  const isMyResults = mode === 'results';
  const pageTitle = isMyResults ? 'My Results' : 'History';
  const pageSubtitle = isMyResults
    ? 'Overview of your skin checks and lesion assessments.'
    : 'Complete record of all your previous skin lesion checks and reports.';

  useEffect(() => {
    let isMounted = true;
    const fetchAnalyses = async () => {
      try {
        const response = await fetch('/api/analyses', {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        });
        if (!response.ok) throw new Error('Failed to load check history');
        const data = await response.json();
        if (isMounted) setAnalyses(Array.isArray(data) ? data : []);
      } catch (err) {
        showToast('Could not load skin check records.', 'error');
        console.warn(err);
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    fetchAnalyses();
    return () => { isMounted = false; };
  }, [showToast]);

  const isFailedAnalysis = (item) => {
    return item.status === 'failed' || item.status === 'error' || item.status === 'image_quality_insufficient' ||
      (!item.status && !item.prediction) ||
      (item.confidence === 0 && !item.prediction);
  };

  const viewAnalysis = async (analysisId, item) => {
    // Guard: if the list-level item already looks failed, skip the fetch
    if (item && isFailedAnalysis(item)) {
      showToast(
        'This analysis could not be completed. Please upload a valid dermoscopic skin image and try again.',
        'warning'
      );
      return;
    }
    try {
      showToast('Loading skin check report...', 'info');
      const response = await fetch(`/api/analyses/${analysisId}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!response.ok) throw new Error('Failed to load analysis');
      const data = await response.json();
      // Guard: full record confirms failure
      if (
        data.status === 'failed' || data.status === 'error' ||
        data.status === 'image_quality_insufficient' ||
        (!data.diagnosis && data.status !== 'completed')
      ) {
        showToast(
          'This analysis could not be completed. Please upload a valid dermoscopic skin image and try again.',
          'warning'
        );
        return;
      }
      if (onAnalysisComplete) {
        onAnalysisComplete(data);
      }
      navigate(`/results/${analysisId}`);
    } catch {
      showToast('Failed to open report. Please try again.', 'error');
    }
  };

  const handleDownload = async (item) => {
    if (downloadingId) return;
    setDownloadingId(item.analysis_id);
    showToast('Preparing your report...', 'info');

    try {
      const response = await fetch(`/api/analyses/${item.analysis_id}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (response.ok) {
        const fullData = await response.json();
        const pdfUrl = fullData?.report?.pdf_url;
        if (pdfUrl) {
          const link = document.createElement('a');
          link.href = pdfUrl;
          link.download = `MelaDetect_Report_${item.analysis_id.substring(0, 8)}.pdf`;
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
          showToast('Report downloaded successfully.', 'success');
        } else {
          showToast("We couldn't generate the report right now. Please try again.", 'warning');
        }
      } else {
        showToast("We couldn't generate the report right now. Please try again.", 'warning');
      }
    } catch {
      showToast("We couldn't generate the report right now. Please try again.", 'error');
    } finally {
      setDownloadingId(null);
    }
  };

  // Determine risk details
  const getRiskInfo = (item) => {
    if (isFailedAnalysis(item)) return { label: 'Analysis Failed', class: 'badge-failed' };
    const isMelanoma = item.prediction === 'Melanoma';
    const conf = item.confidence || 0;
    if (isMelanoma) {
      if (conf >= 80) return { label: 'High Risk', class: 'badge-high' };
      return { label: 'Moderate Risk', class: 'badge-moderate' };
    }
    if (conf < 65) return { label: 'Moderate Risk', class: 'badge-moderate' };
    return { label: 'Low Risk', class: 'badge-low' };
  };

  // Filter analyses
  const filteredAnalyses = analyses.filter((item) => {
    const isMelanoma = item.prediction === 'Melanoma';
    const conf = item.confidence || 0;
    const isHigh = isMelanoma && conf >= 80;
    const isModerate = (isMelanoma && conf < 80) || (!isMelanoma && conf < 65);
    const isLow = !isMelanoma && conf >= 65;

    if (riskFilter === 'high' && !isHigh) return false;
    if (riskFilter === 'moderate' && !isModerate) return false;
    if (riskFilter === 'low' && !isLow) return false;

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchId = item.analysis_id?.toLowerCase().includes(q);
      const matchName = item.image_name?.toLowerCase().includes(q);
      const matchDate = new Date(item.timestamp).toLocaleDateString().toLowerCase().includes(q);
      return matchId || matchName || matchDate;
    }
    return true;
  });

  return (
    <div className="page-container" id="page-history">
      {/* Page Header */}
      <div className="page-header-clean page-header-split">
        <div>
          <h1 className="page-title-clean">{pageTitle}</h1>
          <p className="page-subtitle-clean">{pageSubtitle}</p>
        </div>
        <button
          type="button"
          className="btn btn-primary"
          onClick={() => onNavigate('new-check')}
        >
          <i className="fas fa-camera" aria-hidden="true"></i>
          <span>Start a Skin Check</span>
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="card filters-card">
        <div className="filter-pills-row" role="group" aria-label="Filter skin checks by risk">
          <span className="filter-label">Filter:</span>
          <button
            type="button"
            className={`filter-btn ${riskFilter === 'all' ? 'active' : ''}`}
            onClick={() => setRiskFilter('all')}
          >
            All ({analyses.length})
          </button>
          <button
            type="button"
            className={`filter-btn ${riskFilter === 'low' ? 'active' : ''}`}
            onClick={() => setRiskFilter('low')}
          >
            Low Risk
          </button>
          <button
            type="button"
            className={`filter-btn ${riskFilter === 'moderate' ? 'active' : ''}`}
            onClick={() => setRiskFilter('moderate')}
          >
            Moderate Risk
          </button>
          <button
            type="button"
            className={`filter-btn ${riskFilter === 'high' ? 'active' : ''}`}
            onClick={() => setRiskFilter('high')}
          >
            High Risk
          </button>
        </div>

        <div className="filter-search-box">
          <i className="fas fa-search filter-search-icon" aria-hidden="true"></i>
          <input
            type="text"
            className="filter-search-input"
            placeholder="Search by date or image name..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            aria-label="Search previous skin checks"
          />
        </div>
      </div>

      {/* Content Area */}
      {loading ? (
        <div className="card loading-state-card">
          <i className="fas fa-spinner fa-spin text-teal loading-spinner-icon" aria-hidden="true"></i>
          <p className="loading-state-text">Loading previous skin checks...</p>
        </div>
      ) : filteredAnalyses.length === 0 ? (
        <div className="card empty-records-card">
          <div className="empty-records-icon" aria-hidden="true">
            <i className="fas fa-notes-medical"></i>
          </div>
          <h2 className="empty-records-title">
            {analyses.length === 0 ? 'No skin checks yet' : 'No matching results'}
          </h2>
          <p className="empty-records-desc">
            {analyses.length === 0
              ? 'Start your first skin check to see your results here.'
              : 'Try changing your search term or risk filter.'}
          </p>
          {analyses.length === 0 && (
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => onNavigate('new-check')}
            >
              <i className="fas fa-camera" aria-hidden="true"></i>
              <span>Start Skin Check</span>
            </button>
          )}
        </div>
      ) : (
        <>
          {/* Desktop Table View */}
          <div className="card table-card-wrapper desktop-only-view">
            <table className="clean-data-table" aria-label="Previous skin check results">
              <thead>
                <tr>
                  <th scope="col" style={{ width: '80px' }}>Image</th>
                  <th scope="col">Date</th>
                  <th scope="col">Assessment</th>
                  <th scope="col">Confidence</th>
                  <th scope="col" style={{ textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredAnalyses.map((item) => {
                  const risk = getRiskInfo(item);
                  const dateStr = new Date(item.timestamp).toLocaleDateString('en-US', {
                    month: 'short',
                    day: 'numeric',
                    year: 'numeric',
                  });

                  return (
                    <tr key={item.analysis_id}>
                      {/* Thumbnail */}
                      <td>
                        <div className="table-thumbnail-box">
                          {item.image_url ? (
                            <img src={item.image_url} alt="Skin check thumbnail" />
                          ) : (
                            <div className="thumbnail-fallback">
                              <i className="far fa-image"></i>
                            </div>
                          )}
                        </div>
                      </td>

                      {/* Date */}
                      <td>
                        <strong className="table-date-text">{dateStr}</strong>
                        <div className="table-sub-text">
                          {item.image_name || 'Lesion Image'}
                        </div>
                      </td>

                      {/* Risk Assessment */}
                      <td>
                        <span className={`risk-badge ${risk.class}`}>
                          {risk.label}
                        </span>
                      </td>

                      {/* Confidence */}
                      <td>
                        <strong className="table-confidence-text">
                          {Math.round(item.confidence || 0)}%
                        </strong>
                      </td>

                      {/* Actions */}
                      <td style={{ textAlign: 'right' }}>
                        <div className="table-actions-group">
                          {isFailedAnalysis(item) ? (
                            <button
                              type="button"
                              className="btn btn-sm btn-outline btn-failed-report"
                              onClick={() => showToast('This analysis could not be completed. Please upload a valid dermoscopic skin image and try again.', 'warning')}
                              title="Analysis failed — upload a valid image to retry"
                            >
                              <i className="fas fa-triangle-exclamation" aria-hidden="true"></i>
                              <span>Invalid Image</span>
                            </button>
                          ) : (
                            <>
                              <button
                                type="button"
                                className="btn btn-sm btn-outline"
                                onClick={() => viewAnalysis(item.analysis_id, item)}
                              >
                                <span>View Report</span>
                                <i className="fas fa-arrow-right" aria-hidden="true"></i>
                              </button>
                              <button
                                type="button"
                                className="btn btn-sm btn-ghost"
                                onClick={() => handleDownload(item)}
                                title="Download PDF"
                                aria-label={`Download report for check on ${dateStr}`}
                                disabled={downloadingId === item.analysis_id}
                              >
                                <i className="fas fa-download"></i>
                              </button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Mobile Card Grid View */}
          <div className="mobile-cards-grid mobile-only-view">
            {filteredAnalyses.map((item) => {
              const risk = getRiskInfo(item);
              const dateStr = new Date(item.timestamp).toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric',
                year: 'numeric',
              });

              return (
                <div key={item.analysis_id} className="card result-card-mobile">
                  <div className="mobile-card-top">
                    <div className="mobile-card-thumb">
                      {item.image_url ? (
                        <img src={item.image_url} alt="Skin check thumbnail" />
                      ) : (
                        <div className="thumbnail-fallback">
                          <i className="far fa-image"></i>
                        </div>
                      )}
                    </div>
                    <div className="mobile-card-meta">
                      <span className="mobile-card-date">{dateStr}</span>
                      <span className={`risk-badge ${risk.class}`}>
                        {risk.label}
                      </span>
                      <span className="mobile-card-conf">
                        {Math.round(item.confidence || 0)}% confidence
                      </span>
                    </div>
                  </div>

                  <div className="mobile-card-actions">
                    {isFailedAnalysis(item) ? (
                      <button
                        type="button"
                        className="btn btn-sm btn-outline btn-failed-report mobile-btn-flex"
                        onClick={() => showToast('This analysis could not be completed. Please upload a valid dermoscopic skin image and try again.', 'warning')}
                      >
                        <i className="fas fa-triangle-exclamation" aria-hidden="true"></i>
                        <span>Invalid Image</span>
                      </button>
                    ) : (
                      <>
                        <button
                          type="button"
                          className="btn btn-sm btn-primary mobile-btn-flex"
                          onClick={() => viewAnalysis(item.analysis_id, item)}
                        >
                          <i className="fas fa-file-waveform" aria-hidden="true"></i>
                          <span>View Report</span>
                        </button>
                        <button
                          type="button"
                          className="btn btn-sm btn-outline"
                          onClick={() => handleDownload(item)}
                          aria-label="Download PDF"
                          disabled={downloadingId === item.analysis_id}
                        >
                          <i className="fas fa-download" aria-hidden="true"></i>
                        </button>
                      </>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}

      {/* Subtle Medical Disclaimer */}
      <footer className="medical-disclaimer-box" role="note">
        <p>
          MelaDetect AI provides AI-assisted information and is not a medical diagnosis. If you notice concerning or changing skin lesions, consider consulting a qualified healthcare professional.
        </p>
      </footer>
    </div>
  );
}
