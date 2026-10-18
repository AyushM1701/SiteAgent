import React, { useEffect } from 'react';
import {
  X,
  Cpu,
  CheckCircle2,
  XCircle,
  HelpCircle,
  AlertTriangle,
  Activity,
  Box,
  Layers,
  Code2,
  Gauge,
  Sparkles,
  Crosshair,
  Wand2,
  Copy,
  ScanSearch,
} from 'lucide-react';
import { useWorkspaceStore } from '../../state/workspace-store';
import { useAgentStore } from '../../state/agent-store';
import { useProjectStore } from '../../state/project-store';
import { useSelectionStore } from '../../state/selection-store';
import { toast } from '../../state/toast-store';
import { toTriState, toGateTruthState } from '../../types/agent';
import { useViewportWidth, INSPECTOR_DOCK_MIN, INSPECTOR_WIDTH } from '../../hooks/useViewportWidth';
import { PREVIEW_HIGHLIGHT_EVENT } from '../workspace/PreviewTab';

/** Asks the chat composer to take focus (used by "Edit with AI"). */
export const FOCUS_COMPOSER_EVENT = 'workbench:focus-composer';

const SectionTitle: React.FC<{ icon: React.ReactNode; title: string; right?: React.ReactNode }> = ({ icon, title, right }) => (
  <div className="flex items-center justify-between gap-2 text-slate-400 font-semibold uppercase tracking-wider text-[10px]">
    <div className="flex items-center gap-1.5 min-w-0">
      {icon}
      <span className="truncate">{title}</span>
    </div>
    {right}
  </div>
);

const Row: React.FC<{ label: string; value: React.ReactNode; title?: string }> = ({ label, value, title }) => (
  <div className="flex items-center justify-between gap-3 min-w-0" title={title}>
    <span className="text-slate-400 font-sans shrink-0">{label}</span>
    <span className="text-slate-200 truncate text-right min-w-0">{value}</span>
  </div>
);

const GateStatus: React.FC<{ status: string }> = ({ status }) => {
  if (status === 'passed') return <><CheckCircle2 size={12} className="text-emerald-400" /><span className="text-emerald-400">PASSED</span></>;
  if (status === 'failed') return <><XCircle size={12} className="text-rose-400" /><span className="text-rose-400">FAILED</span></>;
  if (status === 'unverified') return <><AlertTriangle size={12} className="text-amber-400" /><span className="text-amber-400">UNVERIFIED</span></>;
  if (status === 'not_requested') return <span className="text-slate-500 text-[10px]">NOT REQUESTED</span>;
  return <><HelpCircle size={12} className="text-slate-400" /><span className="text-slate-400">UNKNOWN</span></>;
};

function isTransparent(color?: string) {
  return !color || color === 'transparent' || /rgba\([^)]*,\s*0\)$/.test(color);
}

