import React, {useState} from 'react';
import './Collection.css';
const works = [{name:'Quiet Column',type:'Objects',tone:'sand',caption:'A study in vertical rhythm.'},{name:'The Space Between',type:'Studies',tone:'clay',caption:'Two forms, one conversation.'},{name:'Low Horizon',type:'Objects',tone:'ink',caption:'A grounded, horizontal gesture.'}];
export function Collection(){
  const [filter,setFilter]=useState('All');
  return <section className="forma-work" id="work"><div className="forma-work-heading"><div><p className="forma-work-kicker">SELECTED STUDIES</p><h2>Made to be noticed.<br />Designed to belong.</h2></div><div className="forma-filters" role="group" aria-label="Filter work">{['All','Objects','Studies'].map(item=><button key={item} aria-pressed={filter===item} onClick={()=>setFilter(item)}>{item}</button>)}</div></div><div className="forma-grid" aria-live="polite">{works.filter(work=>filter==='All'||work.type===filter).map((work,index)=><article key={work.name}><div className={`forma-object forma-object--${work.tone}`} role="img" aria-label={`${work.name}, an abstract sculptural illustration`}><span/></div><p className="forma-work-number">0{index+1} / {work.type}</p><h3>{work.name}</h3><p>{work.caption}</p></article>)}</div></section>;
}
export default Collection;
