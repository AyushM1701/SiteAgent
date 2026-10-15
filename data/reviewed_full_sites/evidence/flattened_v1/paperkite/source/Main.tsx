import React,{useState} from 'react';

import './Main.css';

export function Hero(){return <section className="kite-hero" id="hello"><div className="kite-banner">A fictional print shop. Real room for imagination.</div><header className="kite-nav"><a href="#hello">paper kite<span>✳</span></a><nav aria-label="Main"><a href="#prints">Shop the prints</a><a href="#about">Our little world</a></nav></header><div className="kite-intro"><p>SMALL EDITIONS. BIG PERSONALITY.</p><h1>Put a little<br /><em>play</em> on your wall.</h1><p className="kite-description">Bold shapes. Unexpected neighbours. Original illustrated prints for spaces that feel like you.</p><a href="#prints" className="kite-cta">Meet your next favourite ↗</a><div className="kite-poster" role="img" aria-label="An original geometric poster of an orange sun above blue arches"><span className="kite-sun"/><span className="kite-arch"/><span className="kite-stamp">GOOD<br />THINGS<br />AHEAD.</span><small>COLOUR STUDY / NO. 01</small></div><span className="kite-scribble" aria-hidden="true">✳</span></div></section>;}

const prints=[{id:'sun',name:'Sunroom',description:'A warmer kind of morning.',price:24},{id:'blue',name:'Blue Hour',description:'For the daydream corner.',price:28},{id:'green',name:'Soft Landing',description:'A small pause in the day.',price:24}];
export function Shop(){
 const [cart,setCart]=useState<Record<string,number>>({});
 const [notice,setNotice]=useState('Your demo bag is empty.');
 const count=Object.values(cart).reduce((a,b)=>a+b,0);
 const total=prints.reduce((sum,p)=>sum+p.price*(cart[p.id]||0),0);
 function add(id:string){setCart(current=>({...current,[id]:(current[id]||0)+1}));setNotice(`${prints.find(p=>p.id===id)?.name} added to your demo bag.`);}
 return <section className="kite-shop" id="prints"><div className="kite-shop-heading"><div><p>THE SMALL COLLECTION</p><h2>Find your happy place.</h2></div><a href="#bag">Your bag ({count}) ↓</a></div><div className="kite-products">{prints.map(p=><article key={p.id}><div className={`kite-print kite-print--${p.id}`} role="img" aria-label={`${p.name}, original geometric print artwork`}><i/><b/><span>{p.name.toUpperCase()}</span></div><div className="kite-product-title"><h3>{p.name}</h3><span>${p.price}</span></div><p>{p.description}</p><button onClick={()=>add(p.id)}>Add {p.name} to bag <span>+</span></button></article>)}</div><aside className="kite-bag" id="bag" aria-label="Demo shopping bag"><div><h3>Your little collection</h3><p role="status">{notice}</p></div><div><p><strong>{count} {count===1?'print':'prints'} · ${total}</strong></p><button disabled={count===0} onClick={()=>{setCart({});setNotice('Your demo bag is empty.');}}>Empty bag</button></div></aside><p className="kite-demo-note">Illustrative prices in USD. This is a demo: no payments, shipping, or orders are processed.</p></section>;
}

export function About(){return <footer className="kite-about" id="about"><span aria-hidden="true">✳</span><h2>Life could use<br />a little more colour.</h2><p>Paper Kite is an original fictional shop, created to explore playful illustration and simple, honest shopping interactions. Every artwork here is made from CSS shapes.</p><a href="#hello">Back to the top ↑</a><small>PAPER KITE / A DEMONSTRATION, NOT A REAL STORE</small></footer>;}

export function Main(){return <><a className="reference-skip" href="#reference-main">Skip to content</a><main id="reference-main"><Hero/><Shop/><About/></main></>;}
export default Main;
