"""Section renderers: content dict -> (TSX, CSS).

Output rules that keep every file valid and validator-clean:
- content is embedded as one JSON constant and rendered through JSX expressions;
- callbacks over DATA are explicitly typed (strict mode rejects implicit any);
- every <button> has onClick first (or is a form submit); no href="#";
- in-page links target real section ids; ids are literal strings;
- CSS is scoped under the section's root class; hovers have :focus-visible twins;
  only transform/opacity animate and reduced motion turns everything static.
"""
from __future__ import annotations

import json
import re
from typing import Any

# ── Shared TSX helpers (injected per module when used) ──────────────────────

H_MEDIA = """
function Media({ img, priority, variant, mark, className }: any) {
  const [missing, setMissing] = useState(false);
  return (
    <div className={'k-media k-art' + (className ? ' ' + className : '')} data-variant={variant || 1}>
      {mark ? <span className="k-art__mark" aria-hidden="true">{mark}</span> : null}
      {img && !missing ? (
        <img alt={img.alt} src={img.src} width={img.w} height={img.h} loading={priority ? 'eager' : 'lazy'} fetchPriority={priority ? 'high' : 'auto'} decoding={priority ? 'sync' : 'async'} onError={() => setMissing(true)} />
      ) : null}
    </div>
  );
}
"""

H_REVEAL = """
function useReveal<T extends HTMLElement>() {
  const ref = useRef<T | null>(null);
  useEffect(() => {
    const root = ref.current;
    if (!root) return;
    const items = Array.from(root.querySelectorAll<HTMLElement>('[data-motion="scroll-reveal"]'));
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (reduce || typeof IntersectionObserver === 'undefined') {
      items.forEach((el) => el.classList.add('is-visible'));
      return;
    }
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          observer.unobserve(entry.target);
        }
      });
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.12 });
    items.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, []);
  return ref;
}
"""

H_MAGNET = """
function useMagnet<T extends HTMLElement>() {
  const ref = useRef<T | null>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const fine = window.matchMedia('(hover: hover) and (pointer: fine)').matches;
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (!fine || reduce) return;
    const move = (event: PointerEvent) => {
      if (event.pointerType !== 'mouse') return;
      const box = el.getBoundingClientRect();
      const x = ((event.clientX - box.left) / box.width - 0.5) * 16;
      const y = ((event.clientY - box.top) / box.height - 0.5) * 12;
      el.style.transform = 'translate3d(' + x.toFixed(1) + 'px, ' + y.toFixed(1) + 'px, 0)';
    };
    const leave = () => {
      el.style.transform = '';
    };
    el.addEventListener('pointermove', move);
    el.addEventListener('pointerleave', leave);
    return () => {
      el.removeEventListener('pointermove', move);
      el.removeEventListener('pointerleave', leave);
    };
  }, []);
  return ref;
}
"""

H_TILT = """
function canTilt() {
  return typeof window !== 'undefined'
    && window.matchMedia('(hover: hover) and (pointer: fine)').matches
    && !window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

function tiltMove(event: ReactPointerEvent<HTMLElement>) {
  if (event.pointerType !== 'mouse' || !canTilt()) return;
  const el = event.currentTarget;
  const box = el.getBoundingClientRect();
  const px = (event.clientX - box.left) / box.width;
  const py = (event.clientY - box.top) / box.height;
  el.style.setProperty('--k-ry', ((px - 0.5) * 8).toFixed(2) + 'deg');
  el.style.setProperty('--k-rx', ((0.5 - py) * 6).toFixed(2) + 'deg');
  el.style.setProperty('--k-mx', (px * 100).toFixed(1) + '%');
  el.style.setProperty('--k-my', (py * 100).toFixed(1) + '%');
  el.style.setProperty('--k-glow', '0.14');
}

function tiltLeave(event: ReactPointerEvent<HTMLElement>) {
  const el = event.currentTarget;
  ['--k-rx', '--k-ry', '--k-glow'].forEach((name: string) => el.style.removeProperty(name));
}
"""

H_SHADER = """
const SHADER_VS = 'attribute vec2 p;void main(){gl_Position=vec4(p,0.0,1.0);}';
const SHADER_FS = 'precision mediump float;uniform vec2 r;uniform float t;uniform vec2 m;uniform vec3 c0;uniform vec3 c1;uniform vec3 c2;'
  + 'void main(){vec2 uv=gl_FragCoord.xy/r;'
  + 'float a=sin(uv.x*3.1+t*0.35)+sin(uv.y*4.3-t*0.27)+sin((uv.x+uv.y)*2.2+t*0.21);'
  + 'float b=sin(uv.x*5.7-t*0.18+sin(uv.y*2.0+t*0.3))*0.5+0.5;'
  + 'vec3 col=mix(c0,c1,smoothstep(-1.2,1.8,a)*MIX_A);'
  + 'col=mix(col,c2,b*smoothstep(0.2,1.0,uv.y)*MIX_B);'
  + 'float g=0.12/(0.12+distance(uv,m)*2.4);col+=c1*g*0.16;'
  + 'col=mix(c0,col,smoothstep(0.0,0.38,uv.y));gl_FragColor=vec4(col,1.0);}';

function ShaderBackdrop() {
  const ref = useRef<HTMLCanvasElement | null>(null);
  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const gl = canvas.getContext('webgl', { antialias: false, alpha: false, preserveDrawingBuffer: false });
    if (!gl) {
      canvas.classList.add('is-fallback');
      return;
    }
    const compile = (type: number, source: string) => {
      const shader = gl.createShader(type);
      if (!shader) return null;
      gl.shaderSource(shader, source);
      gl.compileShader(shader);
      return gl.getShaderParameter(shader, gl.COMPILE_STATUS) ? shader : null;
    };
    const vs = compile(gl.VERTEX_SHADER, SHADER_VS);
    const fs = compile(gl.FRAGMENT_SHADER, SHADER_FS.replace('MIX_A', SHADER_MIX[0]).replace('MIX_B', SHADER_MIX[1]));
    const program = gl.createProgram();
    if (!vs || !fs || !program) {
      canvas.classList.add('is-fallback');
      return;
    }
    gl.attachShader(program, vs);
    gl.attachShader(program, fs);
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
      canvas.classList.add('is-fallback');
      return;
    }
    gl.useProgram(program);
    const buffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
    const loc = gl.getAttribLocation(program, 'p');
    gl.enableVertexAttribArray(loc);
    gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
    const uR = gl.getUniformLocation(program, 'r');
    const uT = gl.getUniformLocation(program, 't');
    const uM = gl.getUniformLocation(program, 'm');
    SHADER_COLORS.forEach((rgb: number[], i: number) => gl.uniform3f(gl.getUniformLocation(program, 'c' + i), rgb[0], rgb[1], rgb[2]));
    const pointer = { x: 0.7, y: 0.6 };
    const start = performance.now();
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    let visible = true;
    let timer = 0;
    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 1.5);
      const width = Math.max(1, Math.round(canvas.clientWidth * dpr));
      const height = Math.max(1, Math.round(canvas.clientHeight * dpr));
      if (canvas.width !== width || canvas.height !== height) {
        canvas.width = width;
        canvas.height = height;
        gl.viewport(0, 0, width, height);
      }
    };
    const draw = () => {
      resize();
      gl.uniform2f(uR, canvas.width, canvas.height);
      gl.uniform1f(uT, reduce ? 0 : (performance.now() - start) / 1000);
      gl.uniform2f(uM, pointer.x, pointer.y);
      gl.drawArrays(gl.TRIANGLES, 0, 3);
    };
    const loop = () => {
      timer = 0;
      if (!visible || document.hidden || reduce) return;
      draw();
      timer = window.setTimeout(loop, 33);
    };
    const wake = () => {
      if (!timer && visible && !document.hidden && !reduce) loop();
    };
    const host = canvas.parentElement;
    const onPointer = (event: PointerEvent) => {
      const box = canvas.getBoundingClientRect();
      pointer.x = (event.clientX - box.left) / box.width;
      pointer.y = 1 - (event.clientY - box.top) / box.height;
    };
    const resizeObserver = new ResizeObserver(() => draw());
    resizeObserver.observe(canvas);
    const io = new IntersectionObserver((entries) => {
      visible = entries.some((entry) => entry.isIntersecting);
      wake();
    });
    io.observe(canvas);
    document.addEventListener('visibilitychange', wake);
    if (host) host.addEventListener('pointermove', onPointer);
    draw();
    wake();
    return () => {
      if (timer) window.clearTimeout(timer);
      resizeObserver.disconnect();
      io.disconnect();
      document.removeEventListener('visibilitychange', wake);
      if (host) host.removeEventListener('pointermove', onPointer);
      const lose = gl.getExtension('WEBGL_lose_context');
      if (lose) lose.loseContext();
    };
  }, []);
  return <canvas ref={ref} className="k-shader" aria-hidden="true" />;
}
"""

H_PRICE = """
function parsePrice(value: string): number {
  const n = parseFloat(String(value || '').replace(/[^0-9.]/g, ''));
  return isNaN(n) ? 0 : n;
}

function useCart() {
  const [lines, setLines] = useState<any[]>([]);
  useEffect(() => {
    const onAdd = (event: Event) => {
      const detail = (event as CustomEvent).detail || {};
      if (!detail.name) return;
      setLines((current: any[]) => {
        if (current.some((line: any) => line.name === detail.name)) {
          return current.map((line: any) => (line.name === detail.name ? { ...line, qty: line.qty + 1 } : line));
        }
        return [...current, { name: detail.name, price: detail.price || '', qty: 1 }];
      });
    };
    window.addEventListener('kit-cart-add', onAdd);
    return () => window.removeEventListener('kit-cart-add', onAdd);
  }, []);
  const remove = (name: string) => setLines((current: any[]) => current.filter((line: any) => line.name !== name));
  return { lines, remove };
}

function cartTotal(lines: any[]) {
  return lines.reduce((sum: number, line: any) => sum + parsePrice(line.price) * line.qty, 0);
}

function orderBody(lines: any[], currency: string) {
  return lines.map((line: any) => line.qty + ' x ' + line.name + (line.price ? ' (' + line.price + ')' : '')).join('\\n')
    + (currency ? '\\n\\nTotal: ' + currency + cartTotal(lines).toFixed(2) : '');
}
"""

H_APP_WINDOW = """
function AppWindow({ labels, bars, title }: any) {
  return (
    <figure className="k-window">
      <div className="k-window__chrome" aria-hidden="true"><span /><span /><span /></div>
      <div className="k-window__body">
        <div className="k-window__side" aria-hidden="true">
          {labels.map((label: string, i: number) => (
            <span key={i} className={'k-window__nav' + (i === 0 ? ' is-active' : '')}>{label}</span>
          ))}
        </div>
        <div className="k-window__main">
          <p className="k-window__title">{title}</p>
          <div className="k-window__tiles">
            {labels.map((label: string, i: number) => (
              <div className="k-window__tile" key={i}>
                <span className="k-window__label">{label}</span>
                <span className="k-window__meter" aria-hidden="true"><span style={{ width: (48 + i * 17) + '%' }} /></span>
              </div>
            ))}
          </div>
          <div className="k-window__chart" aria-hidden="true">
            {bars.map((h: number, i: number) => <span key={i} style={{ height: h + '%' }} />)}
          </div>
        </div>
      </div>
      <figcaption className="k-window__caption">Illustrative interface; not live data</figcaption>
    </figure>
  );
}
"""

