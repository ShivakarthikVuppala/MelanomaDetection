import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../components/AuthContext';
import { useToast } from '../components/Toast';
import { useNotification } from '../components/NotificationContext';

function formatDate(iso) {
  if (!iso) return 'Unknown date';
  try {
    return new Date(iso).toLocaleDateString('en-US', {
      month: 'short', day: 'numeric', year: 'numeric',
    });
  } catch { return 'Unknown date'; }
}

function getRiskInfo(prediction, confidence) {
  const conf = confidence || 0;
  const isMelanoma = prediction === 'Melanoma';
  if (isMelanoma) {
    if (conf >= 80) return { label: 'High Risk', cls: 'badge-high' };
    return { label: 'Moderate Risk', cls: 'badge-moderate' };
  }
  if (conf < 65) return { label: 'Moderate Risk', cls: 'badge-moderate' };
  return { label: 'Low Risk', cls: 'badge-low' };
}

function PatientCard({ patient, onSelect, isSelected }) {
  const isRunning = Boolean(patient.is_running);
  const risk = (!isRunning && patient.last_prediction)
    ? getRiskInfo(patient.last_prediction, patient.last_confidence)
    : null;

  return (
    <div
      className={`card patient-card ${isSelected ? 'patient-card--active' : ''}`}
      onClick={() => onSelect(patient)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') onSelect(patient); }}
      aria-pressed={isSelected}
      aria-label={`Patient ${patient.patient_name}, ID ${patient.patient_id}`}
    >
      <div className="patient-card-left">
        <div className="patient-avatar" aria-hidden="true">
          <i className="fas fa-user-circle"></i>
        </div>
        <div className="patient-meta">
          <strong className="patient-name">{patient.patient_name}</strong>
          <span className="patient-id-tag">ID: {patient.patient_id}</span>
        </div>
      </div>
      <div className="patient-card-right">
        <div className="patient-stats">
          <span className="patient-upload-count">
            <i className="fas fa-images" aria-hidden="true"></i>
            {patient.upload_count} upload{patient.upload_count !== 1 ? 's' : ''}
          </span>
          <span className="patient-last-date">{formatDate(patient.last_upload)}</span>
        </div>
        {isRunning ? (
          <span className="risk-badge badge-running">
            <i className="fas fa-spinner fa-spin" aria-hidden="true"></i>
            Still Running
          </span>
        ) : risk ? (
          <span className={`risk-badge ${risk.cls}`}>{risk.label}</span>
        ) : null}
        <i className="fas fa-chevron-right patient-chevron" aria-hidden="true"></i>
      </div>
    </div>
  );
}

function RunningVisitTimelineItem({ notification, patient }) {
  return (
    <div className="visit-timeline-item visit-timeline-item--running">
      <div className="visit-timeline-connector">
        <div className="visit-dot visit-dot--running"></div>
        <div className="visit-line"></div>
      </div>
      <div className="visit-card card visit-card--running">
        <div className="visit-card-header">
          <div>
            <span className="visit-number" style={{ color: '#0284c7', fontWeight: 600 }}>
              <i className="fas fa-satellite-dish" style={{ marginRight: 6 }}></i>
              Active Assessment
            </span>
            <span className="visit-date">Started just now</span>
          </div>
          <div className="visit-badges">
            <span className="risk-badge badge-running">
              <i className="fas fa-circle-notch fa-spin" style={{ marginRight: 6 }}></i>
              Still Running...
            </span>
          </div>
        </div>
        <div className="visit-card-body">
          <div className="visit-image-box">
            {notification.imagePreview ? (
              <img
                src={notification.imagePreview}
                alt="Running scan preview"
                className="visit-thumb"
              />
            ) : (
              <div className="visit-thumb-fallback" style={{ display: 'flex' }}>
                <i className="fas fa-microscope fa-spin text-teal" style={{ fontSize: 24 }}></i>
              </div>
            )}
          </div>
          <div className="visit-details">
            <div className="visit-detail-row">
              <span className="visit-detail-label">Status</span>
              <span className="visit-detail-value" style={{ color: '#0284c7', fontWeight: 600 }}>
                Diagnostic Pipeline Running
              </span>
            </div>
            <div className="visit-detail-row">
              <span className="visit-detail-label">Patient</span>
              <span className="visit-detail-value">
                {patient.patient_name} (<code>{patient.patient_id}</code>)
              </span>
            </div>
            {notification.lesionLocation && (
              <div className="visit-detail-row">
                <span className="visit-detail-label">Location</span>
                <span className="visit-detail-value">{notification.lesionLocation}</span>
              </div>
            )}
            <div style={{ marginTop: 8 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--text-secondary)' }}>
                <span>Multi-agent assessment & evolution tracking</span>
                <span>In progress...</span>
              </div>
              <div className="running-progress-track">
                <div className="running-progress-bar"></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function VisitTimelineItem({ visit, index, total, onView }) {
  const isRunning = visit.status === 'running';
  const risk = !isRunning ? getRiskInfo(visit.prediction, visit.confidence) : null;
  const isFailed = ['failed', 'error', 'image_quality_insufficient'].includes(visit.status);

  // If failed, do NOT show
  if (isFailed) return null;

  return (
    <div className="visit-timeline-item">
      <div className="visit-timeline-connector">
        <div className={`visit-dot ${isRunning ? 'visit-dot--running' : 'visit-dot--ok'}`}></div>
        {index < total - 1 && <div className="visit-line"></div>}
      </div>
      <div className={`visit-card card ${isRunning ? 'visit-card--running' : ''}`}>
        <div className="visit-card-header">
          <div>
            <span className="visit-number">Visit {index + 1}</span>
            <span className="visit-date">{formatDate(visit.timestamp)}</span>
          </div>
          <div className="visit-badges">
            {isRunning ? (
              <span className="risk-badge badge-running">
                <i className="fas fa-circle-notch fa-spin"></i>
                Still Running
              </span>
            ) : (
              <>
                <span className={`risk-badge ${risk.cls}`}>{risk.label}</span>
                <span className="visit-confidence">
                  {Math.round(visit.confidence || 0)}% confidence
                </span>
              </>
            )}
          </div>
        </div>
        <div className="visit-card-body">
          <div className="visit-image-box">
            <img
              src={`/static/uploads/${visit.analysis_id}.png`}
              alt={`Visit ${index + 1} lesion`}
              className="visit-thumb"
              onError={(e) => {
                e.target.style.display = 'none';
                e.target.nextSibling.style.display = 'flex';
              }}
            />
            <div className="visit-thumb-fallback" style={{ display: 'none' }}>
              <i className="far fa-image"></i>
            </div>
          </div>
          <div className="visit-details">
            <div className="visit-detail-row">
              <span className="visit-detail-label">Prediction</span>
              <span className="visit-detail-value">{isRunning ? 'Still Running...' : (visit.prediction || '—')}</span>
            </div>
            <div className="visit-detail-row">
              <span className="visit-detail-label">Analysis ID</span>
              <code className="visit-analysis-id">{visit.analysis_id}</code>
            </div>
            <div className="visit-detail-row">
              <span className="visit-detail-label">Record Type</span>
              <span className="visit-detail-value" style={{ color: isRunning ? '#0284c7' : '#10b981', fontWeight: 500 }}>
                {isRunning ? 'Processing…' : 'Stored Record'}
              </span>
            </div>
          </div>
        </div>
        {!isRunning && (
          <div className="visit-card-actions">
            <button type="button" className="btn btn-sm btn-outline" onClick={() => onView(visit.analysis_id)}>
              <i className="fas fa-file-waveform" aria-hidden="true"></i>
              <span>View Full Report</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default function PatientHistory() {
  const navigate = useNavigate();
  const { token } = useAuth();
  const { notification } = useNotification();
  const showToast = useToast();

  const [patients, setPatients] = useState([]);
  const [loadingPatients, setLoadingPatients] = useState(true);
  const [search, setSearch] = useState('');
  const [selectedPatient, setSelectedPatient] = useState(null);
  const [visits, setVisits] = useState([]);
  const [loadingVisits, setLoadingVisits] = useState(false);

  // Active running report detection from global notification context
  const isReportRunning = notification?.status === 'running' && Boolean(notification?.patient_id);
  const runningPatientId = notification?.patient_id;
  const runningPatientName = notification?.patient_name;

  const loadPatients = useCallback(async () => {
    if (!token) return;
    try {
      const res = await fetch('/api/patients', {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error('Failed to load patients');
      const data = await res.json();
      setPatients(Array.isArray(data) ? data : []);
    } catch (e) {
      showToast('Could not load patient list.', 'error');
      console.warn(e);
    } finally {
      setLoadingPatients(false);
    }
  }, [token, showToast]);

  useEffect(() => {
    loadPatients();
  }, [loadPatients]);

  // When a report status transitions (e.g. running -> completed), refresh patient list and visits
  useEffect(() => {
    if (notification?.status === 'completed') {
      loadPatients();
      if (selectedPatient) {
        selectPatient(selectedPatient);
      }
    }
  }, [notification?.status]);

  const selectPatient = useCallback(async (patient) => {
    setSelectedPatient(patient);
    setVisits([]);
    setLoadingVisits(true);
    try {
      const res = await fetch(`/api/patients/${encodeURIComponent(patient.patient_id)}/history`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error('Failed to load patient history');
      const data = await res.json();
      // Ensure failed records are never shown
      const cleanList = Array.isArray(data)
        ? data.filter((v) => !['failed', 'error', 'image_quality_insufficient'].includes(v.status))
        : [];
      setVisits(cleanList);
    } catch (e) {
      showToast('Could not load patient history.', 'error');
      console.warn(e);
    } finally {
      setLoadingVisits(false);
    }
  }, [token, showToast]);

  // Synthesize patient list to reflect running report
  const displayPatients = [...patients];
  if (isReportRunning && runningPatientId) {
    const existingIdx = displayPatients.findIndex(
      (p) => p.patient_id?.toLowerCase() === runningPatientId.toLowerCase()
    );
    if (existingIdx >= 0) {
      displayPatients[existingIdx] = {
        ...displayPatients[existingIdx],
        is_running: true,
      };
    } else {
      displayPatients.unshift({
        patient_id: runningPatientId,
        patient_name: runningPatientName || 'New Patient',
        upload_count: 1,
        last_upload: notification?.timestamp || new Date().toISOString(),
        last_prediction: 'Still Running...',
        last_confidence: null,
        is_running: true,
        status: 'running',
      });
    }
  }

  // Filter patients by search query
  const filteredPatients = displayPatients.filter((p) => {
    if (!search.trim()) return true;
    const q = search.toLowerCase();
    return p.patient_name?.toLowerCase().includes(q) || p.patient_id?.toLowerCase().includes(q);
  });

  // Automatically select the active running patient if nothing is selected
  useEffect(() => {
    if (!selectedPatient && isReportRunning && displayPatients.length > 0) {
      const target = displayPatients.find(
        (p) => p.patient_id?.toLowerCase() === runningPatientId?.toLowerCase()
      );
      if (target) {
        setSelectedPatient(target);
      }
    }
  }, [selectedPatient, isReportRunning, runningPatientId, displayPatients]);

  // Is the currently selected patient having an active report running?
  const selectedHasRunningReport =
    isReportRunning &&
    selectedPatient?.patient_id?.toLowerCase() === runningPatientId?.toLowerCase();

  // Filter out any failed visits: show as stored record if succeeded, else if gets failed don't show
  const storedVisits = visits.filter(
    (v) => !['failed', 'error', 'image_quality_insufficient'].includes(v.status)
  );

  return (
    <div className="page-container" id="page-patient-history">
      <div className="page-header-clean page-header-split">
        <div>
          <h1 className="page-title-clean">Patient Records</h1>
          <p className="page-subtitle-clean">
            Longitudinal upload history, active assessments, and stored records for each patient.
          </p>
        </div>
        <button type="button" className="btn btn-primary" onClick={() => navigate('/upload')}>
          <i className="fas fa-cloud-arrow-up" aria-hidden="true"></i>
          <span>Upload for Patient</span>
        </button>
      </div>

      <div className="patient-history-layout">
        {/* Left: patient list */}
        <div className="patient-list-col">
          <div className="card" style={{ padding: '14px' }}>
            <div className="filter-search-box" style={{ marginBottom: 0 }}>
              <i className="fas fa-search filter-search-icon" aria-hidden="true"></i>
              <input
                type="text"
                className="filter-search-input"
                placeholder="Search patients by name or ID…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                aria-label="Search patients"
              />
            </div>
          </div>

          <div className="patient-list-scroll" aria-label="Patient list">
            {loadingPatients ? (
              <div className="card loading-state-card" style={{ marginTop: 16 }}>
                <i className="fas fa-spinner fa-spin text-teal loading-spinner-icon" aria-hidden="true"></i>
                <p className="loading-state-text">Loading patients…</p>
              </div>
            ) : filteredPatients.length === 0 ? (
              <div className="card empty-records-card" style={{ marginTop: 16 }}>
                <div className="empty-records-icon" aria-hidden="true">
                  <i className="fas fa-user-slash"></i>
                </div>
                <h2 className="empty-records-title">
                  {patients.length === 0 ? 'No patients yet' : 'No matching patients'}
                </h2>
                <p className="empty-records-desc">
                  {patients.length === 0
                    ? 'Upload an image for a patient to see them listed here.'
                    : 'Try a different search term.'}
                </p>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 12 }}>
                {filteredPatients.map((p) => (
                  <PatientCard
                    key={p.patient_id}
                    patient={p}
                    onSelect={selectPatient}
                    isSelected={selectedPatient?.patient_id === p.patient_id}
                  />
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right: visit timeline */}
        <div className="patient-timeline-col">
          {!selectedPatient ? (
            <div className="card patient-timeline-empty">
              <div className="patient-timeline-empty-icon" aria-hidden="true">
                <i className="fas fa-timeline"></i>
              </div>
              <h2 className="patient-timeline-empty-title">Select a patient</h2>
              <p className="patient-timeline-empty-desc">
                Choose a patient from the list to view their complete upload history,
                running assessments, and stored diagnostic records.
              </p>
            </div>
          ) : (
            <>
              <div className="card patient-timeline-header">
                <div className="patient-timeline-header-left">
                  <div className="patient-avatar patient-avatar--lg" aria-hidden="true">
                    <i className="fas fa-user-circle"></i>
                  </div>
                  <div>
                    <h2 className="patient-timeline-name">{selectedPatient.patient_name}</h2>
                    <span className="patient-id-tag">ID: {selectedPatient.patient_id}</span>
                  </div>
                </div>
                <div className="patient-timeline-stats">
                  <div className="patient-stat">
                    <span className="patient-stat-value">
                      {selectedPatient.upload_count + (selectedHasRunningReport ? 1 : 0)}
                    </span>
                    <span className="patient-stat-label">Total Uploads</span>
                  </div>
                  <div className="patient-stat">
                    <span className="patient-stat-value">
                      {selectedHasRunningReport ? 'Running…' : formatDate(selectedPatient.last_upload)}
                    </span>
                    <span className="patient-stat-label">Last Visit</span>
                  </div>
                </div>
              </div>

              {loadingVisits && !selectedHasRunningReport ? (
                <div className="card loading-state-card" style={{ marginTop: 16 }}>
                  <i className="fas fa-spinner fa-spin text-teal loading-spinner-icon" aria-hidden="true"></i>
                  <p className="loading-state-text">Loading visit history…</p>
                </div>
              ) : storedVisits.length === 0 && !selectedHasRunningReport ? (
                <div className="card empty-records-card" style={{ marginTop: 16 }}>
                  <h2 className="empty-records-title">No stored records yet</h2>
                  <p className="empty-records-desc">No successful stored visits found for this patient.</p>
                </div>
              ) : (
                <div
                  className="visit-timeline"
                  aria-label={`Visit history for ${selectedPatient.patient_name}`}
                >
                  {/* If report is currently running, show details and 'still running' at top */}
                  {selectedHasRunningReport && (
                    <RunningVisitTimelineItem
                      notification={notification}
                      patient={selectedPatient}
                    />
                  )}

                  {/* Stored records if succeeded (failed records are never rendered) */}
                  {storedVisits.map((v, i) => (
                    <VisitTimelineItem
                      key={v.analysis_id}
                      visit={v}
                      index={i}
                      total={storedVisits.length}
                      onView={(aid) => navigate(`/results/${aid}`)}
                    />
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      </div>

      <footer className="medical-disclaimer-box" role="note">
        <p>
          MelaDetect AI provides AI-assisted information and is not a medical diagnosis.
          Always consult a qualified healthcare professional for clinical decisions.
        </p>
      </footer>
    </div>
  );
}
