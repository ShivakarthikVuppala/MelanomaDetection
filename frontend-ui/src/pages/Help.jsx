import { useState } from 'react';

export default function Help({ onNavigate }) {
  const [openFaq, setOpenFaq] = useState(null);

  const toggleFaq = (idx) => {
    setOpenFaq(openFaq === idx ? null : idx);
  };

  const faqs = [
    {
      question: 'What is the ABCDE rule for skin health monitoring?',
      answer:
        'The ABCDE rule is a recognized guide to help you identify atypical characteristics in moles: A (Asymmetry) - one half does not match the other; B (Border) - edges are uneven, jagged, or blurred; C (Color) - colors vary with multiple shades of brown, black, red, or white; D (Diameter) - the spot is wider than 6 mm across (about the size of a pencil eraser); E (Evolution) - any noticeable change in size, shape, color, or symptoms like itching over time.',
    },
    {
      question: 'How do I take a good photo for the skin check?',
      answer:
        'Use the rear camera of your smartphone under bright, even, natural light. Tap the screen on the mole to focus sharply. Hold the camera parallel to the skin surface, about 4 to 6 inches away, so the lesion is clearly visible without heavy shadows or reflections.',
    },
    {
      question: 'Does MelaDetect AI provide a medical diagnosis?',
      answer:
        'No. MelaDetect AI is an AI-assisted decision-support tool designed for informational and self-monitoring purposes. It evaluates visual skin patterns based on machine learning models, but it does NOT replace an in-person physical examination, dermoscopy, or biopsy performed by a qualified dermatologist.',
    },
    {
      question: 'How do I download and save my report?',
      answer:
        'Once your skin check is complete, click the "Download PDF" button on the report page or from your History page. A downloadable PDF containing your assessment summary, photo, and ABCDE evaluation will be saved to your device.',
    },
    {
      question: 'What should I do if a check indicates Moderate or High Risk?',
      answer:
        'Do not panic. A high risk assessment means the AI detected atypical features similar to those found in clinical reference databases. You should schedule an in-person examination with a board-certified dermatologist or healthcare provider to have the spot professionally inspected.',
    },
  ];

  return (
    <div className="page-container" id="page-help">
      {/* Page Header */}
      <div className="page-header-clean">
        <h1 className="page-title-clean">Help & Skin Health Guide</h1>
        <p className="page-subtitle-clean">
          Learn how to monitor your skin, capture clear photos, and understand your assessment reports.
        </p>
      </div>

      <div className="help-container-clean">
        {/* Quick Guide Cards */}
        <div className="help-guide-cards-grid">
          <div
            className="card help-guide-card"
            onClick={() => onNavigate && onNavigate('new-check')}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === 'Enter') onNavigate('new-check');
            }}
          >
            <div className="help-guide-icon-circle text-teal">
              <i className="fas fa-camera"></i>
            </div>
            <h2 className="help-guide-card-title">Taking Clear Photos</h2>
            <p className="help-guide-card-desc">
              Tips for natural lighting, parallel camera angles, and sharp focus for the best AI assessment.
            </p>
            <span className="help-guide-link">Start a check →</span>
          </div>

          <div className="card help-guide-card">
            <div className="help-guide-icon-circle text-teal">
              <i className="fas fa-shapes"></i>
            </div>
            <h2 className="help-guide-card-title">The ABCDE Rule</h2>
            <p className="help-guide-card-desc">
              How asymmetry, irregular borders, multiple colors, diameter, and changes over time help identify warning signs.
            </p>
            <span className="help-guide-link">Read guide below ↓</span>
          </div>

          <div
            className="card help-guide-card"
            onClick={() => onNavigate && onNavigate('history')}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === 'Enter') onNavigate('history');
            }}
          >
            <div className="help-guide-icon-circle text-teal">
              <i className="fas fa-file-pdf"></i>
            </div>
            <h2 className="help-guide-card-title">Your Reports & PDF</h2>
            <p className="help-guide-card-desc">
              How to view past assessments, compare lesion photos over time, and export PDF summaries.
            </p>
            <span className="help-guide-link">View history →</span>
          </div>
        </div>

        {/* FAQs Accordion */}
        <section className="card help-faq-card" aria-labelledby="help-faq-title">
          <h2 id="help-faq-title" className="faq-section-title">
            Frequently Asked Questions
          </h2>
          <p className="faq-section-desc">
            Common questions regarding skin lesion assessments and platform privacy.
          </p>

          <div className="faq-list">
            {faqs.map((faq, idx) => {
              const isOpen = openFaq === idx;
              return (
                <div key={idx} className={`faq-item ${isOpen ? 'open' : ''}`}>
                  <button
                    type="button"
                    className="faq-question-btn"
                    onClick={() => toggleFaq(idx)}
                    aria-expanded={isOpen}
                  >
                    <span>{faq.question}</span>
                    <i
                      className={`fas fa-chevron-down faq-chevron ${isOpen ? 'rotated' : ''}`}
                      aria-hidden="true"
                    ></i>
                  </button>
                  {isOpen && (
                    <div className="faq-answer-pane">
                      <p>{faq.answer}</p>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </section>

        {/* Medical Disclaimer */}
        <footer className="medical-disclaimer-box" role="note">
          <p>
            MelaDetect AI provides AI-assisted information and is not a medical diagnosis. If you notice concerning or changing skin lesions, consider consulting a qualified healthcare professional.
          </p>
        </footer>
      </div>
    </div>
  );
}
