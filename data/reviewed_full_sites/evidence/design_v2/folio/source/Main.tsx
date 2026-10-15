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
export function Main(){const root=useMotion();const [filter,setFilter]=React.useState('All');const stories=[{title:'The room above the bakery',type:'Places',note:'A fictional story about a small reading room.'},{title:'Mending as a shared language',type:'People',note:'A fictional portrait of a neighborhood repair group.'},{title:'An afternoon along the canal',type:'Places',note:'A fictional walk through changing city edges.'}];return <main className="folio" ref={root}><nav><strong>FOLIO / LOCAL</strong><div><a href="#stories">Stories</a><a href="#reading">Reading list</a></div></nav><header><p>THE NEIGHBORHOOD ISSUE · ORIGINAL DEMO</p><h1>Look closer.<br/><em>There is a story here.</em></h1><div data-art aria-hidden="true"><i/><b/><span>01</span></div></header><section id="stories"><div data-reveal><p>OBSERVATIONS, NOT HEADLINES</p><h2>Good things happen<br/>between the big things.</h2></div><div aria-label="Story categories">{['All','Places','People'].map(category=><button key={category} aria-pressed={filter===category} onClick={()=>setFilter(category)}>{category}</button>)}</div><div data-grid>{stories.filter(story=>filter==='All'||story.type===filter).map((story,index)=><article key={story.title} data-reveal><span>0{index+1} / {story.type}</span><h3>{story.title}</h3><p>{story.note}</p><a href="#reading">Add a slower moment to your day ↓</a></article>)}</div></section><section id="reading" data-reveal><h2>A small reading ritual.</h2><p>Choose a quiet corner. Read one story. Notice one detail you would normally miss.</p><small>Fictional editorial demo. No subscription, tracking or news reporting.</small></section><footer>Folio Local · Original fictional reference · No backend services.</footer></main>;}
export default Main;
