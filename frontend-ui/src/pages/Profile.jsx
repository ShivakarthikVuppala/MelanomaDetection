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
    ((user?.first_name?.[0] || '') + (user?.last_name?.[0] || '')).toUpperCase() || 'MD';

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
      errs.email = 'Email address is required.';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email.trim())) {
      errs.email = 'Please enter a valid email address.';
    }
    return errs;
  };

  const handleSave = async (e) => {
    e.preventDefault();
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
      showToast('Profile information updated successfully.', 'success');
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

  return (
    <div className="page-container" id="page-profile">
      {/* Page Header */}
      <div className="page-header-clean">
        <h1 className="page-title-clean">Profile</h1>
        <p className="page-subtitle-clean">
          Manage your personal details and account contact information.
        </p>
      </div>

      <div className="profile-container-narrow">
        <div className="card profile-card">
          {/* Avatar and Info Header */}
          <div className="profile-card-header">
            <div className="profile-avatar-large" aria-hidden="true">
              {initials}
            </div>
            <div className="profile-header-info">
              <h2 className="profile-name">
                {user?.first_name} {user?.last_name}
              </h2>
              <span className="profile-email-badge">
                {user?.email}
              </span>
            </div>

            <div className="profile-header-action">
              {!editing ? (
                <button
                  type="button"
                  className="btn btn-outline btn-sm"
                  onClick={startEdit}
                >
                  <i className="fas fa-pen" aria-hidden="true"></i>
                  <span>Edit Profile</span>
                </button>
              ) : (
                <button
                  type="button"
                  className="btn btn-outline btn-sm"
                  onClick={cancelEdit}
                  disabled={loading}
                >
                  Cancel
                </button>
              )}
            </div>
          </div>

          {/* Form */}
          <form onSubmit={handleSave} noValidate className="profile-form">
            <div className="form-grid-2col">
              <div className="form-group-clean">
                <label className="form-label-clean" htmlFor="profile-first-name">
                  First Name
                </label>
                {editing ? (
                  <>
                    <input
                      id="profile-first-name"
                      type="text"
                      className={`form-input-clean ${errors.first_name ? 'input-error' : ''}`}
                      value={form.first_name}
                      onChange={handleChange('first_name')}
                    />
                    {errors.first_name && (
                      <span className="field-error-text">{errors.first_name}</span>
                    )}
                  </>
                ) : (
                  <div className="form-static-value">{user?.first_name || '—'}</div>
                )}
              </div>

              <div className="form-group-clean">
                <label className="form-label-clean" htmlFor="profile-last-name">
                  Last Name
                </label>
                {editing ? (
                  <>
                    <input
                      id="profile-last-name"
                      type="text"
                      className={`form-input-clean ${errors.last_name ? 'input-error' : ''}`}
                      value={form.last_name}
                      onChange={handleChange('last_name')}
                    />
                    {errors.last_name && (
                      <span className="field-error-text">{errors.last_name}</span>
                    )}
                  </>
                ) : (
                  <div className="form-static-value">{user?.last_name || '—'}</div>
                )}
              </div>
            </div>

            <div className="form-grid-2col">
              <div className="form-group-clean">
                <label className="form-label-clean" htmlFor="profile-email">
                  Email Address
                </label>
                {editing ? (
                  <>
                    <input
                      id="profile-email"
                      type="email"
                      className={`form-input-clean ${errors.email ? 'input-error' : ''}`}
                      value={form.email}
                      onChange={handleChange('email')}
                    />
                    {errors.email && (
                      <span className="field-error-text">{errors.email}</span>
                    )}
                  </>
                ) : (
                  <div className="form-static-value">{user?.email || '—'}</div>
                )}
              </div>

              <div className="form-group-clean">
                <label className="form-label-clean" htmlFor="profile-phone">
                  Phone Number
                </label>
                {editing ? (
                  <>
                    <input
                      id="profile-phone"
                      type="tel"
                      className={`form-input-clean ${errors.phone ? 'input-error' : ''}`}
                      value={form.phone}
                      onChange={handleChange('phone')}
                    />
                    {errors.phone && (
                      <span className="field-error-text">{errors.phone}</span>
                    )}
                  </>
                ) : (
                  <div className="form-static-value">{user?.phone || '—'}</div>
                )}
              </div>
            </div>

            {editing && (
              <div className="profile-form-actions">
                <button
                  type="button"
                  className="btn btn-outline"
                  onClick={cancelEdit}
                  disabled={loading}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={loading}
                >
                  <i className="fas fa-check" aria-hidden="true"></i>
                  <span>{loading ? 'Saving Changes...' : 'Save Profile'}</span>
                </button>
              </div>
            )}
          </form>
        </div>
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
