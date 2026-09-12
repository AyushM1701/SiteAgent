import '@testing-library/jest-dom';
import { vi } from 'vitest';
import { act } from '@testing-library/react';

// Expose vi as jest so @testing-library/dom detects fake timers and advances them in waitFor/findBy
(globalThis as any).jest = vi;

// Polyfill File in jsdom environment if missing or unconstructible
if (
  typeof globalThis.File === 'undefined' ||
  !(function () {
    try {
      new (globalThis as any).File([], 't');
      return true;
    } catch {
      return false;
    }
  })()
) {
  try {
    const { File } = require('node:buffer');
    globalThis.File = File;
    if (typeof window !== 'undefined') {
      (window as any).File = File;
    }
  } catch {}
}

// Polyfill PointerEvent in jsdom environment
if (typeof window !== 'undefined' && typeof window.PointerEvent === 'undefined') {
  class PointerEvent extends (window.MouseEvent || Object) {
    pointerId: number;
    width: number;
    height: number;
    pressure: number;
    pointerType: string;
    isPrimary: boolean;

    constructor(type: string, params: any = {}) {
      super(type, params);
      this.pointerId = params.pointerId ?? 0;
      this.width = params.width ?? 1;
      this.height = params.height ?? 1;
      this.pressure = params.pressure ?? 0;
      this.pointerType = params.pointerType ?? 'mouse';
      this.isPrimary = params.isPrimary ?? true;
    }
  }
  (window as any).PointerEvent = PointerEvent;
  (globalThis as any).PointerEvent = PointerEvent;
}

// Polyfill scrollIntoView in jsdom environment
if (typeof window !== 'undefined') {
  if (typeof window.HTMLElement !== 'undefined' && typeof window.HTMLElement.prototype.scrollIntoView !== 'function') {
    window.HTMLElement.prototype.scrollIntoView = vi.fn();
  }
  if (typeof window.Element !== 'undefined' && typeof window.Element.prototype.scrollIntoView !== 'function') {
    window.Element.prototype.scrollIntoView = vi.fn();
  }
}

// Polyfill writable navigator.clipboard in jsdom environment
let _clipboard: any = {
  writeText: vi.fn().mockResolvedValue(undefined),
  readText: vi.fn().mockResolvedValue(''),
};
function defineWritableClipboard(target: any) {
  if (!target) return;
  try {
    Object.defineProperty(target, 'clipboard', {
      get() {
        return _clipboard;
      },
      set(val) {
        _clipboard = val;
        if (typeof window !== 'undefined' && window.navigator) {
          try {
            Object.defineProperty(window.navigator, 'clipboard', {
              value: val,
              writable: true,
              configurable: true,
              enumerable: true,
            });
          } catch {}
        }
        if (typeof navigator !== 'undefined') {
          try {
            Object.defineProperty(navigator, 'clipboard', {
              value: val,
              writable: true,
              configurable: true,
              enumerable: true,
            });
          } catch {}
        }
      },
      configurable: true,
      enumerable: true,
    });
  } catch {}
}

if (typeof window !== 'undefined' && window.navigator) {
  defineWritableClipboard(window.navigator);
}
if (typeof navigator !== 'undefined') {
  defineWritableClipboard(navigator);
}

const origAdvance = vi.advanceTimersByTime.bind(vi);
vi.advanceTimersByTime = (ms: number) => {
  let result: any;
  act(() => {
    result = origAdvance(ms);
  });
  return result;
};

const origRunAll = vi.runAllTimers.bind(vi);
vi.runAllTimers = () => {
  let result: any;
  act(() => {
    result = origRunAll();
  });
  return result;
};

const origNextTimer = vi.advanceTimersToNextTimer.bind(vi);
vi.advanceTimersToNextTimer = (steps?: number) => {
  let result: any;
  act(() => {
    result = origNextTimer(steps);
  });
  return result;
};
