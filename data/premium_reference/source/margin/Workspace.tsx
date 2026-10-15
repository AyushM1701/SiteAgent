import React, { useState } from 'react';
import './Workspace.css';
export default function Workspace() {
  const [text, setText] = useState('At the edge of the city, a small door appeared.');
  const [notes, setNotes] = useState(true);
  const words = text.trim() ? text.trim().split(/\s+/).length : 0;
  return <section id="workspace" className="m-work"><div className="section-top"><span className="eyebrow">01 / THE WORKSPACE</span><h2>A thought needs<br />somewhere to land.</h2><p>Try the local editor. Your words stay in this page and disappear when you reload.</p></div><div className="m-editor"><div className="m-editor-bar"><span>UNTITLED / FIRST DRAFT</span><button type="button" aria-pressed={notes} onClick={() => setNotes(!notes)}>{notes ? 'Hide notes' : 'Show notes'}</button></div><div className="m-editor-body"><div><label htmlFor="story">Your first lines</label><textarea id="story" value={text} onChange={event => setText(event.target.value)} spellCheck={false}/><output aria-live="polite">{words} words</output></div>{notes && <aside aria-label="Editorial notes"><span>IN THE MARGIN</span><p>Who notices the door first?</p><p>Give the reader a detail they can feel.</p><small>Illustrative prompts, not live collaboration.</small></aside>}</div></div></section>;
}
