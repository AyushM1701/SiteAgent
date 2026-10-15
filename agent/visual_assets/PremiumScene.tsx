import { useState } from 'react';
import './PremiumScene.css';

type PremiumSceneProps = { label?: string; className?: string };

/** Lightweight CSS 3D art: no WebGL, network assets, render loop or dependencies. */
export default function PremiumScene({ label = 'Interactive dimensional product artwork', className = '' }: PremiumSceneProps) {
  const [paused, setPaused] = useState(false);
  const [view, setView] = useState(0);
  return (
    <figure className={`premium-scene ${className}`} data-paused={paused} data-view={view}>
      <div className="premium-scene__stage" role="img" aria-label={label}>
        <div className="premium-scene__grid" />
        <div className="premium-scene__halo" />
        <div className="premium-scene__perspective">
          <div className="premium-scene__orbit">
            <div className="premium-scene__cube">
              {['front', 'back', 'right', 'left', 'top', 'bottom'].map(face => (
                <div key={face} className={`premium-scene__face premium-scene__face--${face}`}>
                  <span className="premium-scene__chip" />
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
      <figcaption className="premium-scene__controls">
        <span>DIMENSION / {String(view + 1).padStart(2, '0')}</span>
        <button type="button" onClick={() => setView((view + 1) % 3)}>Change view</button>
        <button className="premium-scene__pause" type="button" aria-pressed={paused} onClick={() => setPaused(!paused)}>
          {paused ? 'Resume motion' : 'Pause motion'}
        </button>
      </figcaption>
    </figure>
  );
}
