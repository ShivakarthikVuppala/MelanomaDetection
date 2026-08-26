import { useState } from 'react';

export default function Help() {
  const [openFaq, setOpenFaq] = useState(null);

  const toggleFaq = (idx) => {
    setOpenFaq(openFaq === idx ? null : idx);
  };

  const faqs = [
    {
      question: 'What is the ABCDE rule for melanoma?',
      answer:
        'The ABCDE rule is a clinical guideline for identifying potential melanoma: A (Asymmetry) - one half doesn\'t match the other; B (Border) - irregular, ragged, or blurred edges; C (Color) - uneven distribution of color; D (Diameter) - larger than 6mm (pencil eraser); E (Evolution) - changes in size, shape, color, or symptoms over time.',
    },
    {
      question: 'What image formats are supported?',
      answer:
        'MelaDetect AI supports JPG, JPEG, and PNG formats. For best results, use high-resolution dermoscopic images (minimum 224×224 pixels). The maximum file size is 10MB.',
    },
    {
      question: 'How does the risk scoring work?',
      answer:
        'The ABCDE scoring assigns points for each criterion: Asymmetry (0-2), Border (0-2), Color (0-3), Diameter (0-2), and Evolution (0-2). The total score ranges from 0 to 11. Scores ≥7 indicate High risk, 4-6 indicate Moderate risk, and below 4 indicate Low risk.',
    },
    {
      question: 'Does this replace a doctor\'s evaluation?',
      answer:
        'No. MelaDetect AI is intended as a decision-support tool for healthcare professionals and individuals. It should not replace clinical judgment. Always correlate results with physical examination and patient history. Consult a dermatologist for any concerning lesions.',
    },
    {
      question: 'Is my data secure?',
      answer:
        'All image processing happens locally in your browser. No images or personal data are uploaded to any server. Your privacy is fully protected.',
    },
    {
      question: 'Can I download my analysis report?',
      answer:
        'Yes! After completing an ABCDE analysis, you can download a comprehensive PDF report. Navigate to the Reports page and click "Download PDF" to save it to your system.',
    },
  ];

  return (
    <section className="page active" id="page-help">
      <div className="page-header">
        <h1 className="page-title">Help Center</h1>
        <p className="page-subtitle">Find answers, tutorials, and support resources.</p>
      </div>

      <div className="help-grid">
        <div className="help-card">
          <div className="help-card-icon"><i className="fas fa-book"></i></div>
          <h3>Getting Started</h3>
          <p>Learn the basics of using MelaDetect AI and the ABCDE rule for skin lesion analysis.</p>
        </div>
        <div className="help-card">
          <div className="help-card-icon"><i className="fas fa-diagnoses"></i></div>
          <h3>ABCDE Guide</h3>
          <p>Understand each criterion — Asymmetry, Border, Color, Diameter, and Evolution — in detail.</p>
        </div>
        <div className="help-card">
          <div className="help-card-icon"><i className="fas fa-file-pdf"></i></div>
          <h3>Download Reports</h3>
          <p>Generate and download PDF reports with full ABCDE analysis and clinical recommendations.</p>
        </div>
        <div className="help-card">
          <div className="help-card-icon"><i className="fas fa-shield-alt"></i></div>
          <h3>Privacy & Security</h3>
          <p>All processing happens locally in your browser. No data is sent to any server.</p>
        </div>
        <div className="help-card">
          <div className="help-card-icon"><i className="fas fa-headset"></i></div>
          <h3>Contact Support</h3>
          <p>Reach our team for technical assistance or clinical questions.</p>
        </div>
        <div className="help-card">
          <div className="help-card-icon"><i className="fas fa-newspaper"></i></div>
          <h3>Release Notes</h3>
          <p>Stay updated with the latest features and improvements.</p>
        </div>
      </div>

      <div className="faq-section">
        <h2>Frequently Asked Questions</h2>
        {faqs.map((faq, idx) => (
          <div className={`faq-item ${openFaq === idx ? 'open' : ''}`} key={idx}>
            <div className="faq-question" onClick={() => toggleFaq(idx)}>
              <span>{faq.question}</span>
              <i className="fas fa-chevron-down"></i>
            </div>
            <div className="faq-answer">
              <p>{faq.answer}</p>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