CSS_APP_WINDOW = """
__S__ .k-window { position: relative; margin: 0; border: 1px solid var(--k-line); border-radius: calc(var(--k-radius) + 4px); background-color: var(--k-surface); overflow: hidden; box-shadow: 0 30px 80px -40px rgba(0, 0, 0, 0.45); }
__S__ .k-window__chrome { display: flex; gap: 6px; padding: 12px 14px; border-bottom: 1px solid var(--k-line); }
__S__ .k-window__chrome span { width: 10px; height: 10px; border-radius: 50%; background-color: var(--k-line-strong); }
__S__ .k-window__body { display: grid; grid-template-columns: 160px minmax(0, 1fr); min-height: 300px; }
__S__ .k-window__side { display: grid; align-content: start; gap: 4px; padding: 16px 12px; border-right: 1px solid var(--k-line); }
__S__ .k-window__nav { padding: 8px 10px; border-radius: 8px; font-size: 0.875rem; color: var(--k-muted); }
__S__ .k-window__nav.is-active { background-color: var(--k-accent-soft); color: var(--k-ink); }
__S__ .k-window__main { display: grid; gap: 18px; padding: 20px; align-content: start; }
__S__ .k-window__title { font-weight: 600; font-size: 0.9375rem; }
__S__ .k-window__tiles { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }
__S__ .k-window__tile { display: grid; gap: 10px; padding: 14px; border: 1px solid var(--k-line); border-radius: 10px; background-color: var(--k-bg); }
__S__ .k-window__label { font-size: 0.8125rem; color: var(--k-muted); }
__S__ .k-window__meter { display: block; height: 6px; border-radius: 6px; background-color: var(--k-surface-2); overflow: hidden; }
__S__ .k-window__meter span { display: block; height: 100%; border-radius: inherit; background-color: var(--k-accent); }
__S__ .k-window__chart { display: flex; align-items: flex-end; gap: 8px; height: 140px; padding: 12px; border: 1px solid var(--k-line); border-radius: 10px; }
__S__ .k-window__chart span { flex: 1; border-radius: 4px 4px 0 0; background-image: linear-gradient(to top, var(--k-accent), var(--k-accent-2)); opacity: 0.85; }
__S__ .k-window__caption { padding: 10px 16px; border-top: 1px solid var(--k-line); font-size: 0.75rem; color: var(--k-muted); }
@media (max-width: 640px) {
  __S__ .k-window__body { grid-template-columns: minmax(0, 1fr); }
  __S__ .k-window__side { display: none; }
  __S__ .k-window__tiles { grid-template-columns: minmax(0, 1fr); }
}
"""

RESERVED_SCOPES = {"media", "art", "actions", "display", "link", "head", "text", "btn", "section", "container", "lede",
                   "muted", "eyebrow", "h2", "h3", "tilt", "stagger", "settle", "window", "shader", "sr", "rise-2",
                   "rise-3", "depth-slow", "depth-fast"}


def scope_class(slug: str) -> str:
    return ("k-sec-" if slug in RESERVED_SCOPES else "k-") + slug


def _json_const(data: Any) -> str:
    text = json.dumps(data, ensure_ascii=False, indent=2)
    text = text.replace("</", "<\\/")
    # Keep strings from looking like import statements to naive scanners.
    text = re.sub(r"\b(from|import)(\s*)(?=[\"'])", lambda m: "\\u00" + format(ord(m.group(1)[0]), "x") + m.group(1)[1:] + m.group(2), text)
    return text


def _type_callbacks(code: str) -> str:
    code = re.sub(r"\.map\(\((\w+)\)\s*=>", r".map((\1: any) =>", code)
    code = re.sub(r"\.map\(\((\w+),\s*(\w+)\)\s*=>", r".map((\1: any, \2: number) =>", code)
    return code


def assemble(name: str, data: Any, body: str, helpers: list[str], extra_top: str = "") -> str:
    """Build a module: imports for hooks actually used, DATA, helpers, component, exports."""
    helper_code = "".join(helpers)
    full = helper_code + body
    hooks = [h for h in ("useEffect", "useRef", "useState") if re.search(rf"\b{h}\s*[<(]", full)]
    types = []
    if "ReactPointerEvent" in full:
        types.append("PointerEvent as ReactPointerEvent")
    if "ReactKeyboardEvent" in full:
        types.append("KeyboardEvent as ReactKeyboardEvent")
    if "ReactFormEvent" in full:
        types.append("FormEvent as ReactFormEvent")
    lines = []
    if hooks:
        lines.append("import { " + ", ".join(hooks) + " } from 'react';")
    if types:
        lines.append("import type { " + ", ".join(types) + " } from 'react';")
    if "flushSync" in full:
        lines.append("import { flushSync } from 'react-dom';")
    lines.append(f"import './{name}.css';")
    module = "\n".join(lines) + "\n\nconst DATA: any = " + _json_const(data) + ";\n" + extra_top + helper_code + "\n" + body.strip() + \
        f"\n\nexport default {name};\n"
    return _type_callbacks(module)


def _fill(template: str, **values: str) -> str:
    for key, value in values.items():
        template = template.replace(f"__{key}__", value)
    return template


def _section_open(slug: str, scope: str, tint: bool, reveal: bool, extra_class: str = "") -> str:
    classes = "k-section" + (" k-section--tint" if tint else "") + f" {scope}" + (f" {extra_class}" if extra_class else "")
    ref = " ref={revealRef}" if reveal else ""
    return f'<section id="{slug}" className="{classes}" aria-labelledby="{slug}-title" data-section="{slug}"{ref}>'


def _reveal_hook(reveal: bool) -> str:
    return "  const revealRef = useReveal<HTMLElement>();\n" if reveal else ""


def _ra(reveal: bool) -> str:
    return ' data-motion="scroll-reveal"' if reveal else ""


def _head(slug: str, split: bool = True, eyebrow: bool = False) -> str:
    cls = "k-head k-head--split" if split else "k-head"
    brow = '{DATA.eyebrow ? <p className="k-eyebrow">{DATA.eyebrow}</p> : null}\n            ' if eyebrow else ""
    return (f'<div className="{cls}">\n          <div>\n            {brow}<h2 id="{slug}-title" className="k-h2">{{DATA.title}}</h2>\n          </div>\n'
            f'          {{DATA.intro ? <p className="k-lede">{{DATA.intro}}</p> : null}}\n        </div>')


# ── Renderers ───────────────────────────────────────────────────────────────

