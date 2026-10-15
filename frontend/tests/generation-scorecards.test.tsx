import { screen, within } from '@testing-library/dom';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';
import { ChangeSummary } from '../src/components/chat/ChangeSummary';
vi.hoisted(() => { Object.defineProperty(window, 'matchMedia', { configurable:true, value: () => ({matches:false}) }); });

describe('generation provenance in the result card', () => {
  it('keeps failed native evidence visible when the repaired final site passes', () => {
    document.body.innerHTML = renderToStaticMarkup(<ChangeSummary summary={{filesCreated:['src/Hero.tsx'],filesModified:[],
      generationScorecards:{provenance:{mode:'live'},stages:[
        {id:'native',label:'Model native',status:'failed',first_attempt_sections:2,required_sections:4},
        {id:'deterministic_repair',label:'Deterministic repair',status:'passed',files:['src/Hero.css']},
        {id:'model_repair',label:'Model repair',status:'passed',section_retries:2,project_attempts:1},
        {id:'final',label:'Final site',status:'passed'},
      ]}}} />);
    const native=screen.getByText('Model native').closest('tr')!;
    expect(within(native).getByText('failed')).toBeInTheDocument();
    expect(within(native).getByText('2/4 first attempts')).toBeInTheDocument();
    expect(screen.getByText('2 section retries · 1 project attempts')).toBeInTheDocument();
    expect(within(screen.getByText('Final site').closest('tr')!).getByText('passed')).toBeInTheDocument();
  });
});
