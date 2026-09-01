import { useState } from 'react';
import { useAuth } from '../components/AuthContext';
import { useToast } from '../components/Toast';

export default function Profile() {
  const { user, updateProfile } = useAuth();
  const showToast = useToast();
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({
    first_name: user?.first_name || '',
    last_name: user?.last_name || '',
    phone: user?.phone || '',
    email: user?.email || '',
  });
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);

  const initials =
    ((user?.first_name?.[0] || '') + (user?.last_name?.[0] || '')).toUpperCase() || 'U';

  const startEdit = () => {
    setForm({
      first_name: user?.first_name || '',
      last_name: user?.last_name || '',
      phone: user?.phone || '',
      email: user?.email || '',
    });
    setErrors({});
    setEditing(true);
  };

  const cancelEdit = () => {
    setEditing(false);
    setErrors({});
  };

  const validate = () => {
    const errs = {};
    if (!form.first_name.trim()) errs.first_name = 'First name is required.';
    if (!form.last_name.trim()) errs.last_name = 'Last name is required.';
    if (!form.phone.trim()) {
      errs.phone = 'Phone number is required.';
    } else if (!/^[+]?[\d\s\-().]{7,20}$/.test(form.phone.trim())) {
      errs.phone = 'Please enter a valid phone number.';
    }
    if (!form.email.trim()) {
      errs.email = 'Email is required.';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email.trim())) {
      errs.email = 'Please enter a valid email address.';
    }
    return errs;
  };

  const handleSave = async () => {
    const errs = validate();
    setErrors(errs);
    if (Object.keys(errs).length > 0) return;

    setLoading(true);
    try {
      await updateProfile({
        first_name: form.first_name.trim(),
        last_name: form.last_name.trim(),
        phone: form.phone.trim(),
        email: form.email.trim(),
      });
      setEditing(false);
      showToast('Profile updated successfully!', 'success');
    } catch (err) {
      showToast(err.message || 'Failed to update profile.', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (field) => (e) => {
    setForm((prev) => ({ ...prev, [field]: e.target.value }));
    if (errors[field]) setErrors((prev) => ({ ...prev, [field]: '' }));
  };

  const createdDate = user?.created_at
    ? new Date(user.created_at).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      })
    : '—';

  return (
    <section className="page active" id="page-profile">
      <div className="page-header">
        <h1 className="page-title">Profile</h1>
        <p className="page-subtitle">View and manage your account information.</p>
      </div>

      <div className="profile-layout">
        {/* Profile Card */}
        <div className="profile-card">
          <div className="profile-card-header">
            <div className="profile-avatar-large">{initials}</div>
            <div className="profile-identity">
              <h2>{user?.first_name} {user?.last_name}</h2>
              <p className="profile-email-display">{user?.email}</p>
              <span className="profile-badge">
                <i className="fas fa-calendar-alt"></i>
                Member since {createdDate}
              </span>
            </div>
          </div>
        </div>

        {/* Profile Details */}
        <div className="profile-details-card">
          <div className="profile-details-header">
            <h3>
              <i className="fas fa-id-card" style={{ color: 'var(--primary)' }}></i>
              Personal Information
            </h3>
            {!editing && (
              <button className="btn btn-outline btn-sm" onClick={startEdit}>
                <i className="fas fa-pen"></i> Edit Profile
              </button>
            )}
          </div>

          {editing ? (
            <div className="profile-edit-form">
              <div className="auth-field-row">
                <div className={`auth-field ${errors.first_name ? 'has-error' : ''}`}>
                  <label htmlFor="profile-first-name">First Name</label>
                  <div className="auth-input-wrap">
                    <i className="fas fa-user auth-input-icon"></i>
                    <input
                      id="profile-first-name"
                      type="text"
                      value={form.first_name}
                      onChange={handleChange('first_name')}
                    />
                  </div>
                  {errors.first_name && <span className="auth-field-error">{errors.first_name}</span>}
                </div>
                <div className={`auth-field ${errors.last_name ? 'has-error' : ''}`}>
                  <label htmlFor="profile-last-name">Last Name</label>
                  <div className="auth-input-wrap">
                    <i className="fas fa-user auth-input-icon"></i>
                    <input
                      id="profile-last-name"
                      type="text"
                      value={form.last_name}
                      onChange={handleChange('last_name')}
                    />
                  </div>
                  {errors.last_name && <span className="auth-field-error">{errors.last_name}</span>}
                </div>
              </div>

              <div className={`auth-field ${errors.phone ? 'has-error' : ''}`}>
                <label htmlFor="profile-phone">Phone Number</label>
                <div className="auth-input-wrap">
                  <i className="fas fa-phone auth-input-icon"></i>
                  <input
                    id="profile-phone"
                    type="tel"
                    value={form.phone}
                    onChange={handleChange('phone')}
                  />
                </div>
                {errors.phone && <span className="auth-field-error">{errors.phone}</span>}
              </div>

              <div className={`auth-field ${errors.email ? 'has-error' : ''}`}>
                <label htmlFor="profile-email">Email Address</label>
                <div className="auth-input-wrap">
                  <i className="fas fa-envelope auth-input-icon"></i>
                  <input
                    id="profile-email"
                    type="email"
                    value={form.email}
                    onChange={handleChange('email')}
                  />
                </div>
                {errors.email && <span className="auth-field-error">{errors.email}</span>}
              </div>

              <div className="profile-edit-actions">
                <button
                  className="btn btn-primary"
                  onClick={handleSave}
                  disabled={loading}
                >
                  {loading ? (
                    <>
                      <span className="auth-spinner"></span>
                      Saving…
                    </>
                  ) : (
                    <>
                      <i className="fas fa-check"></i>
                      Save Changes
                    </>
                  )}
                </button>
                <button className="btn btn-outline" onClick={cancelEdit} disabled={loading}>
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <div className="profile-info-grid">
              <div className="profile-info-item">
                <span className="profile-info-label">
                  <i className="fas fa-user"></i> First Name
                </span>
                <span className="profile-info-value">{user?.first_name}</span>
              </div>
              <div className="profile-info-item">
                <span className="profile-info-label">
                  <i className="fas fa-user"></i> Last Name
                </span>
                <span className="profile-info-value">{user?.last_name}</span>
              </div>
              <div className="profile-info-item">
                <span className="profile-info-label">
                  <i className="fas fa-phone"></i> Phone Number
                </span>
                <span className="profile-info-value">{user?.phone}</span>
              </div>
              <div className="profile-info-item">
                <span className="profile-info-label">
                  <i className="fas fa-envelope"></i> Email
                </span>
                <span className="profile-info-value">{user?.email}</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