def render_header(site, slug: str, content: dict) -> tuple[str, str]:
    name = site.component(slug)
    data = content
    body = """
export function __NAME__() {
  const [open, setOpen] = useState(false);
  const [tucked, setTucked] = useState(false);
  const [active, setActive] = useState('');
  const [cartOpen, setCartOpen] = useState(false);
  const toggleRef = useRef<HTMLButtonElement | null>(null);
  const cartButtonRef = useRef<HTMLButtonElement | null>(null);
  const firstLinkRef = useRef<HTMLAnchorElement | null>(null);
  const cart = useCart();
  const count = cart.lines.reduce((sum: number, line: any) => sum + line.qty, 0);

  useEffect(() => {
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)');
    let last = window.scrollY;
    let pending = 0;
    const settle = () => {
      pending = 0;
      const y = window.scrollY;
      if (y > last + 4 && y > 120 && !reduce.matches) setTucked(true);
      else if (y < last - 4 || y <= 120) setTucked(false);
      last = y;
    };
    const onScroll = () => {
      if (!pending) pending = window.setTimeout(settle, 80);
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => {
      window.removeEventListener('scroll', onScroll);
      if (pending) window.clearTimeout(pending);
    };
  }, []);

  useEffect(() => {
    if (typeof IntersectionObserver === 'undefined') return;
    const targets = DATA.links
      .map((link: any) => document.getElementById(link.id))
      .filter((el: HTMLElement | null) => Boolean(el)) as HTMLElement[];
    if (!targets.length) return;
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) setActive(entry.target.id);
      });
    }, { rootMargin: '-45% 0px -50% 0px' });
    targets.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!open && !cartOpen) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    if (open) firstLinkRef.current?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return;
      if (open) {
        setOpen(false);
        toggleRef.current?.focus();
      }
      if (cartOpen) {
        setCartOpen(false);
        cartButtonRef.current?.focus();
      }
    };
    const desktop = window.matchMedia('(min-width: 900px)');
    const onWide = () => {
      if (desktop.matches) setOpen(false);
    };
    document.addEventListener('keydown', onKey);
    desktop.addEventListener('change', onWide);
    return () => {
      document.body.style.overflow = previous;
      document.removeEventListener('keydown', onKey);
      desktop.removeEventListener('change', onWide);
    };
  }, [open, cartOpen]);

  const closeMenu = () => {
    setOpen(false);
    toggleRef.current?.focus();
  };

  return (
    <>
      <header className={'k-header' + (tucked && !open && !cartOpen ? ' is-tucked' : '')} data-section="header">
        <div className="k-container k-header__bar">
          <a className="k-header__brand" href="#site-main">{DATA.brand}</a>
          {DATA.links.length ? (
            <nav className="k-header__nav" aria-label="Primary">
              <ul className="k-header__links">
                {DATA.links.map((link: any) => (
                  <li key={link.id}>
                    <a className="k-header__link" href={link.href} aria-current={active === link.id ? 'location' : undefined}>{link.label}</a>
                  </li>
                ))}
              </ul>
            </nav>
          ) : null}
          <div className="k-header__tools">
            {DATA.store ? (
              <button onClick={() => setCartOpen(!cartOpen)} ref={cartButtonRef} type="button" className="k-header__cart" data-cart-count={count} aria-label={'Cart, ' + count + (count === 1 ? ' item' : ' items')} aria-expanded={cartOpen} aria-controls="site-cart-panel">
                <span>Cart</span>
                <span className="k-header__count" aria-hidden="true">{count}</span>
              </button>
            ) : null}
            {DATA.cta ? <a className="k-btn k-btn--primary k-header__cta" href={DATA.cta.href}>{DATA.cta.label}</a> : null}
            <button onClick={() => setOpen(true)} ref={toggleRef} type="button" className="k-header__toggle" aria-expanded={open} aria-controls="site-menu" aria-label="Open menu">
              <span className="k-header__burger" aria-hidden="true" />
            </button>
          </div>
        </div>
      </header>
      <div id="site-menu" className={'k-header__drawer' + (open ? ' is-open' : '')} role="dialog" aria-modal="true" aria-label="Site menu" inert={!open}>
        <div className="k-header__drawer-top">
          <span className="k-header__brand">{DATA.brand}</span>
          <button onClick={closeMenu} type="button" className="k-header__close" aria-label="Close menu">Close</button>
        </div>
        <nav aria-label="Mobile">
          <ul className="k-header__drawer-links">
            {DATA.links.map((link: any, i: number) => (
              <li key={link.id}>
                <a ref={i === 0 ? firstLinkRef : undefined} onClick={() => setOpen(false)} className="k-header__drawer-link" href={link.href} aria-current={active === link.id ? 'location' : undefined}>{link.label}</a>
              </li>
            ))}
          </ul>
        </nav>
        {DATA.cta ? <a onClick={() => setOpen(false)} className="k-btn k-btn--primary k-header__drawer-cta" href={DATA.cta.href}>{DATA.cta.label}</a> : null}
        {DATA.email ? <a className="k-link k-header__drawer-mail" href={'mailto:' + DATA.email}>{DATA.email}</a> : null}
      </div>
      {DATA.store ? (
        <div id="site-cart-panel" className={'k-header__cartpanel' + (cartOpen ? ' is-open' : '')} role="dialog" aria-modal="true" aria-label="Cart" inert={!cartOpen}>
          <div className="k-header__drawer-top">
            <p className="k-header__cart-title">Your cart</p>
            <button onClick={() => { setCartOpen(false); cartButtonRef.current?.focus(); }} type="button" className="k-header__close" aria-label="Close cart">Close</button>
          </div>
          {cart.lines.length ? (
            <ul className="k-header__lines">
              {cart.lines.map((line: any) => (
                <li key={line.name} className="k-header__line">
                  <span>{line.qty} × {line.name}</span>
                  <span>{line.price}</span>
                  <button onClick={() => cart.remove(line.name)} type="button" className="k-header__remove" aria-label={'Remove ' + line.name}>Remove</button>
                </li>
              ))}
            </ul>
          ) : (
            <p className="k-header__empty">Your cart is empty. Add something you like and it will appear here.</p>
          )}
          {cart.lines.length && DATA.currency ? <p className="k-header__total">Total {DATA.currency}{cartTotal(cart.lines).toFixed(2)}</p> : null}
          <p className="k-header__note">{DATA.checkoutNote}</p>
          {cart.lines.length && DATA.email ? (
            <a className="k-btn k-btn--primary" href={'mailto:' + DATA.email + '?subject=' + encodeURIComponent(`Order from ${DATA.brand}`) + '&body=' + encodeURIComponent(orderBody(cart.lines, DATA.currency))}>Email this order</a>
          ) : null}
        </div>
      ) : null}
    </>
  );
}
"""
    css = """
.k-header { position: sticky; top: 0; z-index: 50; height: var(--k-header-h); background-color: var(--k-glass); -webkit-backdrop-filter: saturate(1.4) blur(14px); backdrop-filter: saturate(1.4) blur(14px); border-bottom: 1px solid var(--k-line); transition: transform 320ms var(--k-ease); }
.k-header.is-tucked { transform: translateY(-100%); }
.k-header .k-header__bar { height: 100%; display: flex; align-items: center; gap: var(--k-space-3); }
.k-header__brand { display: inline-flex; align-items: center; min-height: var(--k-tap); max-width: 62vw; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-family: var(--k-font-display); font-weight: var(--k-display-weight); font-size: 1.375rem; letter-spacing: -0.01em; text-transform: var(--k-display-case); text-decoration: none; }
.k-header .k-header__nav { margin-left: auto; }
.k-header .k-header__links { display: flex; gap: 2px; }
.k-header .k-header__link { position: relative; display: inline-flex; align-items: center; min-height: var(--k-tap); padding: 0 0.75rem; font-size: 0.9375rem; font-weight: 500; color: var(--k-muted); text-decoration: none; transition: color 160ms ease; }
.k-header .k-header__link::after { content: ""; position: absolute; left: 0.75rem; right: 0.75rem; bottom: 8px; height: 2px; background-color: var(--k-accent); transform: scaleX(0); transform-origin: left; transition: transform 220ms var(--k-ease); }
.k-header .k-header__link:hover, .k-header .k-header__link:focus-visible, .k-header .k-header__link[aria-current="location"] { color: var(--k-ink); }
.k-header .k-header__link:hover::after, .k-header .k-header__link:focus-visible::after, .k-header .k-header__link[aria-current="location"]::after { transform: scaleX(1); }
.k-header .k-header__tools { display: flex; align-items: center; gap: var(--k-space-1); margin-left: auto; }
.k-header .k-header__nav ~ .k-header__tools { margin-left: var(--k-space-2); }
.k-header .k-header__cart { display: inline-flex; align-items: center; gap: 0.5rem; min-height: var(--k-tap); padding: 0 0.875rem; border: 1px solid var(--k-line-strong); border-radius: var(--k-radius-btn); background-color: transparent; font-weight: 600; transition: border-color 160ms ease, transform 160ms var(--k-ease); }
.k-header .k-header__cart:hover, .k-header .k-header__cart:focus-visible { border-color: var(--k-ink); }
.k-header .k-header__cart:active, .k-header .k-header__toggle:active { transform: scale(0.98); }
.k-header .k-header__count { display: inline-grid; place-items: center; min-width: 1.5rem; height: 1.5rem; padding: 0 0.375rem; border-radius: 999px; background-color: var(--k-accent); color: var(--k-accent-ink); font-size: 0.75rem; }
.k-header .k-header__cta { min-height: var(--k-tap); padding: 0 1.125rem; font-size: 0.9375rem; }
.k-header .k-header__toggle { display: none; align-items: center; justify-content: center; width: var(--k-tap); height: var(--k-tap); border: 1px solid var(--k-line-strong); border-radius: var(--k-radius-btn); background-color: transparent; transition: border-color 160ms ease, transform 160ms var(--k-ease); }
.k-header .k-header__toggle:hover, .k-header .k-header__toggle:focus-visible { border-color: var(--k-ink); }
.k-header .k-header__burger, .k-header .k-header__burger::before, .k-header .k-header__burger::after { display: block; width: 18px; height: 2px; border-radius: 2px; background-color: currentColor; }
.k-header .k-header__burger { position: relative; }
.k-header .k-header__burger::before, .k-header .k-header__burger::after { content: ""; position: absolute; left: 0; }
.k-header .k-header__burger::before { top: -6px; }
.k-header .k-header__burger::after { top: 6px; }
@media (max-width: 899px) {
  .k-header .k-header__nav { display: none; }
  .k-header .k-header__toggle { display: inline-flex; }
  .k-header .k-header__nav ~ .k-header__tools { margin-left: auto; }
}
@media (max-width: 599px) { .k-header .k-header__cta { display: none; } }

.k-header__drawer, .k-header__cartpanel { position: fixed; z-index: 60; display: flex; flex-direction: column; gap: var(--k-space-4); overflow-y: auto; visibility: hidden; opacity: 0; transition: opacity 240ms var(--k-ease), transform 240ms var(--k-ease), visibility 0s linear 240ms; }
.k-header__drawer { inset: 0; padding: 14px var(--k-gutter) 32px; background-color: var(--k-bg); color: var(--k-ink); transform: translateY(-12px); }
.k-header__cartpanel { top: 0; right: 0; bottom: 0; width: min(420px, 100%); padding: 14px 24px 32px; background-color: var(--k-surface); color: var(--k-ink); border-left: 1px solid var(--k-line); box-shadow: -24px 0 60px -30px rgba(0, 0, 0, 0.35); transform: translateX(24px); }
.k-header__drawer.is-open, .k-header__cartpanel.is-open { visibility: visible; opacity: 1; transform: none; transition: opacity 240ms var(--k-ease), transform 240ms var(--k-ease), visibility 0s; }
.k-header__drawer-top { display: flex; align-items: center; justify-content: space-between; min-height: 44px; }
.k-header__close { min-height: var(--k-tap); padding: 0 1rem; border: 1px solid var(--k-line-strong); border-radius: var(--k-radius-btn); background-color: transparent; font-weight: 600; transition: border-color 160ms ease; }
.k-header__close:hover, .k-header__close:focus-visible { border-color: var(--k-ink); }
.k-header__drawer-links { display: grid; margin-top: var(--k-space-2); }
.k-header__drawer-link { display: flex; align-items: center; min-height: 60px; border-bottom: 1px solid var(--k-line); font-family: var(--k-font-display); font-weight: var(--k-display-weight); font-size: clamp(1.75rem, 7vw, 2.5rem); text-transform: var(--k-display-case); text-decoration: none; transition: color 160ms ease, transform 200ms var(--k-ease); }
.k-header__drawer-link:hover, .k-header__drawer-link:focus-visible { transform: translateX(6px); }
.k-header__drawer-link[aria-current="location"] { color: var(--k-accent-text); }
.k-header__drawer-cta { align-self: flex-start; }
.k-header__drawer-mail { min-height: var(--k-tap); display: inline-flex; align-items: center; }
.k-header__cart-title { font-weight: 700; font-size: 1.125rem; }
.k-header__lines { display: grid; gap: var(--k-space-2); }
.k-header__line { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 4px 12px; padding-bottom: 12px; border-bottom: 1px solid var(--k-line); }
.k-header__remove { justify-self: start; min-height: var(--k-tap); padding: 0; border: 0; background-color: transparent; color: var(--k-muted); text-decoration: underline; text-underline-offset: 0.2em; }
.k-header__remove:hover, .k-header__remove:focus-visible { color: var(--k-ink); }
.k-header__empty, .k-header__note { color: var(--k-muted); }
.k-header__total { font-weight: 700; }
@media (prefers-reduced-motion: reduce) {
  .k-header, .k-header__drawer, .k-header__cartpanel { transition: none; }
  .k-header.is-tucked { transform: none; }
}
"""
    return assemble(name, data, _fill(body, NAME=name), [H_PRICE]), css


def render_footer(site, slug: str, content: dict) -> tuple[str, str]:
    name = site.component(slug)
    body = """
export function __NAME__() {
  const [privacy, setPrivacy] = useState(false);
  const year = new Date().getFullYear();
  return (
    <footer id="site-footer" className="k-footer" data-section="footer">
      <div className="k-container k-footer__grid">
        <div className="k-footer__brand">
          <a className="k-footer__wordmark" href="#site-main">{DATA.brand}</a>
          {DATA.tagline ? <p className="k-footer__tagline">{DATA.tagline}</p> : null}
          {DATA.cta ? <a className="k-btn k-btn--ghost k-footer__cta" href={DATA.cta.href}>{DATA.cta.label}</a> : null}
        </div>
        {DATA.links.length ? (
          <nav className="k-footer__col" aria-label="Footer">
            <p className="k-footer__label">Explore</p>
            <ul className="k-footer__links">
              {DATA.links.map((link: any) => (
                <li key={link.id}><a className="k-footer__link" href={link.href}>{link.label}</a></li>
              ))}
            </ul>
          </nav>
        ) : null}
        <div className="k-footer__col">
          <p className="k-footer__label">Contact</p>
          <ul className="k-footer__links">
            {DATA.email ? <li><a className="k-footer__link" href={'mailto:' + DATA.email}>{DATA.email}</a></li> : null}
            {DATA.location ? <li><span className="k-footer__plain">{DATA.location}</span></li> : null}
            {!DATA.email && DATA.contactHref ? <li><a className="k-footer__link" href={DATA.contactHref}>Send a message</a></li> : null}
            {!DATA.email && !DATA.contactHref ? <li><span className="k-footer__plain">Contact details coming from {DATA.brand} directly.</span></li> : null}
          </ul>
        </div>
      </div>
      <div className="k-container k-footer__base">
        <p>© {year} {DATA.brand}</p>
        <div className="k-footer__base-links">
          <button onClick={() => setPrivacy(!privacy)} type="button" className="k-footer__privacy-toggle" aria-expanded={privacy} aria-controls="footer-privacy">Privacy</button>
          <a className="k-footer__link" href="#site-main">Back to top</a>
        </div>
      </div>
      <div id="footer-privacy" className="k-container k-footer__privacy" hidden={!privacy}>
        <p>{DATA.privacy}</p>
      </div>
    </footer>
  );
}
"""
    css = """
.k-footer { padding-block: clamp(56px, 8vw, 96px) 32px; background-color: var(--k-surface); color: var(--k-ink); border-top: 1px solid var(--k-line); }
.k-footer .k-footer__grid { display: grid; grid-template-columns: minmax(0, 1.4fr) repeat(2, minmax(0, 1fr)); gap: var(--k-space-6); }
.k-footer .k-footer__brand { display: grid; gap: var(--k-space-2); align-content: start; justify-items: start; }
.k-footer .k-footer__wordmark { font-family: var(--k-font-display); font-weight: var(--k-display-weight); font-size: clamp(1.75rem, 3vw, 2.5rem); line-height: 1.05; text-transform: var(--k-display-case); text-decoration: none; }
.k-footer .k-footer__tagline { max-width: 34ch; color: var(--k-muted); }
.k-footer .k-footer__cta { margin-top: var(--k-space-1); }
.k-footer .k-footer__label { margin-bottom: var(--k-space-1); font-size: 0.8125rem; font-weight: 600; letter-spacing: 0.12em; text-transform: uppercase; color: var(--k-muted); }
.k-footer .k-footer__links { display: grid; }
.k-footer .k-footer__link, .k-footer .k-footer__plain { display: inline-flex; align-items: center; min-height: var(--k-tap); text-decoration: none; overflow-wrap: anywhere; }
.k-footer .k-footer__link { text-decoration: underline; text-decoration-color: transparent; text-underline-offset: 0.22em; transition: text-decoration-color 160ms ease; }
.k-footer .k-footer__link:hover, .k-footer .k-footer__link:focus-visible { text-decoration-color: currentColor; }
.k-footer .k-footer__base { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: var(--k-space-2); margin-top: var(--k-space-8); padding-top: var(--k-space-3); border-top: 1px solid var(--k-line); font-size: 0.875rem; color: var(--k-muted); }
.k-footer .k-footer__base-links { display: flex; gap: var(--k-space-3); align-items: center; }
.k-footer .k-footer__privacy-toggle { min-height: var(--k-tap); padding: 0; border: 0; background-color: transparent; color: inherit; text-decoration: underline; text-underline-offset: 0.22em; }
.k-footer .k-footer__privacy-toggle:hover, .k-footer .k-footer__privacy-toggle:focus-visible { color: var(--k-ink); }
.k-footer .k-footer__privacy p { max-width: 70ch; margin-top: var(--k-space-2); font-size: 0.875rem; color: var(--k-muted); }
@media (max-width: 760px) { .k-footer .k-footer__grid { grid-template-columns: minmax(0, 1fr); } }
"""
    return assemble(name, content, _fill(body, NAME=name), []), css


