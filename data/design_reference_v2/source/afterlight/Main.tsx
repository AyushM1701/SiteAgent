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
export function Main(){const root=useMotion();const [day,setDay]=React.useState('Friday');const [saved,setSaved]=React.useState<string[]>([]);const sessions=day==='Friday'?['Deep Listening','Tape Loops']:['Field Recording'];return <main className="afterlight" ref={root}><nav><strong>AFTERLIGHT / LISTENING LAB</strong><div><a href="#programme">Programme</a><a href="#saved">Your list</a></div></nav><header><p>A FICTIONAL FESTIVAL OF SMALL SOUNDS</p><h1>Stay.<br/>A little.<br/><em>Longer.</em></h1><div data-orbit data-art aria-hidden="true"><i/><i/><i/></div></header><section id="programme" data-reveal><div><h2>Follow your ears.</h2><div aria-label="Programme day">{['Friday','Saturday'].map(value=><button key={value} aria-pressed={day===value} onClick={()=>setDay(value)}>{value}</button>)}</div></div><ol>{sessions.map((session,index)=><li key={session}><span>SESSION 0{index+1}</span><h3>{session}</h3><button disabled={saved.includes(session)} onClick={()=>setSaved(current=>[...current,session])}>{saved.includes(session)?'Saved':`Save ${session}`}</button></li>)}</ol></section><section id="saved" data-reveal><h2>Your listening list.</h2><p role="status">{saved.length} saved sessions</p>{saved.map(session=><div data-saved key={session}><span>{session}</span><button onClick={()=>setSaved(current=>current.filter(item=>item!==session))}>Remove {session}</button></div>)}<small>Programme demo. Selections live in memory only. No dates, venues or ticket service.</small></section><footer>Afterlight · Original fictional reference · No backend services.</footer></main>;}
export default Main;
