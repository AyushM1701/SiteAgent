import React from 'react';
import './Main.css';
function useMotion(){
 const ref=React.useRef<HTMLElement>(null);
 React.useEffect(()=>{
  const root=ref.current;if(!root)return;
  const media=matchMedia('(prefers-reduced-motion: reduce)');let frame=0;
  const observer=new IntersectionObserver(entries=>entries.forEach(entry=>{if(entry.isIntersecting){(entry.target as HTMLElement).dataset.seen='true';observer.unobserve(entry.target);}}),{threshold:.12});
  const watched=new WeakSet<Element>();const register=()=>root.querySelectorAll('[data-reveal]').forEach(el=>{if(!watched.has(el)){watched.add(el);observer.observe(el);}});
  register();const mutations=new MutationObserver(register);mutations.observe(root,{childList:true,subtree:true});root.classList.add('motion-ready');
  const update=()=>{frame=0;root.style.setProperty('--shift',media.matches?'0px':`${Math.min(scrollY*.13,85)}px`);};
  const scroll=()=>{if(!frame)frame=requestAnimationFrame(update);};
  window.addEventListener('scroll',scroll,{passive:true});media.addEventListener('change',scroll);update();
  return ()=>{observer.disconnect();mutations.disconnect();cancelAnimationFrame(frame);window.removeEventListener('scroll',scroll);media.removeEventListener('change',scroll);root.classList.remove('motion-ready');};
 },[]);return ref;
}
export function Main(){const root=useMotion();const [checked,setChecked]=React.useState<string[]>([]);const notes=['List your questions','Bring your appointment details','Note accessibility needs'];return <main className="carenotes" ref={root}><nav><strong>CARE NOTES / UI DEMO</strong><div><a href="#services">Directory</a><a href="#prepare">Prepare</a></div></nav><header><div><p>A LITTLE MORE ROOM TO PREPARE</p><h1>Your next visit.<br/><em>A clearer plan.</em></h1><p>A fictional service-directory interface for organizing questions before an appointment.</p></div><div data-art role="img" aria-label="Original abstract illustration of a notebook and a lilac sun"><i/><b/><span>NOTES<br/>FOR YOU</span></div></header><section id="services" data-reveal><h2>Find the right information.</h2><details><summary>Before your appointment</summary><p>Confirm time, location and any instructions directly with your actual provider.</p></details><details><summary>Access and support</summary><p>Ask the actual venue about access arrangements and support options before visiting.</p></details><details><summary>After your appointment</summary><p>Keep the information your provider gives you somewhere easy to find.</p></details></section><section id="prepare" data-reveal><h2>A small preparation list.</h2>{notes.map(note=><label key={note}><input type="checkbox" checked={checked.includes(note)} onChange={event=>setChecked(current=>event.target.checked?[...current,note]:current.filter(item=>item!==note))}/>{note}</label>)}<p role="status">{checked.length} of 3 preparation items selected</p><small>Fictional UI demo, not medical advice or an actual healthcare provider. No appointments or data are submitted.</small></section><footer>Care Notes · Original fictional reference · No backend services.</footer></main>;}
export default Main;