def render_hero(site, slug: str, content: dict) -> tuple[str, str]:
    name = site.component(slug)
    style = content.get("style", "split")
    helpers = [H_MEDIA, H_MAGNET]
    shader = bool(content.get("shader"))
    extra_top = ""
    if shader:
        helpers.append(H_SHADER)
        extra_top = ("const SHADER_COLORS: number[][] = " + json.dumps(content.get("shader_colors")) + ";\n"
                     "const SHADER_MIX: string[] = " + json.dumps(content.get("shader_mix")) + ";\n")
    if style == "product":
        helpers.append(H_APP_WINDOW)
    copy = """
          {DATA.tagline ? <p className="k-eyebrow k-hero__eyebrow k-rise-2">{DATA.tagline}</p> : null}
          <h1 id="__SLUG__-title" className="k-display k-hero__title" data-motion="text-in">{DATA.headline}</h1>
          <p className="k-lede k-hero__lede k-rise-2">{DATA.lede}</p>
          <div className="k-actions k-rise-3">
            <a ref={magnetRef} className="k-btn k-btn--primary" href={DATA.primary.href}>{DATA.primary.label}</a>
            <a className="k-btn k-btn--ghost k-hero__ghost" href={DATA.secondary.href}>{DATA.secondary.label}</a>
          </div>
          {DATA.fact ? <p className="k-hero__fact k-rise-3">{DATA.fact}</p> : null}"""
    shader_jsx = "\n      <ShaderBackdrop />" if shader else ""
    if style == "fullbleed":
        inner = f"""
      <div className="k-hero__bg">
        <Media img={{DATA.img}} priority={{true}} variant={{1}} className="k-hero__bgmedia" />
      </div>
      <div className="k-hero__shade" aria-hidden="true" />{shader_jsx}
      <div className="k-container k-hero__inner">
        <div className="k-hero__copy">{copy}
        </div>
      </div>"""
    elif style == "typographic":
        inner = f"""{shader_jsx}
      <div className="k-container k-hero__inner">
        <div className="k-hero__copy">
          {{DATA.tagline ? <p className="k-eyebrow k-rise-2">{{DATA.tagline}}</p> : null}}
          <h1 id="__SLUG__-title" className="k-display k-hero__title" data-motion="text-in">{{DATA.headline}}</h1>
          <div className="k-hero__rule" aria-hidden="true" />
          <div className="k-hero__row">
            <p className="k-lede k-hero__lede k-rise-2">{{DATA.lede}}</p>
            <div className="k-actions k-rise-3">
              <a ref={{magnetRef}} className="k-btn k-btn--primary" href={{DATA.primary.href}}>{{DATA.primary.label}}</a>
              <a className="k-btn k-btn--ghost k-hero__ghost" href={{DATA.secondary.href}}>{{DATA.secondary.label}}</a>
            </div>
          </div>
          {{DATA.fact ? <p className="k-hero__fact k-rise-3">{{DATA.fact}}</p> : null}}
        </div>
        {{DATA.img ? (
          <div className="k-hero__strip k-depth-fast">
            <Media img={{DATA.img}} priority={{true}} variant={{2}} className="k-hero__stripmedia" />
          </div>
        ) : null}}
      </div>"""
    elif style == "product":
        inner = f"""{shader_jsx}
      <div className="k-container k-hero__inner">
        <div className="k-hero__copy k-hero__copy--center">{copy}
        </div>
        <div className="k-hero__product k-depth-fast">
          <AppWindow labels={{DATA.window.labels}} bars={{DATA.window.bars}} title={{DATA.window.title}} />
        </div>
      </div>"""
    else:
        inner = f"""{shader_jsx}
      <div className="k-container k-hero__inner">
        <div className="k-hero__copy">{copy}
        </div>
        <div className="k-hero__visual k-depth-slow">
          <Media img={{DATA.img}} priority={{true}} variant={{1}} mark={{DATA.mark}} className="k-hero__media" />
        </div>
      </div>"""
    body = f"""
export function __NAME__() {{
  const magnetRef = useMagnet<HTMLAnchorElement>();
  return (
    <section id="__SLUG__" className="k-section k-hero k-hero--{style}" aria-labelledby="__SLUG__-title" data-section="__SLUG__">{inner}
    </section>
  );
}}
"""
    css = """
.k-hero { position: relative; overflow: hidden; isolation: isolate; padding-block: clamp(48px, 7vw, 104px) clamp(64px, 9vw, 128px); }
.k-hero .k-hero__inner { position: relative; z-index: 1; }
.k-hero .k-hero__copy { display: grid; gap: var(--k-space-3); justify-items: start; align-content: center; }
.k-hero .k-hero__title { max-width: 14ch; }
.k-hero .k-hero__lede { max-width: 40ch; }
.k-hero .k-actions { margin-top: var(--k-space-1); }
.k-hero .k-hero__fact { font-size: 0.9375rem; color: var(--k-muted); }
.k-hero .k-hero__fact::before { content: ""; display: inline-block; width: 24px; height: 1px; margin-right: 10px; vertical-align: middle; background-color: currentColor; }
.k-hero .k-shader { position: absolute; inset: 0; z-index: 0; width: 100%; height: 100%; pointer-events: none; }
.k-hero .k-shader.is-fallback { background-image: radial-gradient(70% 60% at 70% 30%, var(--k-accent-soft), transparent 70%), radial-gradient(50% 50% at 20% 80%, var(--k-surface-2), transparent 70%); }

.k-hero--split .k-hero__inner { display: grid; grid-template-columns: minmax(0, 1.05fr) minmax(0, 0.95fr); gap: clamp(32px, 6vw, 88px); align-items: center; min-height: min(78vh, 760px); }
.k-hero--split .k-hero__media { aspect-ratio: 4 / 5; width: 100%; }
@media (max-width: 860px) {
  .k-hero--split .k-hero__inner { grid-template-columns: minmax(0, 1fr); min-height: 0; }
  .k-hero--split .k-hero__media { aspect-ratio: 4 / 3; }
}

.k-hero--fullbleed { display: flex; align-items: flex-end; min-height: min(calc(100svh - var(--k-header-h)), 900px); padding-block: clamp(120px, 18vh, 200px) clamp(48px, 8vh, 96px); background-color: #121212; color: #FFFFFF; }
.k-hero--fullbleed .k-hero__inner { width: 100%; }
.k-hero--fullbleed .k-hero__bg { position: absolute; inset: 0; z-index: -2; }
.k-hero--fullbleed .k-hero__bgmedia { position: absolute; inset: 0; border-radius: 0; }
.k-hero--fullbleed .k-hero__shade { position: absolute; inset: 0; z-index: -1; background-image: linear-gradient(90deg, rgba(10, 10, 12, 0.62) 0%, rgba(10, 10, 12, 0.28) 58%, rgba(10, 10, 12, 0) 100%), linear-gradient(180deg, rgba(10, 10, 12, 0.2) 0%, rgba(10, 10, 12, 0.3) 45%, var(--k-shade) 100%); }
.k-hero--fullbleed .k-hero__title { max-width: 16ch; }
.k-hero--fullbleed .k-hero__lede, .k-hero--fullbleed .k-hero__fact, .k-hero--fullbleed .k-hero__eyebrow { color: rgba(255, 255, 255, 0.88); }
.k-hero--fullbleed .k-hero__ghost { color: #FFFFFF; border-color: rgba(255, 255, 255, 0.55); }
.k-hero--fullbleed .k-hero__ghost:hover, .k-hero--fullbleed .k-hero__ghost:focus-visible { border-color: #FFFFFF; }

.k-hero--typographic .k-hero__title { max-width: 18ch; font-size: clamp(3rem, 9vw, 8.25rem); }
.k-hero--typographic .k-hero__rule { width: 100%; height: 1px; margin-block: var(--k-space-3); background-color: var(--k-line-strong); }
.k-hero--typographic .k-hero__row { display: flex; flex-wrap: wrap; align-items: flex-end; justify-content: space-between; gap: var(--k-space-4); width: 100%; }
.k-hero--typographic .k-hero__strip { margin-top: clamp(40px, 6vw, 80px); }
.k-hero--typographic .k-hero__stripmedia { aspect-ratio: 21 / 9; width: 100%; }
@media (max-width: 640px) { .k-hero--typographic .k-hero__stripmedia { aspect-ratio: 4 / 3; } }

.k-hero--product .k-hero__copy--center { justify-items: center; text-align: center; margin-inline: auto; max-width: 900px; }
.k-hero--product .k-hero__title { max-width: 18ch; }
.k-hero--product .k-hero__lede { margin-inline: auto; }
.k-hero--product .k-actions { justify-content: center; }
.k-hero--product .k-hero__product { max-width: 1040px; margin: clamp(40px, 6vw, 72px) auto 0; }
""" + CSS_APP_WINDOW.replace("__S__", ".k-hero")
    data = dict(content)
    return assemble(name, data, _fill(body, NAME=name, SLUG=slug), helpers, extra_top), css


def _tilt_attrs(site) -> str:
    return " onPointerMove={tiltMove} onPointerLeave={tiltLeave}" if site.theme.lively else ""


def render_features(site, slug: str, content: dict, members: bool = False) -> tuple[str, str]:
    name, scope = site.component(slug), scope_class(slug)
    reveal = site.reveal_section == slug
    key = "members" if members else "items"
    items = content.get(key, [])
    layout = "rows" if (site.theme.rule or len(items) in (2, 4)) else "grid"
    title_expr = "{item.name || item.role || item.title}" if members else "{item.title}"
    role_line = '\n              {item.name && item.role ? <p className="__SC__-role">{item.role}</p> : null}' if members else ""
    body = f"""
export function __NAME__() {{
{_reveal_hook(reveal)}  return (
    {_section_open(slug, scope, site.tints.get(slug, False), reveal)}
      <div className="k-container">
        {_head(slug)}
        <ul className="__SC__-list __SC__-list--{layout} k-stagger">
          {{DATA.{key}.map((item: any, i: number) => (
            <li className="__SC__-item" key={{i}}{_ra(reveal)}>
              <span className="__SC__-index" aria-hidden="true">{{String(i + 1).padStart(2, '0')}}</span>
              <h3 className="k-h3">{title_expr}</h3>{role_line}
              {{item.text ? <p className="k-muted">{{item.text}}</p> : null}}
            </li>
          ))}}
        </ul>
      </div>
    </section>
  );
}}
"""
    css = """
.__SC__ .__SC__-list--grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 250px), 1fr)); gap: clamp(28px, 4vw, 48px) clamp(24px, 3vw, 40px); }
.__SC__ .__SC__-list--grid .__SC__-item { display: grid; gap: var(--k-space-2); align-content: start; padding-top: var(--k-space-3); border-top: 2px solid var(--k-ink); }
.__SC__ .__SC__-list--rows { display: grid; border-top: 1px solid var(--k-line-strong); }
.__SC__ .__SC__-list--rows .__SC__-item { display: grid; grid-template-columns: 64px minmax(0, 0.9fr) minmax(0, 1.1fr); gap: var(--k-space-3) var(--k-space-6); align-items: baseline; padding-block: clamp(22px, 3vw, 36px); border-bottom: 1px solid var(--k-line-strong); }
.__SC__ .__SC__-index { font-size: 0.8125rem; font-weight: 600; letter-spacing: 0.08em; color: var(--k-accent-text); font-variant-numeric: tabular-nums; }
.__SC__ .__SC__-role { font-size: 0.875rem; font-weight: 600; color: var(--k-accent-text); }
.__SC__ .__SC__-item p { max-width: 52ch; }
@media (max-width: 760px) {
  .__SC__ .__SC__-list--rows .__SC__-item { grid-template-columns: minmax(0, 1fr); gap: var(--k-space-1); }
}
"""
    return assemble(name, content, _fill(body, NAME=name).replace("__SC__", scope), [H_REVEAL] if reveal else []), css.replace("__SC__", scope)


