import React, { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import {
  RefreshCw,
  ExternalLink,
  Monitor,
  Tablet,
  Smartphone,
  Crosshair,
  Box,
  Loader2,
  AlertTriangle,
  Hammer,
} from 'lucide-react';
import { useWorkspaceStore, PreviewDevice } from '../../state/workspace-store';
import { useProjectStore } from '../../state/project-store';
import { useSelectionStore } from '../../state/selection-store';
import { useAgentStore } from '../../state/agent-store';
import { api, PreviewStatus } from '../../services/api';
import { projectWsClient } from '../../services/project-ws';

// Logical viewport for each device. The site renders at this width and the frame
// is scaled down to fit the panel, so "Desktop" shows the desktop layout even in
// a narrow workspace.
const DEVICES: Record<PreviewDevice, { width: number; label: string }> = {
  desktop: { width: 1280, label: 'Desktop' },
  tablet: { width: 768, label: 'Tablet' },
  mobile: { width: 390, label: 'Mobile' },
};

type Phase = 'idle' | 'building' | 'ready' | 'error' | 'empty';

// Scroll position per project survives rebuilds and tab switches.
const scrollPositions = new Map<string, { x: number; y: number }>();

/** Dispatched by the inspector to outline the selected element inside the preview. */
export const PREVIEW_HIGHLIGHT_EVENT = 'workbench:preview-highlight';

export const PreviewTab: React.FC = () => {
  const { previewDevice, setPreviewDevice, previewKey, reloadPreview, setInspectorOpen } = useWorkspaceStore();
  const { currentProjectId, currentProject } = useProjectStore();
  const { validationResult, status } = useAgentStore();
  const { inspectMode, setInspectMode, setSelectedElement, setSelected3DObject } = useSelectionStore();
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const stageRef = useRef<HTMLDivElement>(null);
  const [stage, setStage] = useState({ width: 0, height: 0 });
  const [phase, setPhase] = useState<Phase>('idle');
  const [url, setUrl] = useState<string | null>(null);
  const [error, setError] = useState<string>('');
  const [emptyMessage, setEmptyMessage] = useState<string>('');
  const [runtimeErrors, setRuntimeErrors] = useState<string[]>([]);
  const [frameLoading, setFrameLoading] = useState(false);
  const requestRef = useRef(0);
  const isWorking = status === 'generating' || status === 'planning' || status === 'typechecking' || status === 'repairing';

  const loadPreview = useCallback(async (rebuild: boolean) => {
    if (!currentProjectId) {
      setPhase('idle');
      setUrl(null);
      return;
    }
    const request = ++requestRef.current;
    setPhase('building');
    setError('');
    let result: PreviewStatus;
    try {
      result = await api.getPreview(currentProjectId, rebuild);
    } catch (err: any) {
      result = { status: 'error', error: err?.message || String(err) };
    }
    if (request !== requestRef.current) return; // a newer request superseded this one
    if (result.status === 'ready' && result.url) {
      setRuntimeErrors([]);
      setFrameLoading(true);
      setUrl(`${result.url}?_k=${Date.now()}`);
      setPhase('ready');
    } else if (result.status === 'empty') {
      setUrl(null);
      setEmptyMessage(result.message || 'No site files yet.');
      setPhase('empty');
    } else {
      setError(result.error || 'The preview could not be built.');
      setPhase('error');
    }
  }, [currentProjectId]);

  // Rebuild when the project changes or anything asks for a reload (generation
  // result, file save, revert, reload button).
  useEffect(() => {
    loadPreview(false);
  }, [loadPreview, previewKey]);

  // Track the stage size so the device frame can be scaled to fit.
  useLayoutEffect(() => {
    const node = stageRef.current;
    if (!node) return;
    const update = () => setStage({ width: node.clientWidth, height: node.clientHeight });
    update();
    const observer = new ResizeObserver(update);
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  const post = useCallback((message: Record<string, unknown>) => {
    try {
      iframeRef.current?.contentWindow?.postMessage(message, '*');
    } catch (_) {}
  }, []);

  // Keep the picker inside the preview in sync with the toolbar toggle.
  useEffect(() => {
    post({ type: 'workbench:inspect_mode', mode: inspectMode });
  }, [inspectMode, post, url]);

  // Leave inspect mode when the preview goes away.
  useEffect(() => () => setInspectMode('none'), [setInspectMode]);

  useEffect(() => {
    const onHighlight = (event: Event) => post({ type: 'workbench:highlight', selector: (event as CustomEvent).detail });
    window.addEventListener(PREVIEW_HIGHLIGHT_EVENT, onHighlight);
    return () => window.removeEventListener(PREVIEW_HIGHLIGHT_EVENT, onHighlight);
  }, [post]);

  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      if (event.source !== iframeRef.current?.contentWindow) return;
      const data = event.data;
      if (!data || typeof data !== 'object' || typeof data.type !== 'string') return;
      if (data.type === 'workbench:ready') {
        setFrameLoading(false);
        const saved = currentProjectId ? scrollPositions.get(currentProjectId) : undefined;
        if (saved && (saved.x || saved.y)) post({ type: 'workbench:restore_scroll', ...saved });
        post({ type: 'workbench:inspect_mode', mode: useSelectionStore.getState().inspectMode });
      } else if (data.type === 'workbench:scroll_update') {
        if (currentProjectId) scrollPositions.set(currentProjectId, { x: data.scrollX || 0, y: data.scrollY || 0 });
      } else if (data.type === 'workbench:runtime_error') {
        setRuntimeErrors((prev) => (prev.includes(data.message) ? prev : [...prev, String(data.message)].slice(-20)));
      } else if (data.type === 'workbench:inspect_exit') {
        setInspectMode('none');
      } else if (data.type === 'workbench:dom_select') {
        setSelectedElement({
          type: 'dom',
          tagName: data.tagName || 'DIV',
          id: data.id,
          className: data.className,
          componentHint: data.componentHint,
          selector: data.selector || '',
          textContent: data.textContent,
          href: data.href,
          src: data.src,
          alt: data.alt,
          ariaLabel: data.ariaLabel,
          size: data.size,
          styles: data.styles,
        });
        // Tell the agent which section the next edit targets.
        projectWsClient.sendPreviewSelection({
          component: data.componentHint || undefined,
          selector: data.selector,
          tag: String(data.tagName || '').toLowerCase(),
          text: data.textContent,
        });
        setInspectorOpen(true);
      } else if (data.type === 'workbench:3d_select') {
        setSelected3DObject({
          type: '3d',
          name: data.name || 'Mesh',
          uuid: data.uuid || '',
          position: data.position || { x: 0, y: 0, z: 0 },
          rotation: data.rotation || { x: 0, y: 0, z: 0 },
          materialName: data.materialName,
        });
        setInspectorOpen(true);
      }
    };
    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, [currentProjectId, post, setInspectMode, setSelectedElement, setSelected3DObject, setInspectorOpen]);

  const device = DEVICES[previewDevice];
  const padding = 16;
  const availableWidth = Math.max(0, stage.width - padding);
  const availableHeight = Math.max(0, stage.height - padding);
  const logicalWidth = previewDevice === 'desktop' ? Math.max(device.width, availableWidth) : device.width;
  const scale = availableWidth > 0 ? Math.min(1, availableWidth / logicalWidth) : 1;
  const logicalHeight = scale > 0 ? availableHeight / scale : availableHeight;
  const zoomLabel = `${logicalWidth} px · ${Math.round(scale * 100)}%`;
  const validationErrors = validationResult?.errors || [];
  const externalUrl = currentProjectId ? `/preview/${encodeURIComponent(currentProjectId)}/` : null;

  const deviceButton = (id: PreviewDevice, icon: React.ReactNode) => (
    <button
      id={`preview-viewport-${id}`}
      onClick={() => setPreviewDevice(id)}
      aria-pressed={previewDevice === id}
      className={`p-1 rounded cursor-pointer ${previewDevice === id ? 'bg-emerald-500 text-black' : 'text-slate-400 hover:text-slate-200'}`}
      title={`${DEVICES[id].label} (${DEVICES[id].width}px)`}
    >
      {icon}
    </button>
  );

  return (
    <div className="flex-1 flex flex-col h-full bg-[#0a0c10] overflow-hidden select-none">
      {/* Preview toolbar */}
      <div className="h-10 border-b border-white/[0.06] bg-[#141619] px-3 flex items-center justify-between gap-2 text-xs">
        <div className="flex items-center gap-2 min-w-0">
          <div className="flex items-center gap-1 bg-[#191c20] p-0.5 rounded-md border border-white/[0.04]">
            {deviceButton('desktop', <Monitor size={14} />)}
            {deviceButton('tablet', <Tablet size={14} />)}
            {deviceButton('mobile', <Smartphone size={14} />)}
          </div>
          <span id="preview-zoom-label" className="hidden md:inline text-[11px] font-mono text-slate-500 truncate">{zoomLabel}</span>
        </div>

        <div className="flex items-center gap-1.5">
          <button
            id="preview-inspect-dom-btn"
            onClick={() => setInspectMode(inspectMode === 'dom' ? 'none' : 'dom')}
            disabled={phase !== 'ready'}
            aria-pressed={inspectMode === 'dom'}
            className={`flex items-center gap-1 px-2 py-1 rounded text-xs border transition-colors cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed ${
              inspectMode === 'dom'
                ? 'bg-emerald-500/15 border-emerald-500/40 text-emerald-300'
                : 'border-white/[0.06] hover:bg-white/[0.04] text-slate-400 hover:text-slate-200'
            }`}
            title="Pick an element in the preview to inspect it (Esc to stop)"
          >
            <Crosshair size={13} />
            <span className="hidden sm:inline">Inspect</span>
          </button>

          {currentProject?.uses3D && (
            <button
              id="preview-inspect-3d-btn"
              onClick={() => setInspectMode(inspectMode === '3d' ? 'none' : '3d')}
              disabled={phase !== 'ready'}
              aria-pressed={inspectMode === '3d'}
              className={`flex items-center gap-1 px-2 py-1 rounded text-xs border transition-colors cursor-pointer disabled:opacity-40 ${
                inspectMode === '3d'
                  ? 'bg-amber-500/15 border-amber-500/40 text-amber-300'
                  : 'border-white/[0.06] hover:bg-white/[0.04] text-slate-400 hover:text-slate-200'
              }`}
              title="Pick the 3D canvas or scene element"
            >
              <Box size={13} />
              <span className="hidden sm:inline">3D</span>
            </button>
          )}

          <button
            id="preview-reload-btn"
            onClick={reloadPreview}
            disabled={!currentProjectId}
            className="p-1 rounded hover:bg-white/[0.06] text-slate-400 hover:text-slate-200 cursor-pointer disabled:opacity-40"
            title="Reload preview (rebuilds if files changed)"
          >
            <RefreshCw size={13} className={phase === 'building' ? 'animate-spin' : ''} />
          </button>

          {externalUrl && phase === 'ready' && (
            <a
              id="preview-open-external-btn"
              href={externalUrl}
              target="_blank"
              rel="noreferrer"
              className="p-1 rounded hover:bg-white/[0.06] text-slate-400 hover:text-slate-200 cursor-pointer"
              title="Open in a new tab"
            >
              <ExternalLink size={13} />
            </a>
          )}
        </div>
      </div>

      <details id="preview-status-bar" className="border-b border-white/[0.06] bg-[#101216] text-[11px] text-slate-400 px-3 py-1.5">
        <summary className="cursor-pointer flex items-center gap-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-emerald-400">
          <span>{device.label}</span><span>·</span>
          <span>{validationResult ? `Build ${validationResult.build_status || (validationResult.build_passed ? 'passed' : 'failed')}` : 'Build not checked'}</span>
          <span>·</span><span>{validationResult ? `${validationErrors.length} validation errors` : 'Validation not checked'}</span>
          {runtimeErrors.length > 0 && (
            <span id="preview-runtime-error-count" className="ml-auto text-rose-300">{runtimeErrors.length} runtime error{runtimeErrors.length === 1 ? '' : 's'}</span>
          )}
        </summary>
        <div className="pt-2 pb-1 space-y-1 max-h-32 overflow-y-auto select-text">
          <div>Runtime: {validationResult?.runtime_status || 'unknown'} · Motion: {validationResult?.motion_runtime_status || 'not browser verified'} · 3D: {validationResult?.three_d_runtime_status || 'not checked'}</div>
          {runtimeErrors.map((message, index) => <div key={`rt-${index}`} className="text-rose-300">Preview: {message}</div>)}
          {validationErrors.length ? validationErrors.slice(0, 6).map((message, index) => <div key={index} className="text-rose-300">{message}</div>) : <div>{validationResult ? 'No reported compiler, runtime, or interaction errors.' : 'Validation has not run for this project.'}</div>}
        </div>
      </details>

      {/* Stage */}
      <div ref={stageRef} id="preview-stage" className="flex-1 relative overflow-hidden bg-[#07080c]">
        {url && (
          <div
            className="absolute rounded-lg overflow-hidden border border-white/[0.08] shadow-2xl bg-white"
            style={{
              width: logicalWidth * scale,
              height: availableHeight,
              left: Math.max(padding / 2, (stage.width - logicalWidth * scale) / 2),
              top: padding / 2,
            }}
          >
            <iframe
              ref={iframeRef}
              key={url}
              src={url}
              title="Live Preview"
              onLoad={() => setFrameLoading(false)}
              className="border-none bg-white origin-top-left"
              style={{ width: logicalWidth, height: logicalHeight, transform: `scale(${scale})` }}
              sandbox="allow-scripts allow-forms allow-popups"
            />
          </div>
        )}

        {(phase === 'building' || (phase === 'ready' && frameLoading)) && (
          <div id="preview-building-overlay" className="absolute inset-0 flex items-center justify-center bg-black/40 backdrop-blur-[1px]">
            <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-[#141619] border border-white/[0.08] text-xs text-slate-300 shadow-xl">
              <Loader2 size={14} className="animate-spin text-emerald-400" />
              <span>{phase === 'building' ? 'Building preview…' : 'Loading preview…'}</span>
            </div>
          </div>
        )}

        {isWorking && phase !== 'building' && (
          <div className="absolute bottom-3 left-1/2 -translate-x-1/2 px-3 py-1.5 rounded-full bg-[#141619]/95 border border-white/[0.08] text-[11px] text-slate-300 shadow-xl flex items-center gap-2">
            <Loader2 size={12} className="animate-spin text-emerald-400" />
            <span>Generating — the preview refreshes when the build finishes</span>
          </div>
        )}

        {phase === 'error' && (
          <div id="preview-error-panel" className="absolute inset-0 flex items-center justify-center p-6">
            <div className="max-w-xl w-full rounded-xl border border-rose-500/30 bg-[#141619] p-4 space-y-3 shadow-2xl">
              <div className="flex items-center gap-2 text-sm font-semibold text-rose-300">
                <AlertTriangle size={16} />
                <span>The preview build failed</span>
              </div>
              <pre className="max-h-64 overflow-auto rounded-lg bg-black/40 border border-white/[0.06] p-3 text-[11px] leading-relaxed text-slate-300 whitespace-pre-wrap select-text">{error}</pre>
              <div className="flex items-center gap-2">
                <button
                  id="preview-retry-btn"
                  onClick={() => loadPreview(true)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500 text-slate-950 text-xs font-semibold hover:bg-emerald-400 cursor-pointer"
                >
                  <Hammer size={12} />
                  <span>Rebuild preview</span>
                </button>
                <span className="text-[11px] text-slate-500">Fix the file in the Code tab, or ask the agent to repair it.</span>
              </div>
            </div>
          </div>
        )}

        {(phase === 'idle' || phase === 'empty') && (
          <div className="absolute inset-0 flex flex-col items-center justify-center text-center p-8 text-slate-500 space-y-2">
            <Monitor size={32} className="text-slate-600" />
            <p className="text-sm font-medium text-slate-400">{phase === 'empty' ? 'Nothing to preview yet' : 'No active preview'}</p>
            <p className="text-xs text-slate-500 max-w-xs">
              {phase === 'empty' ? emptyMessage : 'Generate a site or select a project to see its live preview.'}
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
