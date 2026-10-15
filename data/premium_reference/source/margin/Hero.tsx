import React from 'react';
import './Hero.css';
export default function Hero() {
  return <><header className="m-nav"><a className="m-brand" href="#intro">margin<span>✳</span></a><nav aria-label="Main"><a href="#workspace">Workspace</a><a href="#plans">Plans</a><a className="m-button" href="#workspace">Open the notebook ↗</a></nav></header>
    <section id="intro" className="m-hero"><span className="eyebrow">A LITTLE SPACE. A BIG IDEA.</span><h1>Your next chapter<br />starts <em>in the margins.</em></h1><p>A shared notebook for unfinished thoughts, surprising turns, and the people who make your writing better.</p><a className="m-button" href="#workspace">Try a little writing ↗</a>
      <div className="m-papers" aria-hidden="true"><div className="m-note m-note--left"><span>THE FIRST THOUGHT</span><strong>What if<br />we began<br />somewhere else?</strong><i>01 — a possibility</i></div><div className="m-note m-note--right"><span>A NOTE FROM THE EDITOR</span><strong>Keep the strange bit.<br />That's where<br />the story is.</strong><i>Leave room for discovery.</i></div><div className="m-star">✳</div></div>
    </section></>;
}
