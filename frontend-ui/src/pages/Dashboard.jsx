import { useState } from 'react';

// Educational content for the modals
const abcdeContent = {
  A: {
    title: 'Asymmetry',
    icon: 'fa-shapes',
    desc: 'Melanoma is often asymmetrical, which means the shape isn\'t even. If you were to draw a line through the middle, the two halves wouldn\'t match. Benign moles are usually symmetrical.',
    visualClass: 'vis-asymmetry'
  },
  B: {
    title: 'Border Irregularity',
    icon: 'fa-border-style',
    desc: 'Melanoma lesions often have irregular, scalloped or poorly defined borders. Normal moles usually have smooth, even borders.',
    visualClass: 'vis-border'
  },
  C: {
    title: 'Color Variation',
    icon: 'fa-palette',
    desc: 'Melanoma lesions often have multiple colors or shades of brown, tan, black, or even white, red, or blue. Benign moles are usually a single shade of brown.',
    visualClass: 'vis-color'
  },
  D: {
    title: 'Diameter',
    icon: 'fa-ruler',
    desc: 'Melanomas are usually larger than 6mm (about the size of a pencil eraser) when diagnosed, but they can be smaller. It\'s important to monitor any spot that is growing.',
    visualClass: 'vis-diameter'
  },
  E: {
    title: 'Evolution',
    icon: 'fa-sync-alt',
    desc: 'Any change in size, shape, color, or elevation of a spot on your skin, or any new symptom in it, such as bleeding, itching or crusting, may be a warning sign of melanoma.',
    visualClass: 'vis-evolution'
  }
};

export default function Dashboard({ onNavigate }) {
  const [activeModal, setActiveModal] = useState(null);

  return (
    <section className="page active" id="page-dashboard">
      <div className="hero-section">
        <div className="hero-content">
          <div className="hero-badge">
            <span className="dot"></span>
            AI-Powered Detection
          </div>
          <h1 className="hero-title">
            AI-Powered<br />
            Melanoma Detection<br />
            with <span className="highlight">Explainability</span>
          </h1>
          <p className="hero-description">
            Get accurate risk assessment of skin lesions using the clinical ABCDE rule.
            Upload an image, provide your observations, and receive a comprehensive analysis report.
          </p>
          <div className="hero-actions">
            <button className="btn btn-primary btn-lg" onClick={() => onNavigate('upload')}>
              <i className="fas fa-upload"></i> Upload Image
            </button>
            <button className="btn btn-secondary btn-lg" onClick={() => onNavigate('help')}>
              <i className="fas fa-book-open"></i> Learn More
            </button>
          </div>
        </div>
        
        {/* Added AI Doctor Trust Badge Area */}
        <div className="trust-badge-container">
           <div className="trust-icon-ring">
             <i className="fas fa-user-md trust-icon"></i>
           </div>
           <div className="trust-text">
             <strong>Clinically Inspired AI</strong>
             <span>Decision support you can trust</span>
           </div>
        </div>

        <div className="hero-visual">
          <div className="hero-visual-inner">
            <div className="hero-glow"></div>
            <div className="hero-card-stack">
              <button className="hero-float-card card-1 clickable" onClick={() => setActiveModal('A')}>
                <i className="fas fa-shapes"></i>
                <span>Asymmetry</span>
              </button>
              <button className="hero-float-card card-2 clickable" onClick={() => setActiveModal('B')}>
                <i className="fas fa-border-style"></i>
                <span>Border</span>
              </button>
              <button className="hero-float-card card-3 clickable" onClick={() => setActiveModal('C')}>
                <i className="fas fa-palette"></i>
                <span>Color</span>
              </button>
              <button className="hero-float-card card-4 clickable" onClick={() => setActiveModal('D')}>
                <i className="fas fa-ruler"></i>
                <span>Diameter</span>
              </button>
              <button className="hero-float-card card-5 clickable" onClick={() => setActiveModal('E')}>
                <i className="fas fa-sync-alt"></i>
                <span>Evolution</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="features-grid">
        <div className="feature-card interactive" onClick={() => onNavigate('upload')}>
          <div className="feature-icon teal"><i className="fas fa-brain"></i></div>
          <h3>ABCDE Analysis <i className="fas fa-arrow-right interactive-arrow"></i></h3>
          <p>Comprehensive risk assessment based on the clinical ABCDE rule — Asymmetry, Border, Color, Diameter, and Evolution.</p>
        </div>
        <div className="feature-card">
          <div className="feature-icon blue"><i className="fas fa-microscope"></i></div>
          <h3>Clinical Insights</h3>
          <p>Detailed evaluation of each criterion with risk scoring and evidence-based explanations for every observation.</p>
        </div>
        <div className="feature-card">
          <div className="feature-icon purple"><i className="fas fa-lightbulb"></i></div>
          <h3>Explainable Results</h3>
          <p>Transparent analysis with clear reasoning behind each risk assessment, helping clinicians make informed decisions.</p>
        </div>
        <div className="feature-card interactive" onClick={() => onNavigate('reports')}>
          <div className="feature-icon amber"><i className="fas fa-history"></i></div>
          <h3>Analysis History <i className="fas fa-arrow-right interactive-arrow"></i></h3>
          <p>View your past melanoma analyses and download comprehensive PDF reports with full ABCDE analysis and risk scores.</p>
        </div>
      </div>

      {/* ABCDE Visualizer Modal */}
      {activeModal && (
        <div className="modal-backdrop" onClick={() => setActiveModal(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <button className="modal-close" onClick={() => setActiveModal(null)}>
              <i className="fas fa-times"></i>
            </button>
            <div className="modal-header">
              <div className="modal-icon"><i className={`fas ${abcdeContent[activeModal].icon}`}></i></div>
              <h2>{abcdeContent[activeModal].title}</h2>
            </div>
            
            {/* CSS-based Visualizer instead of external image */}
            <div className={`modal-visualizer ${abcdeContent[activeModal].visualClass}`}>
               <div className="vis-element"></div>
               <div className="vis-element-secondary"></div>
            </div>

            <p className="modal-desc">{abcdeContent[activeModal].desc}</p>
            <button className="btn btn-primary" style={{width: '100%', justifyContent: 'center'}} onClick={() => setActiveModal(null)}>
              Got it
            </button>
          </div>
        </div>
      )}
    </section>
  );
}
