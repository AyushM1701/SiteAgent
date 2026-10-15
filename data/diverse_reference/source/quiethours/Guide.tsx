import React,{useEffect,useRef} from 'react';
import './Guide.css';
const steps=[['Arrive','Choose a familiar place where you feel comfortable pausing. Put your phone away for a moment.'],['Listen in layers','Notice a sound nearby, one farther away, and the background underneath them. There is no right answer.'],['Leave a small note','Describe one detail in your own words. What did you notice when you stopped trying to get somewhere?']];
export function Guide(){
 const root=useRef<HTMLElement>(null);
 useEffect(()=>{const media=matchMedia('(prefers-reduced-motion: reduce)');const nodes=root.current?.querySelectorAll<HTMLElement>('.quiet-step');if(!nodes)return;const observer=new IntersectionObserver(entries=>entries.forEach(entry=>{if(entry.isIntersecting){entry.target.classList.add('quiet-step--seen');observer.unobserve(entry.target);}}),{threshold:.15});if(!media.matches){nodes.forEach(node=>{node.classList.add('quiet-step--waiting');observer.observe(node);});}const show=()=>{if(media.matches)nodes.forEach(node=>node.classList.add('quiet-step--seen'));};media.addEventListener('change',show);return()=>{observer.disconnect();media.removeEventListener('change',show);};},[]);
 return <section className="quiet-guide" id="guide" ref={root}><p className="quiet-guide-label">A WALK WITHOUT A DESTINATION</p><h2>Three small invitations.</h2><div>{steps.map(([title,text],i)=><article className="quiet-step" key={title}><span>0{i+1}</span><h3>{title}</h3><p>{text}</p></article>)}</div><a href="#journal">Keep a note from your walk ↗</a></section>;
}
export default Guide;
