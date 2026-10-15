import React from 'react';
import './Principles.css';
export default function Principles() {
  return <section className="m-principles" aria-labelledby="m-principles-title"><span className="eyebrow">02 / ROOM TO BE YOURSELF</span><h2 id="m-principles-title">Rough drafts.<br /><em>Real possibilities.</em></h2><div className="m-principle-grid">{[['01','Begin before you are ready.','A sentence, a sketch, a conversation. You do not need the whole story to find its beginning.'],['02','Make feedback a conversation.','Keep suggestions beside the work, so the thread of an idea never gets lost.'],['03','Keep your own voice.','A thoughtful workspace should support your choices, not make them for you.']].map(([number,title,copy]) => <article key={number}><span>{number}</span><h3>{title}</h3><p>{copy}</p></article>)}</div></section>;
}
