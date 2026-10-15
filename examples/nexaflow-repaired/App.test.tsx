import React from 'react';
import {afterEach,expect,it} from 'vitest';
import {cleanup,render,screen,within} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom/vitest';
import App from './App';
afterEach(cleanup);

it('billing changes all prices and annual totals, with keyboard reversal',async()=>{
 const user=userEvent.setup();render(<App/>);
 const toggle=screen.getByRole('switch',{name:'Annual billing'});
 expect(toggle).toHaveAttribute('aria-checked','false');
 expect(screen.getAllByText('Billed monthly')).toHaveLength(3);
 await user.click(toggle);
 for(const amount of [16,40,80]) expect(screen.getByText(`$${amount}`)).toBeVisible();
 for(const total of [192,480,960]) expect(screen.getByText(`$${total} billed yearly`)).toBeVisible();
 expect(toggle).toHaveAttribute('aria-checked','true');
 await user.keyboard(' ');
 expect(toggle).toHaveAttribute('aria-checked','false');
 expect(screen.getAllByText('Billed monthly')).toHaveLength(3);
 await user.click(screen.getByRole('button',{name:/Explore Team/}));
 expect(screen.getByRole('status')).toHaveTextContent('No purchase was made.');
});

it('menu exposes expanded state and Escape restores focus',async()=>{
 const user=userEvent.setup();render(<App/>);
 const toggle=screen.getByRole('button',{name:'Navigation menu'});
 await user.click(toggle);expect(toggle).toHaveAttribute('aria-expanded','true');
 await user.keyboard('{Escape}');expect(toggle).toHaveAttribute('aria-expanded','false');expect(toggle).toHaveFocus();
 await user.click(toggle);
 await user.click(within(screen.getByRole('navigation',{name:'Main navigation'})).getByRole('link',{name:'Pricing'}));
 expect(toggle).toHaveAttribute('aria-expanded','false');
});

it('has six distinct feature cards and all links resolve to real sections',()=>{
 render(<App/>);
 expect(document.querySelectorAll('#features article')).toHaveLength(6);
 expect(new Set(Array.from(document.querySelectorAll('#features h3')).map(e=>e.textContent)).size).toBe(6);
 expect(screen.getByRole('main')).toBeInTheDocument();
 for(const link of screen.getAllByRole('link')){
   const href=link.getAttribute('href')!;expect(href).not.toBe('#');
   expect(document.getElementById(href.slice(1))).not.toBeNull();
 }
});
