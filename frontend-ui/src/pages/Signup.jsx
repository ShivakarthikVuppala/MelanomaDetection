import { useState, useRef } from 'react';
import { useAuth } from '../components/AuthContext';
import { useToast } from '../components/Toast';

export default function Signup({ onNavigate }) {
  const { signup, verifyEmail, resendOtp } = useAuth();
  const showToast = useToast();
  
  // View state: 'form', 'verify'
  const [step, setStep] = useState('form');
  const [registeredEmail, setRegisteredEmail] = useState('');
  
  const [form, setForm] = useState({
    first_name: '',
    last_name: '',
    phone: '',
    email: '',
    password: '',
    confirm_password: '',
  });
  
  // OTP state
  const [otp, setOtp] = useState('');
  const [otpError, setOtpError] = useState('');
  
  const [errors, setErrors] = useState({});
  const [apiError, setApiError] = useState('');
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  
  // Duplicate email modal
  const [showDuplicateModal, setShowDuplicateModal] = useState(false);

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

    if (!form.password) {
      errs.password = 'Password is required.';
    } else if (form.password.length < 6) {
      errs.password = 'Password must be at least 6 characters.';
    }

    if (!form.confirm_password) {
      errs.confirm_password = 'Please confirm your password.';
    } else if (form.password !== form.confirm_password) {
      errs.confirm_password = 'Passwords do not match.';
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
      const data = await signup({
        first_name: form.first_name.trim(),
        last_name: form.last_name.trim(),
        phone: form.phone.trim(),
        email: form.email.trim(),
        password: form.password,
      });
      setRegisteredEmail(data.email);
      setStep('verify');
      showToast('Verification code sent!', 'success');
    } catch (err) {
      if (err.message.includes('already exists') || err.message.includes('Already Used')) {
        setShowDuplicateModal(true);
      } else {
        setApiError(err.message || 'Registration failed. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleVerify = async (e) => {
    e.preventDefault();
    setOtpError('');
    if (otp.length !== 6) {
      setOtpError('Please enter a 6-digit code.');
      return;
    }

    setLoading(true);
    try {
      await verifyEmail(registeredEmail, otp);
      showToast('Email verified successfully! Please sign in.', 'success');
      onNavigate('login');
    } catch (err) {
      setOtpError(err.message || 'Invalid verification code.');
    } finally {
      setLoading(false);
    }
  };

  const handleResend = async () => {
    setLoading(true);
    try {
      await resendOtp(registeredEmail);
      showToast('A new verification code has been sent.', 'success');
      setOtpError('');
      setOtp('');
    } catch (err) {
      setOtpError(err.message || 'Failed to resend code.');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (field) => (e) => {
    setForm((prev) => ({ ...prev, [field]: e.target.value }));
    if (errors[field]) setErrors((prev) => ({ ...prev, [field]: '' }));
    if (apiError) setApiError('');
  };

  const maskEmail = (email) => {
    if (!email) return '';
    const [name, domain] = email.split('@');
    return `${name.charAt(0)}***@${domain}`;
  };

  return (
    <div className="auth-page">
      <div className="auth-bg-pattern"></div>
      <div className="auth-container">
        
        {/* Duplicate Email Modal */}
        {showDuplicateModal && (
          <div style={{
            position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', zIndex: 1000,
            display: 'flex', alignItems: 'center', justifyContent: 'center'
          }}>
            <div style={{
              background: 'var(--bg-card)', padding: '32px', borderRadius: 'var(--radius-lg)',
              width: '100%', maxWidth: '400px', boxShadow: 'var(--shadow-xl)',
              animation: 'slideUp 0.3s ease-out'
            }}>
              <h3 style={{ fontSize: '20px', fontWeight: '700', marginBottom: '16px', color: 'var(--text-primary)' }}>
                Email Already Used
              </h3>
              <p style={{ fontSize: '15px', color: 'var(--text-secondary)', marginBottom: '24px', lineHeight: '1.5' }}>
                This email is already associated with an account.
                <br/><br/>
                Please sign in instead.
              </p>
              <div style={{ display: 'flex', gap: '12px' }}>
                <button 
                  className="btn btn-outline" 
                  onClick={() => setShowDuplicateModal(false)}
                  style={{ flex: 1 }}
                >
                  Cancel
                </button>
                <button 
                  className="btn btn-primary" 
                  onClick={() => onNavigate('login')}
                  style={{ flex: 1, justifyContent: 'center' }}
                >
                  Sign In
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Left panel — branding */}
        <div className="auth-brand-panel">
          <div className="auth-brand-content">
            <div className="auth-brand-icon">🔬</div>
            <h1 className="auth-brand-title">
              Mela<span>Detect</span> AI
            </h1>
            <p className="auth-brand-desc">
              Create your account to access AI-powered melanoma risk assessment
              with clinical ABCDE analysis and comprehensive reports.
            </p>
            <div className="auth-brand-features">
              <div className="auth-brand-feature">
                <i className="fas fa-user-shield"></i>
                <span>Your data stays secure</span>
              </div>
              <div className="auth-brand-feature">
                <i className="fas fa-history"></i>
                <span>Track analysis history</span>
              </div>
              <div className="auth-brand-feature">
                <i className="fas fa-download"></i>
                <span>Export PDF reports</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right panel — form */}
        <div className="auth-form-panel">
          <div className="auth-form-wrapper">
            
            {step === 'form' ? (
              <>
                <div className="auth-form-header">
                  <h2>Create Account</h2>
                  <p>Register to start using MelaDetect AI</p>
                </div>

                {apiError && (
                  <div className="auth-error-banner">
                    <i className="fas fa-exclamation-circle"></i>
                    <span>{apiError}</span>
                  </div>
                )}

                <form className="auth-form" onSubmit={handleSubmit} noValidate>
                  <div className="auth-field-row">
                    <div className={`auth-field ${errors.first_name ? 'has-error' : ''}`}>
                      <label htmlFor="signup-first-name">First Name</label>
                      <div className="auth-input-wrap">
                        <i className="fas fa-user auth-input-icon"></i>
                        <input
                          id="signup-first-name"
                          type="text"
                          placeholder="First name"
                          value={form.first_name}
                          onChange={handleChange('first_name')}
                          autoComplete="given-name"
                          autoFocus
                        />
                      </div>
                      {errors.first_name && <span className="auth-field-error">{errors.first_name}</span>}
                    </div>

                    <div className={`auth-field ${errors.last_name ? 'has-error' : ''}`}>
                      <label htmlFor="signup-last-name">Last Name</label>
                      <div className="auth-input-wrap">
                        <i className="fas fa-user auth-input-icon"></i>
                        <input
                          id="signup-last-name"
                          type="text"
                          placeholder="Last name"
                          value={form.last_name}
                          onChange={handleChange('last_name')}
                          autoComplete="family-name"
                        />
                      </div>
                      {errors.last_name && <span className="auth-field-error">{errors.last_name}</span>}
                    </div>
                  </div>

                  <div className={`auth-field ${errors.phone ? 'has-error' : ''}`}>
                    <label htmlFor="signup-phone">Phone Number</label>
                    <div className="auth-input-wrap">
                      <i className="fas fa-phone auth-input-icon"></i>
                      <input
                        id="signup-phone"
                        type="tel"
                        placeholder="+1 (555) 123-4567"
                        value={form.phone}
                        onChange={handleChange('phone')}
                        autoComplete="tel"
                      />
                    </div>
                    {errors.phone && <span className="auth-field-error">{errors.phone}</span>}
                  </div>

                  <div className={`auth-field ${errors.email ? 'has-error' : ''}`}>
                    <label htmlFor="signup-email">Email Address</label>
                    <div className="auth-input-wrap">
                      <i className="fas fa-envelope auth-input-icon"></i>
                      <input
                        id="signup-email"
                        type="email"
                        placeholder="you@example.com"
                        value={form.email}
                        onChange={handleChange('email')}
                        autoComplete="email"
                      />
                    </div>
                    {errors.email && <span className="auth-field-error">{errors.email}</span>}
                  </div>

                  <div className="auth-field-row">
                    <div className={`auth-field ${errors.password ? 'has-error' : ''}`}>
                      <label htmlFor="signup-password">Password</label>
                      <div className="auth-input-wrap">
                        <i className="fas fa-lock auth-input-icon"></i>
                        <input
                          id="signup-password"
                          type={showPassword ? 'text' : 'password'}
                          placeholder="Min. 6 characters"
                          value={form.password}
                          onChange={handleChange('password')}
                          autoComplete="new-password"
                        />
                        <button
                          type="button"
                          className="auth-password-toggle"
                          onClick={() => setShowPassword(!showPassword)}
                          tabIndex={-1}
                        >
                          <i className={`fas ${showPassword ? 'fa-eye-slash' : 'fa-eye'}`}></i>
                        </button>
                      </div>
                      {errors.password && <span className="auth-field-error">{errors.password}</span>}
                    </div>

                    <div className={`auth-field ${errors.confirm_password ? 'has-error' : ''}`}>
                      <label htmlFor="signup-confirm">Confirm Password</label>
                      <div className="auth-input-wrap">
                        <i className="fas fa-lock auth-input-icon"></i>
                        <input
                          id="signup-confirm"
                          type={showConfirm ? 'text' : 'password'}
                          placeholder="Re-enter password"
                          value={form.confirm_password}
                          onChange={handleChange('confirm_password')}
                          autoComplete="new-password"
                        />
                        <button
                          type="button"
                          className="auth-password-toggle"
                          onClick={() => setShowConfirm(!showConfirm)}
                          tabIndex={-1}
                        >
                          <i className={`fas ${showConfirm ? 'fa-eye-slash' : 'fa-eye'}`}></i>
                        </button>
                      </div>
                      {errors.confirm_password && (
                        <span className="auth-field-error">{errors.confirm_password}</span>
                      )}
                    </div>
                  </div>

                  <button type="submit" className="btn btn-primary auth-submit" disabled={loading}>
                    {loading ? (
                      <>
                        <span className="auth-spinner"></span>
                        Creating Account…
                      </>
                    ) : (
                      <>
                        <i className="fas fa-user-plus"></i>
                        Create Account
                      </>
                    )}
                  </button>
                </form>

                <div className="auth-footer">
                  <p>
                    Already have an account?{' '}
                    <button className="auth-link" onClick={() => onNavigate('login')}>
                      Sign In
                    </button>
                  </p>
                </div>
              </>
            ) : (
              <>
                <div className="auth-form-header">
                  <h2>Verify Your Email</h2>
                  <p>
                    We sent a 6-digit verification code to:<br/>
                    <strong style={{ color: 'var(--text-primary)' }}>{maskEmail(registeredEmail)}</strong>
                  </p>
                </div>

                {otpError && (
                  <div className="auth-error-banner" style={{ marginBottom: '24px' }}>
                    <i className="fas fa-exclamation-circle"></i>
                    <span>{otpError}</span>
                  </div>
                )}

                <form className="auth-form" onSubmit={handleVerify}>
                  <div className="auth-field">
                    <div className="auth-input-wrap">
                      <i className="fas fa-key auth-input-icon"></i>
                      <input
                        type="text"
                        maxLength="6"
                        placeholder="Enter 6-digit code"
                        value={otp}
                        onChange={(e) => {
                          setOtp(e.target.value.replace(/\D/g, ''));
                          setOtpError('');
                        }}
                        style={{ fontSize: '18px', letterSpacing: '4px', textAlign: 'center', paddingLeft: '40px' }}
                        autoFocus
                      />
                    </div>
                  </div>

                  <button type="submit" className="btn btn-primary auth-submit" disabled={loading || otp.length !== 6}>
                    {loading ? (
                      <>
                        <span className="auth-spinner"></span>
                        Verifying…
                      </>
                    ) : (
                      <>
                        <i className="fas fa-check-circle"></i>
                        Verify Email
                      </>
                    )}
                  </button>
                </form>

                <div className="auth-footer" style={{ marginTop: '24px' }}>
                  <p style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    <span>Didn't receive the code?</span>
                    <button 
                      className="btn btn-outline" 
                      onClick={handleResend}
                      disabled={loading}
                      style={{ margin: '0 auto' }}
                    >
                      Resend Code
                    </button>
                  </p>
                </div>
              </>
            )}

          </div>
        </div>
      </div>
    </div>
  );
}
