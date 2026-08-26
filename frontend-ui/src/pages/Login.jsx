import { useState } from 'react';
import { useAuth } from '../components/AuthContext';

export default function Login({ onNavigate }) {
  const { login } = useAuth();
  const [form, setForm] = useState({ email: '', password: '' });
  const [errors, setErrors] = useState({});
  const [apiError, setApiError] = useState('');
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const validate = () => {
    const errs = {};
    if (!form.email.trim()) {
      errs.email = 'Email is required.';
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
      // Auth context handles redirect via isAuthenticated change
    } catch (err) {
      setApiError(err.message || 'Invalid email or password.');
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
    <div className="auth-page">
      <div className="auth-bg-pattern"></div>
      <div className="auth-container">
        {/* Left panel — branding */}
        <div className="auth-brand-panel">
          <div className="auth-brand-content">
            <div className="auth-brand-icon">🔬</div>
            <h1 className="auth-brand-title">
              Mela<span>Detect</span> AI
            </h1>
            <p className="auth-brand-desc">
              AI-powered melanoma detection with clinical ABCDE analysis.
              Get accurate risk assessments and explainable results.
            </p>
            <div className="auth-brand-features">
              <div className="auth-brand-feature">
                <i className="fas fa-shield-alt"></i>
                <span>Secure & Private</span>
              </div>
              <div className="auth-brand-feature">
                <i className="fas fa-brain"></i>
                <span>AI-Powered Analysis</span>
              </div>
              <div className="auth-brand-feature">
                <i className="fas fa-file-medical-alt"></i>
                <span>Comprehensive Reports</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right panel — form */}
        <div className="auth-form-panel">
          <div className="auth-form-wrapper">
            <div className="auth-form-header">
              <h2>Welcome back</h2>
              <p>Sign in to your account to continue</p>
            </div>

            {apiError && (
              <div className="auth-error-banner">
                <i className="fas fa-exclamation-circle"></i>
                <span>{apiError}</span>
              </div>
            )}

            <form className="auth-form" onSubmit={handleSubmit} noValidate>
              <div className={`auth-field ${errors.email ? 'has-error' : ''}`}>
                <label htmlFor="login-email">Email Address</label>
                <div className="auth-input-wrap">
                  <i className="fas fa-envelope auth-input-icon"></i>
                  <input
                    id="login-email"
                    type="email"
                    placeholder="you@example.com"
                    value={form.email}
                    onChange={handleChange('email')}
                    autoComplete="email"
                    autoFocus
                  />
                </div>
                {errors.email && <span className="auth-field-error">{errors.email}</span>}
              </div>

              <div className={`auth-field ${errors.password ? 'has-error' : ''}`}>
                <label htmlFor="login-password">Password</label>
                <div className="auth-input-wrap">
                  <i className="fas fa-lock auth-input-icon"></i>
                  <input
                    id="login-password"
                    type={showPassword ? 'text' : 'password'}
                    placeholder="Enter your password"
                    value={form.password}
                    onChange={handleChange('password')}
                    autoComplete="current-password"
                  />
                  <button
                    type="button"
                    className="auth-password-toggle"
                    onClick={() => setShowPassword(!showPassword)}
                    tabIndex={-1}
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                  >
                    <i className={`fas ${showPassword ? 'fa-eye-slash' : 'fa-eye'}`}></i>
                  </button>
                </div>
                {errors.password && <span className="auth-field-error">{errors.password}</span>}
              </div>

              <button type="submit" className="btn btn-primary auth-submit" disabled={loading}>
                {loading ? (
                  <>
                    <span className="auth-spinner"></span>
                    Signing in…
                  </>
                ) : (
                  <>
                    <i className="fas fa-sign-in-alt"></i>
                    Sign In
                  </>
                )}
              </button>
            </form>

            <div className="auth-footer">
              <p>
                Don't have an account?{' '}
                <button className="auth-link" onClick={() => onNavigate('signup')}>
                  Create Account
                </button>
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
