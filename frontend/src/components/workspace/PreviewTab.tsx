import React, { useEffect, useRef } from 'react';
import { 
  RefreshCw, 
  ExternalLink, 
  Monitor, 
  Tablet, 
  Smartphone, 
  Crosshair, 
  Box 
} from 'lucide-react';
import { useWorkspaceStore } from '../../state/workspace-store';
import { useProjectStore } from '../../state/project-store';
import { useSelectionStore } from '../../state/selection-store';
import { useAgentStore } from '../../state/agent-store';

export const PreviewTab: React.FC = () => {
  const { previewDevice, setPreviewDevice, previewKey, reloadPreview, setInspectorOpen } = useWorkspaceStore();
  const { currentProjectId } = useProjectStore();
  const { validationResult } = useAgentStore();
  const { inspectMode, setInspectMode, setSelectedElement, setSelected3DObject } = useSelectionStore();
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const scrollPosRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });

  const previewUrl = currentProjectId
    ? `/preview/${encodeURIComponent(currentProjectId)}/?_k=${previewKey}`
    : null;

  const handleIframeLoad = () => {
    try {
      const cw = iframeRef.current?.contentWindow;
      if (!cw) return;

      // Restore scroll position after reload (Item 24: keep preview live while tuning scroll behavior)
      if (scrollPosRef.current.x > 0 || scrollPosRef.current.y > 0) {
        cw.scrollTo({
          left: scrollPosRef.current.x,
          top: scrollPosRef.current.y,
          behavior: 'instant' as ScrollBehavior,
        });
      }

      // Track ongoing scroll coordinates
      cw.addEventListener('scroll', () => {
        try {
          scrollPosRef.current = {
            x: cw.scrollX || cw.document.documentElement.scrollLeft || 0,
            y: cw.scrollY || cw.document.documentElement.scrollTop || 0,
          };
        } catch {}
      }, { passive: true });
    } catch {}
  };

  // Listen for inspect messages posted from preview iframe
  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      if (event.source !== iframeRef.current?.contentWindow) return;
      if (!event.data || typeof event.data !== 'object') return;
      if (event.data.type === 'workbench:scroll_update') {
        scrollPosRef.current = { x: event.data.scrollX || 0, y: event.data.scrollY || 0 };
      } else if (event.data.type === 'workbench:dom_select') {
        setSelectedElement({
          type: 'dom',
          tagName: event.data.tagName || 'DIV',
          className: event.data.className,
          componentHint: event.data.componentHint,
          selector: event.data.selector || '',
          textContent: event.data.textContent,
        });
        setInspectorOpen(true);
      } else if (event.data.type === 'workbench:3d_select') {
        setSelected3DObject({
          type: '3d',
          name: event.data.name || 'Mesh',
          uuid: event.data.uuid || '',
          position: event.data.position || { x: 0, y: 0, z: 0 },
          rotation: event.data.rotation || { x: 0, y: 0, z: 0 },
          materialName: event.data.materialName,
        });
        setInspectorOpen(true);
      }
    };

    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, []);

  const deviceWidth = {
    desktop: 'w-full',
    tablet: 'w-[768px]',
    mobile: 'w-[375px]',
  }[previewDevice];
  const viewportLabel = { desktop: 'Responsive desktop', tablet: '768 px', mobile: '375 px' }[previewDevice];
  const validationErrors = validationResult?.errors || [];

  return (
    <div className="flex-1 flex flex-col h-full bg-[#0a0c10] overflow-hidden select-none">
      {/* Preview toolbar */}
      <div className="h-10 border-b border-white/[0.06] bg-[#141619] px-3 flex items-center justify-between text-xs">
        {/* Viewport switcher */}
        <div className="flex items-center gap-1 bg-[#191c20] p-0.5 rounded-md border border-white/[0.04]">
          <button
            id="preview-viewport-desktop"
            onClick={() => setPreviewDevice('desktop')}
            className={`p-1 rounded cursor-pointer ${
              previewDevice === 'desktop'
                ? 'bg-emerald-500 text-black'
                : 'text-slate-400 hover:text-slate-200'
            }`}
            title="Desktop Viewport (100%)"
          >
            <Monitor size={14} />
          </button>
          <button
            id="preview-viewport-tablet"
            onClick={() => setPreviewDevice('tablet')}
            className={`p-1 rounded cursor-pointer ${
              previewDevice === 'tablet'
                ? 'bg-emerald-500 text-black'
                : 'text-slate-400 hover:text-slate-200'
            }`}
            title="Tablet Viewport (768px)"
          >
            <Tablet size={14} />
          </button>
          <button
            id="preview-viewport-mobile"
            onClick={() => setPreviewDevice('mobile')}
            className={`p-1 rounded cursor-pointer ${
              previewDevice === 'mobile'
                ? 'bg-emerald-500 text-black'
                : 'text-slate-400 hover:text-slate-200'
            }`}
            title="Mobile Viewport (375px)"
          >
            <Smartphone size={14} />
          </button>
        </div>

        {/* Action buttons: Inspect, Reload, Popout */}
        <div className="flex items-center gap-1.5">
          <button
            id="preview-inspect-dom-btn"
            onClick={() => setInspectMode(inspectMode === 'dom' ? 'none' : 'dom')}
            className={`flex items-center gap-1 px-2 py-1 rounded text-xs border transition-colors cursor-pointer ${
              inspectMode === 'dom'
                ? 'bg-emerald-500/15 border-emerald-500/40 text-emerald-300'
                : 'border-white/[0.06] hover:bg-white/[0.04] text-slate-400 hover:text-slate-200'
            }`}
            title="Inspect DOM Elements"
          >
            <Crosshair size={13} />
            <span className="hidden sm:inline">Inspect DOM</span>
          </button>

          <button
            id="preview-inspect-3d-btn"
            onClick={() => setInspectMode(inspectMode === '3d' ? 'none' : '3d')}
            className={`flex items-center gap-1 px-2 py-1 rounded text-xs border transition-colors cursor-pointer ${
              inspectMode === '3d'
                ? 'bg-amber-500/15 border-amber-500/40 text-amber-300'
                : 'border-white/[0.06] hover:bg-white/[0.04] text-slate-400 hover:text-slate-200'
            }`}
            title="Inspect 3D Objects"
          >
            <Box size={13} />
            <span className="hidden sm:inline">Inspect 3D</span>
          </button>

          <button
            id="preview-reload-btn"
            onClick={reloadPreview}
            className="p-1 rounded hover:bg-white/[0.06] text-slate-400 hover:text-slate-200 cursor-pointer"
            title="Reload Preview"
          >
            <RefreshCw size={13} />
          </button>

          {previewUrl && (
            <a
              id="preview-open-external-btn"
              href={previewUrl}
              target="_blank"
              rel="noreferrer"
              className="p-1 rounded hover:bg-white/[0.06] text-slate-400 hover:text-slate-200 cursor-pointer"
              title="Open in new window"
            >
              <ExternalLink size={13} />
            </a>
          )}
        </div>
      </div>

      <details className="border-b border-white/[0.06] bg-[#101216] text-[11px] text-slate-400 px-3 py-1.5">
        <summary className="cursor-pointer flex items-center gap-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-emerald-400">
          <span>{viewportLabel}</span><span>·</span>
          <span>{validationResult ? `Build ${validationResult.build_status || (validationResult.build_passed ? 'passed' : 'failed')}` : 'Build not checked'}</span>
          <span>·</span><span>{validationResult ? `${validationErrors.length} validation errors` : 'Validation not checked'}</span>
        </summary>
        <div className="pt-2 pb-1 space-y-1 max-h-28 overflow-y-auto">
          <div>Runtime: {validationResult?.runtime_status || 'unknown'} · Motion: {validationResult?.motion_runtime_status || 'not browser verified'} · 3D: {validationResult?.three_d_runtime_status || 'not checked'}</div>
          {validationErrors.length ? validationErrors.slice(0, 6).map((error, index) => <div key={index} className="text-rose-300">{error}</div>) : <div>{validationResult ? 'No reported compiler, runtime, or interaction errors.' : 'Validation has not run for this project.'}</div>}
        </div>
      </details>

      {/* Iframe Viewport Container */}
      <div className="flex-1 flex items-center justify-center p-2 bg-[#07080c] overflow-auto">
        {previewUrl ? (
          <div
            className={`h-full ${deviceWidth} transition-all duration-300 rounded-lg overflow-hidden border border-white/[0.08] shadow-2xl bg-black relative`}
          >
            <iframe
              ref={iframeRef}
              src={previewUrl}
              title="Live Preview"
              onLoad={handleIframeLoad}
              className="w-full h-full border-none bg-black"
              sandbox="allow-scripts allow-forms allow-popups"
            />
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center text-center p-8 text-slate-500 space-y-2">
            <Monitor size={32} className="text-slate-600" />
            <p className="text-sm font-medium text-slate-400">No active preview</p>
            <p className="text-xs text-slate-500">
              Generate a component or select an existing project to launch live preview.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
