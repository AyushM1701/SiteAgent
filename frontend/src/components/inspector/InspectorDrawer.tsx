import React from 'react';
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
  Sparkles 
} from 'lucide-react';
import { useWorkspaceStore } from '../../state/workspace-store';
import { useAgentStore } from '../../state/agent-store';
import { useProjectStore } from '../../state/project-store';
import { useSelectionStore } from '../../state/selection-store';
import { TriState, toTriState, GateTruthState, toGateTruthState } from '../../types/agent';

export const InspectorDrawer: React.FC = () => {
  const { inspectorOpen, toggleInspector, files } = useWorkspaceStore();
  const { metrics, validationResult, elapsedSeconds, status, gpuReady, modelLoaded, serverConnected } = useAgentStore();
  const { currentProject, currentProjectId } = useProjectStore();
  const { selectedElement, selected3DObject, clearSelection } = useSelectionStore();

  // The fallback is an estimate from visible content, not a tokenizer measurement.
  const contextSource = metrics.contextTokens > 0 ? 'verified' : 'estimated';
  const effectiveContextTokens = React.useMemo(() => {
    if (metrics.contextTokens > 0) return metrics.contextTokens;
    let chars = 0;
    const pText = currentProject?.prompt || currentProject?.description;
    if (pText) chars += pText.length;
    if (files) {
      Object.values(files).forEach((content) => {
        if (typeof content === 'string') chars += Math.min(content.length, 4000);
      });
    }
    if (chars > 0) {
      return Math.min(metrics.maxContextTokens, Math.round(chars / 3.8));
    }
    return 0;
  }, [metrics.contextTokens, metrics.maxContextTokens, currentProject, files]);

  if (!inspectorOpen) return null;

  const contextPercent = Math.min(
    100,
    Math.round((effectiveContextTokens / Math.max(1, metrics.maxContextTokens)) * 100)
  );

  return (
    <div
      id="inspector-drawer-panel"
      className="w-80 border-l border-white/[0.08] bg-[#141414] flex flex-col h-full z-20 shrink-0 shadow-2xl transition-all duration-200"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/[0.06] bg-white/[0.01]">
        <div className="flex items-center gap-2">
          <Gauge size={15} className="text-emerald-400" />
          <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-200">
            System & Inspector
          </h2>
        </div>
        <button
          id="inspector-close-btn"
          onClick={toggleInspector}
          className="p-1 rounded hover:bg-white/[0.06] text-slate-400 hover:text-white transition-colors"
          title="Close Inspector (Alt+1)"
        >
          <X size={15} />
        </button>
      </div>

      {/* Body content with scrolling */}
      <div className="flex-1 overflow-y-auto p-4 space-y-5">
        <div className="space-y-4">
          {/* Model & Inference Spec */}
          <div id="inspector-model-runtime" className="space-y-2">
            <div className="flex items-center gap-1.5 text-slate-400 font-semibold uppercase tracking-wider text-[10px]">
              <Cpu size={13} className="text-indigo-400" />
              <span>Agent Runtime</span>
            </div>
            <div className="bg-[#1c1c1c] rounded-xl p-3 border border-white/[0.04] space-y-1.5 font-mono text-[11px]">
              <div className="flex justify-between">
                <span className="text-slate-400 font-sans">Model:</span>
                <span className="text-emerald-400 font-semibold">{metrics.modelName}</span>
              </div>
              {metrics.baseFingerprint && (
                <div className="flex justify-between" title={metrics.baseFingerprint}>
                  <span className="text-slate-400 font-sans">Base Fingerprint:</span>
                  <span className="text-slate-300 font-mono text-[10px]">{metrics.baseFingerprint.slice(0, 12)}…</span>
                </div>
              )}
              {metrics.adapterFingerprint && (
                <div className="flex justify-between" title={metrics.adapterFingerprint}>
                  <span className="text-slate-400 font-sans">Adapter:</span>
                  <span className="text-slate-300 font-mono text-[10px]">{metrics.adapterFingerprint.slice(0, 12)}…</span>
                </div>
              )}
              <div className="flex justify-between">
                <span className="text-slate-400 font-sans">Model state:</span>
                <span className="text-slate-300">{!serverConnected ? 'Unknown' : modelLoaded ? 'Loaded' : 'Loading or unavailable'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400 font-sans">GPU:</span>
                <span className="text-slate-300">{!serverConnected || !modelLoaded ? 'Unknown' : gpuReady ? 'Ready' : 'Unavailable'}</span>
              </div>
            </div>
          </div>

          {/* Context Budget & Performance */}
          <div id="inspector-context-window" className="space-y-2">
            <div className="flex items-center justify-between text-slate-400 font-semibold uppercase tracking-wider text-[10px]">
              <div className="flex items-center gap-1.5">
                <Activity size={13} className="text-emerald-400" />
                <span>Context Window</span>
              </div>
              <span className="font-mono text-slate-300">
                {effectiveContextTokens > 0 ? `${effectiveContextTokens.toLocaleString()} ${contextSource} / ` : 'Unknown / '}{metrics.maxContextTokens.toLocaleString()}
              </span>
            </div>

            <div className="w-full bg-black/50 h-1.5 rounded-full overflow-hidden border border-white/[0.04]">
              <div
                className={`h-full transition-all duration-300 ${
                  contextPercent > 85 ? 'bg-rose-500' : contextPercent > 65 ? 'bg-amber-400' : 'bg-emerald-400'
                }`}
                style={{ width: `${contextPercent}%` }}
              />
            </div>
            <div className="flex justify-between text-[11px] text-slate-400 font-mono">
              <span>{effectiveContextTokens > 0 ? `${contextPercent}% ${contextSource}` : 'Usage unknown'}</span>
              <span>{effectiveContextTokens > 0 ? `${(metrics.maxContextTokens - effectiveContextTokens).toLocaleString()} ${contextSource} tok left` : 'Tokenizer count unavailable'}</span>
            </div>
          </div>

          {/* Execution & Performance */}
          <div id="inspector-performance-metrics" className="space-y-2">
            <div className="flex items-center gap-1.5 text-slate-400 font-semibold uppercase tracking-wider text-[10px]">
              <Layers size={13} className="text-teal-400" />
              <span>Performance</span>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div className="bg-[#1c1c1c] p-2.5 rounded-xl border border-white/[0.04]">
                <div className="text-[10px] text-slate-400">Tool Calls</div>
                <div className="text-base font-semibold font-mono text-slate-100">
                  {metrics.toolCallsCount}
                </div>
              </div>
              <div className="bg-[#1c1c1c] p-2.5 rounded-xl border border-white/[0.04]">
                <div className="text-[10px] text-slate-400">Generation Time</div>
                <div className="text-base font-semibold font-mono text-slate-100">
                  {elapsedSeconds.toFixed(1)}s
                </div>
              </div>
            </div>
          </div>

          {/* Gate Verification */}
          {validationResult && (
            <div id="inspector-validation-gates" className="space-y-2">
              <div className="flex items-center justify-between text-slate-400 font-semibold uppercase tracking-wider text-[10px]">
                <div className="flex items-center gap-1.5">
                  <CheckCircle2
                    size={13}
                    className={
                      validationResult.passed
                        ? 'text-emerald-400'
                        : validationResult.code_passed
                        ? 'text-amber-400'
                        : 'text-rose-400'
                    }
                  />
                  <span>Validation Gates</span>
                </div>
                {validationResult.passed ? (
                  <span className="text-[9px] px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono">
                    ALL PASSED
                  </span>
                ) : validationResult.code_passed ? (
                  <span className="text-[9px] px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20 font-mono">
                    CODE ONLY
                  </span>
                ) : (
                  <span className="text-[9px] px-1.5 py-0.5 rounded bg-rose-500/10 text-rose-400 border border-rose-500/20 font-mono">
                    FAILED
                  </span>
                )}
              </div>
              <div className="bg-[#1c1c1c] rounded-xl p-3 border border-white/[0.04] space-y-2">
                {[
                  {
                    name: 'TypeScript',
                    status: validationResult.typecheck_status ?? (validationResult.typecheck_passed !== undefined ? toTriState(validationResult.typecheck_passed) : 'unknown'),
                  },
                  {
                    name: 'Production Build',
                    status: validationResult.build_status ?? (validationResult.build_passed !== undefined ? toTriState(validationResult.build_passed) : 'unknown'),
                  },
                  {
                    name: 'Lint Rules',
                    status: validationResult.lint_status ?? (validationResult.lint_passed !== undefined ? toTriState(validationResult.lint_passed) : 'unknown'),
                  },
                  {
                    name: 'Contract Check',
                    status: validationResult.contract_status ?? (validationResult.contract_passed !== undefined ? toTriState(validationResult.contract_passed) : 'unknown'),
                  },
                  {
                    name: 'Accessibility',
                    status: validationResult.accessibility_status ?? (validationResult.accessibility_passed !== undefined ? toTriState(validationResult.accessibility_passed) : 'unknown'),
                  },
                  {
                    name: 'Motion Rules',
                    status: validationResult.motion_status ?? (validationResult.motion_passed !== undefined ? toTriState(validationResult.motion_passed) : 'unknown'),
                  },
                  {
                    name: 'Runtime Sanity',
                    status: validationResult.runtime_unverified
                      ? 'unverified'
                      : (validationResult.runtime_status ?? (validationResult.runtime_passed !== undefined ? toGateTruthState(validationResult.runtime_passed) : 'unknown')),
                  },
                  {
                    name: 'Preview Runtime',
                    status: validationResult.preview_status ?? (validationResult.preview_running !== undefined ? toGateTruthState(validationResult.preview_running) : 'unknown'),
                  },
                  {
                    name: 'DOM Interactions',
                    status: validationResult.runtime_unverified
                      ? 'unverified'
                      : (validationResult.interaction_status ?? (validationResult.interaction_passed !== undefined ? toGateTruthState(validationResult.interaction_passed) : 'unknown')),
                  },
                ].map((gate) => (
                  <div key={gate.name} className="flex items-center justify-between text-xs">
                    <span className="text-slate-300">{gate.name}</span>
                    <span className="flex items-center gap-1 font-mono text-[11px]">
                      {gate.status === 'passed' ? (
                        <>
                          <CheckCircle2 size={12} className="text-emerald-400" />
                          <span className="text-emerald-400">PASSED</span>
                        </>
                      ) : gate.status === 'failed' ? (
                        <>
                          <XCircle size={12} className="text-rose-400" />
                          <span className="text-rose-400">FAILED</span>
                        </>
                      ) : gate.status === 'unverified' ? (
                        <>
                          <AlertTriangle size={12} className="text-amber-400" />
                          <span className="text-amber-400">UNVERIFIED</span>
                        </>
                      ) : gate.status === 'not_requested' ? (
                        <span className="text-slate-500 font-mono text-[10px]">NOT REQUESTED</span>
                      ) : (
                        <>
                          <HelpCircle size={12} className="text-slate-400" />
                          <span className="text-slate-400">UNKNOWN</span>
                        </>
                      )}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Motion Plan & Dynamics (Item 21 & 22) */}
          {(Boolean(validationResult?.motion_plan?.length) || Boolean(metrics.hasMotion) || validationResult?.motion_status === 'passed') && (
            <div id="inspector-motion-plan" className="space-y-2">
              <div className="flex items-center justify-between text-slate-400 font-semibold uppercase tracking-wider text-[10px]">
                <div className="flex items-center gap-1.5">
                  <Sparkles size={13} className="text-violet-400" />
                  <span>Motion Dynamics</span>
                </div>
                {validationResult?.motion_status === 'passed' ? (
                  <span className="text-[9px] px-1.5 py-0.5 rounded bg-violet-500/15 text-violet-300 border border-violet-500/30 font-mono flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-violet-400" />
                    MOTION VERIFIED
                  </span>
                ) : validationResult?.motion_status === 'failed' ? (
                  <span className="text-[9px] px-1.5 py-0.5 rounded bg-rose-500/15 text-rose-300 border border-rose-500/30 font-mono">
                    MOTION FAILED
                  </span>
                ) : (
                  <span className="text-[9px] px-1.5 py-0.5 rounded bg-slate-500/15 text-slate-300 border border-slate-500/30 font-mono">
                    UNVERIFIED
                  </span>
                )}
              </div>

              <div className="bg-[#1c1c1c] rounded-xl p-3 border border-white/[0.04] space-y-2">
                {validationResult?.motion_plan && validationResult.motion_plan.length > 0 ? (
                  <div className="space-y-2">
                    {validationResult.motion_plan.map((item, idx) => (
                      <div key={idx} className="p-2 rounded-lg bg-white/[0.02] border border-white/[0.04] text-xs space-y-1 font-mono">
                        <div className="flex items-center justify-between text-slate-200 font-semibold">
                          <span className="capitalize">{item.type.replace('_', ' ')}</span>
                          <span className="text-[10px] text-violet-400 uppercase font-normal">{item.intensity || 'subtle'}</span>
                        </div>
                        <div className="text-[10px] text-slate-400 flex flex-wrap gap-x-3 gap-y-0.5">
                          {item.section && <span>Section: <span className="text-slate-300">{item.section}</span></span>}
                          {item.mobile_fallback && <span>Mobile: <span className="text-slate-300">{item.mobile_fallback}</span></span>}
                          <span>Trigger: <span className="text-slate-300">{item.trigger || 'viewport'}</span></span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-[11px] text-slate-400 font-mono space-y-1">
                    <div className="text-slate-300 font-sans">Active Motion Policies:</div>
                    <div className="text-[10px] text-slate-400 space-y-0.5">
                      <div>✓ Reduced motion fallback (`prefers-reduced-motion`)</div>
                      <div>✓ Zero wheel/touch hijacking</div>
                      <div>✓ Passive scroll listeners & RAF cleanup</div>
                      <div>✓ Unobserve on reveal</div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Selection Details */}
          {(selectedElement || selected3DObject) && (
            <div id="inspector-selection-metadata" className="space-y-2">
              <div className="flex items-center justify-between text-slate-400 font-semibold uppercase tracking-wider text-[10px]">
                <div className="flex items-center gap-1.5">
                  <Box size={13} className="text-amber-400" />
                  <span>Selected Target</span>
                </div>
                <button id="inspector-clear-selection-btn" onClick={clearSelection} className="text-slate-400 hover:text-white underline text-[10px]">
                  Clear
                </button>
              </div>

              {selectedElement && (
                <div className="bg-[#1c1c1c] rounded-xl p-3 border border-white/[0.04] space-y-1.5 font-mono text-[11px]">
                  <div>
                    <span className="text-slate-500">Tag:</span>{' '}
                    <span className="text-emerald-400">&lt;{selectedElement.tagName.toLowerCase()}&gt;</span>
                  </div>
                  {selectedElement.componentHint && (
                    <div>
                      <span className="text-slate-500">Component:</span>{' '}
                      <span className="text-indigo-300">{selectedElement.componentHint}</span>
                    </div>
                  )}
                  <div>
                    <span className="text-slate-500">Selector:</span>{' '}
                    <span className="text-slate-400 break-all">{selectedElement.selector}</span>
                  </div>
                </div>
              )}

              {selected3DObject && (
                <div className="bg-[#1c1c1c] rounded-xl p-3 border border-white/[0.04] space-y-1.5 font-mono text-[11px]">
                  <div>
                    <span className="text-slate-500">3D Mesh:</span>{' '}
                    <span className="text-amber-300">{selected3DObject.name || 'Unnamed Mesh'}</span>
                  </div>
                  <div>
                    <span className="text-slate-500">Position:</span>{' '}
                    <span className="text-slate-300">
                      [{selected3DObject.position.x.toFixed(1)}, {selected3DObject.position.y.toFixed(1)}, {selected3DObject.position.z.toFixed(1)}]
                    </span>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Project Details */}
          {currentProject && (
            <div id="inspector-project-info" className="space-y-2">
              <div className="flex items-center gap-1.5 text-slate-400 font-semibold uppercase tracking-wider text-[10px]">
                <Code2 size={13} className="text-violet-400" />
                <span>Project Info</span>
              </div>
              <div className="bg-[#1c1c1c] rounded-xl p-3 border border-white/[0.04] space-y-1.5 text-xs">
                <div className="flex justify-between">
                  <span className="text-slate-400">Title:</span>
                  <span className="text-slate-200 font-medium truncate max-w-[150px]">
                    {currentProject.title}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Mode:</span>
                  <span className="font-mono uppercase text-emerald-400 font-medium">
                    {currentProject.mode}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Total Turns:</span>
                  <span className="font-mono text-slate-200">{currentProject.turnCount}</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
