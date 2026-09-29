import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useToast } from '../components/Toast';
import { useAuth } from '../components/AuthContext';

export default function Results({ analysisResult, onNavigate }) {
  const { reportId } = useParams();
  const { token } = useAuth();
  const navigate = useNavigate();
  const showToast = useToast();

  const [currentResult, setCurrentResult] = useState(analysisResult || null);
  const [loading, setLoading] = useState(!analysisResult);
  const [activeImageTab, setActiveImageTab] = useState('original');
  const [zoomModal, setZoomModal] = useState(false);
  const [downloading, setDownloading] = useState(false);

  const handleNav = (target) => {
    if (onNavigate) {
      onNavigate(target);
    } else {
      const mapping = {
        'new-check': '/upload',
        upload: '/upload',
        history: '/history',
        reports: '/history',
      };
      navigate(mapping[target] || target);
    }
  };

  useEffect(() => {
    if (analysisResult) {
      setCurrentResult(analysisResult);
      setLoading(false);
      return;
    }

    if (!token) {
      setLoading(false);
      return;
    }

    let isMounted = true;
    setLoading(true);

    const targetUrl = reportId ? `/api/analyses/${reportId}` : '/api/analyses';

    fetch(targetUrl, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (!isMounted) return;
        if (Array.isArray(data)) {
          if (data.length > 0) {
            return fetch(`/api/analyses/${data[0].analysis_id}`, {
              headers: { Authorization: `Bearer ${token}` },
            })
              .then((r) => (r.ok ? r.json() : data[0]))
              .then((full) => {
                if (isMounted) setCurrentResult(full);
              });
          } else {
            setCurrentResult(null);
          }
        } else {
          setCurrentResult(data);
        }
      })
      .catch((e) => {
        console.warn('Failed to fetch analysis:', e);
      })
      .finally(() => {
        if (isMounted) setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [analysisResult, reportId, token]);

  if (loading) {
    return (
      <div className="page-container" id="page-report-loading">
        <div className="card report-empty-card" style={{ padding: '60px 24px', textAlign: 'center' }}>
          <div className="loading-spinner" style={{ margin: '0 auto 16px', fontSize: '28px', color: 'var(--primary)' }}>
            <i className="fas fa-spinner fa-spin"></i>
          </div>
          <h2 style={{ fontSize: '18px', fontWeight: 600, color: 'var(--text-primary)' }}>Loading Skin Check Report...</h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '14px', marginTop: '6px' }}>Fetching analysis metrics and dermatological assessment.</p>
        </div>
      </div>
    );
  }

  if (!currentResult) {
    return (
      <div className="page-container" id="page-report-empty">
        <div className="card report-empty-card">
          <div className="report-empty-icon" aria-hidden="true">
            <i className="fas fa-file-waveform"></i>
          </div>
          <h2 className="report-empty-title">No Skin Check Selected</h2>
          <p className="report-empty-subtitle">
            Start a new skin check or select a past assessment from your history to view its report.
          </p>
          <div className="report-empty-actions">
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
              className="btn btn-outline"
              onClick={() => handleNav('history')}
            >
              <i className="fas fa-history" aria-hidden="true"></i>
              <span>View History</span>
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Handle insufficient quality or incomplete result
  if (currentResult.status !== 'completed' || !currentResult.diagnosis) {
    return (
      <div className="page-container" id="page-report-error">
        <div className="card report-error-card">
          <div className="report-error-icon" aria-hidden="true">
            <i className="fas fa-triangle-exclamation"></i>
          </div>
          <h2 className="report-error-title">
            {currentResult.status === 'image_quality_insufficient'
              ? 'Image Quality Needs Adjustment'
              : 'Analysis Could Not Be Completed'}
          </h2>
          <p className="report-error-subtitle">
            {currentResult.message ||
              'The uploaded photo could not be clearly analyzed. For best results, use good natural lighting and make sure the lesion is sharp and centered.'}
          </p>
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => handleNav('new-check')}
          >
            <i className="fas fa-redo" aria-hidden="true"></i>
            <span>Try With Another Photo</span>
          </button>
        </div>
      </div>
    );
  }

  const {
    diagnosis,
    explanation,
    report,
    original_image_url,
    analysis_id,
    timestamp,
    _customContext,
  } = currentResult;

  const pred = diagnosis?.diagnosis?.prediction || 'Benign';
  const isMelanoma = pred === 'Melanoma';
  const confidence = Math.round(diagnosis?.diagnosis?.confidence || 0);
  const melanomaProb = Number(
    diagnosis?.melanoma_probability ?? diagnosis?.probabilities?.melanoma ?? 0
  );

  // Semantic Risk Assessment Tiering
  let riskAssessment = 'Low Risk';
  let riskBadgeClass = 'badge-low';
  let riskSummaryText =
    'The features analyzed align with typical benign dermatological characteristics. Continue normal routine self-checks.';

  if (isMelanoma) {
    if (confidence >= 80 || melanomaProb >= 0.7) {
      riskAssessment = 'High Risk';
      riskBadgeClass = 'badge-high';
      riskSummaryText =
        'The model observed notable structural asymmetry, irregular borders, or pigment heterogeneity. We strongly recommend having this spot examined in person by a qualified dermatologist.';
    } else {
      riskAssessment = 'Moderate Risk';
      riskBadgeClass = 'badge-moderate';
      riskSummaryText =
        'Some atypical characteristics were identified that warrant professional observation. Consider consulting a healthcare professional for an in-person check.';
    }
  } else if (melanomaProb >= 0.35 || confidence < 65) {
    riskAssessment = 'Moderate Risk';
    riskBadgeClass = 'badge-moderate';
    riskSummaryText =
      'The assessment indicates mild morphological variance. Monitoring over time or scheduling a routine skin check is advised.';
  }

  // ABCDE Clinical Features
  const clinicalFeatures = diagnosis?.clinical_features || {};
  const measurements = diagnosis?.measurements?.lesion || {};
  const hasPhysicalScale = Boolean(measurements.physical_scale_available);

  // Download PDF Report handler
  const handleDownloadPDF = () => {
    if (downloading) return;
    setDownloading(true);
    showToast('Preparing your report...', 'info');

    setTimeout(() => {
      if (report?.pdf_url) {
        const link = document.createElement('a');
        link.href = report.pdf_url;
        link.download = `MelaDetect_Report_${analysis_id?.substring(0, 8) || 'SkinCheck'}.pdf`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        setDownloading(false);
        showToast('Report downloaded successfully.', 'success');
      } else {
        setDownloading(false);
        showToast("We couldn't generate the report right now. Please try again.", 'warning');
      }
    }, 800);
  };

  const handlePrint = () => {
    window.print();
  };

  // Determine current inspection image
  let activeDisplayUrl = original_image_url;
  if (activeImageTab === 'mask' && diagnosis?.segmentation?.mask_url) {
    activeDisplayUrl = diagnosis.segmentation.mask_url;
  } else if (activeImageTab === 'overlay' && diagnosis?.segmentation?.overlay_url) {
    activeDisplayUrl = diagnosis.segmentation.overlay_url;
  } else if (activeImageTab === 'gradcam' && explanation?.grad_cam_url) {
    activeDisplayUrl = explanation.grad_cam_url;
  }

  // Format date
  const displayDate = timestamp
    ? new Date(timestamp).toLocaleDateString('en-US', {
        month: 'long',
        day: 'numeric',
        year: 'numeric',
      })
    : new Date().toLocaleDateString('en-US', {
        month: 'long',
        day: 'numeric',
        year: 'numeric',
      });

  return (
    <div className="page-container report-page-wrapper" id="page-report">
      {/* Top Action Bar */}
      <div className="report-action-bar top-bar">
        <button
          type="button"
          className="btn btn-outline report-nav-back-btn"
          onClick={() => onNavigate('history')}
        >
          <i className="fas fa-arrow-left" aria-hidden="true"></i>
          <span>Back to Results</span>
        </button>

        <div className="report-actions-right">
          <button
            type="button"
            className="btn btn-outline"
            onClick={handlePrint}
            title="Print or save as digital copy"
          >
            <i className="fas fa-print" aria-hidden="true"></i>
            <span>Print</span>
          </button>

          <button
            type="button"
            className="btn btn-primary btn-download-pdf"
            onClick={handleDownloadPDF}
            disabled={downloading}
          >
            <i className="fas fa-download" aria-hidden="true"></i>
            <span>{downloading ? 'Preparing...' : 'Download PDF'}</span>
          </button>
        </div>
      </div>

      {/* Main Report Document Sheet */}
      <article className="card report-sheet">
        {/* Report Document Header */}
        <header className="report-document-header">
          <div className="report-header-left">
            <div className="report-brand-badge">
              <i className="fas fa-plus-square text-teal" aria-hidden="true"></i>
              <span>MelaDetect AI</span>
            </div>
            <h1 className="report-main-title">Skin Lesion Analysis Report</h1>
            <p className="report-meta-line">
              <span>Date: <strong>{displayDate}</strong></span>
              {analysis_id && (
                <span className="report-id-text">
                  Reference: #{analysis_id.substring(0, 8).toUpperCase()}
                </span>
              )}
              {_customContext?.location && (
                <span>Location: <strong>{_customContext.location}</strong></span>
              )}
            </p>
          </div>

          <div className="report-header-right">
            <span className={`risk-badge-lg ${riskBadgeClass}`}>
              {riskAssessment}
            </span>
          </div>
        </header>

        {/* 1. Assessment Summary */}
        <section className="report-section" aria-labelledby="assessment-summary-heading">
          <h2 id="assessment-summary-heading" className="report-section-heading">
            Assessment Summary
          </h2>

          <div className="assessment-summary-grid">
            <div className="summary-stat-box">
              <span className="summary-stat-label">Risk Assessment</span>
              <span className={`summary-stat-value risk-badge ${riskBadgeClass}`}>
                {riskAssessment}
              </span>
            </div>

            <div className="summary-stat-box">
              <span className="summary-stat-label">Model Confidence</span>
              <strong className="summary-stat-value text-primary font-manrope">
                {confidence}%
              </strong>
            </div>

            <div className="summary-stat-box">
              <span className="summary-stat-label">Status</span>
              <span className="summary-stat-value text-success">
                <i className="fas fa-check-circle" aria-hidden="true"></i>
                <span style={{ marginLeft: '6px' }}>Complete</span>
              </span>
            </div>
          </div>

          <div className="assessment-meaning-card">
            <h3 className="meaning-title">What this assessment means:</h3>
            <p className="meaning-text">{riskSummaryText}</p>
          </div>
        </section>

        {/* 2. Uploaded Image & Inspection Viewport */}
        <section className="report-section" aria-labelledby="lesion-image-heading">
          <h2 id="lesion-image-heading" className="report-section-heading">
            Uploaded Image
          </h2>

          <div className="report-image-container">
            <div className="report-image-viewport">
              <img
                src={original_image_url}
                alt="Analyzed skin lesion"
                className="report-lesion-img"
              />
              <button
                type="button"
                className="image-expand-btn"
                onClick={() => {
                  setActiveImageTab('original');
                  setZoomModal(true);
                }}
                title="View full-screen"
                aria-label="View photo in full screen"
              >
                <i className="fas fa-expand"></i>
              </button>
            </div>
            <p className="image-caption">
              Captured image submitted for algorithmic segmentation and feature analysis.
            </p>
          </div>
        </section>

        {/* 3. ABCDE Analysis */}
        <section className="report-section" aria-labelledby="abcde-analysis-heading">
          <h2 id="abcde-analysis-heading" className="report-section-heading">
            ABCDE Analysis
          </h2>
          <p className="report-section-sub">
            Evaluation of dermatological characteristics commonly referenced in skin health observation:
          </p>

          <div className="abcde-report-sections">
            {/* A - Asymmetry */}
            <div className="abcde-report-item">
              <div className="abcde-item-header">
                <div className="abcde-circle-badge">A</div>
                <div>
                  <h3 className="abcde-item-title">A — Asymmetry</h3>
                  <span className="abcde-item-metric">
                    Assessment: <strong>{clinicalFeatures.asymmetry?.score_label || 'Evaluated'}</strong>
                  </span>
                </div>
              </div>
              <p className="abcde-item-explanation">
                {clinicalFeatures.asymmetry?.score_label === 'High'
                  ? 'The lesion contours show noticeable structural asymmetry between halves.'
                  : clinicalFeatures.asymmetry?.score_label === 'Moderate'
                  ? 'Mild asymmetry observed across the contour axes.'
                  : 'The lesion halves display balanced symmetry and even outline.'}
              </p>
            </div>

            {/* B - Border */}
            <div className="abcde-report-item">
              <div className="abcde-item-header">
                <div className="abcde-circle-badge">B</div>
                <div>
                  <h3 className="abcde-item-title">B — Border</h3>
                  <span className="abcde-item-metric">
                    Assessment: <strong>{clinicalFeatures.border?.score_label || 'Evaluated'}</strong>
                  </span>
                </div>
              </div>
              <p className="abcde-item-explanation">
                {clinicalFeatures.border?.score_label === 'Irregular'
                  ? 'The perimeter exhibits scalloped, jagged, or less distinct outer boundaries.'
                  : 'The outer margin appears relatively regular and circumscribed.'}
              </p>
            </div>

            {/* C - Color */}
            <div className="abcde-report-item">
              <div className="abcde-item-header">
                <div className="abcde-circle-badge">C</div>
                <div>
                  <h3 className="abcde-item-title">C — Color</h3>
                  <span className="abcde-item-metric">
                    Assessment: <strong>{clinicalFeatures.color?.score_label || 'Evaluated'}</strong>
                  </span>
                </div>
              </div>
              <p className="abcde-item-explanation">
                {clinicalFeatures.color?.score_label?.includes('Multiple')
                  ? 'Variable pigmentation and mixed color tones detected across the surface.'
                  : 'Color distribution is generally uniform across the lesion surface.'}
              </p>
            </div>

            {/* D - Diameter */}
            <div className="abcde-report-item">
              <div className="abcde-item-header">
                <div className="abcde-circle-badge">D</div>
                <div>
                  <h3 className="abcde-item-title">D — Diameter</h3>
                  <span className="abcde-item-metric">
                    Assessment:{' '}
                    <strong>
                      {hasPhysicalScale && measurements.diameter_mm
                        ? `${measurements.diameter_mm} mm`
                        : 'Evaluated'}
                    </strong>
                  </span>
                </div>
              </div>
              <p className="abcde-item-explanation">
                {hasPhysicalScale && measurements.diameter_mm
                  ? measurements.diameter_mm > 6
                    ? `Physical diameter is measured at ${measurements.diameter_mm} mm (larger than 6 mm benchmark).`
                    : `Physical diameter is measured at ${measurements.diameter_mm} mm (within typical 6 mm threshold).`
                  : 'Lesion dimension estimated. Spots exceeding 6mm or showing rapid expansion warrant in-person review.'}
              </p>
            </div>

            {/* E - Evolution */}
            <div className="abcde-report-item">
              <div className="abcde-item-header">
                <div className="abcde-circle-badge">E</div>
                <div>
                  <h3 className="abcde-item-title">E — Evolution</h3>
                  <span className="abcde-item-metric">
                    Assessment: <strong>Baseline Documented</strong>
                  </span>
                </div>
              </div>
              <p className="abcde-item-explanation">
                {_customContext?.notes
                  ? `Reported observation: "${_customContext.notes}". Continued tracking of any changes in shape, size, elevation, or sensation is recommended.`
                  : 'Documenting this skin check establishes a baseline. Note any future changes in size, contour, elevation, or symptoms like itching.'}
              </p>
            </div>
          </div>
        </section>

        {/* 4. AI Explanation */}
        <section className="report-section" aria-labelledby="ai-explainability-heading">
          <h2 id="ai-explainability-heading" className="report-section-heading">
            AI Explanation
          </h2>
          <p className="report-section-sub">
            Inspection maps displaying model attention and boundary delineation:
          </p>

          <div className="explainability-workspace">
            {/* Layer Tabs */}
            <div className="explainability-tab-bar" role="tablist">
              <button
                type="button"
                role="tab"
                aria-selected={activeImageTab === 'original'}
                className={`tab-pill ${activeImageTab === 'original' ? 'active' : ''}`}
                onClick={() => setActiveImageTab('original')}
              >
                Original Image
              </button>
              {diagnosis?.segmentation?.overlay_url && (
                <button
                  type="button"
                  role="tab"
                  aria-selected={activeImageTab === 'overlay'}
                  className={`tab-pill ${activeImageTab === 'overlay' ? 'active' : ''}`}
                  onClick={() => setActiveImageTab('overlay')}
                >
                  Lesion Boundary Overlay
                </button>
              )}
              {explanation?.grad_cam_url && (
                <button
                  type="button"
                  role="tab"
                  aria-selected={activeImageTab === 'gradcam'}
                  className={`tab-pill ${activeImageTab === 'gradcam' ? 'active' : ''}`}
                  onClick={() => setActiveImageTab('gradcam')}
                >
                  Model Attention Map
                </button>
              )}
              {diagnosis?.segmentation?.mask_url && (
                <button
                  type="button"
                  role="tab"
                  aria-selected={activeImageTab === 'mask'}
                  className={`tab-pill ${activeImageTab === 'mask' ? 'active' : ''}`}
                  onClick={() => setActiveImageTab('mask')}
                >
                  Segmentation Mask
                </button>
              )}
            </div>

            {/* Side-by-Side Comparison Container */}
            <div className="explainability-side-by-side">
              <div className="compare-pane">
                <span className="compare-pane-title">Original Image</span>
                <div className="compare-image-box">
                  <img src={original_image_url} alt="Original lesion" />
                </div>
              </div>

              <div className="compare-pane">
                <span className="compare-pane-title">
                  {activeImageTab === 'overlay'
                    ? 'Boundary Delineation'
                    : activeImageTab === 'gradcam'
                    ? 'Attention Focus (Grad-CAM)'
                    : activeImageTab === 'mask'
                    ? 'Binary Segmentation Mask'
                    : 'Selected Layer'}
                </span>
                <div className="compare-image-box">
                  <img src={activeDisplayUrl} alt="Model explanation visualization" />
                </div>
              </div>
            </div>

            <div className="explainability-note-box">
              <i className="fas fa-circle-info text-teal" aria-hidden="true"></i>
              <p>
                The highlighted areas indicate regions that contributed to the model&apos;s assessment.
                This visualization highlights areas of algorithmic focus and does not prove melanoma.
              </p>
            </div>
          </div>
        </section>

        {/* 5. Recommended Next Steps */}
        <section className="report-section" aria-labelledby="next-steps-heading">
          <h2 id="next-steps-heading" className="report-section-heading">
            Recommended Next Steps
          </h2>

          <div className="next-steps-card">
            <div className="next-step-row">
              <div className="next-step-icon">
                <i className="fas fa-user-doctor"></i>
              </div>
              <div className="next-step-text">
                <strong>Schedule a Clinical Skin Examination</strong>
                <p>
                  If you notice any new, unusual, or rapidly changing spots, consider having them evaluated in person by a certified dermatologist.
                </p>
              </div>
            </div>

            <div className="next-step-row">
              <div className="next-step-icon">
                <i className="fas fa-calendar-check"></i>
              </div>
              <div className="next-step-text">
                <strong>Perform Monthly Self-Checks</strong>
                <p>
                  Keep track of moles across your skin once a month. Take photos under good lighting to monitor changes over time.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Bottom Disclaimer */}
        <footer className="medical-disclaimer-box" role="note">
          <p>
            MelaDetect AI provides AI-assisted information and is not a medical diagnosis. If you notice concerning or changing skin lesions, consider consulting a qualified healthcare professional.
          </p>
        </footer>
      </article>

      {/* Bottom Action Bar */}
      <div className="report-action-bar bottom-bar">
        <button
          type="button"
          className="btn btn-outline"
          onClick={() => onNavigate('history')}
        >
          <i className="fas fa-arrow-left" aria-hidden="true"></i>
          <span>Back to Results</span>
        </button>

        <div className="report-actions-right">
          <button
            type="button"
            className="btn btn-outline"
            onClick={handlePrint}
          >
            <i className="fas fa-print" aria-hidden="true"></i>
            <span>Print Report</span>
          </button>
          <button
            type="button"
            className="btn btn-primary"
            onClick={handleDownloadPDF}
            disabled={downloading}
          >
            <i className="fas fa-download" aria-hidden="true"></i>
            <span>{downloading ? 'Preparing...' : 'Download PDF'}</span>
          </button>
        </div>
      </div>

      {/* Fullscreen Zoom Modal */}
      {zoomModal && (
        <div
          className="modal-backdrop"
          onClick={() => setZoomModal(false)}
          role="dialog"
          aria-modal="true"
        >
          <div className="modal-card modal-zoom-card" onClick={(e) => e.stopPropagation()}>
            <button
              type="button"
              className="modal-close-btn"
              onClick={() => setZoomModal(false)}
              aria-label="Close full screen view"
            >
              <i className="fas fa-times"></i>
            </button>
            <img
              src={activeDisplayUrl}
              alt="High resolution skin lesion view"
              className="zoom-image-element"
            />
          </div>
        </div>
      )}
    </div>
  );
}
