import { useEffect } from 'react';

export default function SignOutModal({ isOpen, onClose, onConfirm }) {
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      className="modal-backdrop"
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(15, 23, 42, 0.6)',
        backdropFilter: 'blur(4px)',
        zIndex: 1000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '16px',
        animation: 'fadeIn 0.15s ease-out',
      }}
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="signout-modal-title"
    >
      <div
        className="card"
        style={{
          width: '100%',
          maxWidth: '400px',
          padding: '28px 24px',
          textAlign: 'center',
          borderRadius: 'var(--radius-md)',
          boxShadow: 'var(--shadow-lg)',
          backgroundColor: 'var(--surface)',
          border: '1px solid var(--border)',
          transform: 'scale(1)',
          animation: 'modalScale 0.18s ease-out',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div
          style={{
            width: '48px',
            height: '48px',
            borderRadius: '50%',
            backgroundColor: 'var(--danger-bg)',
            color: 'var(--danger)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 16px',
            fontSize: '20px',
          }}
          aria-hidden="true"
        >
          <i className="fas fa-sign-out-alt"></i>
        </div>

        <h3
          id="signout-modal-title"
          style={{
            fontSize: '18px',
            fontWeight: 600,
            color: 'var(--text-primary)',
            marginBottom: '8px',
          }}
        >
          Sign Out
        </h3>

        <p
          style={{
            fontSize: '14px',
            color: 'var(--text-secondary)',
            marginBottom: '24px',
            lineHeight: 1.5,
          }}
        >
          Are you sure you want to sign out?
        </p>

        <div
          style={{
            display: 'flex',
            gap: '12px',
            justifyContent: 'center',
          }}
        >
          <button
            type="button"
            className="btn btn-outline"
            style={{
              flex: 1,
              height: '40px',
              fontSize: '14px',
              fontWeight: 500,
            }}
            onClick={onClose}
          >
            No
          </button>
          <button
            type="button"
            className="btn"
            style={{
              flex: 1,
              height: '40px',
              fontSize: '14px',
              fontWeight: 600,
              backgroundColor: 'var(--danger)',
              color: '#FFFFFF',
              borderColor: 'var(--danger)',
            }}
            onClick={onConfirm}
          >
            Yes, Sign Out
          </button>
        </div>
      </div>
    </div>
  );
}
