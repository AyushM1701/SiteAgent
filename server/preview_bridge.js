/* Workbench preview bridge.
 * Injected into sandboxed previews by server/preview_manager.py. The preview runs
 * on an opaque origin, so the workbench cannot reach into it; this script is the
 * only channel. It reports scroll position, restores it after a rebuild, and
 * implements the element picker behind "Inspect". */
(function () {
  if (window.__workbenchBridge) return;
  window.__workbenchBridge = true;
  var parentWin = window.parent;
  if (!parentWin || parentWin === window) return;

  var mode = 'none';
  var box = null;
  var label = null;
  var hovered = null;

  function post(message) {
    try { parentWin.postMessage(message, '*'); } catch (e) {}
  }

  function cssEscape(value) {
    return window.CSS && CSS.escape ? CSS.escape(value) : String(value).replace(/[^\w-]/g, '\\$&');
  }

  function selectorFor(el) {
    var parts = [];
    var node = el;
    while (node && node.nodeType === 1 && node !== document.documentElement && parts.length < 6) {
      if (node.id) {
        parts.unshift('#' + cssEscape(node.id));
        break;
      }
      var part = node.tagName.toLowerCase();
      var cls = (typeof node.className === 'string' ? node.className : '').trim().split(/\s+/).filter(Boolean);
      if (cls.length) part += '.' + cls.slice(0, 2).map(cssEscape).join('.');
      var parent = node.parentElement;
      if (parent) {
        var same = Array.prototype.filter.call(parent.children, function (c) { return c.tagName === node.tagName; });
        if (same.length > 1) part += ':nth-of-type(' + (same.indexOf(node) + 1) + ')';
      }
      parts.unshift(part);
      node = parent;
    }
    return parts.join(' > ');
  }

  function sectionFor(el) {
    var node = el.closest ? el.closest('section[id], header, footer, nav, main > [id]') : null;
    if (!node) return '';
    if (node.id) return node.id;
    return node.tagName.toLowerCase();
  }

  function describe(el) {
    var rect = el.getBoundingClientRect();
    var style = window.getComputedStyle(el);
    var text = (el.innerText || el.textContent || '').replace(/\s+/g, ' ').trim();
    return {
      type: 'workbench:dom_select',
      tagName: el.tagName,
      id: el.id || undefined,
      className: typeof el.className === 'string' ? el.className : '',
      selector: selectorFor(el),
      componentHint: sectionFor(el),
      textContent: text.slice(0, 280),
      href: el.getAttribute('href') || undefined,
      src: el.getAttribute('src') || undefined,
      alt: el.getAttribute('alt') || undefined,
      role: el.getAttribute('role') || undefined,
      ariaLabel: el.getAttribute('aria-label') || undefined,
      size: { width: Math.round(rect.width), height: Math.round(rect.height) },
      styles: {
        color: style.color,
        backgroundColor: style.backgroundColor,
        fontFamily: style.fontFamily,
        fontSize: style.fontSize,
        fontWeight: style.fontWeight,
        padding: style.padding,
        margin: style.margin,
        borderRadius: style.borderRadius,
        display: style.display
      }
    };
  }

  function ensureOverlay() {
    if (box) return;
    box = document.createElement('div');
    box.setAttribute('data-workbench-overlay', '');
    box.style.cssText = 'position:fixed;pointer-events:none;z-index:2147483646;border:2px solid #34d399;' +
      'background:rgba(52,211,153,0.12);border-radius:3px;transition:all 60ms ease-out;display:none;';
    label = document.createElement('div');
    label.setAttribute('data-workbench-overlay', '');
    label.style.cssText = 'position:fixed;pointer-events:none;z-index:2147483647;background:#065f46;color:#ecfdf5;' +
      'font:600 11px/1.4 ui-monospace,Menlo,Consolas,monospace;padding:2px 6px;border-radius:4px;display:none;' +
      'max-width:60vw;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;';
    document.documentElement.appendChild(box);
    document.documentElement.appendChild(label);
  }

  function highlight(el) {
    ensureOverlay();
    if (!el) {
      box.style.display = 'none';
      label.style.display = 'none';
      return;
    }
    var r = el.getBoundingClientRect();
    box.style.display = 'block';
    box.style.left = r.left + 'px';
    box.style.top = r.top + 'px';
    box.style.width = r.width + 'px';
    box.style.height = r.height + 'px';
    var name = el.tagName.toLowerCase();
    var cls = typeof el.className === 'string' ? el.className.trim().split(/\s+/).filter(Boolean)[0] : '';
    label.textContent = name + (cls ? '.' + cls : '') + '  ' + Math.round(r.width) + '×' + Math.round(r.height);
    label.style.display = 'block';
    var top = r.top - 22;
    label.style.top = (top < 0 ? r.bottom + 4 : top) + 'px';
    label.style.left = Math.max(0, r.left) + 'px';
  }

  function isOverlay(el) {
    return el && el.hasAttribute && el.hasAttribute('data-workbench-overlay');
  }

  function onMove(event) {
    var el = event.target;
    if (!el || isOverlay(el) || el === hovered) return;
    hovered = el;
    highlight(el);
  }

  function swallow(event) {
    event.preventDefault();
    event.stopPropagation();
    event.stopImmediatePropagation();
  }

  function onClick(event) {
    swallow(event);
    var el = event.target;
    if (!el || isOverlay(el)) return;
    post(describe(el));
  }

  function onKey(event) {
    if (event.key === 'Escape') {
      setMode('none');
      post({ type: 'workbench:inspect_exit' });
    }
  }

  function setMode(next) {
    if (next === mode) return;
    var on = next !== 'none';
    var wasOn = mode !== 'none';
    mode = next;
    if (on && !wasOn) {
      document.addEventListener('mousemove', onMove, true);
      document.addEventListener('click', onClick, true);
      document.addEventListener('mousedown', swallow, true);
      document.addEventListener('mouseup', swallow, true);
      document.addEventListener('submit', swallow, true);
      document.addEventListener('keydown', onKey, true);
      document.documentElement.style.cursor = 'crosshair';
    } else if (!on && wasOn) {
      document.removeEventListener('mousemove', onMove, true);
      document.removeEventListener('click', onClick, true);
      document.removeEventListener('mousedown', swallow, true);
      document.removeEventListener('mouseup', swallow, true);
      document.removeEventListener('submit', swallow, true);
      document.removeEventListener('keydown', onKey, true);
      document.documentElement.style.cursor = '';
      hovered = null;
      highlight(null);
    }
  }

  function highlightSelector(selector) {
    try {
      var el = selector ? document.querySelector(selector) : null;
      if (el) {
        el.scrollIntoView({ block: 'center', behavior: 'instant' });
        highlight(el);
      } else {
        highlight(null);
      }
    } catch (e) {
      highlight(null);
    }
  }

  window.addEventListener('message', function (event) {
    if (event.source !== parentWin) return;
    var data = event.data;
    if (!data || typeof data !== 'object') return;
    if (data.type === 'workbench:inspect_mode') setMode(data.mode === 'dom' || data.mode === '3d' ? data.mode : 'none');
    else if (data.type === 'workbench:restore_scroll') window.scrollTo({ left: data.x || 0, top: data.y || 0, behavior: 'instant' });
    else if (data.type === 'workbench:highlight') highlightSelector(data.selector);
  });

  var pending = 0;
  window.addEventListener('scroll', function () {
    if (pending) return;
    pending = window.setTimeout(function () {
      pending = 0;
      post({ type: 'workbench:scroll_update', scrollX: window.scrollX, scrollY: window.scrollY });
    }, 120);
  }, { passive: true });

  window.addEventListener('error', function (event) {
    post({ type: 'workbench:runtime_error', message: String(event.message || 'Script error'), source: event.filename || '' });
  });
  window.addEventListener('unhandledrejection', function (event) {
    var reason = event.reason;
    post({ type: 'workbench:runtime_error', message: String((reason && reason.message) || reason || 'Unhandled promise rejection') });
  });

  function ready() {
    post({ type: 'workbench:ready', title: document.title, href: location.href });
  }
  if (document.readyState === 'complete') ready();
  else window.addEventListener('load', ready);
})();
