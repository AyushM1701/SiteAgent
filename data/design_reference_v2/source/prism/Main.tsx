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
export function Main(){const root=useMotion();const [light,setLight]=React.useState('Amber');const [flat,setFlat]=React.useState(false);return <main className="prism" ref={root}><nav><strong>PRISM ROOM / 001</strong><div><a href="#scene">Installation</a><a href="#statement">Statement</a><a href="#light">Light</a></div></nav><section id="scene"><div data-reveal><p>DIGITAL MATERIAL STUDY</p><h1>Nothing solid.<br/><em>Everything felt.</em></h1></div><div data-stage data-tone={light} data-flat={flat} role="img" aria-label="Rotating dimensional translucent cube, original CSS sculpture"><div data-cube>{[0,1,2,3,4,5].map(face=><i key={face} data-face={face}/>)}</div></div><small>CSS 3D sculpture · no WebGL renderer · motion stops when reduced motion is requested.</small></section><section id="statement" data-reveal><p>THE SPACE BETWEEN SURFACES</p><h2>Light becomes<br/>the material.</h2><p>A fictional exhibition exploring how six ordinary planes can become a changing object. Shift the light and watch the same geometry feel different.</p></section><section id="light" data-reveal><h2>Set the atmosphere.</h2><div aria-label="Sculpture lighting">{['Amber','Ice'].map(tone=><button key={tone} aria-pressed={light===tone} onClick={()=>setLight(tone)}>{tone}</button>)}</div><p role="status">{light} light selected.</p><label><input type="checkbox" checked={flat} onChange={event=>setFlat(event.target.checked)}/> Show flat composition</label><small>Original interactive art demo. No real-world venue or ticket service.</small></section><footer>Prism Room · Original fictional reference · No backend services.</footer></main>;}
export default Main;
