import { useCallback, useRef, useState } from 'react';
import { useToast } from '../components/Toast';

const MAX_BYTES = 10 * 1024 * 1024;
const TYPES = new Set(['image/jpeg', 'image/jpg', 'image/png', 'image/webp']);
const EXTENSIONS = new Set(['.jpeg', '.jpg', '.png', '.webp']);
const STATUS_STEPS = [
  'Uploading image...',
  'Checking image quality...',
  'Segmenting lesion with SegFormer...',
  'Extracting lesion measurements...',
  'Classifying lesion...',
  'Retrieving medical evidence...',
  'Generating explanation...',
  'Generating report...',
];

const COIN_OPTIONS = [
  { key: '', label: 'Select a coin...' },
  { key: 'us_penny', label: 'US Penny (19.05 mm)' },
  { key: 'us_quarter', label: 'US Quarter (24.26 mm)' },
  { key: 'us_dime', label: 'US Dime (17.91 mm)' },
  { key: 'euro_1', label: 'Euro 1 (23.25 mm)' },
  { key: 'euro_2', label: 'Euro 2 (25.75 mm)' },
  { key: 'inr_1', label: 'INR 1 Coin (21.5 mm)' },
  { key: 'inr_2', label: 'INR 2 Coin (25.0 mm)' },
  { key: 'inr_5', label: 'INR 5 Coin (23.0 mm)' },
  { key: 'gbp_1p', label: 'UK 1 Penny (20.3 mm)' },
  { key: 'gbp_1', label: 'UK 1 Pound (22.5 mm)' },
  { key: 'sticker_25mm', label: 'Calibration Sticker 25 mm' },
  { key: 'sticker_20mm', label: 'Calibration Sticker 20 mm' },
];

const GUIDELINES = [
  {
    icon: 'fas fa-camera',
    color: '#6c63ff',
    title: 'Use a rear camera',
    desc: 'Smartphone rear cameras provide higher resolution. Clean the lens before taking the photo.',
  },
  {
    icon: 'fas fa-sun',
    color: '#f59e0b',
    title: 'Good, even lighting',
    desc: 'Avoid glare, flash reflections, or shadows. Natural daylight or a ring light works best.',
  },
  {
    icon: 'fas fa-crosshairs',
    color: '#10b981',
    title: 'Keep the lesion centered and sharp',
    desc: 'Tap the screen to focus on the lesion. Keep the camera parallel to the skin surface.',
  },
  {
    icon: 'fas fa-ban',
    color: '#ef4444',
    title: 'No filters or heavy edits',
    desc: 'Avoid beauty filters, color corrections, or cropping that distorts the lesion.',
  },
  {
    icon: 'fas fa-ruler',
    color: '#3b82f6',
    title: 'Include a scale reference (optional)',
    desc: 'Place a coin or sticker next to the lesion for accurate physical-size estimation.',
  },
  {
    icon: 'fas fa-file-image',
    color: '#8b5cf6',
    title: 'Accepted formats',
    desc: 'JPEG, JPG, PNG or WEBP — maximum 10 MB. Minimum 256 × 256 pixels.',
  },
];

function validateFile(file) {
  const extension = `.${file.name.split('.').pop()?.toLowerCase()}`;
  if (!TYPES.has(file.type) || !EXTENSIONS.has(extension)) {
    return 'Unsupported image format. Please upload a JPEG, JPG, PNG, or WEBP image.';
  }
  if (file.size > MAX_BYTES) return 'Image file is too large. Please upload an image no larger than 10 MB.';
  return null;
}

function decodeImage(file) {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const image = new Image();
    image.onload = () => {
      URL.revokeObjectURL(url);
      const ratio = Math.max(image.width / image.height, image.height / image.width);
      if (image.width < 256 || image.height < 256) reject(new Error('Image resolution is too low for reliable analysis. Please upload a clearer image.'));
      else if (ratio > 4) reject(new Error('The image shape is too extreme. Please upload a closer, well-framed image.'));
      else resolve();
    };
    image.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error('The selected file could not be decoded as an image.'));
    };
    image.src = url;
  });
}

