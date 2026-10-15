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
export function Main(){const root=useMotion();const [room,setRoom]=React.useState('Night Room');const [nights,setNights]=React.useState(2);const total=nights*(room==='Night Room'?90:140);return <main className="tidehouse" ref={root}><nav><strong>TIDEHOUSE</strong><div><a href="#rooms">The rooms</a><a href="#stay">Imagine a stay</a></div></nav><header><p>A FICTIONAL PLACE TO SLOW DOWN</p><h1>A little closer<br/>to the <em>water.</em></h1><div data-landscape data-art role="img" aria-label="Original coastal landscape with a warm sun and layered waves"><i/><b/><span/></div></header><section id="rooms"><div data-reveal><p>SPACE TO BREATHE</p><h2>Two ways to<br/>make yourself at home.</h2></div><div data-rooms><article data-reveal><span>01 / NIGHT ROOM</span><h3>For a lighter stay.</h3><p>A compact imagined room with morning light and a reading corner.</p><strong>Illustrative $90 / night</strong></article><article data-reveal><span>02 / STUDIO</span><h3>For a longer pause.</h3><p>An imagined studio with extra space for a slow breakfast.</p><strong>Illustrative $140 / night</strong></article></div></section><section id="stay" data-reveal><h2>Imagine your stay.</h2><label>Room<select aria-label="Room" value={room} onChange={event=>setRoom(event.target.value)}><option>Night Room</option><option>Studio</option></select></label><label>Nights<select aria-label="Nights" value={nights} onChange={event=>setNights(Number(event.target.value))}>{[1,2,3,4,5,6,7].map(value=><option key={value}>{value}</option>)}</select></label><p role="status">Estimated demo stay: ${total}</p><small>Illustrative estimate only. No availability, reservations, taxes or payment are provided.</small></section><footer>Tidehouse · Original fictional reference · No backend services.</footer></main>;}
export default Main;
