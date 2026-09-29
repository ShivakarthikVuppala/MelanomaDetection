import { useState, useEffect } from 'react';
import { useAuth } from '../../components/AuthContext';

const FONT = "'Inter', 'Segoe UI', system-ui, sans-serif";

function Toast({ msg, type, onDone }) {
  useEffect(() => { const t = setTimeout(onDone, 3000); return () => clearTimeout(t); }, []);
  return (
    <div style={{
      position: 'fixed', bottom: '28px', right: '28px', zIndex: 9999,
      background: type === 'success' ? '#0F766E' : '#dc2626',
      color: '#fff', padding: '14px 22px', borderRadius: '12px',
      fontSize: '14px', fontWeight: 600,
      boxShadow: '0 8px 24px rgba(0,0,0,0.18)',
      display: 'flex', alignItems: 'center', gap: '10px', fontFamily: FONT,
    }}>
      <i className={type === 'success' ? 'fas fa-check-circle' : 'fas fa-times-circle'} />
      {msg}
    </div>
  );
}

function Field({ label, icon, ...inputProps }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
      <label style={{ fontSize: '13px', fontWeight: 600, color: 'var(--adm-text-2)', fontFamily: FONT }}>{label}</label>
      <div style={{ position: 'relative' }}>
        <i className={`fas ${icon}`} style={{
          position: 'absolute', left: '14px', top: '50%',
          transform: 'translateY(-50%)',
          color: 'var(--adm-text-muted)', fontSize: '14px', pointerEvents: 'none',
        }} />
        <input
          {...inputProps}
          style={{
            width: '100%', padding: '11px 14px 11px 40px',
            border: '1px solid var(--adm-input-border)',
            background: 'var(--adm-input-bg)',
            color: 'var(--adm-text)',
            borderRadius: '10px', fontSize: '14px',
            fontFamily: FONT, outline: 'none', boxSizing: 'border-box',
            transition: 'border-color .15s, box-shadow .15s',
          }}
          onFocus={e => { e.target.style.borderColor = '#0F766E'; e.target.style.boxShadow = '0 0 0 3px rgba(15,118,110,0.12)'; }}
          onBlur={e => { e.target.style.borderColor = 'var(--adm-input-border)'; e.target.style.boxShadow = 'none'; }}
        />
      </div>
    </div>
  );
}