export const InspectorDrawer: React.FC = () => {
  const { inspectorOpen, toggleInspector, setInspectorOpen, files, setActiveTab } = useWorkspaceStore();
  const { metrics, validationResult, elapsedSeconds, serverConnected, modelLoaded, gpuReady } = useAgentStore();
  const { currentProject } = useProjectStore();
  const { selectedElement, selected3DObject, clearSelection, setInspectMode, inspectMode } = useSelectionStore();
  const viewport = useViewportWidth();
  const docked = viewport >= INSPECTOR_DOCK_MIN;

  // The fallback is an estimate from visible content, not a tokenizer measurement.
  const contextSource = metrics.contextTokens > 0 ? 'verified' : 'estimated';
  const effectiveContextTokens = React.useMemo(() => {
    if (metrics.contextTokens > 0) return metrics.contextTokens;
    let chars = 0;
    const pText = currentProject?.prompt || currentProject?.description;
    if (pText) chars += pText.length;
    Object.values(files || {}).forEach((content) => {
      if (typeof content === 'string') chars += Math.min(content.length, 4000);
    });
    return chars > 0 ? Math.min(metrics.maxContextTokens, Math.round(chars / 3.8)) : 0;
  }, [metrics.contextTokens, metrics.maxContextTokens, currentProject, files]);

  // As an overlay, Escape closes the drawer (unless the element picker is active).
  useEffect(() => {
    if (!inspectorOpen || docked) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && useSelectionStore.getState().inspectMode === 'none') setInspectorOpen(false);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [inspectorOpen, docked, setInspectorOpen]);

  if (!inspectorOpen) return null;

  const contextPercent = Math.min(100, Math.round((effectiveContextTokens / Math.max(1, metrics.maxContextTokens)) * 100));

  const showInPreview = () => {
    if (!selectedElement) return;
    setActiveTab('preview');
    window.setTimeout(() => window.dispatchEvent(new CustomEvent(PREVIEW_HIGHLIGHT_EVENT, { detail: selectedElement.selector })), 50);
  };

  const copySelector = async () => {
    if (!selectedElement) return;
    try {
      await navigator.clipboard.writeText(selectedElement.selector);
      toast.success('Copied', 'CSS selector copied to the clipboard.');
    } catch {
      toast.error('Copy failed', 'Clipboard access was denied.');
    }
  };

  const editWithAI = () => {
    setInspectMode('none');
    window.dispatchEvent(new CustomEvent(FOCUS_COMPOSER_EVENT));
    if (!docked) setInspectorOpen(false);
  };

  const gates = validationResult ? [
    { name: 'TypeScript', status: validationResult.typecheck_status ?? (validationResult.typecheck_passed !== undefined ? toTriState(validationResult.typecheck_passed) : 'unknown') },
    { name: 'Production build', status: validationResult.build_status ?? (validationResult.build_passed !== undefined ? toTriState(validationResult.build_passed) : 'unknown') },
    { name: 'Lint rules', status: validationResult.lint_status ?? (validationResult.lint_passed !== undefined ? toTriState(validationResult.lint_passed) : 'unknown') },
    { name: 'Contract check', status: validationResult.contract_status ?? (validationResult.contract_passed !== undefined ? toTriState(validationResult.contract_passed) : 'unknown') },
    { name: 'Accessibility', status: validationResult.accessibility_status ?? (validationResult.accessibility_passed !== undefined ? toTriState(validationResult.accessibility_passed) : 'unknown') },
    { name: 'Motion rules', status: validationResult.motion_status ?? (validationResult.motion_passed !== undefined ? toTriState(validationResult.motion_passed) : 'unknown') },
    { name: 'Runtime sanity', status: validationResult.runtime_unverified ? 'unverified' : (validationResult.runtime_status ?? (validationResult.runtime_passed !== undefined ? toGateTruthState(validationResult.runtime_passed) : 'unknown')) },
    { name: 'Preview runtime', status: validationResult.preview_status ?? (validationResult.preview_running !== undefined ? toGateTruthState(validationResult.preview_running) : 'unknown') },
    { name: 'DOM interactions', status: validationResult.runtime_unverified ? 'unverified' : (validationResult.interaction_status ?? (validationResult.interaction_passed !== undefined ? toGateTruthState(validationResult.interaction_passed) : 'unknown')) },
  ] : [];

  const styles = selectedElement?.styles || {};

  return (
    <>
      {!docked && (
        <div className="fixed inset-0 top-12 z-40 bg-black/30" aria-hidden="true" onClick={() => setInspectorOpen(false)} />
      )}
      <aside
        id="inspector-drawer-panel"
        aria-label="Inspector"
        style={{ width: Math.min(INSPECTOR_WIDTH, viewport) }}
        className={`border-l border-white/[0.08] bg-[#141414] flex flex-col shrink-0 shadow-2xl ${
          docked ? 'relative h-full z-20' : 'fixed right-0 top-12 bottom-0 z-50'
        }`}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-white/[0.06]">
          <div className="flex items-center gap-2">
            <Gauge size={15} className="text-emerald-400" />
            <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-200">Inspector</h2>
          </div>
          <button
            id="inspector-close-btn"
            onClick={toggleInspector}
            aria-label="Close inspector"
            className="p-1 rounded hover:bg-white/[0.06] text-slate-400 hover:text-white transition-colors cursor-pointer"
            title="Close Inspector (Alt+1)"
          >
            <X size={15} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-5 text-xs">
          {/* Selected element */}
          <section id="inspector-selection-metadata" className="space-y-2">
            <SectionTitle
              icon={<Box size={13} className="text-amber-400" />}
              title="Selected element"
              right={(selectedElement || selected3DObject) ? (
                <button id="inspector-clear-selection-btn" onClick={clearSelection} className="text-slate-400 hover:text-white underline text-[10px] normal-case tracking-normal cursor-pointer">
                  Clear
                </button>
              ) : undefined}
            />

            {selectedElement ? (
              <div className="bg-[#1c1c1c] rounded-xl p-3 border border-white/[0.04] space-y-2.5">
                <div className="flex items-center gap-2 flex-wrap font-mono text-[11px]">
                  <span className="text-emerald-400">&lt;{selectedElement.tagName.toLowerCase()}&gt;</span>
                  {selectedElement.componentHint && (
                    <span className="px-1.5 py-0.5 rounded bg-indigo-500/15 text-indigo-300 border border-indigo-500/25">#{selectedElement.componentHint}</span>
                  )}
                  {selectedElement.size && (
                    <span className="text-slate-500">{selectedElement.size.width}×{selectedElement.size.height}</span>
                  )}
                </div>
                {selectedElement.textContent && (
                  <p className="text-slate-200 leading-snug line-clamp-4 select-text">“{selectedElement.textContent}”</p>
                )}
                <div className="space-y-1 font-mono text-[11px]">
                  {selectedElement.href && <Row label="Link" value={selectedElement.href} title={selectedElement.href} />}
                  {selectedElement.alt && <Row label="Alt" value={selectedElement.alt} title={selectedElement.alt} />}
                  {selectedElement.ariaLabel && <Row label="Label" value={selectedElement.ariaLabel} />}
                  {styles.fontFamily && <Row label="Font" value={`${styles.fontFamily.split(',')[0].replace(/["']/g, '')} ${styles.fontSize || ''} ${styles.fontWeight || ''}`} />}
                  {styles.color && (
                    <Row label="Text" value={<span className="inline-flex items-center gap-1.5"><span className="w-3 h-3 rounded-sm border border-white/20" style={{ background: styles.color }} />{styles.color}</span>} />
                  )}
                  {!isTransparent(styles.backgroundColor) && (
                    <Row label="Fill" value={<span className="inline-flex items-center gap-1.5"><span className="w-3 h-3 rounded-sm border border-white/20" style={{ background: styles.backgroundColor }} />{styles.backgroundColor}</span>} />
                  )}
                  {styles.padding && styles.padding !== '0px' && <Row label="Padding" value={styles.padding} />}
                  {styles.borderRadius && styles.borderRadius !== '0px' && <Row label="Radius" value={styles.borderRadius} />}
                </div>
                <div className="text-[10px] font-mono text-slate-500 break-all select-text" title="CSS selector">{selectedElement.selector}</div>
                <div className="flex flex-wrap gap-1.5 pt-0.5">
                  <button id="inspector-edit-with-ai-btn" onClick={editWithAI} className="flex items-center gap-1 px-2 py-1 rounded-md bg-emerald-500 text-slate-950 font-semibold text-[11px] hover:bg-emerald-400 cursor-pointer">
                    <Wand2 size={12} /> Edit with AI
                  </button>
                  <button id="inspector-show-in-preview-btn" onClick={showInPreview} className="flex items-center gap-1 px-2 py-1 rounded-md border border-white/[0.08] text-slate-300 hover:bg-white/[0.06] text-[11px] cursor-pointer">
                    <ScanSearch size={12} /> Show in preview
                  </button>
                  <button id="inspector-copy-selector-btn" onClick={copySelector} className="flex items-center gap-1 px-2 py-1 rounded-md border border-white/[0.08] text-slate-300 hover:bg-white/[0.06] text-[11px] cursor-pointer">
                    <Copy size={12} /> Selector
                  </button>
                </div>
              </div>
            ) : selected3DObject ? (
              <div className="bg-[#1c1c1c] rounded-xl p-3 border border-white/[0.04] space-y-1.5 font-mono text-[11px]">
                <Row label="3D mesh" value={selected3DObject.name || 'Unnamed mesh'} />
                <Row label="Position" value={`[${selected3DObject.position.x.toFixed(1)}, ${selected3DObject.position.y.toFixed(1)}, ${selected3DObject.position.z.toFixed(1)}]`} />
              </div>
            ) : (
              <div className="rounded-xl p-3 border border-dashed border-white/[0.08] text-slate-400 leading-relaxed">
                <p>Pick any element in the live preview to see its text, size, colours and fonts, then ask the agent to change it.</p>
                <button
                  id="inspector-start-picking-btn"
                  onClick={() => { setActiveTab('preview'); setInspectMode(inspectMode === 'dom' ? 'none' : 'dom'); }}
                  disabled={!currentProject}
                  className="mt-2 flex items-center gap-1 px-2 py-1 rounded-md border border-emerald-500/30 text-emerald-300 hover:bg-emerald-500/10 text-[11px] cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  <Crosshair size={12} /> {inspectMode === 'dom' ? 'Picking… (Esc to stop)' : 'Pick an element'}
                </button>
              </div>
            )}
          </section>

          {/* Validation gates */}
          {validationResult && (
            <section id="inspector-validation-gates" className="space-y-2">
              <SectionTitle
                icon={<CheckCircle2 size={13} className={validationResult.passed ? 'text-emerald-400' : validationResult.code_passed ? 'text-amber-400' : 'text-rose-400'} />}
                title="Validation gates"
                right={
                  <span className={`text-[9px] px-1.5 py-0.5 rounded font-mono border ${
                    validationResult.passed
                      ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                      : validationResult.code_passed
                      ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                      : 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                  }`}>
                    {validationResult.passed ? 'ALL PASSED' : validationResult.code_passed ? 'CODE ONLY' : 'FAILED'}
                  </span>
                }
              />
              <div className="bg-[#1c1c1c] rounded-xl p-3 border border-white/[0.04] space-y-2">
                {gates.map((gate) => (
                  <div key={gate.name} className="flex items-center justify-between">
                    <span className="text-slate-300">{gate.name}</span>
                    <span className="flex items-center gap-1 font-mono text-[11px]"><GateStatus status={String(gate.status)} /></span>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Model runtime */}
          <section id="inspector-model-runtime" className="space-y-2">
            <SectionTitle icon={<Cpu size={13} className="text-indigo-400" />} title="Agent runtime" />
            <div className="bg-[#1c1c1c] rounded-xl p-3 border border-white/[0.04] space-y-1.5 font-mono text-[11px]">
              <Row label="Model" value={<span className="text-emerald-400 font-semibold">{metrics.modelName}</span>} title={metrics.modelName} />
              <Row label="Adapter" value={metrics.adapterFingerprint ? `${metrics.adapterFingerprint.slice(0, 12)}…` : 'none (base model)'} title={metrics.adapterFingerprint} />
              {metrics.baseFingerprint && <Row label="Base hash" value={`${metrics.baseFingerprint.slice(0, 12)}…`} title={metrics.baseFingerprint} />}
              <Row label="Model state" value={!serverConnected ? 'Server offline' : modelLoaded ? 'Loaded' : 'Loading or unavailable'} />
              <Row label="GPU" value={!serverConnected ? 'Unknown' : gpuReady ? 'Ready' : 'Unavailable'} />
            </div>
          </section>

          {/* Context window */}
          <section id="inspector-context-window" className="space-y-2">
            <SectionTitle
              icon={<Activity size={13} className="text-emerald-400" />}
              title="Context window"
              right={<span className="font-mono text-slate-300 normal-case tracking-normal">{effectiveContextTokens > 0 ? effectiveContextTokens.toLocaleString() : '—'} / {metrics.maxContextTokens.toLocaleString()}</span>}
            />
            <div className="w-full bg-black/50 h-1.5 rounded-full overflow-hidden border border-white/[0.04]">
              <div
                className={`h-full transition-all duration-300 ${contextPercent > 85 ? 'bg-rose-500' : contextPercent > 65 ? 'bg-amber-400' : 'bg-emerald-400'}`}
                style={{ width: `${contextPercent}%` }}
              />
            </div>
            <div className="flex justify-between text-[11px] text-slate-400 font-mono">
              <span>{effectiveContextTokens > 0 ? `${contextPercent}% ${contextSource}` : 'Usage unknown'}</span>
              <span>{effectiveContextTokens > 0 ? `${(metrics.maxContextTokens - effectiveContextTokens).toLocaleString()} left` : 'No tokenizer count'}</span>
            </div>
          </section>

          {/* Performance */}
          <section id="inspector-performance-metrics" className="space-y-2">
            <SectionTitle icon={<Layers size={13} className="text-teal-400" />} title="Last run" />
            <div className="grid grid-cols-2 gap-2">
              <div className="bg-[#1c1c1c] p-2.5 rounded-xl border border-white/[0.04]">
                <div className="text-[10px] text-slate-400">Tool calls</div>
                <div className="text-base font-semibold font-mono text-slate-100">{metrics.toolCallsCount}</div>
              </div>
              <div className="bg-[#1c1c1c] p-2.5 rounded-xl border border-white/[0.04]">
                <div className="text-[10px] text-slate-400">Generation time</div>
                <div className="text-base font-semibold font-mono text-slate-100">{elapsedSeconds > 1 ? `${elapsedSeconds.toFixed(1)}s` : '—'}</div>
              </div>
            </div>
          </section>

          {/* Motion plan */}
          {(Boolean(validationResult?.motion_plan?.length) || Boolean(metrics.hasMotion)) && (
            <section id="inspector-motion-plan" className="space-y-2">
              <SectionTitle
                icon={<Sparkles size={13} className="text-violet-400" />}
                title="Motion"
                right={
                  <span className={`text-[9px] px-1.5 py-0.5 rounded font-mono border ${
                    validationResult?.motion_status === 'passed'
                      ? 'bg-violet-500/15 text-violet-300 border-violet-500/30'
                      : validationResult?.motion_status === 'failed'
                      ? 'bg-rose-500/15 text-rose-300 border-rose-500/30'
                      : 'bg-slate-500/15 text-slate-300 border-slate-500/30'
                  }`}>
                    {validationResult?.motion_status === 'passed' ? 'VERIFIED' : validationResult?.motion_status === 'failed' ? 'FAILED' : 'UNVERIFIED'}
                  </span>
                }
              />
              <div className="bg-[#1c1c1c] rounded-xl p-3 border border-white/[0.04] space-y-2">
                {(validationResult?.motion_plan || []).map((item, idx) => (
                  <div key={idx} className="p-2 rounded-lg bg-white/[0.02] border border-white/[0.04] space-y-1 font-mono">
                    <div className="flex items-center justify-between text-slate-200 font-semibold">
                      <span className="capitalize">{item.type.replace(/_/g, ' ')}</span>
                      <span className="text-[10px] text-violet-400 uppercase font-normal">{item.intensity || 'subtle'}</span>
                    </div>
                    <div className="text-[10px] text-slate-400 flex flex-wrap gap-x-3 gap-y-0.5">
                      {(item.section || item.target_section) && <span>Section: <span className="text-slate-300">{item.section || item.target_section}</span></span>}
                      {item.mobile_fallback && <span>Mobile: <span className="text-slate-300">{item.mobile_fallback}</span></span>}
                      <span>Trigger: <span className="text-slate-300">{item.trigger || 'viewport'}</span></span>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Project */}
          {currentProject && (
            <section id="inspector-project-info" className="space-y-2">
              <SectionTitle icon={<Code2 size={13} className="text-violet-400" />} title="Project" />
              <div className="bg-[#1c1c1c] rounded-xl p-3 border border-white/[0.04] space-y-1.5">
                <Row label="Title" value={currentProject.title} title={currentProject.title} />
                <Row label="Mode" value={<span className="font-mono uppercase text-emerald-400">{currentProject.mode}</span>} />
                <Row label="Turns" value={<span className="font-mono">{currentProject.turnCount}</span>} />
                <Row label="Files" value={<span className="font-mono">{Object.keys(files).length}</span>} />
                {currentProject.folderName && <Row label="Folder" value={<span className="font-mono">{currentProject.folderName}</span>} title={currentProject.fullPath} />}
              </div>
            </section>
          )}
        </div>
      </aside>
    </>
  );
};
