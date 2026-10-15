import React, { useState } from 'react';
import './Plans.css';
export default function Plans() {
  const [annual, setAnnual] = useState(false);
  return <section id="plans" className="m-plans"><div><span className="eyebrow">03 / CHOOSE YOUR SPACE</span><h2>Start small.<br />Write something big.</h2><p>Illustrative pricing for this fictional product. No purchase or signup is collected.</p><button className="m-billing" type="button" role="switch" aria-checked={annual} onClick={() => setAnnual(!annual)}>Annual billing {annual ? 'on' : 'off'}</button></div><article><span>THE PERSONAL NOTEBOOK</span><h3><span data-testid="price">${annual ? '8' : '10'}</span><small> / month</small></h3><p>{annual ? '$96 billed yearly in this example.' : '$10 billed monthly in this example.'}</p><ul><li>A place for every draft</li><li>Focused editorial notes</li><li>Your words, your pace</li></ul><a className="m-button" href="#workspace">Try the local notebook ↗</a></article></section>;
}