def render_story(site, slug: str, content: dict) -> tuple[str, str]:
    name, scope = site.component(slug), scope_class(slug)
    reveal = site.reveal_section == slug
    side = "right" if site.section_index(slug) % 2 else "left"
    body = f"""
export function __NAME__() {{
{_reveal_hook(reveal)}  return (
    {_section_open(slug, scope, site.tints.get(slug, False), reveal)}
      <div className="k-container __SC__-grid __SC__-grid--{side} k-stagger">
        <div className="__SC__-visual"{_ra(reveal)}>
          <Media img={{DATA.img}} variant={{2}} mark={{DATA.mark}} className="__SC__-media k-settle" />
        </div>
        <div className="__SC__-copy"{_ra(reveal)}>
          {{DATA.eyebrow ? <p className="k-eyebrow">{{DATA.eyebrow}}</p> : null}}
          <h2 id="{slug}-title" className="k-h2">{{DATA.title}}</h2>
          {{DATA.intro ? <p className="k-lede">{{DATA.intro}}</p> : null}}
          {{DATA.paragraphs.map((p: string, i: number) => (
            <p key={{i}} className={{i === 0 ? 'k-text __SC__-first' : 'k-text k-muted'}}>{{p}}</p>
          ))}}
          {{DATA.bullets.length ? (
            <ul className="__SC__-list">
              {{DATA.bullets.map((b: string, i: number) => <li key={{i}}>{{b}}</li>)}}
            </ul>
          ) : null}}
        </div>
      </div>
    </section>
  );
}}
"""
    css = """
.__SC__ .__SC__-grid { display: grid; grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr); gap: clamp(32px, 7vw, 112px); align-items: center; }
.__SC__ .__SC__-grid--right .__SC__-visual { order: 2; }
.__SC__ .__SC__-media { aspect-ratio: 4 / 5; width: 100%; }
.__SC__ .__SC__-copy { display: grid; gap: var(--k-space-3); justify-items: start; }
.__SC__ .__SC__-first { font-size: clamp(1.125rem, 1.5vw, 1.25rem); line-height: 1.55; }
.__SC__ .__SC__-list { display: grid; gap: var(--k-space-1); margin-top: var(--k-space-1); }
.__SC__ .__SC__-list li { display: flex; gap: 12px; align-items: baseline; font-weight: 500; }
.__SC__ .__SC__-list li::before { content: ""; flex: 0 0 18px; height: 2px; transform: translateY(-4px); background-color: var(--k-accent); }
@media (max-width: 860px) {
  .__SC__ .__SC__-grid { grid-template-columns: minmax(0, 1fr); }
  .__SC__ .__SC__-grid--right .__SC__-visual { order: 0; }
  .__SC__ .__SC__-media { aspect-ratio: 4 / 3; }
}
"""
    helpers = [H_MEDIA] + ([H_REVEAL] if reveal else [])
    return assemble(name, content, _fill(body, NAME=name).replace("__SC__", scope), helpers), css.replace("__SC__", scope)


def render_work(site, slug: str, content: dict) -> tuple[str, str]:
    name, scope = site.component(slug), scope_class(slug)
    reveal = site.reveal_section == slug
    items = content.get("items", [])
    reel = len(items) >= 4 and all(item.get("img") for item in items)
    tilt = site.theme.lively
    tilt_cls = " k-tilt" if tilt else ""
    helpers = [H_MEDIA] + ([H_REVEAL] if reveal else []) + ([H_TILT] if tilt else [])
    card = f"""<figure className="__SC__-figure{tilt_cls}"{_tilt_attrs(site)}>
                <Media img={{item.img}} variant={{(i % 3) + 1}} mark={{item.title.charAt(0)}} className="__SC__-media" />
                <figcaption className="__SC__-caption">
                  <h3 className="k-h3">{{item.title}}</h3>
                  {{item.caption ? <p className="k-muted">{{item.caption}}</p> : null}}
                </figcaption>
              </figure>"""
    if reel:
        body = f"""
export function __NAME__() {{
{_reveal_hook(reveal)}  const trackRef = useRef<HTMLDivElement | null>(null);
  const page = (direction: number) => {{
    const track = trackRef.current;
    if (!track) return;
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    track.scrollBy({{ left: direction * track.clientWidth * 0.8, behavior: reduce ? 'auto' : 'smooth' }});
  }};
  return (
    {_section_open(slug, scope, site.tints.get(slug, False), reveal)}
      <div className="k-container __SC__-top">
        {_head(slug)}
        <div className="__SC__-controls">
          <button onClick={{() => page(-1)}} type="button" className="__SC__-arrow" aria-label="Previous items">←</button>
          <button onClick={{() => page(1)}} type="button" className="__SC__-arrow" aria-label="Next items">→</button>
        </div>
      </div>
      <div className="__SC__-track" ref={{trackRef}} tabIndex={{0}} role="region" aria-label={{DATA.title}}>
        <ul className="__SC__-reel k-stagger">
          {{DATA.items.map((item: any, i: number) => (
            <li className="__SC__-card" key={{i}}{_ra(reveal)}>
              {card}
            </li>
          ))}}
        </ul>
      </div>
    </section>
  );
}}
"""
    else:
        body = f"""
export function __NAME__() {{
{_reveal_hook(reveal)}  return (
    {_section_open(slug, scope, site.tints.get(slug, False), reveal)}
      <div className="k-container">
        {_head(slug)}
        <ul className="__SC__-grid k-stagger">
          {{DATA.items.map((item: any, i: number) => (
            <li className={{'__SC__-cell' + (i === 0 ? ' __SC__-cell--lead' : '')}} key={{i}}{_ra(reveal)}>
              {card}
            </li>
          ))}}
        </ul>
      </div>
    </section>
  );
}}
"""
    css = """
.__SC__ .__SC__-figure { display: grid; gap: var(--k-space-2); height: 100%; margin: 0; border-radius: var(--k-radius); }
.__SC__ .__SC__-caption { display: grid; gap: 4px; }
.__SC__ .__SC__-media { width: 100%; aspect-ratio: 4 / 3; }
.__SC__ .__SC__-grid { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: clamp(20px, 3vw, 36px); }
.__SC__ .__SC__-cell { grid-column: span 2; }
.__SC__ .__SC__-cell--lead { grid-column: span 4; grid-row: span 2; }
.__SC__ .__SC__-cell--lead .__SC__-media { aspect-ratio: auto; min-height: 320px; height: calc(100% - 96px); }
.__SC__ .__SC__-top { display: flex; flex-wrap: wrap; align-items: flex-end; justify-content: space-between; gap: var(--k-space-3); }
.__SC__ .__SC__-top .k-head { flex: 1 1 520px; margin-bottom: 0; }
.__SC__ .__SC__-controls { display: flex; gap: var(--k-space-1); }
.__SC__ .__SC__-arrow { width: 48px; height: 48px; border: 1px solid var(--k-line-strong); border-radius: var(--k-radius-btn); background-color: transparent; font-size: 1.125rem; transition: border-color 160ms ease, transform 160ms var(--k-ease); }
.__SC__ .__SC__-arrow:hover, .__SC__ .__SC__-arrow:focus-visible { border-color: var(--k-ink); transform: translateY(-2px); }
.__SC__ .__SC__-arrow:active { transform: scale(0.96); }
.__SC__ .__SC__-track { margin-top: clamp(32px, 5vw, 56px); overflow-x: auto; scroll-snap-type: x mandatory; scroll-padding-inline: var(--k-gutter); overscroll-behavior-x: contain; scrollbar-width: thin; }
.__SC__ .__SC__-reel { display: flex; gap: clamp(16px, 2.4vw, 28px); width: max-content; padding-inline: max(var(--k-gutter), calc((100vw - var(--k-max)) / 2)); padding-bottom: var(--k-space-2); }
.__SC__ .__SC__-card { flex: 0 0 auto; width: min(78vw, 440px); scroll-snap-align: start; }
.__SC__ .__SC__-card .__SC__-media { aspect-ratio: 4 / 5; }
@media (max-width: 860px) {
  .__SC__ .__SC__-grid { grid-template-columns: minmax(0, 1fr); }
  .__SC__ .__SC__-cell, .__SC__ .__SC__-cell--lead { grid-column: auto; grid-row: auto; }
  .__SC__ .__SC__-cell--lead .__SC__-media { aspect-ratio: 4 / 3; min-height: 0; height: auto; }
}
"""
    return assemble(name, content, _fill(body, NAME=name).replace("__SC__", scope), helpers), css.replace("__SC__", scope)


def render_products(site, slug: str, content: dict) -> tuple[str, str]:
    name, scope = site.component(slug), scope_class(slug)
    reveal = site.reveal_section == slug
    store = site.is_store
    if store:
        action = """<button onClick={() => add(item)} type="button" className="k-btn k-btn--ghost __SC__-add" aria-label={'Add ' + item.name + ' to cart'}>{added === item.name ? 'Added' : 'Add to cart'}</button>"""
        state = """  const [added, setAdded] = useState('');
  const [status, setStatus] = useState('');
  const add = (item: any) => {
    window.dispatchEvent(new CustomEvent('kit-cart-add', { detail: { name: item.name, price: item.price || '' } }));
    setAdded(item.name);
    setStatus(item.name + ' added to cart.');
    window.setTimeout(() => setAdded(''), 1600);
  };
"""
        live = '\n        <p className="k-sr" aria-live="polite">{status}</p>'
    else:
        action = """<a className="k-link __SC__-ask" href={item.ask}>Ask about this piece</a>"""
        state = ""
        live = ""
    body = f"""
export function __NAME__() {{
{_reveal_hook(reveal)}{state}  return (
    {_section_open(slug, scope, site.tints.get(slug, False), reveal)}
      <div className="k-container">
        {_head(slug)}
        <ul className="__SC__-grid k-stagger">
          {{DATA.items.map((item: any, i: number) => (
            <li className="__SC__-card" key={{i}} data-product={{item.name}}{_ra(reveal)}>
              <Media img={{item.img}} variant={{(i % 3) + 1}} mark={{item.name.charAt(0)}} className="__SC__-media k-settle" />
              <div className="__SC__-body">
                <div className="__SC__-row">
                  <h3 className="k-h3">{{item.name}}</h3>
                  {{item.price ? <p className="__SC__-price">{{item.price}}</p> : null}}
                </div>
                {{item.description ? <p className="k-muted">{{item.description}}</p> : null}}
                {action}
              </div>
            </li>
          ))}}
        </ul>{live}
      </div>
    </section>
  );
}}
"""
    css = """
.__SC__ .__SC__-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, 250px), 1fr)); gap: clamp(28px, 4vw, 44px) clamp(20px, 3vw, 32px); }
.__SC__ .__SC__-card { display: grid; gap: var(--k-space-2); align-content: start; }
.__SC__ .__SC__-media { width: 100%; aspect-ratio: 4 / 5; }
.__SC__ .__SC__-body { display: grid; gap: var(--k-space-1); justify-items: start; }
.__SC__ .__SC__-row { display: flex; justify-content: space-between; align-items: baseline; gap: var(--k-space-2); width: 100%; }
.__SC__ .__SC__-price { font-weight: 600; font-variant-numeric: tabular-nums; white-space: nowrap; }
.__SC__ .__SC__-add { margin-top: var(--k-space-1); min-height: var(--k-tap); }
.__SC__ .__SC__-ask { display: inline-flex; align-items: center; min-height: var(--k-tap); font-weight: 600; }
"""
    helpers = [H_MEDIA] + ([H_REVEAL] if reveal else [])
    return assemble(name, content, _fill(body, NAME=name).replace("__SC__", scope), helpers), css.replace("__SC__", scope)