export default function Upload({ onAnalysisComplete }) {
  const showToast = useToast();
  const inputRef = useRef(null);
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [step, setStep] = useState(0);
  const [uploadPercent, setUploadPercent] = useState(0);

  // Guidelines gate
  const [guidelinesAccepted, setGuidelinesAccepted] = useState(false);

  // Scale reference state
  const [scaleMethod, setScaleMethod] = useState('auto');
  const [scaleReferenceKey, setScaleReferenceKey] = useState('');
  const [scaleManualMm, setScaleManualMm] = useState('');

  const selectFile = useCallback(async (candidate) => {
    if (!candidate) return;
    const validationError = validateFile(candidate);
    if (validationError) { setError(validationError); return; }
    try {
      await decodeImage(candidate);
      if (preview) URL.revokeObjectURL(preview);
      setFile(candidate);
      setPreview(URL.createObjectURL(candidate));
      setError(null);
    } catch (decodeError) {
      setError(decodeError.message);
    }
  }, [preview]);

  const clearFile = () => {
    if (preview) URL.revokeObjectURL(preview);
    setFile(null);
    setPreview(null);
    setError(null);
    if (inputRef.current) inputRef.current.value = '';
  };

  const startAnalysis = async () => {
    if (!file) { setError('Please select an image first.'); return; }
    if (scaleMethod === 'coin' && !scaleReferenceKey) {
      setError('Select the coin type visible next to the lesion so its physical diameter is known.');
      return;
    }
    if (scaleMethod === 'manual' && (!scaleManualMm || Number(scaleManualMm) <= 0)) {
      setError('Enter the physical diameter of the circular reference object in millimeters.');
      return;
    }
    setIsAnalyzing(true);
    setStep(0);
    setUploadPercent(0);
    setError(null);

    const timer = window.setInterval(() => {
      setStep((current) => Math.min(current + 1, STATUS_STEPS.length - 1));
    }, 2500);

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('scale_method', scaleMethod);
      if (scaleMethod === 'coin' && scaleReferenceKey) {
        formData.append('scale_reference_key', scaleReferenceKey);
      }
      if (scaleMethod === 'manual' && scaleManualMm) {
        formData.append('scale_reference_mm', scaleManualMm);
      }

      const result = await new Promise((resolve, reject) => {
        const request = new XMLHttpRequest();
        request.open('POST', '/api/analyze');
        request.responseType = 'json';
        request.upload.onprogress = (event) => {
          if (event.lengthComputable) setUploadPercent(Math.round((event.loaded / event.total) * 100));
        };
        request.onload = () => {
          const body = request.response || {};
          if (request.status >= 200 && request.status < 300) resolve(body);
          else reject(new Error(body.detail?.message || 'The image could not be analyzed.'));
        };
        request.onerror = () => reject(new Error('The analysis service could not be reached.'));
        request.send(formData);
      });

      window.clearInterval(timer);
      setStep(STATUS_STEPS.length - 1);
      setUploadPercent(100);
      setIsAnalyzing(false);
      if (result.message) setError(result.message);
      if (result.status === 'completed') showToast('Analysis complete.', 'success');
      onAnalysisComplete(result);
    } catch (requestError) {
      window.clearInterval(timer);
      setIsAnalyzing(false);
      setError(requestError.message);
      showToast(requestError.message, 'error');
    }
  };

  return (
    <section className="page active" id="page-upload">
      <div className="page-header">
        <h1 className="page-title">Upload Skin Lesion</h1>
        <p className="page-subtitle">AI-powered dermoscopic analysis — review the guidelines before you begin.</p>
      </div>

      {!guidelinesAccepted ? (
        /* ── GUIDELINES SCREEN ── */
        <div className="guidelines-screen">
          <div className="guidelines-card">
            <div className="guidelines-intro">
              <div className="guidelines-icon-wrap">
                <i className="fas fa-shield-alt" />
              </div>
              <h2>Before You Upload</h2>
              <p>
                Image quality directly affects the accuracy of AI analysis. Please read
                these guidelines carefully to ensure the best possible results.
              </p>
            </div>

            <ul className="guidelines-list">
              {GUIDELINES.map((g, i) => (
                <li
                  key={g.title}
                  className="guideline-item"
                  style={{ animationDelay: `${i * 80}ms` }}
                >
                  <div className="guideline-icon" style={{ background: `${g.color}18`, color: g.color }}>
                    <i className={g.icon} />
                  </div>
                  <div className="guideline-text">
                    <strong>{g.title}</strong>
                    <span>{g.desc}</span>
                  </div>
                </li>
              ))}
            </ul>

            <div className="guidelines-disclaimer">
              <i className="fas fa-exclamation-triangle" />
              <p>
                <strong>Medical disclaimer:</strong> This is an AI-based research/decision-support tool and does{' '}
                <em>not</em> provide a definitive diagnosis. It does not replace evaluation by a qualified
                dermatologist. Seek professional medical advice for any lesion that is new, changing,
                bleeding, or otherwise concerning.
              </p>
            </div>

            <button
              className="btn btn-primary guidelines-continue-btn"
              onClick={() => setGuidelinesAccepted(true)}
              id="btn-continue-to-upload"
            >
              <i className="fas fa-arrow-right" />
              I understand — Continue to Upload
            </button>
          </div>
        </div>
      ) : (
        /* ── UPLOAD SCREEN ── */
        <>
          {isAnalyzing ? (
            <div className="analysis-card">
              <h2>Analysis in progress</h2>
              <p>{step === 0 && uploadPercent < 100 ? `${STATUS_STEPS[step]} ${uploadPercent}%` : STATUS_STEPS[step]}</p>
              <div className="progress-bar-container"><div className="progress-bar" style={{ width: `${step === 0 ? Math.max(8, uploadPercent) : ((step + 1) / STATUS_STEPS.length) * 100}%` }} /></div>
              <div className="pipeline-stepper" aria-label="Analysis progress">
                {STATUS_STEPS.map((label, index) => (
                  <div className="pipeline-step" key={label}>
                    <div className={`pipeline-step-node ${index < step ? 'completed' : ''} ${index === step ? 'active' : ''}`}>
                      {index < step ? '✓' : index + 1}
                    </div>
                    <div className={`pipeline-step-label ${index === step ? 'active' : ''}`}>{label.replace('...', '')}</div>
                    {index < STATUS_STEPS.length - 1 && <div className={`pipeline-step-connector ${index < step ? 'completed' : ''}`} />}
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="upload-container">
              {/* Back link */}
              <button
                className="guidelines-back-btn"
                onClick={() => setGuidelinesAccepted(false)}
                id="btn-back-to-guidelines"
              >
                <i className="fas fa-chevron-left" /> Back to guidelines
              </button>

              <div className={`upload-zone-card ${dragOver ? 'drag-over' : ''}`} onDragOver={(event) => { event.preventDefault(); setDragOver(true); }} onDragLeave={() => setDragOver(false)} onDrop={(event) => { event.preventDefault(); setDragOver(false); selectFile(event.dataTransfer.files[0]); }}>
                <div className="upload-dropzone" onClick={() => inputRef.current?.click()}>
                  {preview ? <img src={preview} alt="Selected lesion preview" style={{ maxWidth: '100%', maxHeight: '280px', objectFit: 'contain', borderRadius: '8px' }} /> : <div className="upload-dropzone-icon"><i className="fas fa-cloud-upload-alt" /></div>}
                  <h3>{file ? file.name : 'Drag & drop image here'}</h3>
                  <p>{file ? 'Image preview ready for analysis.' : 'or click to browse'}</p>
                  <p className="mt-8 text-muted" style={{ fontSize: '12px' }}>JPEG, JPG, PNG, WEBP · maximum 10 MB</p>
                  <input ref={inputRef} type="file" className="upload-file-input" accept=".jpeg,.jpg,.png,.webp,image/jpeg,image/png,image/webp" onChange={(event) => selectFile(event.target.files[0])} />
                </div>

                {/* Scale Reference Input */}
                {file && (
                  <div className="scale-reference-panel">
                    <div className="scale-reference-header" style={{ cursor: 'pointer' }}>
                      <h4><i className="fas fa-ruler" style={{ color: 'var(--accent-blue)', marginRight: '8px' }} />Reference Scale (Optional)</h4>
                      <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>For physical measurements in mm</span>
                    </div>
                    <div className="scale-options">
                      {[
                        { value: 'auto', label: 'Auto-detect', icon: 'fas fa-search', desc: 'Detect a metric ruler or known reference for mm' },
                        { value: 'coin', label: 'Coin', icon: 'fas fa-coins', desc: 'Select a known coin in the image' },
                        { value: 'manual', label: 'Manual', icon: 'fas fa-pencil-alt', desc: 'Enter known object size' },
                        { value: 'none', label: 'None', icon: 'fas fa-times', desc: 'Skip scale calibration' },
                      ].map((opt) => (
                        <label key={opt.value} className={`scale-option ${scaleMethod === opt.value ? 'active' : ''}`}>
                          <input
                            type="radio"
                            name="scale_method"
                            value={opt.value}
                            checked={scaleMethod === opt.value}
                            onChange={() => setScaleMethod(opt.value)}
                          />
                          <i className={opt.icon} />
                          <div>
                            <strong>{opt.label}</strong>
                            <span>{opt.desc}</span>
                          </div>
                        </label>
                      ))}
                    </div>

                    {scaleMethod === 'coin' && (
                      <div className="scale-input-group">
                        <label htmlFor="coin-select">Coin type visible in the image:</label>
                        <select
                          id="coin-select"
                          value={scaleReferenceKey}
                          onChange={(e) => setScaleReferenceKey(e.target.value)}
                          className="scale-select"
                        >
                          {COIN_OPTIONS.map((c) => (
                            <option key={c.key} value={c.key}>{c.label}</option>
                          ))}
                        </select>
                      </div>
                    )}

                    {scaleMethod === 'manual' && (
                      <div className="scale-input-group">
                        <label htmlFor="manual-mm">Known object diameter (mm):</label>
                        <input
                          id="manual-mm"
                          type="number"
                          min="0.1"
                          step="0.1"
                          placeholder="e.g. 25.0"
                          value={scaleManualMm}
                          onChange={(e) => setScaleManualMm(e.target.value)}
                          className="scale-number-input"
                        />
                        <span className="scale-hint">Enter the diameter in millimeters of any visible reference object.</span>
                      </div>
                    )}
                  </div>
                )}

                {file && <div className="preview-actions" style={{ display: 'flex', justifyContent: 'space-between', marginTop: '16px' }}><button className="btn btn-white btn-sm" onClick={clearFile}>Remove</button><button className="btn btn-white btn-sm" onClick={() => inputRef.current?.click()}>Replace</button><button className="btn btn-primary" onClick={startAnalysis}>Run analysis</button></div>}
              </div>
            </div>
          )}

          {error && <div role="alert" style={{ marginTop: '16px', padding: '12px 16px', color: 'var(--accent-red)', background: 'var(--accent-red-bg)', borderRadius: '8px' }}>{error}{file && !isAnalyzing && <button className="btn btn-sm btn-white" style={{ marginLeft: '12px' }} onClick={startAnalysis}>Retry</button>}</div>}
        </>
      )}
    </section>
  );
}
