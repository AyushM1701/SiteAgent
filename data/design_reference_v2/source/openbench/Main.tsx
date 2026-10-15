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
export function Main(){const root=useMotion();const [step,setStep]=React.useState(0);const [answer,setAnswer]=React.useState('');const lessons=[{title:'Give the headline a job.',body:'Choose one message. Let size and spacing show where reading begins.'},{title:'Make room for the text.',body:'Use a comfortable line length and generous line spacing for paragraphs.'},{title:'Check the small screen.',body:'Keep labels readable and test the layout without horizontal scrolling.'}];return <main className="openbench" ref={root}><nav><strong>OPEN BENCH / TYPE LAB</strong><div><a href="#lesson">Workshop</a><a href="#quiz">Try it</a></div></nav><header><p>LEARN BY MAKING A SMALL THING</p><h1>Good type.<br/>Clear thinking.</h1><div data-art aria-hidden="true">Aa<span>THE EVERYDAY ALPHABET</span></div></header><section id="lesson" data-reveal><aside><p>01 — THE WORKSHOP</p>{lessons.map((lesson,index)=><button key={lesson.title} aria-pressed={step===index} onClick={()=>setStep(index)}>Step {index+1}</button>)}</aside><article><p>LESSON {step+1} OF 3</p><h2>{lessons[step].title}</h2><p>{lessons[step].body}</p><progress aria-label="Lesson progress" value={step+1} max={3}/></article></section><section id="quiz" data-reveal><h2>Which pairing is easier to read?</h2><div data-quiz><button onClick={()=>setAnswer('Try again: choose a clearer text/background contrast.')}>Pale text on a pale background</button><button onClick={()=>setAnswer('Correct: dark text on a light background is clearer here.')}>Dark text on a light background</button></div><p role="status">{answer}</p><small>Original learning demo. No enrollment, certificate or saved account.</small></section><footer>Open Bench · Original fictional reference · No backend services.</footer></main>;}
export default Main;
