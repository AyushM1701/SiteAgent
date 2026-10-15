import React, {useEffect, useRef, useState} from 'react';
import './App.css';

const features = [
  ['01', 'A canvas for your process', 'Connect a trigger, an action, and a decision. Make the next step clear.', '↗'],
  ['02', 'AI where it helps', 'Design steps to summarize a document, organize an idea, or draft a response.', '✧'],
  ['03', 'People stay in control', 'Build an approval step into the moments that need a human decision.', '◎'],
  ['04', 'Follow every handoff', 'See where information comes from and where your workflow takes it next.', '⌁'],
  ['05', 'Start with a pattern', 'Explore repeatable workflow concepts and adapt them to your team.', '▦'],
  ['06', 'Make room to improve', 'Review the shape of a process before you put it into motion.', '↻'],
];
const plans = [
  {name:'Starter', price:20, description:'Explore your first workflow.', items:['Personal workspace concept', 'Core workflow building blocks', 'Community learning resources']},
  {name:'Team', price:50, description:'Bring your process together.', items:['Shared workspace concept', 'Approval step templates', 'Workflow collaboration concept']},
  {name:'Scale', price:100, description:'Plan a connected operation.', items:['Multiple workspace concept', 'Advanced process templates', 'Guided setup concept']},
];

export default function App(){
  const [open,setOpen]=useState(false);
  const [annual,setAnnual]=useState(false);
  const [selected,setSelected]=useState('');
  const menu=useRef<HTMLButtonElement>(null);
  useEffect(()=>{
    if(!open)return;
    const close=(event:KeyboardEvent)=>{if(event.key==='Escape'){setOpen(false);menu.current?.focus();}};
    window.addEventListener('keydown',close);
    return()=>window.removeEventListener('keydown',close);
  },[open]);
  return <div className="nf-root">
    <a className="nf-skip" href="#main">Skip to content</a>
    <header className="nf-header">
      <a className="nf-brand" href="#hero" aria-label="NexaFlow home"><span aria-hidden="true">✳</span>NexaFlow</a>
      <button ref={menu} className="nf-menu" aria-label="Navigation menu" aria-expanded={open} aria-controls="nf-navigation" onClick={()=>setOpen(!open)}>{open?'Close':'Menu'} <span aria-hidden="true">{open?'×':'☰'}</span></button>
      <nav id="nf-navigation" className={`nf-nav ${open?'nf-nav-open':''}`} aria-label="Main navigation">
        <a href="#features" onClick={()=>setOpen(false)}>Why NexaFlow</a><a href="#pricing" onClick={()=>setOpen(false)}>Pricing</a>
        <a className="nf-button nf-button-small" href="#pricing" onClick={()=>setOpen(false)}>Explore plans <span aria-hidden="true">↗</span></a>
      </nav>
    </header>
    <main id="main">
      <section id="hero" className="nf-hero nf-container">
        <div className="nf-eyebrow"><span/> A clearer way to work</div>
        <h1>Your ambition.<br/><span className="nf-gradient">In full flow.</span></h1>
        <p className="nf-intro">Less passing work around. More moving it forward.<br className="nf-desktop-break"/> Imagine your team's next chapter with AI workflow automation.</p>
        <div className="nf-hero-actions"><a className="nf-button" href="#pricing">Find your flow <span aria-hidden="true">↗</span></a><a className="nf-text-link" href="#features">Explore the possibilities <span aria-hidden="true">↓</span></a></div>
        <div className="nf-workflow" role="img" aria-label="Illustrative workflow: new request, AI summary, human approval, ready for handoff">
          <div className="nf-canvas-header"><span><i/> Workflow canvas</span><span>Product concept · Preview</span></div>
          <div className="nf-nodes">
            <div className="nf-node"><b>01 / TRIGGER</b><span>New request</span><small>Start with a signal</small></div>
            <span className="nf-connector" aria-hidden="true">→</span>
            <div className="nf-node nf-node-ai"><b>02 / INTELLIGENCE</b><span>AI summary <i>✧</i></span><small>Find the useful details</small></div>
            <span className="nf-connector" aria-hidden="true">→</span>
            <div className="nf-node"><b>03 / APPROVAL</b><span>Your team's call</span><small>Keep a human in the loop</small></div>
          </div>
          <div className="nf-canvas-footer"><span>Built around the way you think.</span><span>Next: ready for handoff ↗</span></div>
        </div>
        <p className="nf-caption">An original interface concept. No live automation or integrations are connected.</p>
      </section>
      <section id="features" className="nf-features nf-container">
        <div className="nf-section-heading"><div><p className="nf-eyebrow">Designed for the in-between</p><h2>Connect the work.<br/>Keep the intention.</h2></div><p>Six ideas for making everyday processes<br/>feel a little more effortless.</p></div>
        <div className="nf-feature-grid">{features.map(([number,title,description,icon])=><article className="nf-feature" key={number}><div className="nf-feature-top"><span>{number}</span><span aria-hidden="true">{icon}</span></div><h3>{title}</h3><p>{description}</p></article>)}</div>
      </section>
      <section id="pricing" className="nf-pricing nf-container">
        <div className="nf-pricing-heading"><p className="nf-eyebrow">A little structure. More possibility.</p><h2>Choose your starting point.</h2><p>Illustrative demo pricing. These plans are product concepts, not offers for sale.</p>
          <div className="nf-billing"><span>Monthly</span><button type="button" role="switch" aria-label="Annual billing" aria-checked={annual} className="nf-switch" onClick={()=>setAnnual(!annual)}><span/></button><span>Annual <b>Save 20%</b></span></div>
        </div>
        <div className="nf-plans">{plans.map(plan=>{const amount=annual?plan.price*.8:plan.price;return <article className={`nf-plan ${plan.name==='Team'?'nf-plan-featured':''}`} key={plan.name}><div className="nf-plan-name"><h3>{plan.name}</h3>{plan.name==='Team'&&<span>For collaboration</span>}</div><p>{plan.description}</p><div className="nf-price"><strong>${amount}</strong><span>/ month</span></div><p className="nf-billing-line">{annual?`$${amount*12} billed yearly`:'Billed monthly'}</p><button className="nf-button" onClick={()=>setSelected(`${plan.name} selected for this demo. ${annual?'Annual':'Monthly'} billing. No purchase was made.`)}>Explore {plan.name} <span aria-hidden="true">↗</span></button><ul>{plan.items.map(item=><li key={item}>{item}</li>)}</ul></article>})}</div>
        <p className="nf-selection" role="status" aria-live="polite">{selected||'Explore a plan to see a local demo confirmation. No signup or payment is required.'}</p>
      </section>
    </main>
    <footer className="nf-footer nf-container"><div><a className="nf-brand" href="#hero"><span aria-hidden="true">✳</span>NexaFlow</a><p>Make space for what comes next.</p></div><nav aria-label="Footer navigation"><a href="#features">Features</a><a href="#pricing">Pricing</a><a href="#hero">Back to top ↑</a></nav><small>© {new Date().getFullYear()} NexaFlow · Illustrative product concept</small></footer>
  </div>;
}
