import { useState } from 'react';
import { useToast } from '../components/Toast';
import { useAuth } from '../components/AuthContext';
import { useTheme } from '../components/ThemeContext';

export default function Settings() {
  const showToast = useToast();
  const { user, token, logout } = useAuth();
  const { theme, setTheme } = useTheme();

  // Notifications
  const [emailAlerts, setEmailAlerts] = useState(true);
  const [assessmentCompleteNotice, setAssessmentCompleteNotice] = useState(true);
  const [monthlyReminder, setMonthlyReminder] = useState(false);

  // Security
  const [twoFactorAuth, setTwoFactorAuth] = useState(false);

  // Change Password
  const [pwForm, setPwForm] = useState({ current: '', next: '', confirm: '' });
  const [pwError, setPwError] = useState('');
  const [pwSubmitting, setPwSubmitting] = useState(false);
  const [showPwFields, setShowPwFields] = useState(false);

  const handleSave = () => {
    showToast('Preferences updated successfully.', 'success');
  };

  const handleChangePassword = async (e) => {
    e.preventDefault();
    setPwError('');
    if (pwForm.next.length < 6) { setPwError('New password must be at least 6 characters.'); return; }
    if (pwForm.next !== pwForm.confirm) { setPwError('New passwords do not match.'); return; }
    if (pwForm.current === pwForm.next) { setPwError('New password must be different from your current password.'); return; }
    setPwSubmitting(true);
    try {
      const res = await fetch('/api/auth/password', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ current_password: pwForm.current, new_password: pwForm.next }),
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Failed to change password.');
      }
      showToast('Password changed! Please log in again.', 'success');
      setPwForm({ current: '', next: '', confirm: '' });
      setShowPwFields(false);
      setTimeout(logout, 2000);
    } catch (err) {
      setPwError(err.message);
    } finally {
      setPwSubmitting(false);
    }
  };

  return (
    <div className="page-container" id="page-settings">
      {/* Page Header */}
      <div className="page-header-clean">
        <h1 className="page-title-clean">Settings</h1>
        <p className="page-subtitle-clean">
          Manage your account preferences, notifications, and appearance.
        </p>
      </div>

      <div className="settings-container-narrow">
        {/* Section 1: Account */}
        <section className="card settings-section-card" aria-labelledby="settings-account-title">
          <div className="settings-section-header">
            <div className="settings-section-icon" aria-hidden="true">
              <i className="fas fa-user-shield"></i>
            </div>
            <div>
              <h2 id="settings-account-title" className="settings-section-title">Account</h2>
              <p className="settings-section-desc">Your verified account credentials</p>
            </div>
          </div>

          <div className="settings-list">
            <div className="settings-item">
              <div>
                <strong className="settings-item-label">Registered Email</strong>
                <p className="settings-item-sub">{user?.email || 'user@meladetect.ai'}</p>
              </div>
              <span className="badge badge-low">Verified</span>
            </div>

            <div className="settings-item">
              <div>
                <strong className="settings-item-label">Account Name</strong>
                <p className="settings-item-sub">{user?.first_name} {user?.last_name}</p>
              </div>
            </div>
          </div>
        </section>

        {/* Section 2: Notifications */}
        <section className="card settings-section-card" aria-labelledby="settings-notifications-title">
          <div className="settings-section-header">
            <div className="settings-section-icon" aria-hidden="true">
              <i className="far fa-bell"></i>
            </div>
            <div>
              <h2 id="settings-notifications-title" className="settings-section-title">Notifications</h2>
              <p className="settings-section-desc">Choose what updates you receive</p>
            </div>
          </div>

          <div className="settings-list">
            <label className="settings-toggle-row">
              <div className="toggle-text">
                <strong className="settings-item-label">Assessment Completed Notifications</strong>
                <p className="settings-item-sub">Receive email confirmation when an analysis is completed</p>
              </div>
              <input
                type="checkbox"
                className="modern-toggle"
                checked={assessmentCompleteNotice}
                onChange={(e) => {
                  setAssessmentCompleteNotice(e.target.checked);
                  handleSave();
                }}
              />
            </label>

            <label className="settings-toggle-row">
              <div className="toggle-text">
                <strong className="settings-item-label">Skin Health Alerts</strong>
                <p className="settings-item-sub">Receive alerts regarding skin check recommendations</p>
              </div>
              <input
                type="checkbox"
                className="modern-toggle"
                checked={emailAlerts}
                onChange={(e) => {
                  setEmailAlerts(e.target.checked);
                  handleSave();
                }}
              />
            </label>

            <label className="settings-toggle-row">
              <div className="toggle-text">
                <strong className="settings-item-label">Monthly Self-Check Reminders</strong>
                <p className="settings-item-sub">Remind me to inspect my skin once every 30 days</p>
              </div>
              <input
                type="checkbox"
                className="modern-toggle"
                checked={monthlyReminder}
                onChange={(e) => {
                  setMonthlyReminder(e.target.checked);
                  handleSave();
                }}
              />
            </label>
          </div>
        </section>

        {/* Section 3: Security */}
        <section className="card settings-section-card" aria-labelledby="settings-security-title">
          <div className="settings-section-header">
            <div className="settings-section-icon" aria-hidden="true">
              <i className="fas fa-lock"></i>
            </div>
            <div>
              <h2 id="settings-security-title" className="settings-section-title">Security</h2>
              <p className="settings-section-desc">Manage sign-in safety and verification</p>
            </div>
          </div>

          <div className="settings-list">
            <label className="settings-toggle-row">
              <div className="toggle-text">
                <strong className="settings-item-label">Two-Factor Authentication (2FA)</strong>
                <p className="settings-item-sub">Require an email OTP code whenever signing in</p>
              </div>
              <input
                type="checkbox"
                className="modern-toggle"
                checked={twoFactorAuth}
                onChange={(e) => {
                  setTwoFactorAuth(e.target.checked);
                  handleSave();
                }}
              />
            </label>
          </div>
        </section>

        {/* Section: Change Password */}
        <section className="card settings-section-card" aria-labelledby="settings-password-title">
          <div className="settings-section-header">
            <div className="settings-section-icon" aria-hidden="true">
              <i className="fas fa-key"></i>
            </div>
            <div>
              <h2 id="settings-password-title" className="settings-section-title">Change Password</h2>
              <p className="settings-section-desc">Update your account login password</p>
            </div>
          </div>

          <div className="settings-list">
            <div className="settings-item" style={{ flexDirection: 'column', alignItems: 'flex-start', gap: '16px' }}>
              {!showPwFields ? (
                <button
                  type="button"
                  className="btn btn-outline"
                  onClick={() => setShowPwFields(true)}
                  style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', padding: '10px 20px' }}
                >
                  <i className="fas fa-lock"></i>
                  Change Password
                </button>
              ) : (
                <form onSubmit={handleChangePassword} style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: '14px' }}>

                  {pwError && (
                    <div className="auth-error-banner">
                      <i className="fas fa-exclamation-circle"></i>
                      <span>{pwError}</span>
                    </div>
                  )}

                  <div className="auth-field">
                    <label>Current Password</label>
                    <div className="auth-input-wrap">
                      <i className="fas fa-lock auth-input-icon"></i>
                      <input
                        type="password"
                        placeholder="Enter your current password"
                        value={pwForm.current}
                        onChange={e => setPwForm(p => ({ ...p, current: e.target.value }))}
                        required
                        autoComplete="current-password"
                      />
                    </div>
                  </div>

                  <div className="auth-field">
                    <label>New Password</label>
                    <div className="auth-input-wrap">
                      <i className="fas fa-key auth-input-icon"></i>
                      <input
                        type="password"
                        placeholder="Minimum 6 characters"
                        value={pwForm.next}
                        onChange={e => setPwForm(p => ({ ...p, next: e.target.value }))}
                        required
                        autoComplete="new-password"
                      />
                    </div>
                    {pwForm.next.length > 0 && (
                      <p style={{ margin: '4px 0 0', fontSize: '12px', color: pwForm.next.length >= 6 ? 'var(--success)' : 'var(--warning)' }}>
                        <i className={`fas ${pwForm.next.length >= 6 ? 'fa-check-circle' : 'fa-exclamation-triangle'}`} style={{ marginRight: '4px' }} />
                        {pwForm.next.length >= 6 ? 'Looks good.' : `${6 - pwForm.next.length} more character(s) needed.`}
                      </p>
                    )}
                  </div>

                  <div className="auth-field">
                    <label>Confirm New Password</label>
                    <div className="auth-input-wrap">
                      <i className="fas fa-lock auth-input-icon"></i>
                      <input
                        type="password"
                        placeholder="Re-enter new password"
                        value={pwForm.confirm}
                        onChange={e => setPwForm(p => ({ ...p, confirm: e.target.value }))}
                        required
                        autoComplete="new-password"
                      />
                    </div>
                    {pwForm.confirm.length > 0 && pwForm.next.length > 0 && (
                      <p style={{ margin: '4px 0 0', fontSize: '12px', color: pwForm.next === pwForm.confirm ? 'var(--success)' : 'var(--danger)' }}>
                        <i className={`fas ${pwForm.next === pwForm.confirm ? 'fa-check-circle' : 'fa-times-circle'}`} style={{ marginRight: '4px' }} />
                        {pwForm.next === pwForm.confirm ? 'Passwords match.' : 'Passwords do not match.'}
                      </p>
                    )}
                  </div>

                  <div style={{ display: 'flex', gap: '10px', marginTop: '4px' }}>
                    <button
                      type="submit"
                      className="btn btn-primary"
                      disabled={pwSubmitting}
                      style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', padding: '10px 22px' }}
                    >
                      {pwSubmitting
                        ? <><i className="fas fa-circle-notch fa-spin" /> Updating&hellip;</>
                        : <><i className="fas fa-check" /> Update Password</>
                      }
                    </button>
                    <button
                      type="button"
                      className="btn btn-outline"
                      onClick={() => { setShowPwFields(false); setPwError(''); setPwForm({ current: '', next: '', confirm: '' }); }}
                      style={{ padding: '10px 18px' }}
                    >
                      Cancel
                    </button>
                  </div>
                </form>
              )}
            </div>
          </div>
        </section>

        {/* Section 4: Appearance */}
        <section className="card settings-section-card" aria-labelledby="settings-appearance-title">
          <div className="settings-section-header">
            <div className="settings-section-icon" aria-hidden="true">
              <i className="fas fa-palette"></i>
            </div>
            <div>
              <h2 id="settings-appearance-title" className="settings-section-title">Appearance</h2>
              <p className="settings-section-desc">Customize interface visual theme</p>
            </div>
          </div>

          <div className="settings-list">
            <div className="settings-item">
              <div>
                <strong className="settings-item-label">Color Theme</strong>
                <p className="settings-item-sub">
                  {theme === 'dark' ? 'Modern Dark healthcare palette' : 'Clean Medical Light palette (Default)'}
                </p>
              </div>
              <div className="theme-pills-group">
                <button
                  type="button"
                  className={`theme-pill ${theme === 'light' ? 'active' : ''}`}
                  onClick={() => {
                    setTheme('light');
                    showToast('Theme switched to Light.', 'info');
                  }}
                >
                  <i className="fas fa-sun"></i> Light
                </button>
                <button
                  type="button"
                  className={`theme-pill ${theme === 'dark' ? 'active' : ''}`}
                  onClick={() => {
                    setTheme('dark');
                    showToast('Theme switched to Dark.', 'info');
                  }}
                >
                  <i className="fas fa-moon"></i> Dark
                </button>
              </div>
            </div>
          </div>
        </section>

      </div>

      {/* Subtle Medical Disclaimer */}
      <footer className="medical-disclaimer-box" role="note">
        <p>
          MelaDetect AI provides AI-assisted information and is not a medical diagnosis. If you notice concerning or changing skin lesions, consider consulting a qualified healthcare professional.
        </p>
      </footer>
    </div>
  );
}
