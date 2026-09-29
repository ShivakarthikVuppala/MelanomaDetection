import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../components/AuthContext';
import { useToast } from '../components/Toast';

const abcdeSummary = [
  {
    letter: 'A',
    name: 'Asymmetry',
    summary: 'One half does not match the other in shape or contour.',
    detail: 'Benign moles are usually symmetrical. If you draw a line through the center of an atypical mole, the two halves often do not match in outline or surface texture.',
    clinicalSign: 'Asymmetrical outline, uneven weight distribution',
  },
  {
    letter: 'B',
    name: 'Border',
    summary: 'Edges are irregular, scalloped, notched, or poorly defined.',
    detail: 'A normal mole usually has smooth, even borders. The edges of an early melanoma tend to be uneven, notched, ragged, or blurry.',
    clinicalSign: 'Scalloped contours, blurred or irregular margin',
  },
  {
    letter: 'C',
    name: 'Color',
    summary: 'Shades vary with mixed brown, black, red, or white tones.',
    detail: 'Most benign moles are all one shade of brown. An alert sign is the presence of several different colors or uneven color distribution within the same spot.',
    clinicalSign: 'Multiple chromatic hues, uneven pigment network',
  },
  {
    letter: 'D',
    name: 'Diameter',
    summary: 'Spot is larger than 6 mm across (about pencil eraser size).',
    detail: 'While early melanomas can be smaller, lesions greater than 6 mm in diameter should be assessed, especially when accompanied by other atypical signs.',
    clinicalSign: 'Dimension exceeding 6mm or rapid growth',
  },
  {
    letter: 'E',
    name: 'Evolution',
    summary: 'Mole changes in size, shape, color, or symptoms over time.',
    detail: 'Any change in size, shape, elevation, or new symptoms like itching, crusting, or bleeding is one of the most critical warning signs.',
    clinicalSign: 'Morphological progression, bleeding, or itching',
  },
];

