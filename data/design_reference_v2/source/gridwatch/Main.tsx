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
export function Main(){const root=useMotion();const [period,setPeriod]=React.useState('Day');const [baseline,setBaseline]=React.useState(false);const energy=period==='Day'?18:104;const points=period==='Day'?'15,180 90,145 165,80 240,30 315,65 390,140 465,178':'15,165 90,115 165,130 240,50 315,90 390,30 465,70';return <main className="gridwatch" ref={root}><nav><strong>GRIDWATCH / SAMPLE CONSOLE</strong><div><a href="#energy">Energy</a><a href="#baseline">Compare</a></div></nav><header><p>ILLUSTRATIVE DATA · NO LIVE TELEMETRY</p><h1>A clearer view<br/>of the <em>day.</em></h1></header><section id="energy" data-reveal><aside><span>SAMPLE GENERATION</span><strong>{energy}<small> kWh</small></strong><p>{period} illustrative total</p><div aria-label="Chart period">{['Day','Week'].map(value=><button key={value} aria-pressed={period===value} onClick={()=>setPeriod(value)}>{value}</button>)}</div></aside><article><h2>{period} generation shape</h2><svg viewBox="0 0 500 220" role="img" aria-label={`${period} illustrative energy generation line chart`}><title>{period} demo generation, not live measurements</title><path d="M15 20V190H480" fill="none" stroke="#84988a"/><polyline points={points} fill="none" stroke="#b5dc79" strokeWidth="4"/><text x="20" y="210" fill="#dce8d4" fontSize="11">START</text><text x="435" y="210" fill="#dce8d4" fontSize="11">END</text></svg><p>Shape only; sample total is shown at left. This chart is not a monitoring service.</p></article></section><section id="baseline" data-reveal><h2>Keep comparisons honest.</h2><label><input type="checkbox" checked={baseline} onChange={event=>setBaseline(event.target.checked)}/> Show baseline</label>{baseline&&<p role="status">Demo baseline: {period==='Day'?12:84} kWh. Illustrative comparison, not a performance guarantee.</p>}<small>Original dashboard demo. No account, telemetry connection, billing or saved state.</small></section><footer>Gridwatch · Original fictional reference · No backend services.</footer></main>;}
export default Main;
