import { useCallback, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useToast } from '../components/Toast';
import { useAuth } from '../components/AuthContext';
import { useNotification } from '../components/NotificationContext';

const MAX_BYTES = 10 * 1024 * 1024;
const MAX_MB = 10;
const TYPES = new Set(['image/jpeg', 'image/jpg', 'image/png', 'image/webp']);
const EXTENSIONS = new Set(['.jpeg', '.jpg', '.png', '.webp']);

const ANALYSIS_STEPS = [
  { id: 'upload', label: 'Image uploaded' },
  { id: 'preprocess', label: 'Image preprocessing' },
  { id: 'ai', label: 'AI analysis' },
  { id: 'report', label: 'Generating report' },
];

const BODY_LOCATIONS = ['Face', 'Arm', 'Leg', 'Back', 'Chest', 'Other'];

function validateFile(file) {
  const extension = `.${file.name.split('.').pop()?.toLowerCase()}`;
  if (!TYPES.has(file.type) || !EXTENSIONS.has(extension)) {
    return 'Unsupported image format. Please upload a JPG, JPEG, PNG, or WEBP file.';
  }
  if (file.size > MAX_BYTES) {
    return `Image file is too large. Please upload an image under ${MAX_MB} MB.`;
  }
  return null;
}

function decodeImage(file) {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const image = new Image();
    image.onload = () => {
      URL.revokeObjectURL(url);
      const ratio = Math.max(image.width / image.height, image.height / image.width);
      if (image.width < 256 || image.height < 256) {
        reject(new Error('Image resolution is too low (< 256px). Please upload a clearer photo.'));
      } else if (ratio > 4) {
        reject(new Error('The image aspect ratio is too extreme. Please upload a centered photo.'));
      } else {
        resolve();
      }
    };
    image.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error('The selected file could not be read as an image.'));
    };
    image.src = url;
  });
}

