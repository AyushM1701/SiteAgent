import React, { useRef, useEffect, useCallback } from 'react';
import { useWorkspaceStore } from '../../state/workspace-store';

export const WorkspaceResizer: React.FC = () => {
  const { workspaceWidth, setWorkspaceWidth, isResizing, setIsResizing, workspaceOpen } =
    useWorkspaceStore();

  const startXRef = useRef<number>(0);
  const startWidthRef = useRef<number>(workspaceWidth);
  const resizerRef = useRef<HTMLDivElement>(null);

  // Bounds
  const minWidth = 360;
  const getBounds = useCallback(() => {
    const windowWidth = typeof window !== 'undefined' ? window.innerWidth : 1280;
    const maxWidth = Math.max(minWidth, windowWidth - 360);
    return { minWidth, maxWidth };
  }, []);

  // Clamp correctly on window resize
  useEffect(() => {
    const handleWindowResize = () => {
      const { maxWidth } = getBounds();
      const current = useWorkspaceStore.getState().workspaceWidth;
      if (current > maxWidth) {
        setWorkspaceWidth(maxWidth);
      } else if (current < minWidth) {
        setWorkspaceWidth(minWidth);
      }
    };

    window.addEventListener('resize', handleWindowResize);
    return () => window.removeEventListener('resize', handleWindowResize);
  }, [getBounds, setWorkspaceWidth]);

  // Window fail-safe: ensures resize never gets stuck if pointer drops outside or window blurs
  useEffect(() => {
    if (!isResizing) return;

    const stopResizing = () => {
      setIsResizing(false);
    };

    window.addEventListener('pointerup', stopResizing);
    window.addEventListener('pointercancel', stopResizing);
    window.addEventListener('blur', stopResizing);

    return () => {
      window.removeEventListener('pointerup', stopResizing);
      window.removeEventListener('pointercancel', stopResizing);
      window.removeEventListener('blur', stopResizing);
    };
  }, [isResizing, setIsResizing]);

  if (!workspaceOpen) return null;

  const handlePointerDown = (e: React.PointerEvent<HTMLDivElement>) => {
    e.preventDefault();
    try {
      resizerRef.current?.setPointerCapture(e.pointerId);
    } catch (_) {}

    startXRef.current = e.clientX;
    startWidthRef.current = workspaceWidth;
    setIsResizing(true);
  };

  const handlePointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    if (!isResizing) return;
    e.preventDefault();

    // Dragging left increases workspace width (anchored on right)
    const delta = startXRef.current - e.clientX;
    const { maxWidth } = getBounds();
    const newWidth = Math.min(Math.max(startWidthRef.current + delta, minWidth), maxWidth);
    setWorkspaceWidth(newWidth);
  };

  const handlePointerUp = (e: React.PointerEvent<HTMLDivElement>) => {
    if (!isResizing) return;
    try {
      if (resizerRef.current?.hasPointerCapture(e.pointerId)) {
        resizerRef.current.releasePointerCapture(e.pointerId);
      }
    } catch (_) {}
    setIsResizing(false);
  };

  const handlePointerCancel = (e: React.PointerEvent<HTMLDivElement>) => {
    try {
      if (resizerRef.current?.hasPointerCapture(e.pointerId)) {
        resizerRef.current.releasePointerCapture(e.pointerId);
      }
    } catch (_) {}
    setIsResizing(false);
  };

  const handleLostPointerCapture = () => {
    setIsResizing(false);
  };

  const handleDoubleClick = () => {
    // Double-click reset to 50% of viewport width
    const targetWidth = Math.round((typeof window !== 'undefined' ? window.innerWidth : 1280) * 0.5);
    const { maxWidth } = getBounds();
    setWorkspaceWidth(Math.min(Math.max(targetWidth, minWidth), maxWidth));
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    const step = e.shiftKey ? 60 : 20;
    const { maxWidth } = getBounds();

    if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
      e.preventDefault();
      setWorkspaceWidth(Math.min(maxWidth, workspaceWidth + step));
    } else if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
      e.preventDefault();
      setWorkspaceWidth(Math.max(minWidth, workspaceWidth - step));
    } else if (e.key === 'Home') {
      e.preventDefault();
      setWorkspaceWidth(minWidth);
    } else if (e.key === 'End') {
      e.preventDefault();
      setWorkspaceWidth(maxWidth);
    } else if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleDoubleClick();
    }
  };

  const { maxWidth } = getBounds();

  return (
    <>
      {/* Invisible full-screen backdrop during drag so iframes don't steal pointer events */}
      {isResizing && (
        <div className="fixed inset-0 z-50 cursor-col-resize select-none pointer-events-auto" />
      )}

      {/* Accessible, Touch-Ready Draggable Divider Splitter */}
      <div
        ref={resizerRef}
        id="workspace-resizer-handle"
        role="separator"
        tabIndex={0}
        aria-orientation="vertical"
        aria-label="Workspace resizer"
        aria-valuenow={workspaceWidth}
        aria-valuemin={minWidth}
        aria-valuemax={maxWidth}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerCancel={handlePointerCancel}
        onLostPointerCapture={handleLostPointerCapture}
        onDoubleClick={handleDoubleClick}
        onKeyDown={handleKeyDown}
        style={{ touchAction: 'none' }}
        className={`relative w-2 hover:w-2 -mx-1 cursor-col-resize select-none flex items-center justify-center group z-40 transition-colors focus:outline-none focus-visible:ring-1 focus-visible:ring-emerald-400 ${
          isResizing ? 'bg-emerald-500/20' : 'hover:bg-white/[0.04]'
        }`}
        title="Drag to resize workspace (double-click to reset 50%, arrow keys to adjust)"
      >
        <div
          className={`w-[1px] h-full transition-colors pointer-events-none ${
            isResizing ? 'bg-emerald-400 w-[2px]' : 'bg-white/[0.08] group-hover:bg-emerald-400/80 group-focus-visible:bg-emerald-400'
          }`}
        />
      </div>
    </>
  );
};