export default function Home({ onNavigate, onViewReport }) {
  const { user, token } = useAuth();
  const navigate = useNavigate();
  const showToast = useToast();
  const [analyses, setAnalyses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedAbcde, setSelectedAbcde] = useState(null);

  const firstName = user?.first_name || 'there';

  const handleNav = (target) => {
    if (onNavigate) {
      onNavigate(target);
    } else {
      const mapping = {
        'new-check': '/upload',
        upload: '/upload',
        results: '/results',
        history: '/history',
        reports: '/history',
      };
      navigate(mapping[target] || target);
    }
  };

  useEffect(() => {
    if (!token) {
      setLoading(false);
      return;
    }
    let isMounted = true;
    const loadAnalyses = async () => {
      try {
        const res = await fetch('/api/analyses', {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const data = await res.json();
          if (isMounted) setAnalyses(Array.isArray(data) ? data : []);
        } else if (res.status === 401) {
          // Token expired — auth context will handle logout
        }
      } catch (e) {
        console.warn('Could not load skin checks:', e);
      } finally {
        if (isMounted) setLoading(false);
      }
    };
    loadAnalyses();
    return () => { isMounted = false; };
  }, [token]);

  const latestAnalysis = analyses.length > 0 ? analyses[0] : null;

  const handleOpenReport = async (analysis) => {
    if (!analysis) return;
    if (onViewReport) {
      onViewReport(analysis);
    } else if (onNavigate) {
      onNavigate('results');
    } else {
      navigate(analysis.analysis_id ? `/results/${analysis.analysis_id}` : '/results');
    }
  };

  // Format date helper
  const formatDate = (isoString) => {
    if (!isoString) return 'Recent';
    try {
      const d = new Date(isoString);
      return d.toLocaleDateString('en-US', {
        month: 'long',
        day: 'numeric',
        year: 'numeric',
      });
    } catch {
      return 'Recent';
    }
  };

  // Determine risk presentation
  const getRiskInfo = (item) => {
    if (!item) return { label: 'Completed', className: 'badge-low', isHigh: false };
    const isMelanoma = item.prediction === 'Melanoma';
    const conf = item.confidence || 0;
    if (isMelanoma) {
      if (conf >= 80) return { label: 'High Risk', className: 'badge-high', isHigh: true };
      return { label: 'Moderate Risk', className: 'badge-moderate', isHigh: false };
    }
    if (conf < 65) return { label: 'Review Suggested', className: 'badge-moderate', isHigh: false };
    return { label: 'Low Risk', className: 'badge-low', isHigh: false };
  };

  const latestRisk = latestAnalysis ? getRiskInfo(latestAnalysis) : null;

  return (
    <div className="page-container" id="page-home">
      {/* Compact & Elegant Hero Section */}
      <section className="home-hero-card" aria-label="Welcome and quick actions">
        <div className="home-hero-content">
          <h1 className="home-hero-title">Hello, {firstName}</h1>
          <p className="home-hero-subtitle">
            Understand your skin health with AI-assisted lesion analysis.
          </p>
          <div className="home-hero-actions">
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => handleNav('new-check')}
            >
              <i className="fas fa-camera" aria-hidden="true"></i>
              <span>Start a Skin Check</span>
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => handleNav(latestAnalysis ? 'results' : 'history')}
            >
              <i className="fas fa-clipboard-list" aria-hidden="true"></i>
              <span>View Previous Results</span>
            </button>
          </div>
        </div>
      </section>

      {/* Your Latest Check Section */}
      <section className="home-section" aria-labelledby="latest-check-heading">
        <div className="section-header-compact">
          <h2 id="latest-check-heading" className="section-title">Your Latest Check</h2>
        </div>

        {loading ? (
          <div className="card latest-check-skeleton">
            <div className="skeleton-line" style={{ width: '40%', height: '18px' }}></div>
            <div className="skeleton-line" style={{ width: '25%', height: '14px', marginTop: '10px' }}></div>
          </div>
        ) : latestAnalysis ? (
          <div className="card latest-check-card">
            <div className="latest-check-left">
              <div className="latest-check-status-badge">
                <i className="fas fa-check-circle" aria-hidden="true"></i>
                <span>Completed</span>
              </div>
              <div className="latest-check-date">
                {formatDate(latestAnalysis.timestamp)}
              </div>
              <div className="latest-check-assessment">
                <span className={`risk-badge ${latestRisk?.className}`}>
                  {latestRisk?.label}
                </span>
                {latestAnalysis.confidence !== undefined && (
                  <span className="latest-check-confidence">
                    {Math.round(latestAnalysis.confidence)}% confidence
                  </span>
                )}
                <span className="latest-check-ref">
                  Assessment available
                </span>
              </div>
            </div>

            <div className="latest-check-right">
              <button
                type="button"
                className="btn btn-outline latest-check-btn"
                onClick={() => handleOpenReport(latestAnalysis)}
              >
                <span>View Report</span>
                <i className="fas fa-arrow-right" aria-hidden="true"></i>
              </button>
            </div>
          </div>
        ) : (
          <div className="card latest-check-empty">
            <div className="latest-check-empty-icon" aria-hidden="true">
              <i className="fas fa-notes-medical"></i>
            </div>
            <div className="latest-check-empty-text">
              <h3 className="empty-title">No skin checks yet</h3>
              <p className="empty-subtitle">
                Start your first skin check to see your results here.
              </p>
            </div>
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => onNavigate('new-check')}
            >
              <i className="fas fa-camera" aria-hidden="true"></i>
              <span>Start Skin Check</span>
            </button>
          </div>
        )}
      </section>

      {/* Understanding Skin Changes: Compact ABCDE Section */}
      <section className="home-section" aria-labelledby="abcde-section-heading">
        <div className="section-header-compact">
          <div>
            <h2 id="abcde-section-heading" className="section-title">
              Understanding Skin Changes
            </h2>
            <p className="section-subtitle">
              Learn about the ABCDE signs commonly used when observing skin lesions.
            </p>
          </div>
          <button
            type="button"
            className="text-link-btn"
            onClick={() => onNavigate('help')}
          >
            <span>Learn about ABCDE</span>
            <i className="fas fa-arrow-right" aria-hidden="true"></i>
          </button>
        </div>

        <div className="abcde-compact-grid">
          {abcdeSummary.map((item) => (
            <div
              key={item.letter}
              className="abcde-compact-card"
              onClick={() => setSelectedAbcde(item)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  setSelectedAbcde(item);
                }
              }}
              aria-label={`Learn about ${item.name}`}
            >
              <div className="abcde-badge-pill" aria-hidden="true">{item.letter}</div>
              <h3 className="abcde-card-title">{item.name}</h3>
              <p className="abcde-card-desc">{item.summary}</p>
              <span className="abcde-card-action">Learn more →</span>
            </div>
          ))}
        </div>
      </section>

      {/* Subtle Medical Disclaimer */}
      <footer className="medical-disclaimer-box" role="note">
        <p>
          MelaDetect AI provides AI-assisted information and is not a medical diagnosis. If you notice concerning or changing skin lesions, consider consulting a qualified healthcare professional.
        </p>
      </footer>

      {/* Educational ABCDE Detail Modal */}
      {selectedAbcde && (
        <div
          className="modal-backdrop"
          onClick={() => setSelectedAbcde(null)}
          role="dialog"
          aria-modal="true"
          aria-labelledby="abcde-modal-title"
        >
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <button
              type="button"
              className="modal-close-btn"
              onClick={() => setSelectedAbcde(null)}
              aria-label="Close dialog"
            >
              <i className="fas fa-times"></i>
            </button>

            <div className="modal-header-row">
              <div className="modal-letter-badge" aria-hidden="true">
                {selectedAbcde.letter}
              </div>
              <div>
                <h3 id="abcde-modal-title" className="modal-title">
                  {selectedAbcde.letter} — {selectedAbcde.name}
                </h3>
                <span className="modal-subtitle">{selectedAbcde.clinicalSign}</span>
              </div>
            </div>

            <div className="modal-body-content">
              <p className="modal-text">{selectedAbcde.detail}</p>
              <div className="modal-tip-box">
                <i className="fas fa-info-circle text-teal" aria-hidden="true"></i>
                <span>
                  Regular monthly self-examinations help spot subtle morphological changes early.
                </span>
              </div>
            </div>

            <div className="modal-actions-row">
              <button
                type="button"
                className="btn btn-outline"
                onClick={() => setSelectedAbcde(null)}
              >
                Close
              </button>
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => {
                  setSelectedAbcde(null);
                  onNavigate('new-check');
                }}
              >
                Start a Skin Check
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
