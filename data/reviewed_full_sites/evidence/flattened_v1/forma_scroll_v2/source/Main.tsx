import React,{useEffect,useRef,useState} from 'react';

import './Main.css';

export function Hero() {
  const root=useRef<HTMLElement>(null);
  useEffect(()=>{const media=matchMedia('(prefers-reduced-motion: reduce)');let frame=0;const update=()=>{cancelAnimationFrame(frame);frame=requestAnimationFrame(()=>root.current?.style.setProperty('--forma-scroll',media.matches?'0px':`${Math.min(scrollY*.09,55)}px`));};addEventListener('scroll',update,{passive:true});media.addEventListener('change',update);update();return()=>{removeEventListener('scroll',update);media.removeEventListener('change',update);cancelAnimationFrame(frame);};},[]);
  return <section className="forma-hero" id="intro" ref={root}>
    <header className="forma-nav"><a href="#intro" className="forma-brand">forma<span>®</span></a><nav aria-label="Main"><a href="#work">Selected work</a><a href="#contact">The studio ↗</a></nav></header>
    <div className="forma-heading"><p className="forma-label">INDEPENDENT OBJECT DESIGN / DEMO PORTFOLIO</p><h1>Less object.<br /><em>More presence.</em></h1><p className="forma-summary">An exploration of weight, light, and the space in between. Sculptural studies for everyday surroundings.</p><a className="forma-link" href="#work">Explore the collection <span>↓</span></a></div>
    <div className="forma-stage" role="img" aria-label="A dimensional composition of three sculptural blocks in clay, cream, and charcoal"><div className="forma-orbit" aria-hidden="true"><i className="forma-cube forma-cube--clay"/><i className="forma-cube forma-cube--cream"/><i className="forma-cube forma-cube--ink"/></div><span className="forma-art-label">STUDY 01 — BALANCE / CSS COMPOSITION</span></div>
    <p className="forma-bottom">Objects with room to breathe.<span>01 / 03</span></p>
  </section>;
}

const works = [{name:'Quiet Column',type:'Objects',tone:'sand',caption:'A study in vertical rhythm.'},{name:'The Space Between',type:'Studies',tone:'clay',caption:'Two forms, one conversation.'},{name:'Low Horizon',type:'Objects',tone:'ink',caption:'A grounded, horizontal gesture.'}];
export function Collection(){
  const [filter,setFilter]=useState('All');
  const root=useRef<HTMLElement>(null);
  useEffect(()=>{const media=matchMedia('(prefers-reduced-motion: reduce)');const nodes=root.current?.querySelectorAll<HTMLElement>('.forma-work-heading,.forma-grid article');if(!nodes)return;const observer=new IntersectionObserver(entries=>entries.forEach(entry=>{if(entry.isIntersecting){entry.target.classList.add('forma-revealed');observer.unobserve(entry.target);}}),{threshold:.12});if(!media.matches)nodes.forEach(node=>{node.classList.add('forma-reveal');observer.observe(node);});const show=()=>{if(media.matches)nodes.forEach(node=>node.classList.add('forma-revealed'));};media.addEventListener('change',show);return()=>{observer.disconnect();media.removeEventListener('change',show);};},[filter]);
  return <section className="forma-work" id="work" ref={root}><div className="forma-work-heading"><div><p className="forma-work-kicker">SELECTED STUDIES</p><h2>Made to be noticed.<br />Designed to belong.</h2></div><div className="forma-filters" role="group" aria-label="Filter work">{['All','Objects','Studies'].map(item=><button key={item} aria-pressed={filter===item} onClick={()=>setFilter(item)}>{item}</button>)}</div></div><div className="forma-grid" aria-live="polite">{works.filter(work=>filter==='All'||work.type===filter).map((work,index)=><article key={work.name}><div className={`forma-object forma-object--${work.tone}`} role="img" aria-label={`${work.name}, an abstract sculptural illustration`}><span/></div><p className="forma-work-number">0{index+1} / {work.type}</p><h3>{work.name}</h3><p>{work.caption}</p></article>)}</div></section>;
}

export function Contact(){return <footer className="forma-contact" id="contact"><p>THE NEXT EXPLORATION</p><h2>A little space.<br />A new possibility.</h2><p className="forma-contact-note">This is a fictional design portfolio. Commission enquiries and studio visits would appear here on a live site.</p><a href="#intro">Back to the beginning ↑</a><div><span>forma / objects & studies</span><span>Original demonstration portfolio</span></div></footer>;}

export function Main(){return <><a className="reference-skip" href="#reference-main">Skip to content</a><main id="reference-main"><Hero/><Collection/><Contact/></main></>;}
export default Main;
