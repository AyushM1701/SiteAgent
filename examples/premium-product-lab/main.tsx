import React, { useState } from 'react';
import { createRoot } from 'react-dom/client';
import PremiumScene from '../../agent/visual_assets/PremiumScene';
import './style.css';

function App() {
  const [tab, setTab] = useState('Compose');
  const [email, setEmail] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const details: Record<string, string> = {
    Compose: 'Bring the pieces together. Shape a clear product story with an expressive visual system.',
    Explore: 'Change your perspective. Explore form, light and movement without losing the clarity of the interface.',
    Refine: 'Keep what matters. Fine-tune spacing, contrast and motion until every detail has a purpose.',
  };
  return <>
    <a className="skip" href="#main">Skip to content</a>
    <header><a className="brand" href="#main"><span className="mark">◈</span> form<span className="brand-dot">®</span></a>
      <nav aria-label="Main navigation"><a href="#system">The system</a><a href="#principles">Principles</a><a className="nav-cta" href="#access">Explore the demo <span>↗</span></a></nav>
    </header>
    <main id="main">
      <section className="hero" aria-labelledby="hero-title">
        <div className="hero-copy"><div className="eyebrow"><i /> THE FUTURE ISN'T FLAT</div>
          <h1 id="hero-title">Think beyond<br />the <em>surface.</em></h1>
          <p>For ideas that refuse to fit the frame. Step into a dimensional workspace where structure meets the unexpected.</p>
          <div className="hero-actions"><a className="button" href="#system">Explore the system <span>↗</span></a><span className="small-note">Thoughtfully composed.<br />Built to be explored.</span></div>
          <div className="hero-meta"><span>01 / CREATIVE INFRASTRUCTURE</span><span>SCROLL TO DISCOVER ↓</span></div>
        </div>
        <div className="hero-art"><div className="art-kicker"><span>FORM STUDY — 001</span><span>LIVE / CSS 3D</span></div><PremiumScene label="Rotating green architectural cube in a dimensional grid" /></div>
      </section>
      <section id="system" className="system" aria-labelledby="system-title"><div className="section-label">THE SYSTEM / 02</div>
        <div className="section-heading"><h2 id="system-title">Complex ideas.<br /><span>Considered simplicity.</span></h2><p>One visual language, from the first sketch to the smallest interaction. Nothing added without a reason.</p></div>
        <div className="workspace"><div className="workspace-tabs" role="tablist" aria-label="Product workflow">{Object.keys(details).map((name, index) => <button key={name} id={`tab-${name}`} role="tab" aria-selected={tab === name} aria-controls="workflow-panel" tabIndex={tab === name ? 0 : -1} onClick={() => setTab(name)} onKeyDown={event => { const keys = Object.keys(details); const move = event.key === 'ArrowRight' ? 1 : event.key === 'ArrowLeft' ? -1 : 0; if (move) {event.preventDefault(); const next = keys[(index + move + keys.length) % keys.length]; setTab(next); document.getElementById(`tab-${next}`)?.focus();}}}><span>0{index + 1}</span>{name}<span>↗</span></button>)}</div>
          <div id="workflow-panel" role="tabpanel" aria-labelledby={`tab-${tab}`} tabIndex={0} className="workspace-panel"><div className="orb" aria-hidden="true" /><div><span className="eyebrow">SPACE FOR POSSIBILITY</span><h3>{tab} with intention.</h3><p>{details[tab]}</p></div></div>
        </div>
      </section>
      <section id="principles" className="principles" aria-labelledby="principles-title"><div className="section-label">OUR PRINCIPLES / 03</div><h2 id="principles-title">Less friction.<br />More forward.</h2><div className="principle-grid">{[['01','Clarity first','A confident hierarchy. Readable type. A clear next step at every turn.'],['02','Depth with purpose','Dimensional details invite exploration without getting between you and the work.'],['03','Motion that respects you','Pause the artwork at any time. Reduced-motion preferences are honored automatically.']].map(([number,title,text]) => <article key={number}><span>{number} /</span><h3>{title}</h3><p>{text}</p></article>)}</div></section>
      <section id="access" className="access"><div><div className="eyebrow">MAKE ROOM FOR WHAT'S NEXT</div><h2>Your next idea<br />starts here.</h2></div><form onSubmit={event => {event.preventDefault(); setSubmitted(true);}}><label htmlFor="email">Try the local interaction demo</label><div className="input-row"><input id="email" type="email" required placeholder="you@studio.com" value={email} onChange={event => {setEmail(event.target.value); setSubmitted(false);}}/><button className="button" type="submit">Try it ↗</button></div><p role="status">{submitted ? 'Demo complete. Your email was not sent or stored.' : 'Local demonstration only. No signup or network submission.'}</p></form></section>
    </main><footer><a className="brand" href="#main">◈ form</a><span>A REACTAGENT VISUAL REFERENCE / NOT MODEL-GENERATED</span><a href="#main">Back to top ↑</a></footer>
  </>;
}
createRoot(document.getElementById('root')!).render(<App />);
