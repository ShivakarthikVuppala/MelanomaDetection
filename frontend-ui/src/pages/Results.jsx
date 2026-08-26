import { useToast } from '../components/Toast';

export default function Results({ analysisResult, onNavigate }) {
  const showToast = useToast();

  if (!analysisResult) {
    return (
      <section className="page active" id="page-results">
        <div className="empty-state">
          <div className="empty-state-icon"><i className="fas fa-chart-bar"></i></div>
          <h2>No Results Yet</h2>
          <p>Upload an image and run the pipeline to see results here.</p>
          <button className="btn btn-primary" onClick={() => onNavigate('upload')}>
            <i className="fas fa-upload"></i> Upload Image
          </button>
        </div>
      </section>
    );
  }

  if (analysisResult.status !== 'completed' || !analysisResult.diagnosis) {
    return (
      <section className="page active" id="page-results">
        <div className="empty-state" style={{ color: 'var(--danger)' }}>
          <div className="empty-state-icon" style={{ color: 'inherit' }}><i className="fas fa-exclamation-triangle"></i></div>
          <h2>{analysisResult.status === 'image_quality_insufficient' ? 'Image quality insufficient' : 'Analysis could not be completed'}</h2>
          <p>{analysisResult.message || 'Please try again with a clearer image.'}</p>
          <div style={{ marginTop: '16px', padding: '16px', background: 'var(--surface-light)', borderRadius: '8px', color: 'var(--text-light)' }}>
            {analysisResult.error_code && <div>{analysisResult.error_code}</div>}
          </div>
          <button className="btn btn-primary mt-24" onClick={() => onNavigate('upload')}>
            <i className="fas fa-redo"></i> Try Again
          </button>
        </div>
      </section>
    );
  }

  const {
    diagnosis,
    evidence,
    explanation,
    report,
    original_image_url
  } = analysisResult;

  const isMelanoma = diagnosis?.diagnosis?.prediction === 'Melanoma';
  const melanomaProbability = Number(
    diagnosis?.melanoma_probability ?? diagnosis?.probabilities?.melanoma ?? 0
  );
  const focusNeedsReview = diagnosis?.explainability?.attention_inside_lesion != null
    && diagnosis.explainability.attention_inside_lesion < 0.30;
  const lowProbabilityFlag = isMelanoma && melanomaProbability < 0.50;
  const riskColor = focusNeedsReview || lowProbabilityFlag
    ? 'var(--accent-amber)'
    : isMelanoma ? 'var(--danger)' : 'var(--success)';
  const riskLevel = focusNeedsReview
    ? 'Focus review required'
    : lowProbabilityFlag
      ? 'Screening flag below 50%'
      : isMelanoma ? 'Screening flag' : 'Below melanoma threshold';

  const handleDownloadPDF = () => {
    if (report?.pdf_url) {
      const link = document.createElement('a');
      link.href = report.pdf_url;
      link.download = `Melanoma_Report_${analysisResult.analysis_id.substring(0, 8)}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } else {
      showToast('PDF report is not available for this analysis.', 'warning');
    }
  };

  return (
    <section className="page active" id="page-results">
      <div className="results-header">
        <div>
          <h1 className="page-title">Analysis Results</h1>
          <p className="page-subtitle">Multi-Phase Pipeline Output</p>
        </div>
        <div className="results-actions">
          <button className="btn btn-white" onClick={handleDownloadPDF} disabled={!report?.pdf_url}>
            <i className="fas fa-download"></i> Download PDF
          </button>
          <button className="btn btn-primary" onClick={() => onNavigate('upload')}>
            <i className="fas fa-plus"></i> New Analysis
          </button>
        </div>
      </div>

      <div className="results-grid">
        {/* Phase 1: Diagnosis Card */}
        <div className="result-card">
          <div className="result-card-header">
            <h3 className="result-card-title">Phase 1: Diagnosis</h3>
            <span
              className={`diagnosis-badge ${isMelanoma ? 'high' : 'low'}`}
              style={{ backgroundColor: riskColor + '20', color: riskColor }}
            >
              <i className={`fas ${isMelanoma ? 'fa-exclamation-triangle' : 'fa-check-circle'}`}></i>{' '}
              {riskLevel}
            </span>
          </div>

          <div className="confidence-section">
            <div className="confidence-circle">
              <svg viewBox="0 0 64 64">
                <circle className="bg" cx="32" cy="32" r="28"></circle>
                <circle
                  className="progress"
                  cx="32" cy="32" r="28"
                  style={{
                    strokeDashoffset: 175.9 - (175.9 * (diagnosis?.diagnosis?.confidence || 0)) / 100,
                    stroke: riskColor,
                  }}
                ></circle>
              </svg>
              <span className="confidence-value" style={{ fontSize: '14px' }}>
                {(diagnosis?.diagnosis?.confidence || 0).toFixed(1)}%
              </span>
            </div>
          <div className="confidence-info">
            <h4>{diagnosis?.diagnosis?.prediction}</h4>
            <p>Thresholded model score (not a diagnosis)</p>
          </div>
          </div>

          <div className="metrics-row" style={{ marginTop: '20px' }}>
            <div><strong>{(melanomaProbability * 100).toFixed(1)}%</strong><span>Melanoma probability</span></div>
            <div><strong>{((diagnosis?.non_melanoma_probability ?? diagnosis?.probabilities?.non_melanoma ?? diagnosis?.probabilities?.not_melanoma ?? 0) * 100).toFixed(1)}%</strong><span>Non-melanoma probability</span></div>
            <div><strong>{diagnosis?.classification_threshold != null ? `${(diagnosis.classification_threshold * 100).toFixed(1)}%` : 'N/A'}</strong><span>Validated threshold</span></div>
          </div>

          <h3 className="result-card-title mb-16" style={{ marginTop: '24px' }}>AI-Extracted Clinical Features</h3>
          <div className="clinical-features">
            {Object.entries(diagnosis?.clinical_features || {}).map(([key, feature]) => (
              <div className="clinical-feature" key={key}>
                <span className="clinical-feature-name" style={{ textTransform: 'capitalize' }}>
                  <i className="fas fa-microscope"></i> {key}
                </span>
                <span className="clinical-feature-value">
                  {feature.score_label}
                  <span className="feature-score">({(feature.score_numeric || 0).toFixed(2)})</span>
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Visualizations Card */}
        <div className="result-card">
          <div className="result-card-header">
            <h3 className="result-card-title">Visualizations</h3>
          </div>

          <div className="images-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginTop: '16px' }}>
            {original_image_url && (
              <div className="result-image-preview">
                <img src={original_image_url} alt="Original" />
                <div className="result-image-label">Original Image</div>
              </div>
            )}
            
            {diagnosis?.segmentation?.mask_url && (
              <div className="result-image-preview">
                <img src={diagnosis.segmentation.mask_url} alt="Segmentation Mask" />
                <div className="result-image-label">SegFormer Segmentation</div>
              </div>
            )}

            {diagnosis?.segmentation?.overlay_url && (
              <div className="result-image-preview">
                <img src={diagnosis.segmentation.overlay_url} alt="Original image with SegFormer lesion overlay" />
                <div className="result-image-label">Original + SegFormer Overlay</div>
              </div>
            )}

            {explanation?.grad_cam_url && (
              <div className="result-image-preview" style={{ gridColumn: '1 / -1' }}>
                <img src={explanation.grad_cam_url} alt="Grad-CAM" />
                <div className="result-image-label">Grad-CAM Attention Map</div>
              </div>
            )}
          </div>
        </div>

        <div className="result-card full-width">
          <h3 className="result-card-title mb-16">Measurements and ABCD findings</h3>

          {/* Pixel measurements */}
          <div className="metrics-row">
            {Object.entries(diagnosis?.measurements?.lesion || {}).filter(([key]) => key.endsWith('_px') && !key.includes('bounding')).map(([key, value]) => <div key={key}><strong>{typeof value === 'number' ? value.toLocaleString() : 'N/A'}</strong><span>{key.replaceAll('_', ' ')}</span></div>)}
          </div>

          {/* Physical measurements (when scale calibration is available) */}
          {diagnosis?.measurements?.lesion?.physical_scale_available && (
            <div style={{ marginTop: '16px', padding: '16px', background: 'var(--accent-green-bg)', borderRadius: '8px', border: '1px solid rgba(34,197,94,0.2)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                <i className="fas fa-ruler-combined" style={{ color: 'var(--accent-green)' }} />
                <strong style={{ color: 'var(--accent-green)' }}>Physical Measurements (Calibrated)</strong>
                {diagnosis?.scale_calibration?.detected && (
                  <span style={{ marginLeft: 'auto', fontSize: '11px', padding: '3px 10px', borderRadius: '12px', background: 'var(--accent-green-bg)', border: '1px solid var(--accent-green)', color: 'var(--accent-green)' }}>
                    {diagnosis.scale_calibration.method} — {(diagnosis.scale_calibration.confidence * 100).toFixed(0)}% confidence
                  </span>
                )}
              </div>
              <div className="metrics-row">
                {diagnosis.measurements.lesion.diameter_mm != null && (
                  <div><strong>{diagnosis.measurements.lesion.diameter_mm} mm</strong><span>diameter</span></div>
                )}
                {diagnosis.measurements.lesion.area_mm2 != null && (
                  <div><strong>{diagnosis.measurements.lesion.area_mm2} mm²</strong><span>area</span></div>
                )}
                {diagnosis.measurements.lesion.perimeter_mm != null && (
                  <div><strong>{diagnosis.measurements.lesion.perimeter_mm} mm</strong><span>perimeter</span></div>
                )}
              </div>
            </div>
          )}

          {diagnosis?.scale_calibration && !diagnosis.scale_calibration.calibration_valid && (
            <div style={{ marginTop: '16px', padding: '14px 16px', background: 'var(--accent-amber-bg)', borderRadius: '8px', color: 'var(--text-light)' }}>
              <strong>Physical measurement: UNAVAILABLE</strong>
              <div style={{ marginTop: '4px' }}>
                {diagnosis.scale_calibration.calibration_reason || 'The reference calibration could not be verified.'}
              </div>
              <div style={{ marginTop: '4px' }}>Pixel measurements remain available.</div>
            </div>
          )}

          <div className="clinical-features" style={{ marginTop: '18px' }}>
            {Object.entries(diagnosis?.clinical_features || {}).map(([key, feature]) => <div className="clinical-feature" key={key}><span className="clinical-feature-name">{key}</span><span className="clinical-feature-value">{feature.score_label} ({feature.score_numeric.toFixed(2)})</span></div>)}
            {diagnosis?.clinical_interpretations?.diameter && <div className="clinical-feature"><span className="clinical-feature-name">Diameter interpretation</span><span className="clinical-feature-value">{diagnosis.clinical_interpretations.diameter}</span></div>}
          </div>
          <p style={{ color: 'var(--text-light)', fontSize: '13px', marginBottom: 0 }}>
            {diagnosis?.measurements?.lesion?.physical_scale_available
              ? 'Physical measurements were calibrated using a detected reference object. Accuracy depends on calibration quality.'
              : 'Measurements are reported in image pixels. Include a reference object (ruler, coin) in the image for physical mm measurements.'}
          </p>
        </div>

        {/* Phase 3: Explanation Card */}
        <div className="result-card full-width">
          <h3 className="result-card-title mb-16">Phase 3: Explainability & Reasoning</h3>
          <div className="summary-card" style={{ marginBottom: '16px' }}>
            <h4>{explanation?.summary}</h4>
          </div>
          {explanation?.next_steps && (
            <div style={{ marginBottom: '18px', padding: '16px', borderLeft: '4px solid var(--primary)', background: 'var(--surface-light)', borderRadius: '8px' }}>
              <strong>What to do next</strong>
              <p style={{ margin: '6px 0 0', lineHeight: 1.55 }}>{explanation.next_steps}</p>
            </div>
          )}
          
          <div className="detailed-analysis-grid" style={{ gridTemplateColumns: '1fr' }}>
            {explanation?.reasoning?.map((reason, idx) => (
              <div className="analysis-detail-item" key={idx} style={{ padding: '12px' }}>
                <p><i className="fas fa-check text-success" style={{ marginRight: '8px' }}></i> {reason}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Phase 2: Evidence Card */}
        <div className="result-card full-width">
          <h3 className="result-card-title mb-16">Phase 2: Medical Evidence (BGE + Qdrant)</h3>
          {evidence && evidence.length > 0 ? (
            <div className="evidence-list" style={{ display: 'grid', gap: '16px' }}>
              {evidence.map((item, idx) => (
                <div className="evidence-item" key={idx} style={{ background: 'var(--surface)', padding: '16px', borderRadius: '8px', border: '1px solid var(--border)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                    <h4 style={{ color: 'var(--primary)', margin: 0 }}>{item.title}</h4>
                    <span style={{ fontSize: '12px', background: 'var(--surface-light)', padding: '4px 8px', borderRadius: '4px' }}>
                      Score: {item.relevance_score?.toFixed(2)}
                    </span>
                  </div>
                  <div style={{ fontSize: '12px', color: 'var(--text-light)', marginBottom: '8px' }}>Source: {item.source}</div>
                  <p style={{ fontSize: '14px', lineHeight: '1.5', margin: 0 }}>"{item.snippet}"</p>
                </div>
              ))}
            </div>
          ) : (
            <p>No medical evidence retrieved for this analysis.</p>
          )}
        </div>
      </div>
      <div style={{ marginTop: '24px', padding: '14px 16px', background: 'var(--accent-red-bg)', borderRadius: '8px', fontSize: '13px' }}><strong>Medical disclaimer:</strong> This AI-based decision-support/research tool does not provide a definitive medical diagnosis and should not replace evaluation by a qualified dermatologist or healthcare professional.</div>
    </section>
  );
}