def render_cart(site, slug: str, content: dict) -> tuple[str, str]:
    name, scope = site.component(slug), scope_class(slug)
    body = f"""
export function __NAME__() {{
  const cart = useCart();
  const total = cartTotal(cart.lines);
  return (
    {_section_open(slug, scope, site.tints.get(slug, False), False)}
      <div className="k-container __SC__-grid">
        <div className="k-head">
          <h2 id="{slug}-title" className="k-h2">{{DATA.title}}</h2>
          {{DATA.text ? <p className="k-lede">{{DATA.text}}</p> : null}}
        </div>
        <div className="__SC__-panel">
          {{cart.lines.length ? (
            <ul className="__SC__-lines">
              {{cart.lines.map((line: any) => (
                <li className="__SC__-line" key={{line.name}}>
                  <span className="__SC__-name">{{line.qty}} × {{line.name}}</span>
                  <span>{{line.price}}</span>
                  <button onClick={{() => cart.remove(line.name)}} type="button" className="__SC__-remove" aria-label={{'Remove ' + line.name}}>Remove</button>
                </li>
              ))}}
            </ul>
          ) : (
            <p className="__SC__-empty">Your cart is empty. Add something you like and it will appear here.</p>
          )}}
          {{cart.lines.length && DATA.currency ? <p className="__SC__-total">Total {{DATA.currency}}{{total.toFixed(2)}}</p> : null}}
          <p className="k-muted">{{DATA.note}}</p>
          {{cart.lines.length && DATA.email ? (
            <a className="k-btn k-btn--primary" href={{'mailto:' + DATA.email + '?subject=' + encodeURIComponent(`Order from ${{DATA.brand}}`) + '&body=' + encodeURIComponent(orderBody(cart.lines, DATA.currency))}}>Email this order</a>
          ) : null}}
        </div>
      </div>
    </section>
  );
}}
"""
    css = """
.__SC__ .__SC__-grid { display: grid; grid-template-columns: minmax(0, 0.8fr) minmax(0, 1.2fr); gap: var(--k-space-8); align-items: start; }
.__SC__ .__SC__-panel { display: grid; gap: var(--k-space-2); padding: clamp(20px, 3vw, 32px); border: 1px solid var(--k-line); border-radius: var(--k-radius); background-color: var(--k-bg); color: var(--k-ink); }
.__SC__ .__SC__-lines { display: grid; gap: var(--k-space-2); }
.__SC__ .__SC__-line { display: grid; grid-template-columns: minmax(0, 1fr) auto auto; gap: var(--k-space-2); align-items: center; padding-bottom: var(--k-space-2); border-bottom: 1px solid var(--k-line); }
.__SC__ .__SC__-remove { min-height: var(--k-tap); padding: 0 4px; border: 0; background-color: transparent; color: var(--k-muted); text-decoration: underline; text-underline-offset: 0.2em; }
.__SC__ .__SC__-remove:hover, .__SC__ .__SC__-remove:focus-visible { color: var(--k-ink); }
.__SC__ .__SC__-empty { color: var(--k-muted); }
.__SC__ .__SC__-total { font-weight: 700; font-size: 1.125rem; }
@media (max-width: 760px) { .__SC__ .__SC__-grid { grid-template-columns: minmax(0, 1fr); } }
"""
    return assemble(name, content, _fill(body, NAME=name).replace("__SC__", scope), [H_PRICE]), css.replace("__SC__", scope)


def render_menu(site, slug: str, content: dict) -> tuple[str, str]:
    name, scope = site.component(slug), scope_class(slug)
    categories = content.get("categories", [])
    vt = f"k-panel-{slug}"
    if len(categories) >= 2:
        board = f"""<div className="__SC__-tabs" role="tablist" aria-label={{DATA.title}}>
            {{DATA.categories.map((cat: any, i: number) => (
              <button onClick={{() => select(i, false)}} onKeyDown={{(event: ReactKeyboardEvent<HTMLButtonElement>) => onKey(event, i)}} ref={{(el: HTMLButtonElement | null) => {{ tabsRef.current[i] = el; }}}} key={{i}} type="button" role="tab" id={{'{slug}-tab-' + i}} aria-selected={{active === i}} aria-controls="{slug}-panel" tabIndex={{active === i ? 0 : -1}} className="__SC__-tab">{{cat.name}}</button>
            ))}}
          </div>
          <div id="{slug}-panel" role="tabpanel" aria-labelledby={{'{slug}-tab-' + active}} className="__SC__-panel" tabIndex={{0}}>
            <ul className="__SC__-dishes">
              {{DATA.categories[active].items.map((dish: any, i: number) => (
                <li className="__SC__-dish" key={{i}}>
                  <div className="__SC__-dishrow">
                    <h3 className="__SC__-dishname">{{dish.name}}</h3>
                    {{dish.price ? <span className="__SC__-leader" aria-hidden="true" /> : null}}
                    {{dish.price ? <span className="__SC__-price">{{dish.price}}</span> : null}}
                  </div>
                  {{dish.description ? <p className="k-muted">{{dish.description}}</p> : null}}
                </li>
              ))}}
            </ul>
          </div>"""
        state = """  const [active, setActive] = useState(0);
  const tabsRef = useRef<Array<HTMLButtonElement | null>>([]);
  const select = (index: number, focus: boolean) => {
    const count = DATA.categories.length;
    const next = (index + count) % count;
    const apply = () => setActive(next);
    const doc: any = document;
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (doc.startViewTransition && !reduce) {
      doc.startViewTransition(() => flushSync(apply));
    } else {
      apply();
    }
    if (focus) tabsRef.current[next]?.focus();
  };
  const onKey = (event: ReactKeyboardEvent<HTMLButtonElement>, index: number) => {
    const last = DATA.categories.length - 1;
    const moves: Record<string, number> = { ArrowRight: index + 1, ArrowLeft: index - 1, Home: 0, End: last };
    if (event.key in moves) {
      event.preventDefault();
      select(moves[event.key], true);
    }
  };
"""
    elif categories:
        board = """<div className="__SC__-panel">
            <ul className="__SC__-dishes">
              {DATA.categories[0].items.map((dish: any, i: number) => (
                <li className="__SC__-dish" key={i}>
                  <div className="__SC__-dishrow"><h3 className="__SC__-dishname">{dish.name}</h3></div>
                  {dish.description ? <p className="k-muted">{dish.description}</p> : null}
                </li>
              ))}
            </ul>
          </div>"""
        state = ""
    else:
        board = """<div className="__SC__-panel __SC__-panel--empty">
            <p className="k-lede">{DATA.empty}</p>
          </div>"""
        state = ""
    body = f"""
export function __NAME__() {{
{state}  return (
    {_section_open(slug, scope, site.tints.get(slug, False), False)}
      <div className="k-container __SC__-grid">
        <div className="__SC__-intro">
          <h2 id="{slug}-title" className="k-h2">{{DATA.title}}</h2>
          {{DATA.intro ? <p className="k-lede">{{DATA.intro}}</p> : null}}
          <Media img={{DATA.img}} variant={{3}} mark={{DATA.mark}} className="__SC__-media k-settle" />
        </div>
        <div className="__SC__-board">
          {board}
        </div>
      </div>
    </section>
  );
}}
"""
    css = f"""
.__SC__ .__SC__-grid {{ display: grid; grid-template-columns: minmax(0, 0.85fr) minmax(0, 1.15fr); gap: clamp(32px, 6vw, 96px); align-items: start; }}
.__SC__ .__SC__-intro {{ display: grid; gap: var(--k-space-3); position: sticky; top: calc(var(--k-header-h) + 24px); }}
.__SC__ .__SC__-media {{ width: 100%; aspect-ratio: 4 / 3; margin-top: var(--k-space-2); }}
.__SC__ .__SC__-tabs {{ display: flex; flex-wrap: wrap; gap: var(--k-space-1); margin-bottom: var(--k-space-4); }}
.__SC__ .__SC__-tab {{ min-height: var(--k-tap); padding: 0 1.125rem; border: 1px solid var(--k-line-strong); border-radius: var(--k-radius-btn); background-color: transparent; color: var(--k-ink); font-weight: 600; transition: border-color 160ms ease, transform 160ms var(--k-ease); }}
.__SC__ .__SC__-tab:hover, .__SC__ .__SC__-tab:focus-visible {{ border-color: var(--k-ink); transform: translateY(-1px); }}
.__SC__ .__SC__-tab[aria-selected="true"] {{ background-color: var(--k-accent); color: var(--k-accent-ink); border-color: var(--k-accent); }}
.__SC__ .__SC__-panel {{ view-transition-name: {vt}; }}
.__SC__ .__SC__-panel:focus-visible {{ outline-offset: 8px; }}
.__SC__ .__SC__-dishes {{ display: grid; }}
.__SC__ .__SC__-dish {{ display: grid; gap: 4px; padding-block: var(--k-space-3); border-bottom: 1px solid var(--k-line); }}
.__SC__ .__SC__-dishrow {{ display: flex; align-items: baseline; gap: var(--k-space-2); }}
.__SC__ .__SC__-dishname {{ font-family: var(--k-font-display); font-weight: var(--k-display-weight); font-size: clamp(1.2rem, 1.6vw, 1.4rem); line-height: 1.25; }}
.__SC__ .__SC__-leader {{ flex: 1; border-bottom: 1px dotted var(--k-line-strong); transform: translateY(-4px); }}
.__SC__ .__SC__-price {{ font-weight: 600; font-variant-numeric: tabular-nums; }}
::view-transition-old({vt}), ::view-transition-new({vt}) {{ animation-duration: 240ms; }}
@media (max-width: 860px) {{
  .__SC__ .__SC__-grid {{ grid-template-columns: minmax(0, 1fr); }}
  .__SC__ .__SC__-intro {{ position: static; }}
}}
"""
    return assemble(name, content, _fill(body, NAME=name).replace("__SC__", scope), [H_MEDIA]), css.replace("__SC__", scope)


def render_steps(site, slug: str, content: dict) -> tuple[str, str]:
    name, scope = site.component(slug), scope_class(slug)
    body = f"""
export function __NAME__() {{
  const [current, setCurrent] = useState(0);
  const listRef = useRef<HTMLOListElement | null>(null);
  useEffect(() => {{
    const list = listRef.current;
    if (!list || typeof IntersectionObserver === 'undefined') return;
    const items = Array.from(list.querySelectorAll<HTMLElement>('[data-step]'));
    const observer = new IntersectionObserver((entries) => {{
      entries.forEach((entry) => {{
        if (entry.isIntersecting) setCurrent(Number((entry.target as HTMLElement).dataset.step || 0));
      }});
    }}, {{ rootMargin: '-45% 0px -45% 0px' }});
    items.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }}, []);
  const total = DATA.steps.length;
  const progress = total > 1 ? current / (total - 1) : 1;
  return (
    {_section_open(slug, scope, site.tints.get(slug, False), False)}
      <div className="k-container __SC__-grid">
        <div className="__SC__-pin" data-motion="sticky-story">
          <div className="__SC__-visual">
            <Media img={{DATA.img}} variant={{3}} mark={{DATA.mark}} className="__SC__-media" />
            <div className="__SC__-meter">
              <p className="__SC__-counter" aria-hidden="true">
                <span className="__SC__-now">{{String(current + 1).padStart(2, '0')}}</span> / {{String(total).padStart(2, '0')}}
              </p>
              <svg className="__SC__-line" viewBox="0 0 100 4" preserveAspectRatio="none" aria-hidden="true">
                <line x1="0" y1="2" x2="100" y2="2" pathLength={{1}} className="__SC__-track" />
                <line x1="0" y1="2" x2="100" y2="2" pathLength={{1}} className="__SC__-fill" style={{{{ strokeDashoffset: 1 - progress }}}} />
              </svg>
            </div>
          </div>
        </div>
        <div className="__SC__-copy">
          {_head(slug, split=False)}
          <ol className="__SC__-list" ref={{listRef}}>
            {{DATA.steps.map((step: any, i: number) => (
              <li key={{i}} data-step={{i}} className="__SC__-step" aria-current={{current === i ? 'step' : undefined}}>
                <span className="__SC__-num" aria-hidden="true">{{String(i + 1).padStart(2, '0')}}</span>
                <div className="__SC__-text">
                  <h3 className="k-h3">{{step.title}}</h3>
                  {{step.text ? <p className="k-muted">{{step.text}}</p> : null}}
                </div>
              </li>
            ))}}
          </ol>
        </div>
      </div>
    </section>
  );
}}
"""
    css = """
.__SC__ .__SC__-grid { display: grid; grid-template-columns: minmax(0, 0.95fr) minmax(0, 1.05fr); gap: clamp(32px, 6vw, 96px); align-items: start; }
.__SC__ .__SC__-pin { position: sticky; top: calc(var(--k-header-h) + 32px); }
.__SC__ .__SC__-visual { display: grid; gap: var(--k-space-2); }
.__SC__ .__SC__-media { width: 100%; aspect-ratio: 4 / 5; max-height: 70vh; }
.__SC__ .__SC__-meter { display: grid; gap: 10px; }
.__SC__ .__SC__-counter { font-size: 0.875rem; font-weight: 600; letter-spacing: 0.08em; color: var(--k-muted); font-variant-numeric: tabular-nums; }
.__SC__ .__SC__-now { color: var(--k-ink); }
.__SC__ .__SC__-line { width: 100%; height: 4px; overflow: visible; }
.__SC__ .__SC__-track, .__SC__ .__SC__-fill { stroke-width: 4; fill: none; }
.__SC__ .__SC__-track { stroke: var(--k-line); }
.__SC__ .__SC__-fill { stroke: var(--k-accent); stroke-dasharray: 1; transition: stroke-dashoffset 420ms var(--k-ease); }
.__SC__ .__SC__-list { display: grid; }
.__SC__ .__SC__-step { display: grid; grid-template-columns: 56px minmax(0, 1fr); gap: var(--k-space-2); min-height: 38vh; padding-block: var(--k-space-4); border-top: 1px solid var(--k-line); opacity: 0.42; transition: opacity 300ms var(--k-ease); }
.__SC__ .__SC__-step[aria-current="step"] { opacity: 1; }
.__SC__ .__SC__-num { font-family: var(--k-font-display); font-size: 1.5rem; color: var(--k-accent-text); font-variant-numeric: tabular-nums; }
.__SC__ .__SC__-text { display: grid; gap: var(--k-space-1); align-content: start; }
@media (max-width: 860px) {
  .__SC__ .__SC__-grid { grid-template-columns: minmax(0, 1fr); }
  .__SC__ .__SC__-pin { position: static; }
  .__SC__ .__SC__-media { aspect-ratio: 16 / 10; }
  .__SC__ .__SC__-step { min-height: 0; opacity: 1; }
}
@media (prefers-reduced-motion: reduce) { .__SC__ .__SC__-step { opacity: 1; } }
"""
    return assemble(name, content, _fill(body, NAME=name).replace("__SC__", scope), [H_MEDIA]), css.replace("__SC__", scope)


