import React from 'react';
import ReactDOM from 'react-dom/client';

// Mount whatever component is exported by latest/Component.tsx
import * as Mod from './latest/Component';

const AnyComponent: any = Mod.default || Object.values(Mod).find(v => typeof v === 'function') || (() => <div>No component found</div>);

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <div style={{ padding: 24, maxWidth: 1200, margin: '0 auto' }}>
      <AnyComponent />
    </div>
  </React.StrictMode>
);

