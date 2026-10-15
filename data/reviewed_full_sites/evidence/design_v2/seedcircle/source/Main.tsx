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
export function Main(){const root=useMotion();const [name,setName]=React.useState('');const [project,setProject]=React.useState('Seed sorting');const [notice,setNotice]=React.useState('');return <main className="seedcircle" ref={root}><nav><strong>SEED CIRCLE</strong><div><a href="#projects">Small projects</a><a href="#join">Lend a hand</a></div></nav><header><p>AN ORIGINAL COMMUNITY-GARDEN DEMO</p><h1>Small hands.<br/><em>Shared ground.</em></h1><div data-leaf data-art aria-hidden="true"><i/><i/><i/></div></header><section id="projects"><h2 data-reveal>There is a useful<br/>place to begin.</h2><div data-projects>{[{name:'Seed sorting',text:'Organize labelled packets for a fictional seed exchange.'},{name:'Bed preparation',text:'Plan a shared planting area with the actual project organizer.'},{name:'Garden notes',text:'Record seasonal observations in a shared project notebook.'}].map((item,index)=><article data-reveal key={item.name}><span>0{index+1}</span><h3>{item.name}</h3><p>{item.text}</p></article>)}</div></section><section id="join" data-reveal><div><h2>A little time.<br/>A shared intention.</h2><p>Try the interest form. Nothing is sent or stored beyond this page.</p></div><form onSubmit={event=>{event.preventDefault();setNotice(name.trim()?`Demo interest recorded: ${name.trim()} — ${project}. Nothing was submitted.`:'Enter your name to create a demo interest note.');}} noValidate><label>Your name<input value={name} onChange={event=>setName(event.target.value)} maxLength={60}/></label><label>Project<select aria-label="Project" value={project} onChange={event=>setProject(event.target.value)}><option>Seed sorting</option><option>Bed preparation</option><option>Garden notes</option></select></label><button type="submit">Create interest note</button><button type="button" onClick={()=>{setName('');setNotice('Demo note cleared.');}}>Clear note</button><p role="status">{notice}</p></form></section><footer>Seed Circle · Original fictional reference · No backend services.</footer></main>;}
export default Main;