export default function AdminSettings() {
  const { token, logout } = useAuth();
  const [toast, setToast] = useState(null);
  const showToast = (msg, type = 'success') => setToast({ msg, type });

  const [isDarkMode, setIsDarkMode] = useState(() => {
    const saved = localStorage.getItem('theme');
    if (saved) return saved === 'dark';
    return window.matchMedia?.('(prefers-color-scheme: dark)').matches ?? false;
  });

  useEffect(() => {
    const root = document.documentElement;
    if (isDarkMode) {
      root.classList.add('dark');
      root.setAttribute('data-theme', 'dark');
      localStorage.setItem('theme', 'dark');
    } else {
      root.classList.remove('dark');
      root.setAttribute('data-theme', 'light');
      localStorage.setItem('theme', 'light');
    }
  }, [isDarkMode]);

  const toggleTheme = (theme) => {
    setIsDarkMode(theme === 'dark');
    showToast(`Switched to ${theme} mode`, 'success');
  };

  const [form, setForm] = useState({ current: '', next: '', confirm: '' });
  const [submitting, setSubmitting] = useState(false);
  const [pwError, setPwError] = useState('');

  const handleChangePassword = async (e) => {
    e.preventDefault();
    setPwError('');
    if (form.next.length < 6) { setPwError('New password must be at least 6 characters.'); return; }
    if (form.next !== form.confirm) { setPwError('New passwords do not match.'); return; }
    if (form.current === form.next) { setPwError('New password must be different from current.'); return; }
    setSubmitting(true);
    try {
      const res = await fetch('/api/admin/password', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ current_password: form.current, new_password: form.next }),
      });
      if (!res.ok) { const d = await res.json(); throw new Error(d.detail || 'Failed.'); }
      showToast('Password changed! Logging you out…', 'success');
      setForm({ current: '', next: '', confirm: '' });
      setTimeout(logout, 1800);
    } catch (err) {
      setPwError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const card = {
    background: 'var(--adm-surface)',
    border: '1px solid var(--adm-border)',
    borderRadius: '16px', padding: '28px',
    boxShadow: 'var(--adm-shadow)',
    marginBottom: '20px',
  };

  const sectionHead = {
    display: 'flex', alignItems: 'center', gap: '10px',
    fontSize: '16px', fontWeight: 800, color: 'var(--adm-text)',
    marginBottom: '6px', fontFamily: FONT,
  };

  const sectionSub = {
    fontSize: '13.5px', color: 'var(--adm-text-3)',
    marginBottom: '22px', lineHeight: 1.5, fontFamily: FONT,
  };

  return (
    <div style={{ padding: '36px 40px', fontFamily: FONT, maxWidth: '680px', color: 'var(--adm-text)', background: 'var(--adm-bg)', minHeight: '100%' }}>
      <div style={{ marginBottom: '32px' }}>
        <h1 style={{ fontSize: '26px', fontWeight: 800, margin: 0, color: 'var(--adm-text)' }}>Admin Settings</h1>
        <p style={{ color: 'var(--adm-text-3)', margin: '6px 0 0', fontSize: '14.5px' }}>
          Manage system appearance and account security.
        </p>
      </div>

      {/* Appearance */}
      <div style={card}>
        <div style={sectionHead}>
          <div style={{ width: '34px', height: '34px', borderRadius: '9px', background: '#f0fdfa', color: '#0F766E', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '16px' }}>
            <i className="fas fa-palette" />
          </div>
          Appearance
        </div>
        <p style={sectionSub}>Customize the look and feel of the Admin Dashboard.</p>
        <div style={{ display: 'flex', gap: '12px' }}>
          {[
            { label: 'Light Mode', icon: 'fa-sun',  theme: 'light', active: !isDarkMode },
            { label: 'Dark Mode',  icon: 'fa-moon', theme: 'dark',  active: isDarkMode  },
          ].map(({ label, icon, theme, active }) => (
            <button key={theme} onClick={() => toggleTheme(theme)} style={{
              flex: 1, padding: '14px', borderRadius: '12px',
              border: active ? '2px solid #0F766E' : `1px solid var(--adm-border)`,
              background: active ? '#f0fdfa' : 'var(--adm-surface)',
              color: active ? '#0F766E' : 'var(--adm-text-3)',
              fontSize: '14px', fontWeight: active ? 700 : 500,
              cursor: 'pointer', display: 'flex', alignItems: 'center',
              justifyContent: 'center', gap: '8px', fontFamily: FONT,
              transition: 'all .15s',
            }}>
              <i className={`fas ${icon}`} style={{ fontSize: '16px' }} />
              {label}
              {active && <span style={{ marginLeft: '4px', width: '8px', height: '8px', borderRadius: '50%', background: '#0F766E', display: 'inline-block' }} />}
            </button>
          ))}
        </div>
      </div>

      {/* Security — Change Password */}
      <div style={card}>
        <div style={sectionHead}>
          <div style={{ width: '34px', height: '34px', borderRadius: '9px', background: '#fef2f2', color: '#dc2626', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '16px' }}>
            <i className="fas fa-shield-alt" />
          </div>
          Security
        </div>
        <p style={sectionSub}>Change your administrative password. You will be logged out after a successful change.</p>

        {pwError && (
          <div style={{
            background: '#fef2f2', border: '1px solid #fecaca',
            borderRadius: '10px', padding: '12px 16px', marginBottom: '20px',
            color: '#b91c1c', fontSize: '13.5px',
            display: 'flex', alignItems: 'center', gap: '9px', fontFamily: FONT,
          }}>
            <i className="fas fa-exclamation-circle" />{pwError}
          </div>
        )}

        <form onSubmit={handleChangePassword} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <Field label="Current Password"   icon="fa-lock" type="password" placeholder="Enter current password"   value={form.current} onChange={e => setForm(p => ({ ...p, current: e.target.value }))} required />
          <Field label="New Password"        icon="fa-key"  type="password" placeholder="Minimum 6 characters"     value={form.next}    onChange={e => setForm(p => ({ ...p, next: e.target.value }))}    required />
          {form.next.length > 0 && (
            <div style={{ fontSize: '12.5px', color: form.next.length >= 6 ? '#0F766E' : '#f59e0b', fontFamily: FONT }}>
              <i className={`fas ${form.next.length >= 6 ? 'fa-check-circle' : 'fa-exclamation-triangle'}`} style={{ marginRight: '5px' }} />
              {form.next.length >= 6 ? 'Password length is good.' : `Need ${6 - form.next.length} more character(s).`}
            </div>
          )}
          <Field label="Confirm New Password" icon="fa-lock" type="password" placeholder="Re-enter new password"   value={form.confirm} onChange={e => setForm(p => ({ ...p, confirm: e.target.value }))} required />

          <button type="submit" disabled={submitting} style={{
            marginTop: '4px', padding: '13px', borderRadius: '11px',
            border: 'none', background: submitting ? '#94a3b8' : '#dc2626',
            color: '#fff', fontSize: '14.5px', fontWeight: 700,
            cursor: submitting ? 'not-allowed' : 'pointer',
            fontFamily: FONT, display: 'flex', alignItems: 'center',
            justifyContent: 'center', gap: '9px', transition: 'background .15s',
          }}
            onMouseEnter={e => { if (!submitting) e.currentTarget.style.background = '#b91c1c'; }}
            onMouseLeave={e => { if (!submitting) e.currentTarget.style.background = '#dc2626'; }}
          >
            {submitting
              ? <><i className="fas fa-circle-notch fa-spin" /> Changing…</>
              : <><i className="fas fa-key" /> Change Password</>}
          </button>
        </form>
      </div>

      {toast && <Toast msg={toast.msg} type={toast.type} onDone={() => setToast(null)} />}
    </div>
  );
}
