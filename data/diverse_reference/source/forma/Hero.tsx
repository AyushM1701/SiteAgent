import React from 'react';
import './Hero.css';
export function Hero() {
  return <section className="forma-hero" id="intro">
    <header className="forma-nav"><a href="#intro" className="forma-brand">forma<span>®</span></a><nav aria-label="Main"><a href="#work">Selected work</a><a href="#contact">The studio ↗</a></nav></header>
    <div className="forma-heading"><p className="forma-label">INDEPENDENT OBJECT DESIGN / DEMO PORTFOLIO</p><h1>Less object.<br /><em>More presence.</em></h1><p className="forma-summary">An exploration of weight, light, and the space in between. Sculptural studies for everyday surroundings.</p><a className="forma-link" href="#work">Explore the collection <span>↓</span></a></div>
    <div className="forma-stage" role="img" aria-label="A dimensional composition of three sculptural blocks in clay, cream, and charcoal"><div className="forma-orbit" aria-hidden="true"><i className="forma-cube forma-cube--clay"/><i className="forma-cube forma-cube--cream"/><i className="forma-cube forma-cube--ink"/></div><span className="forma-art-label">STUDY 01 — BALANCE / CSS COMPOSITION</span></div>
    <p className="forma-bottom">Objects with room to breathe.<span>01 / 03</span></p>
  </section>;
}
export default Hero;