def render_faq(site, slug: str, content: dict) -> tuple[str, str]:
    name, scope = site.component(slug), scope_class(slug)
    body = f"""
export function __NAME__() {{
  const [open, setOpen] = useState(0);
  return (
    {_section_open(slug, scope, site.tints.get(slug, False), False)}
      <div className="k-container __SC__-grid">
        {_head(slug, split=False)}
        <div className="__SC__-list">
          {{DATA.items.map((item: any, i: number) => (
            <div className="__SC__-item" key={{i}}>
              <h3 className="__SC__-q">
                <button onClick={{() => setOpen(open === i ? -1 : i)}} type="button" id={{'{slug}-q-' + i}} aria-expanded={{open === i}} aria-controls={{'{slug}-a-' + i}} className="__SC__-trigger">
                  <span>{{item.q}}</span>
                  <span className="__SC__-icon" aria-hidden="true" />
                </button>
              </h3>
              <div id={{'{slug}-a-' + i}} role="region" aria-labelledby={{'{slug}-q-' + i}} className="__SC__-answer" hidden={{open !== i}}>
                <p>{{item.a}}</p>
              </div>
            </div>
          ))}}
        </div>
      </div>
    </section>
  );
}}
"""
    css = """
.__SC__ .__SC__-grid { display: grid; grid-template-columns: minmax(0, 0.8fr) minmax(0, 1.2fr); gap: clamp(32px, 6vw, 96px); align-items: start; }
.__SC__ .__SC__-list { border-top: 1px solid var(--k-line-strong); }
.__SC__ .__SC__-item { border-bottom: 1px solid var(--k-line-strong); }
.__SC__ .__SC__-q { font-size: inherit; font-weight: inherit; }
.__SC__ .__SC__-trigger { display: flex; width: 100%; align-items: center; justify-content: space-between; gap: var(--k-space-3); min-height: 64px; padding: var(--k-space-2) 0; border: 0; background-color: transparent; color: var(--k-ink); font-family: var(--k-font-display); font-weight: var(--k-display-weight); font-size: clamp(1.125rem, 1.6vw, 1.375rem); line-height: 1.3; text-align: left; transition: color 160ms ease; }
.__SC__ .__SC__-trigger:hover, .__SC__ .__SC__-trigger:focus-visible { color: var(--k-accent-text); }
.__SC__ .__SC__-icon { position: relative; flex: 0 0 18px; height: 18px; }
.__SC__ .__SC__-icon::before, .__SC__ .__SC__-icon::after { content: ""; position: absolute; top: 8px; left: 0; width: 18px; height: 2px; background-color: currentColor; transition: transform 220ms var(--k-ease); }
.__SC__ .__SC__-icon::after { transform: rotate(90deg); }
.__SC__ .__SC__-trigger[aria-expanded="true"] .__SC__-icon::after { transform: rotate(0deg); }
.__SC__ .__SC__-answer { padding-bottom: var(--k-space-3); color: var(--k-muted); }
.__SC__ .__SC__-answer p { max-width: 60ch; }
.__SC__ .__SC__-answer:not([hidden]) { animation: __SC__-open 260ms var(--k-ease); }
@keyframes __SC__-open { from { opacity: 0; transform: translateY(-6px); } to { opacity: 1; transform: none; } }
@media (max-width: 860px) { .__SC__ .__SC__-grid { grid-template-columns: minmax(0, 1fr); } }
"""
    return assemble(name, content, _fill(body, NAME=name).replace("__SC__", scope), []), css.replace("__SC__", scope)


def render_articles(site, slug: str, content: dict) -> tuple[str, str]:
    name, scope = site.component(slug), scope_class(slug)
    reveal = site.reveal_section == slug
    tilt = site.theme.lively
    helpers = [H_MEDIA] + ([H_REVEAL] if reveal else []) + ([H_TILT] if tilt else [])
    body = f"""
export function __NAME__() {{
{_reveal_hook(reveal)}  return (
    {_section_open(slug, scope, site.tints.get(slug, False), reveal)}
      <div className="k-container">
        {_head(slug)}
        <ul className="__SC__-grid k-stagger">
          {{DATA.items.map((item: any, i: number) => (
            <li className={{'__SC__-cell' + (i === 0 ? ' __SC__-cell--lead' : '')}} key={{i}}{_ra(reveal)}>
              <article className={{'__SC__-card{' k-tilt' if tilt else ''}'}}{_tilt_attrs(site)}>
                {{i === 0 ? <Media img={{item.img}} variant={{2}} mark={{item.title.charAt(0)}} className="__SC__-media" /> : null}}
                <div className="__SC__-body">
                  {{item.tag ? <p className="__SC__-tag">{{item.tag}}</p> : null}}
                  <h3 className="k-h3">{{item.title}}</h3>
                  {{item.excerpt ? <p className="__SC__-excerpt">{{item.excerpt}}</p> : null}}
                </div>
              </article>
            </li>
          ))}}
        </ul>
      </div>
    </section>
  );
}}
"""
    css = """
.__SC__ .__SC__-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); grid-auto-rows: minmax(180px, auto); gap: clamp(16px, 2.4vw, 28px); }
.__SC__ .__SC__-cell--lead { grid-row: span 2; }
.__SC__ .__SC__-card { display: grid; gap: var(--k-space-2); align-content: start; height: 100%; padding: clamp(20px, 2.6vw, 32px); border: 1px solid var(--k-line); border-radius: var(--k-radius); background-color: var(--k-bg); color: var(--k-ink); }
.__SC__ .__SC__-cell--lead .__SC__-card { background-color: var(--k-accent-soft); border-color: transparent; }
.__SC__ .__SC__-media { width: 100%; aspect-ratio: 16 / 10; }
.__SC__ .__SC__-body { display: grid; gap: var(--k-space-1); }
.__SC__ .__SC__-tag { font-size: 0.75rem; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; color: var(--k-ink); }
.__SC__ .__SC__-excerpt { color: var(--k-ink); opacity: 0.86; }
@media (max-width: 960px) { .__SC__ .__SC__-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 640px) { .__SC__ .__SC__-grid { grid-template-columns: minmax(0, 1fr); } .__SC__ .__SC__-cell--lead { grid-row: auto; } }
"""
    return assemble(name, content, _fill(body, NAME=name).replace("__SC__", scope), helpers), css.replace("__SC__", scope)


def render_pricing(site, slug: str, content: dict) -> tuple[str, str]:
    name, scope = site.component(slug), scope_class(slug)
    reveal = site.reveal_section == slug
    body = f"""
export function __NAME__() {{
{_reveal_hook(reveal)}  return (
    {_section_open(slug, scope, site.tints.get(slug, False), reveal)}
      <div className="k-container">
        {_head(slug)}
        <ul className="__SC__-grid k-stagger">
          {{DATA.tiers.map((tier: any, i: number) => (
            <li className={{'__SC__-tier' + (DATA.featured === i ? ' __SC__-tier--featured' : '')}} key={{i}}{_ra(reveal)}>
              <h3 className="k-h3">{{tier.name}}</h3>
              <p className="__SC__-price">{{tier.price || 'Pricing on request'}}</p>
              {{tier.description ? <p className="__SC__-desc">{{tier.description}}</p> : null}}
              {{tier.features.length ? (
                <ul className="__SC__-features">
                  {{tier.features.map((f: string, j: number) => <li key={{j}}>{{f}}</li>)}}
                </ul>
              ) : null}}
              <a className={{'k-btn ' + (DATA.featured === i ? 'k-btn--primary' : 'k-btn--ghost') + ' __SC__-cta'}} href={{DATA.quoteHref}}>Ask for a quote</a>
            </li>
          ))}}
        </ul>
      </div>
    </section>
  );
}}
"""
    css = """
.__SC__ .__SC__-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 260px), 1fr)); gap: clamp(16px, 2.4vw, 28px); align-items: stretch; }
.__SC__ .__SC__-tier { display: flex; flex-direction: column; gap: var(--k-space-2); padding: clamp(24px, 3vw, 36px); border: 1px solid var(--k-line-strong); border-radius: var(--k-radius); background-color: var(--k-bg); color: var(--k-ink); }
.__SC__ .__SC__-tier--featured { background-color: var(--k-ink); color: var(--k-bg); border-color: var(--k-ink); }
.__SC__ .__SC__-price { font-family: var(--k-font-display); font-size: 1.5rem; line-height: 1.2; }
.__SC__ .__SC__-desc { opacity: 0.86; }
.__SC__ .__SC__-features { display: grid; gap: 8px; margin-bottom: var(--k-space-2); }
.__SC__ .__SC__-features li { display: flex; gap: 10px; align-items: baseline; }
.__SC__ .__SC__-features li::before { content: ""; flex: 0 0 12px; height: 2px; transform: translateY(-4px); background-color: var(--k-accent); }
.__SC__ .__SC__-cta { margin-top: auto; align-self: flex-start; }
.__SC__ .__SC__-tier--featured .k-btn--ghost { color: var(--k-bg); }
"""
    return assemble(name, content, _fill(body, NAME=name).replace("__SC__", scope), [H_REVEAL] if reveal else []), css.replace("__SC__", scope)


def render_quotes(site, slug: str, content: dict) -> tuple[str, str]:
    name, scope = site.component(slug), scope_class(slug)
    body = f"""
export function __NAME__() {{
  return (
    {_section_open(slug, scope, site.tints.get(slug, False), False)}
      <div className="k-container">
        {{DATA.quotes.length ? (
          <>
            <div className="k-head"><h2 id="{slug}-title" className="k-h2">{{DATA.title}}</h2></div>
            <ul className="__SC__-grid">
              {{DATA.quotes.map((q: any, i: number) => (
                <li key={{i}}>
                  <figure className="__SC__-quote">
                    <blockquote><p>{{q.quote}}</p></blockquote>
                    {{q.author ? <figcaption>{{q.author}}</figcaption> : null}}
                  </figure>
                </li>
              ))}}
            </ul>
          </>
        ) : (
          <div className="__SC__-invite">
            <h2 id="{slug}-title" className="k-h2">{{DATA.title}}</h2>
            {{DATA.intro ? <p className="k-lede">{{DATA.intro}}</p> : null}}
            <p className="k-text">{{DATA.invite}}</p>
            <a className="k-btn k-btn--ghost" href={{DATA.feedbackHref}}>Share your experience</a>
          </div>
        )}}
      </div>
    </section>
  );
}}
"""
    css = """
.__SC__ .__SC__-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 300px), 1fr)); gap: var(--k-space-4); }
.__SC__ .__SC__-quote { display: grid; gap: var(--k-space-2); margin: 0; padding-top: var(--k-space-3); border-top: 2px solid var(--k-ink); }
.__SC__ .__SC__-quote blockquote { margin: 0; font-family: var(--k-font-display); font-size: clamp(1.25rem, 2vw, 1.6rem); line-height: 1.3; }
.__SC__ .__SC__-quote figcaption { color: var(--k-muted); font-size: 0.9375rem; }
.__SC__ .__SC__-invite { display: grid; gap: var(--k-space-3); justify-items: start; max-width: 760px; }
"""
    return assemble(name, content, _fill(body, NAME=name).replace("__SC__", scope), []), css.replace("__SC__", scope)


