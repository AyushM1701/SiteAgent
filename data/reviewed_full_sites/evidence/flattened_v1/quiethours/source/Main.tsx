import React,{useEffect,useRef,useState} from 'react';

import './Main.css';

export function Hero(){
 const art=useRef<HTMLDivElement>(null);
 useEffect(()=>{const media=matchMedia('(prefers-reduced-motion: reduce)');let frame=0;const update=()=>{cancelAnimationFrame(frame);frame=requestAnimationFrame(()=>{art.current?.style.setProperty('--drift',media.matches?'0px':`${Math.min(scrollY*.12,55)}px`);});};addEventListener('scroll',update,{passive:true});media.addEventListener('change',update);update();return()=>{removeEventListener('scroll',update);media.removeEventListener('change',update);cancelAnimationFrame(frame);};},[]);
 return <section className="quiet-hero" id="start"><header className="quiet-nav"><a href="#start">quiet hours<span>↟</span></a><nav aria-label="Main"><a href="#guide">Take a soundwalk</a><a href="#journal">Field journal</a></nav></header><div className="quiet-hero-grid"><div><p className="quiet-eyebrow">A SMALL PRACTICE IN PAYING ATTENTION</p><h1>The world<br />has a <em>quieter</em><br />side.</h1><p className="quiet-intro">Step outside. Slow your pace. Notice the layers of sound that usually slip between the things you do.</p><a className="quiet-button" href="#guide">Begin with listening ↓</a></div><div className="quiet-landscape" ref={art} role="img" aria-label="An abstract evening landscape with a pale moon and layered hills"><i className="quiet-moon"/><i className="quiet-hill quiet-hill--back"/><i className="quiet-hill quiet-hill--front"/><span>LISTEN / NOTICE / REMEMBER</span></div></div><p className="quiet-caption">No microphone. No location tracking. Just your attention.</p></section>;
}

const steps=[['Arrive','Choose a familiar place where you feel comfortable pausing. Put your phone away for a moment.'],['Listen in layers','Notice a sound nearby, one farther away, and the background underneath them. There is no right answer.'],['Leave a small note','Describe one detail in your own words. What did you notice when you stopped trying to get somewhere?']];
export function Guide(){
 const root=useRef<HTMLElement>(null);
 useEffect(()=>{const media=matchMedia('(prefers-reduced-motion: reduce)');const nodes=root.current?.querySelectorAll<HTMLElement>('.quiet-step');if(!nodes)return;const observer=new IntersectionObserver(entries=>entries.forEach(entry=>{if(entry.isIntersecting){entry.target.classList.add('quiet-step--seen');observer.unobserve(entry.target);}}),{threshold:.15});if(!media.matches){nodes.forEach(node=>{node.classList.add('quiet-step--waiting');observer.observe(node);});}const show=()=>{if(media.matches)nodes.forEach(node=>node.classList.add('quiet-step--seen'));};media.addEventListener('change',show);return()=>{observer.disconnect();media.removeEventListener('change',show);};},[]);
 return <section className="quiet-guide" id="guide" ref={root}><p className="quiet-guide-label">A WALK WITHOUT A DESTINATION</p><h2>Three small invitations.</h2><div>{steps.map(([title,text],i)=><article className="quiet-step" key={title}><span>0{i+1}</span><h3>{title}</h3><p>{text}</p></article>)}</div><a href="#journal">Keep a note from your walk ↗</a></section>;
}

export function Journal(){
 const [note,setNote]=useState('');const [saved,setSaved]=useState('');const [error,setError]=useState('');
 function submit(event:React.FormEvent){event.preventDefault();if(!note.trim()){setError('Write a few words before saving your note.');return;}setSaved(note.trim());setError('');}
 return <section className="quiet-journal" id="journal"><div><p className="quiet-journal-label">YOUR FIELD JOURNAL</p><h2>What stayed<br />with you?</h2><p className="quiet-journal-intro">A bicycle bell. Wind in a doorway. The quiet after a bus goes by. Give one small moment a place to stay.</p><small>Your note stays in this page’s memory only. Refreshing clears it. Nothing is sent or recorded.</small></div><form onSubmit={submit} noValidate><label htmlFor="quiet-note">One thing I noticed</label><textarea id="quiet-note" value={note} onChange={e=>setNote(e.target.value)} maxLength={400} rows={5} aria-invalid={!!error} aria-describedby="quiet-error" placeholder="Today, I heard…"/><p id="quiet-error" role="alert">{error}</p><div className="quiet-journal-actions"><span>{note.length}/400</span><button type="submit">Save this moment ↗</button></div><div className="quiet-saved" role="status">{saved&&<><strong>A note from your walk</strong><p>{saved}</p><button type="button" onClick={()=>{setSaved('');setNote('');}}>Clear note</button></>}</div></form><footer><span>quiet hours / an original soundwalk journal</span><a href="#start">Back to the beginning ↑</a></footer></section>;
}

export function Main(){return <><a className="reference-skip" href="#reference-main">Skip to content</a><main id="reference-main"><Hero/><Guide/><Journal/></main></>;}
export default Main;
