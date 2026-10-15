import React,{useState} from 'react';
import './Journal.css';
export function Journal(){
 const [note,setNote]=useState('');const [saved,setSaved]=useState('');const [error,setError]=useState('');
 function submit(event:React.FormEvent){event.preventDefault();if(!note.trim()){setError('Write a few words before saving your note.');return;}setSaved(note.trim());setError('');}
 return <section className="quiet-journal" id="journal"><div><p className="quiet-journal-label">YOUR FIELD JOURNAL</p><h2>What stayed<br />with you?</h2><p className="quiet-journal-intro">A bicycle bell. Wind in a doorway. The quiet after a bus goes by. Give one small moment a place to stay.</p><small>Your note stays in this page’s memory only. Refreshing clears it. Nothing is sent or recorded.</small></div><form onSubmit={submit} noValidate><label htmlFor="quiet-note">One thing I noticed</label><textarea id="quiet-note" value={note} onChange={e=>setNote(e.target.value)} maxLength={400} rows={5} aria-invalid={!!error} aria-describedby="quiet-error" placeholder="Today, I heard…"/><p id="quiet-error" role="alert">{error}</p><div className="quiet-journal-actions"><span>{note.length}/400</span><button type="submit">Save this moment ↗</button></div><div className="quiet-saved" role="status">{saved&&<><strong>A note from your walk</strong><p>{saved}</p><button type="button" onClick={()=>{setSaved('');setNote('');}}>Clear note</button></>}</div></form><footer><span>quiet hours / an original soundwalk journal</span><a href="#start">Back to the beginning ↑</a></footer></section>;
}
export default Journal;