def render_contact(site, slug: str, content: dict) -> tuple[str, str]:
    name, scope = site.component(slug), scope_class(slug)
    body = f"""
export function __NAME__() {{
  const [values, setValues] = useState({{ name: '', email: '', message: '' }});
  const [errors, setErrors] = useState<Record<string, string>>({{}});
  const [state, setState] = useState('idle');
  const update = (field: string, value: string) => setValues((current: any) => ({{ ...current, [field]: value }}));
  const submit = (event: ReactFormEvent<HTMLFormElement>) => {{
    event.preventDefault();
    const next: Record<string, string> = {{}};
    if (!values.name.trim()) next.name = 'Please add your name.';
    if (!/^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/.test(values.email)) next.email = 'Please add a valid email address.';
    if (values.message.trim().length < 10) next.message = 'Please write a short message of at least ten characters.';
    setErrors(next);
    if (Object.keys(next).length) return;
    setState('busy');
    window.setTimeout(() => {{
      if (DATA.email) {{
        const body = values.message + '\\n\\n' + values.name + ' (' + values.email + ')';
        window.location.href = 'mailto:' + DATA.email + '?subject=' + encodeURIComponent(`Message from ${{values.name}}`) + '&body=' + encodeURIComponent(body);
      }}
      setState('done');
    }}, 400);
  }};
  return (
    {_section_open(slug, scope, site.tints.get(slug, False), False)}
      <div className="k-container __SC__-grid">
        <div className="__SC__-intro">
          <h2 id="{slug}-title" className="k-h2">{{DATA.title}}</h2>
          {{DATA.text ? <p className="k-lede">{{DATA.text}}</p> : null}}
          {{DATA.email || DATA.location ? (
            <dl className="__SC__-details">
              {{DATA.email ? (
                <div><dt>Email</dt><dd><a className="k-link" href={{'mailto:' + DATA.email}}>{{DATA.email}}</a></dd></div>
              ) : null}}
              {{DATA.location ? (
                <div><dt>Location</dt><dd>{{DATA.location}}</dd></div>
              ) : null}}
            </dl>
          ) : null}}
        </div>
        <form className="__SC__-form" noValidate onSubmit={{submit}} aria-describedby="{slug}-form-note">
          <div className="__SC__-field">
            <label htmlFor="{slug}-name">Name</label>
            <input id="{slug}-name" name="name" type="text" autoComplete="name" required value={{values.name}} aria-invalid={{errors.name ? true : undefined}} aria-describedby={{errors.name ? '{slug}-name-error' : undefined}} onChange={{(event) => update('name', event.target.value)}} />
            {{errors.name ? <p id="{slug}-name-error" className="__SC__-error">{{errors.name}}</p> : null}}
          </div>
          <div className="__SC__-field">
            <label htmlFor="{slug}-email">Email</label>
            <input id="{slug}-email" name="email" type="email" autoComplete="email" required value={{values.email}} aria-invalid={{errors.email ? true : undefined}} aria-describedby={{errors.email ? '{slug}-email-error' : undefined}} onChange={{(event) => update('email', event.target.value)}} />
            {{errors.email ? <p id="{slug}-email-error" className="__SC__-error">{{errors.email}}</p> : null}}
          </div>
          <div className="__SC__-field">
            <label htmlFor="{slug}-message">Message</label>
            <textarea id="{slug}-message" name="message" rows={{5}} required value={{values.message}} aria-invalid={{errors.message ? true : undefined}} aria-describedby={{errors.message ? '{slug}-message-error' : undefined}} onChange={{(event) => update('message', event.target.value)}} />
            {{errors.message ? <p id="{slug}-message-error" className="__SC__-error">{{errors.message}}</p> : null}}
          </div>
          <button type="submit" className="k-btn k-btn--primary __SC__-submit" aria-busy={{state === 'busy'}} disabled={{state === 'busy'}}>{{state === 'busy' ? 'Preparing…' : DATA.button}}</button>
          <p id="{slug}-form-note" className="__SC__-note" aria-live="polite">{{state === 'done' ? DATA.doneNote : DATA.note}}</p>
        </form>
      </div>
    </section>
  );
}}
"""
    css = """
.__SC__ .__SC__-grid { display: grid; grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr); gap: clamp(32px, 6vw, 96px); align-items: start; }
.__SC__ .__SC__-intro { display: grid; gap: var(--k-space-3); }
.__SC__ .__SC__-details { display: grid; gap: var(--k-space-2); margin: var(--k-space-2) 0 0; }
.__SC__ .__SC__-details dt { font-size: 0.8125rem; font-weight: 600; letter-spacing: 0.12em; text-transform: uppercase; color: var(--k-muted); }
.__SC__ .__SC__-details dd { margin: 0; font-size: 1.125rem; overflow-wrap: anywhere; }
.__SC__ .__SC__-form { display: grid; gap: var(--k-space-3); padding: clamp(20px, 3vw, 36px); border: 1px solid var(--k-line); border-radius: var(--k-radius); background-color: var(--k-bg); color: var(--k-ink); }
.__SC__ .__SC__-field { display: grid; gap: 6px; }
.__SC__ .__SC__-field label { font-weight: 600; font-size: 0.9375rem; }
.__SC__ .__SC__-field input, .__SC__ .__SC__-field textarea { width: 100%; min-height: 48px; padding: 12px 14px; border: 1px solid var(--k-line-strong); border-radius: calc(var(--k-radius-btn) / 2 + 2px); background-color: var(--k-surface); color: var(--k-ink); transition: border-color 160ms ease, box-shadow 160ms ease; }
.__SC__ .__SC__-field textarea { resize: vertical; }
.__SC__ .__SC__-field input:hover, .__SC__ .__SC__-field textarea:hover { border-color: var(--k-ink); }
.__SC__ .__SC__-field input:focus-visible, .__SC__ .__SC__-field textarea:focus-visible { outline: none; border-color: var(--k-accent-text); box-shadow: 0 0 0 3px var(--k-accent-soft); }
.__SC__ .__SC__-field [aria-invalid="true"] { border-color: #B42318; }
.__SC__ .__SC__-error { font-size: 0.875rem; font-weight: 600; color: var(--k-ink); }
.__SC__ .__SC__-error::before { content: "! "; color: #D92D20; }
.__SC__ .__SC__-submit { justify-self: start; }
.__SC__ .__SC__-note { font-size: 0.875rem; color: var(--k-muted); }
@media (max-width: 860px) { .__SC__ .__SC__-grid { grid-template-columns: minmax(0, 1fr); } }
"""
    return assemble(name, content, _fill(body, NAME=name).replace("__SC__", scope), []), css.replace("__SC__", scope)


def render_cta(site, slug: str, content: dict) -> tuple[str, str]:
    name, scope = site.component(slug), scope_class(slug)
    body = f"""
export function __NAME__() {{
  return (
    {_section_open(slug, scope, False, False)}
      <div className="k-container">
        <div className="__SC__-band">
          <h2 id="{slug}-title" className="k-h2">{{DATA.title}}</h2>
          {{DATA.text ? <p className="__SC__-text">{{DATA.text}}</p> : null}}
          <a className="__SC__-btn" href={{DATA.href}}>{{DATA.button}}</a>
        </div>
      </div>
    </section>
  );
}}
"""
    css = """
.__SC__ .__SC__-band { display: grid; gap: var(--k-space-3); justify-items: start; padding: clamp(32px, 6vw, 80px); border-radius: var(--k-radius); background-color: var(--k-accent); color: var(--k-accent-ink); }
.__SC__ .__SC__-band .k-h2 { max-width: 20ch; }
.__SC__ .__SC__-text { max-width: 52ch; font-size: 1.125rem; }
.__SC__ .__SC__-btn { display: inline-flex; align-items: center; min-height: 48px; padding: 0 1.5rem; border-radius: var(--k-radius-btn); background-color: var(--k-accent-ink); color: var(--k-accent); font-weight: 600; text-decoration: none; transition: transform 180ms var(--k-ease); }
.__SC__ .__SC__-btn:hover, .__SC__ .__SC__-btn:focus-visible { transform: translateY(-2px); }
.__SC__ .__SC__-btn:active { transform: scale(0.98); }
.__SC__ .__SC__-btn:focus-visible { outline-color: var(--k-accent-ink); }
"""
    return assemble(name, content, _fill(body, NAME=name).replace("__SC__", scope), []), css.replace("__SC__", scope)


def render_preview(site, slug: str, content: dict) -> tuple[str, str]:
    name, scope = site.component(slug), scope_class(slug)
    body = f"""
export function __NAME__() {{
  return (
    {_section_open(slug, scope, site.tints.get(slug, False), False)}
      <div className="k-container __SC__-grid">
        <div className="__SC__-copy">
          <h2 id="{slug}-title" className="k-h2">{{DATA.title}}</h2>
          {{DATA.intro ? <p className="k-lede">{{DATA.intro}}</p> : null}}
          <ul className="__SC__-points">
            {{DATA.points.map((point: any, i: number) => (
              <li key={{i}}>
                <h3 className="k-h3">{{point.title}}</h3>
                {{point.text ? <p className="k-muted">{{point.text}}</p> : null}}
              </li>
            ))}}
          </ul>
        </div>
        <div className="__SC__-visual">
          <AppWindow labels={{DATA.labels}} bars={{DATA.bars}} title={{DATA.title}} />
        </div>
      </div>
    </section>
  );
}}
"""
    css = """
.__SC__ .__SC__-grid { display: grid; grid-template-columns: minmax(0, 0.85fr) minmax(0, 1.15fr); gap: clamp(32px, 6vw, 88px); align-items: center; }
.__SC__ .__SC__-copy { display: grid; gap: var(--k-space-3); }
.__SC__ .__SC__-points { display: grid; gap: var(--k-space-3); margin-top: var(--k-space-1); }
.__SC__ .__SC__-points li { display: grid; gap: 4px; padding-left: var(--k-space-3); border-left: 2px solid var(--k-accent); }
@media (max-width: 900px) { .__SC__ .__SC__-grid { grid-template-columns: minmax(0, 1fr); } }
""" + CSS_APP_WINDOW.replace("__S__", ".__SC__")
    return assemble(name, content, _fill(body, NAME=name).replace("__SC__", scope), [H_APP_WINDOW]), css.replace("__SC__", scope)


def render_section(site, slug: str, kind: str, content: dict) -> tuple[str, str]:
    if kind == "header":
        return render_header(site, slug, content)
    if kind == "footer":
        return render_footer(site, slug, content)
    if kind == "hero":
        return render_hero(site, slug, content)
    if kind == "features":
        return render_features(site, slug, content)
    if kind == "team":
        return render_features(site, slug, content, members=True)
    if kind in {"story", "split"}:
        return render_story(site, slug, content)
    if kind == "work":
        return render_work(site, slug, content)
    if kind == "products":
        return render_products(site, slug, content)
    if kind == "cart":
        return render_cart(site, slug, content)
    if kind == "menu":
        return render_menu(site, slug, content)
    if kind == "steps":
        return render_steps(site, slug, content)
    if kind == "faq":
        return render_faq(site, slug, content)
    if kind == "articles":
        return render_articles(site, slug, content)
    if kind == "pricing":
        return render_pricing(site, slug, content)
    if kind == "quotes":
        return render_quotes(site, slug, content)
    if kind == "contact":
        return render_contact(site, slug, content)
    if kind == "cta":
        return render_cta(site, slug, content)
    if kind == "preview":
        return render_preview(site, slug, content)
    return render_story(site, slug, content)