export default function Upload({ onAnalysisComplete, onNavigate }) {
  const showToast = useToast();
  const { token } = useAuth();
  const { startReportRunning, setReportCompleted, setReportFailed } = useNotification();
  const navigate = useNavigate();
  const inputRef = useRef(null);

  // Gate: user must acknowledge instructions before they can upload
  const [instructionsAcknowledged, setInstructionsAcknowledged] = useState(false);

  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState(null);

  // Workflow states: 'idle' | 'analyzing' | 'complete'
  const [workflowState, setWorkflowState] = useState('idle');
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [completedAnalysis, setCompletedAnalysis] = useState(null);

  // Optional contextual location
  const [lesionLocation, setLesionLocation] = useState('Arm');
  const [notes, setNotes] = useState('');

  const selectFile = useCallback(async (candidate) => {
    if (!candidate) return;
    const validationError = validateFile(candidate);
    if (validationError) {
      setError(validationError);
      return;
    }
    try {
      await decodeImage(candidate);
      if (preview) URL.revokeObjectURL(preview);
      setFile(candidate);
      setPreview(URL.createObjectURL(candidate));
      setError(null);
      setWorkflowState('idle');
      setCompletedAnalysis(null);
    } catch (decodeError) {
      setError(decodeError.message);
    }
  }, [preview]);

  const clearFile = () => {
    if (preview) URL.revokeObjectURL(preview);
    setFile(null);
    setPreview(null);
    setError(null);
    setWorkflowState('idle');
    setCompletedAnalysis(null);
    if (inputRef.current) inputRef.current.value = '';
  };

  const startAnalysis = async () => {
    if (!file) {
      setError('Please select or drop a skin lesion image first.');
      return;
    }

    setWorkflowState('analyzing');
    setCurrentStepIndex(0);
    setError(null);
    startReportRunning();

    // Step progression animation timer
    let stepTimer = window.setInterval(() => {
      setCurrentStepIndex((prev) => {
        if (prev < ANALYSIS_STEPS.length - 1) {
          return prev + 1;
        }
        return prev;
      });
    }, 1800);

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('scale_method', 'auto');

      const result = await new Promise((resolve, reject) => {
        const request = new XMLHttpRequest();
        request.open('POST', '/api/analyze');
        request.responseType = 'json';
        if (token) {
          request.setRequestHeader('Authorization', `Bearer ${token}`);
        }

        request.onload = () => {
          const body = request.response || {};
          if (request.status >= 200 && request.status < 300) {
            resolve(body);
          } else {
            reject(new Error(body.detail?.message || 'The image could not be analyzed. Please try again.'));
          }
        };
        request.onerror = () => reject(new Error('The analysis service could not be reached. Please check the backend.'));
        request.send(formData);
      });

      window.clearInterval(stepTimer);
      setCurrentStepIndex(ANALYSIS_STEPS.length - 1);

      // Attach custom context for results
      result._customContext = {
        location: lesionLocation,
        notes: notes,
      };

      setCompletedAnalysis(result);
      setWorkflowState('complete');
      setReportCompleted(result);
      showToast('Skin check assessment completed.', 'success');
    } catch (requestError) {
      window.clearInterval(stepTimer);
      setWorkflowState('idle');
      setError(requestError.message);
      setReportFailed(requestError.message);
      showToast(requestError.message, 'error');
    }
  };

  const handleViewReport = () => {
    if (completedAnalysis) {
      if (onAnalysisComplete) {
        onAnalysisComplete(completedAnalysis);
      }
      navigate(`/results/${completedAnalysis.analysis_id}`);
    }
  };

  const handleDownloadReport = () => {
    if (!completedAnalysis?.report?.pdf_url) {
      showToast('Preparing your report...', 'info');
      // If pdf_url is not ready yet, simulate quick check or show clean message
      setTimeout(() => {
        if (completedAnalysis?.report?.pdf_url) {
          const link = document.createElement('a');
          link.href = completedAnalysis.report.pdf_url;
          link.download = `MelaDetect_Report_${completedAnalysis.analysis_id?.substring(0, 8) || 'SkinCheck'}.pdf`;
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
          showToast('Report downloaded successfully.', 'success');
        } else {
          showToast("We couldn't generate the report right now. Please try viewing the report.", 'warning');
        }
      }, 1000);
      return;
    }

    showToast('Preparing your report...', 'info');
    setTimeout(() => {
      const link = document.createElement('a');
      link.href = completedAnalysis.report.pdf_url;
      link.download = `MelaDetect_Report_${completedAnalysis.analysis_id?.substring(0, 8) || 'SkinCheck'}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      showToast('Report downloaded successfully.', 'success');
    }, 600);
  };

  // Helper for risk tiering in completion summary
  const getRiskDetails = (analysis) => {
    if (!analysis) return { label: 'Assessed', class: 'badge-low', confidence: 0 };
    const diag = analysis.diagnosis?.diagnosis;
    const isMelanoma = diag?.prediction === 'Melanoma';
    const conf = Math.round(diag?.confidence || 0);

    if (isMelanoma) {
      if (conf >= 80) return { label: 'High Risk', class: 'badge-high', confidence: conf };
      return { label: 'Moderate Risk', class: 'badge-moderate', confidence: conf };
    }
    if (conf < 65) return { label: 'Moderate Risk', class: 'badge-moderate', confidence: conf };
    return { label: 'Low Risk', class: 'badge-low', confidence: conf };
  };

  const riskDetails = completedAnalysis ? getRiskDetails(completedAnalysis) : null;

  return (
    <div className="page-container" id="page-new-check">
      {/* Page Header */}
      <div className="page-header-clean">
        <h1 className="page-title-clean">Start a Skin Check</h1>
        <p className="page-subtitle-clean">
          Upload a clear image of the skin lesion you want to analyze.
        </p>
      </div>

      {/* â”€â”€ Step 1: Instructions Acknowledgment Gate â”€â”€ */}
      {!instructionsAcknowledged ? (
        <div className="instructions-gate-wrapper">
          <div className="card instructions-gate-card">
            <div className="instructions-gate-header">
              <div className="instructions-gate-icon" aria-hidden="true">
                <i className="fas fa-clipboard-list"></i>
              </div>
              <h2 className="instructions-gate-title">Before You Upload</h2>
              <p className="instructions-gate-subtitle">
                Please read the following guidelines carefully to ensure the most accurate AI analysis.
              </p>
            </div>

            <ul className="instructions-gate-list" aria-label="Image capture guidelines">
              <li className="instruction-gate-item">
                <div className="instruction-gate-num" aria-hidden="true">1</div>
                <div>
                  <strong>Use a clear, well-focused image</strong>
                  <p>Blurry or out-of-focus photos reduce analysis accuracy significantly.</p>
                </div>
              </li>
              <li className="instruction-gate-item">
                <div className="instruction-gate-num" aria-hidden="true">2</div>
                <div>
                  <strong>Ensure good, even lighting</strong>
                  <p>Natural daylight or a bright indoor light works best. Avoid dark or shadowy conditions.</p>
                </div>
              </li>
              <li className="instruction-gate-item">
                <div className="instruction-gate-num" aria-hidden="true">3</div>
                <div>
                  <strong>Keep the lesion fully visible in the frame</strong>
                  <p>The entire area of concern should be clearly visible and centered.</p>
                </div>
              </li>
              <li className="instruction-gate-item">
                <div className="instruction-gate-num" aria-hidden="true">4</div>
                <div>
                  <strong>Avoid shadows, reflections, or glare</strong>
                  <p>Position the camera to eliminate direct reflections from skin or lighting.</p>
                </div>
              </li>
              <li className="instruction-gate-item">
                <div className="instruction-gate-num" aria-hidden="true">5</div>
                <div>
                  <strong>Do not use filtered or edited images</strong>
                  <p>Only upload original, unprocessed photographs. Filters distort color analysis.</p>
                </div>
              </li>
              <li className="instruction-gate-item">
                <div className="instruction-gate-num" aria-hidden="true">6</div>
                <div>
                  <strong>Hold the camera parallel to the skin</strong>
                  <p>Shoot straight-on rather than at an angle for consistent results.</p>
                </div>
              </li>
              <li className="instruction-gate-item">
                <div className="instruction-gate-num" aria-hidden="true">7</div>
                <div>
                  <strong>Include only one main lesion when possible</strong>
                  <p>Isolating a single lesion yields the most precise risk assessment.</p>
                </div>
              </li>
            </ul>

            <div className="instructions-gate-specs">
              <i className="fas fa-image" aria-hidden="true"></i>
              <span>Accepted formats: JPG, JPEG, PNG, WEBP &nbsp;&middot;&nbsp; Max size: {MAX_MB} MB &nbsp;&middot;&nbsp; Min resolution: 256 &times; 256 px</span>
            </div>

            <div className="instructions-gate-disclaimer">
              <i className="fas fa-shield-alt" aria-hidden="true"></i>
              <p>MelaDetect AI provides AI-assisted risk assessment only and is <strong>not a substitute for professional medical diagnosis</strong>. Always consult a qualified healthcare professional for concerning lesions.</p>
            </div>

            <div className="instructions-gate-cta">
              <button
                type="button"
                className="btn btn-primary btn-lg instructions-acknowledge-btn"
                onClick={() => setInstructionsAcknowledged(true)}
              >
                <i className="fas fa-check-circle" aria-hidden="true"></i>
                <span>I Understand &mdash; Proceed to Upload</span>
              </button>
            </div>
          </div>
        </div>
      ) : (
        /* Step 2: Upload UI (shown after acknowledgment) */
        <div className="skin-check-grid">
          {/* LEFT COLUMN: Upload Card / Loading / Complete */}
          <div className="skin-check-main-col">
            {workflowState === 'idle' && (
              <div className="card upload-card-wrapper">
                {!preview ? (
                  /* Premium Dashed Upload Dropzone */
                  <div
                    className={`upload-dropzone-premium ${dragOver ? 'drag-active' : ''}`}
                    onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                    onDragLeave={() => setDragOver(false)}
                    onDrop={(e) => {
                      e.preventDefault();
                      setDragOver(false);
                      if (e.dataTransfer.files?.[0]) selectFile(e.dataTransfer.files[0]);
                    }}
                    onClick={() => inputRef.current?.click()}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        inputRef.current?.click();
                      }
                    }}
                    aria-label="Upload skin lesion image by drag and drop or browsing"
                  >
                    <input
                      ref={inputRef}
                      type="file"
                      style={{ display: 'none' }}
                      accept=".jpeg,.jpg,.png,.webp,image/jpeg,image/png,image/webp"
                      onChange={(e) => {
                        if (e.target.files?.[0]) selectFile(e.target.files[0]);
                      }}
                    />

                    <div className="upload-icon-circle" aria-hidden="true">
                      <i className="fas fa-cloud-arrow-up"></i>
                    </div>

                    <h2 className="upload-prompt-title">Drag &amp; drop your image here</h2>
                    <p className="upload-prompt-or">or</p>
                    <button
                      type="button"
                      className="btn btn-outline upload-browse-btn"
                      onClick={(e) => {
                        e.stopPropagation();
                        inputRef.current?.click();
                      }}
                    >
                      Browse Image
                    </button>

                    <p className="upload-supported-text">
                      Supported formats: JPG, JPEG, PNG, WEBP (Max {MAX_MB} MB)
                    </p>
                  </div>
                ) : (
                  /* Selected Image Preview State */
                  <div className="upload-preview-card">
                    <div className="preview-image-box">
                      <img src={preview} alt="Skin lesion preview" className="preview-img-element" />
                    </div>

                    <div className="preview-file-bar">
                      <div className="preview-file-info">
                        <i className="far fa-image text-teal" aria-hidden="true"></i>
                        <div className="preview-file-text">
                          <strong className="preview-filename">{file?.name}</strong>
                          <span className="preview-filesize">
                            {(file?.size ? (file.size / (1024 * 1024)).toFixed(2) : 0)} MB
                          </span>
                        </div>
                      </div>

                      <div className="preview-btn-group">
                        <button
                          type="button"
                          className="btn btn-sm btn-outline"
                          onClick={() => inputRef.current?.click()}
                        >
                          <i className="fas fa-sync-alt" aria-hidden="true"></i>
                          <span>Change Image</span>
                        </button>
                        <button
                          type="button"
                          className="btn btn-sm btn-outline text-danger"
                          onClick={clearFile}
                        >
                          <i className="fas fa-trash-alt" aria-hidden="true"></i>
                          <span>Remove</span>
                        </button>
                      </div>
                    </div>

                    {/* Optional Location Context */}
                    <div className="upload-context-section">
                      <label className="context-label">Anatomical Location (Optional)</label>
                      <div className="location-pills-row">
                        {BODY_LOCATIONS.map((loc) => (
                          <button
                            key={loc}
                            type="button"
                            className={`location-pill ${lesionLocation === loc ? 'active' : ''}`}
                            onClick={() => setLesionLocation(loc)}
                          >
                            {loc}
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* Optional Observations Context */}
                    <div className="upload-context-section">
                      <label className="context-label" htmlFor="upload-notes">Observed Changes (Optional)</label>
                      <input
                        id="upload-notes"
                        type="text"
                        className="form-input-clean"
                        placeholder="e.g. Noticed recent darkening or slight itching..."
                        value={notes}
                        onChange={(e) => setNotes(e.target.value)}
                      />
                    </div>

                    {/* Analyze Action */}
                    <div className="upload-cta-row">
                      <button
                        type="button"
                        className="btn btn-primary btn-analyze-full"
                        onClick={startAnalysis}
                        disabled={!file}
                      >
                        <i className="fas fa-microscope" aria-hidden="true"></i>
                        <span>Analyze Image</span>
                      </button>
                    </div>
                  </div>
                )}

                {/* Error Message */}
                {error && (
                  <div className="upload-error-box" role="alert">
                    <i className="fas fa-circle-exclamation text-danger" aria-hidden="true"></i>
                    <span>{error}</span>
                  </div>
                )}
              </div>
            )}

            {/* Analysis Loading State */}
            {workflowState === 'analyzing' && (
              <div className="card analysis-loading-card" aria-live="polite">
                <div className="loading-header">
                  <h2 className="loading-title">Analyzing your image</h2>
                  <p className="loading-subtitle">
                    Please wait while MelaDetect AI processes the lesion image.
                  </p>
                </div>

                {preview && (
                  <div className="loading-preview-mini">
                    <img src={preview} alt="Lesion being analyzed" />
                  </div>
                )}

                {/* Subtle Progress Track */}
                <div className="progress-track-clean">
                  <div
                    className="progress-fill-clean"
                    style={{ width: `${((currentStepIndex + 1) / ANALYSIS_STEPS.length) * 100}%` }}
                  ></div>
                </div>

                {/* Step Checklist */}
                <div className="analysis-steps-list">
                  {ANALYSIS_STEPS.map((s, index) => {
                    const isDone = index < currentStepIndex;
                    const isCurrent = index === currentStepIndex;

                    return (
                      <div
                        key={s.id}
                        className={`analysis-step-item ${isDone ? 'step-done' : isCurrent ? 'step-current' : 'step-pending'}`}
                      >
                        <span className="step-indicator" aria-hidden="true">
                          {isDone ? (
                            <i className="fas fa-check"></i>
                          ) : isCurrent ? (
                            <span className="step-pulse-dot"></span>
                          ) : (
                            <span className="step-circle-dot"></span>
                          )}
                        </span>
                        <span className="step-label-text">{s.label}</span>
                      </div>
                    );
                  })}
                </div>

                <p className="loading-calm-note">
                  AI algorithms are evaluating lesion contours, pigment distribution, and clinical criteria.
                </p>
              </div>
            )}

            {/* Analysis Complete State */}
            {workflowState === 'complete' && completedAnalysis && (
              <div className="card analysis-complete-card" aria-live="polite">
                <div className="complete-badge-row">
                  <div className="complete-icon-circle" aria-hidden="true">
                    <i className="fas fa-check"></i>
                  </div>
                  <div>
                    <h2 className="complete-title">Analysis Complete</h2>
                    <p className="complete-subtitle">Your skin lesion assessment is ready.</p>
                  </div>
                </div>

                {/* Clean Result Summary */}
                <div className="complete-summary-box">
                  <div className="summary-item">
                    <span className="summary-item-label">Risk Assessment</span>
                    <div className="summary-item-value">
                      <span className={`risk-badge ${riskDetails?.class}`}>
                        {riskDetails?.label}
                      </span>
                    </div>
                  </div>

                  <div className="summary-item">
                    <span className="summary-item-label">Confidence</span>
                    <div className="summary-item-value">
                      <strong className="summary-confidence-number">
                        {riskDetails?.confidence}%
                      </strong>
                    </div>
                  </div>

                  <div className="summary-item">
                    <span className="summary-item-label">Assessment Generated</span>
                    <div className="summary-item-value text-secondary">
                      {new Date().toLocaleDateString('en-US', {
                        month: 'long',
                        day: 'numeric',
                        year: 'numeric',
                      })}
                    </div>
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="complete-actions-bar">
                  <button
                    type="button"
                    className="btn btn-primary btn-lg complete-action-btn"
                    onClick={handleViewReport}
                  >
                    <i className="fas fa-file-waveform" aria-hidden="true"></i>
                    <span>View Report</span>
                  </button>

                  <button
                    type="button"
                    className="btn btn-secondary btn-lg complete-action-btn"
                    onClick={handleDownloadReport}
                  >
                    <i className="fas fa-download" aria-hidden="true"></i>
                    <span>Download Report</span>
                  </button>
                </div>

                <button
                  type="button"
                  className="complete-restart-btn"
                  onClick={clearFile}
                >
                  Start another skin check
                </button>
              </div>
            )}
          </div>

          {/* RIGHT COLUMN: Quick tips recap */}
          <div className="skin-check-side-col">
            <div className="card upload-instructions-card">
              <div className="instructions-header">
                <h3 className="instructions-title">Quick Reminders</h3>
                <p className="instructions-subtitle">Tips for a clearer analysis</p>
              </div>

              <ul className="instructions-checklist" aria-label="Image capture guidelines">
                <li className="instruction-item">
                  <div className="instruction-check-circle" aria-hidden="true">
                    <i className="fas fa-check"></i>
                  </div>
                  <span>Use a clear, well-focused image</span>
                </li>
                <li className="instruction-item">
                  <div className="instruction-check-circle" aria-hidden="true">
                    <i className="fas fa-check"></i>
                  </div>
                  <span>Use good, even lighting</span>
                </li>
                <li className="instruction-item">
                  <div className="instruction-check-circle" aria-hidden="true">
                    <i className="fas fa-check"></i>
                  </div>
                  <span>Keep the lesion fully visible</span>
                </li>
                <li className="instruction-item">
                  <div className="instruction-check-circle" aria-hidden="true">
                    <i className="fas fa-check"></i>
                  </div>
                  <span>Avoid heavy shadows or reflections</span>
                </li>
                <li className="instruction-item">
                  <div className="instruction-check-circle" aria-hidden="true">
                    <i className="fas fa-check"></i>
                  </div>
                  <span>Do not use filters or edited images</span>
                </li>
                <li className="instruction-item">
                  <div className="instruction-check-circle" aria-hidden="true">
                    <i className="fas fa-check"></i>
                  </div>
                  <span>Keep the camera parallel to the skin</span>
                </li>
                <li className="instruction-item">
                  <div className="instruction-check-circle" aria-hidden="true">
                    <i className="fas fa-check"></i>
                  </div>
                  <span>Include only one main lesion when possible</span>
                </li>
              </ul>

              <div className="instructions-specs-box">
                <div className="specs-title">Image requirements</div>
                <div className="specs-detail">
                  <span>Formats: JPG, JPEG, PNG, WEBP</span>
                  <span>Maximum size: {MAX_MB} MB</span>
                </div>
              </div>

              <button
                type="button"
                className="btn btn-ghost btn-sm instructions-back-btn"
                onClick={() => { setInstructionsAcknowledged(false); clearFile(); }}
              >
                <i className="fas fa-arrow-left" aria-hidden="true"></i>
                <span>Back to Instructions</span>
              </button>
            </div>
          </div>
        </div>
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
