import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../components/AuthContext';

export default function Login({ onNavigate }) {
  const { login } = useAuth();
  const navigate = useNavigate();

  const [form, setForm] = useState({ email: '', password: '' });
  const [errors, setErrors] = useState({});
  const [apiError, setApiError] = useState('');
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const handleNav = (target) => {
    if (onNavigate) {
      onNavigate(target);
    } else {
      navigate(target.startsWith('/') ? target : `/${target}`);
    }
  };

  const validate = () => {
    const errs = {};
    if (!form.email.trim()) {
      errs.email = 'Email address is required.';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email.trim())) {
      errs.email = 'Please enter a valid email address.';
    }
    if (!form.password) {
      errs.password = 'Password is required.';
    }
    return errs;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setApiError('');
    const errs = validate();
    setErrors(errs);
    if (Object.keys(errs).length > 0) return;

    setLoading(true);
    try {
      await login(form.email.trim(), form.password);
      handleNav('/home');
    } catch (err) {
      setApiError(err.message || 'Invalid email address or password.');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (field) => (e) => {
    setForm((prev) => ({ ...prev, [field]: e.target.value }));
    if (errors[field]) setErrors((prev) => ({ ...prev, [field]: '' }));
    if (apiError) setApiError('');
  };

  return (
    <div className="auth-page auth-page-minimal">
      <div className="auth-card-minimal card">
        {/* Brand Header */}
        <div className="auth-minimal-header">
          <div className="auth-minimal-logo">
            <i className="fas fa-plus-square"></i>
          </div>
          <h1 className="auth-minimal-brand">
            Mela<span>Detect</span> AI
          </h1>
          <h2 className="auth-minimal-title">Welcome Back</h2>
          <p className="auth-minimal-subtitle">Sign in to your skin health account</p>
        </div>

        {apiError && (
          <div role="alert" className="auth-error-banner">
            <i className="fas fa-exclamation-circle"></i>
            <span>{apiError}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} noValidate className="auth-minimal-form">
          <div className="form-group">
            <label className="form-label" htmlFor="login-email">
              Email Address
            </label>
            <input
              id="login-email"
              type="email"
              className="form-input"
              placeholder="name@example.com"
              value={form.email}
              onChange={handleChange('email')}
              autoComplete="email"
              disabled={loading}
            />
            {errors.email && <div className="form-error">{errors.email}</div>}
          </div>

          <div className="form-group">
            <div className="form-label-row">
              <label className="form-label" htmlFor="login-password">
                Password
              </label>
              <button
                type="button"
                className="btn-link-subtle"
                onClick={() => setShowPassword(!showPassword)}
                tabIndex={-1}
              >
                {showPassword ? 'Hide' : 'Show'}
              </button>
            </div>
            <input
              id="login-password"
              type={showPassword ? 'text' : 'password'}
              className="form-input"
              placeholder="Enter your password"
              value={form.password}
              onChange={handleChange('password')}
              autoComplete="current-password"
              disabled={loading}
            />
            {errors.password && <div className="form-error">{errors.password}</div>}
          </div>

          <button
            type="submit"
            className="btn btn-primary btn-block"
            disabled={loading}
          >
            {loading ? (
              <>
                <i className="fas fa-spinner fa-spin"></i>
                <span>Signing In...</span>
              </>
            ) : (
              'Sign In'
            )}
          </button>
        </form>

        <div className="auth-minimal-footer">
          <span>Don't have an account?</span>{' '}
          <button
            type="button"
            className="btn-link-action"
            onClick={() => handleNav('/signup')}
          >
            Create Account
          </button>
        </div>
      </div>
    </div>
  );
}
