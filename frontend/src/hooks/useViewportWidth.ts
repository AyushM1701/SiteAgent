import { useEffect, useState } from 'react';

/** Current window.innerWidth, updated on resize. */
export function useViewportWidth(): number {
  const [width, setWidth] = useState(() => (typeof window !== 'undefined' ? window.innerWidth : 1280));
  useEffect(() => {
    const update = () => setWidth(window.innerWidth);
    window.addEventListener('resize', update);
    return () => window.removeEventListener('resize', update);
  }, []);
  return width;
}

export const SIDEBAR_WIDTH = 256;
export const INSPECTOR_WIDTH = 320;
export const MIN_CHAT_WIDTH = 380;
export const MIN_WORKSPACE_WIDTH = 360;
/** At or above this width the inspector docks beside the workspace; below it overlays. */
export const INSPECTOR_DOCK_MIN = 1280;

/** Widest the workspace may be while leaving the chat usable. */
export function maxWorkspaceWidth(viewport: number, sidebarOpen: boolean, inspectorOpen: boolean): number {
  const reserved = (sidebarOpen && viewport >= 768 ? SIDEBAR_WIDTH : 0)
    + (inspectorOpen && viewport >= INSPECTOR_DOCK_MIN ? INSPECTOR_WIDTH : 0)
    + MIN_CHAT_WIDTH;
  return Math.max(MIN_WORKSPACE_WIDTH, viewport - reserved);
}
