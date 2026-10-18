import React, { useState } from 'react';
import { Check, CheckCircle2, Copy, Eye, FileDiff, Folder, HelpCircle, Sparkles, XCircle } from 'lucide-react';
import { ChangeSummaryData } from '../../types/chat';
import { TriState, toTriState } from '../../types/agent';
import { useWorkspaceStore } from '../../state/workspace-store';
import { useProjectStore } from '../../state/project-store';

interface ChangeSummaryProps {
  summary: ChangeSummaryData;
}

export const ChangeSummary: React.FC<ChangeSummaryProps> = ({ summary }) => {
  const { setActiveTab, setWorkspaceOpen } = useWorkspaceStore();
  const { currentProject } = useProjectStore();
  const [copied, setCopied] = useState(false);

  const handleOpenPreview = () => {
    setActiveTab('preview');
    setWorkspaceOpen(true);
  };

  const handleOpenDiff = () => {
    setActiveTab('diff');
    setWorkspaceOpen(true);
  };

  const isNoFileChange = (summary.filesModified?.length || 0) === 0 && (summary.filesCreated?.length || 0) === 0;
  const blocked = summary.completionStatus === 'BLOCKED' || Boolean(summary.blockedSections?.length);
  const isUnchanged = !blocked && (summary.validationStatus === 'unchanged' || isNoFileChange);

  const validation = summary.validation;
  // The "TypeScript" badge reports the typecheck gate, not the combined code verdict
  // (which also folds in accessibility and runtime results).
  const codeStatus: TriState = (validation as any)?.typecheck_status
    ?? ((validation as any)?.typecheck_passed !== undefined ? toTriState((validation as any).typecheck_passed) : undefined)
    ?? summary.codeStatus
    ?? validation?.code_status
    ?? (summary.code_passed !== undefined ? toTriState(summary.code_passed) : (validation?.code_passed !== undefined ? toTriState(validation.code_passed) : 'unknown'));

  const buildStatus: TriState = summary.buildStatus
    ?? validation?.build_status
    ?? (summary.build_passed !== undefined ? toTriState(summary.build_passed) : (validation?.build_passed !== undefined ? toTriState(validation.build_passed) : 'unknown'));

  const contractStatus: TriState = summary.contractStatus
    ?? validation?.contract_status
    ?? (summary.contract_passed !== undefined ? toTriState(summary.contract_passed) : (validation?.contract_passed !== undefined ? toTriState(validation.contract_passed) : 'unknown'));

  const accessibilityStatus: TriState = summary.accessibilityStatus
    ?? validation?.accessibility_status
    ?? (summary.accessibility_passed !== undefined ? toTriState(summary.accessibility_passed) : (validation?.accessibility_passed !== undefined ? toTriState(validation.accessibility_passed) : 'unknown'));

  const motionStatus: TriState = (summary as any).motionStatus
    ?? validation?.motion_status
    ?? ((summary as any).motion_passed !== undefined ? toTriState((summary as any).motion_passed) : (validation?.motion_passed !== undefined ? toTriState(validation.motion_passed) : 'unknown'));

  const previewStatus: TriState = summary.previewStatus
    ?? validation?.preview_status
    ?? (summary.preview_running !== undefined ? toTriState(summary.preview_running) : (validation?.preview_running !== undefined ? toTriState(validation.preview_running) : 'unknown'));

  const renderGateBadge = (label: string, status: TriState) => {
    if (status === 'passed') {
      return (
        <span className="flex items-center gap-1 text-emerald-400/90 font-mono">
          <CheckCircle2 size={12} className="text-emerald-400" />
          <span>{label}</span>
        </span>
      );
    }
    if (status === 'failed') {
      return (
        <span className="flex items-center gap-1 text-rose-400 font-mono">
          <XCircle size={12} className="text-rose-400" />
          <span>{label}</span>
        </span>
      );
    }
    return (
      <span className="flex items-center gap-1 text-slate-400 font-mono" title={`${label} status unknown / unverified`}>
        <HelpCircle size={12} className="text-slate-400" />
        <span>{label} (unverified)</span>
      </span>
    );
  };

  return (
    <div className="w-full my-2 rounded-xl bg-[#141414] border border-white/[0.08] shadow-lg overflow-hidden">
      {/* Header bar */}
      <div className="flex items-center justify-between px-3.5 py-2 bg-white/[0.02] border-b border-white/[0.06]">
        <div className="flex items-center gap-2">
          <div className="flex items-center justify-center w-5 h-5 rounded-md bg-emerald-500/10 text-emerald-400">
            <Sparkles size={12} />
          </div>
          <span className="text-xs font-semibold text-slate-200">
            {isNoFileChange
              ? (blocked ? 'Generation blocked' : 'Task completed')
              : blocked ? 'Generation blocked — partial files saved'
              : (summary.filesModified?.length || 0) > 0
              ? 'Changes Applied'
              : 'Project Ready'}
          </span>
        </div>

      </div>

      <div className="p-3.5 space-y-3">
        {blocked && (
          <div className="p-2.5 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-[11px] space-y-1" role="alert">
            <div className="font-semibold">Generation blocked{summary.sectionCompletion ? ` · ${summary.sectionCompletion} sections complete` : ''}. Accepted files were preserved; the site is not complete.</div>
            <ul className="list-disc pl-4">
              {(summary.blockedSections || []).map((item, i) => (
                <li key={i}>{typeof item === 'string' ? item : `${item.section || item.name || 'Section'}: ${item.reason || item.error || 'Generation blocked'}`}</li>
              ))}
            </ul>
          </div>
        )}
        {/* Metric Pills */}
        <div className="flex flex-wrap items-center gap-2">
          <div className="inline-flex items-center gap-1.5 px-2 py-1 rounded-md bg-white/[0.04] text-[11px] text-slate-300 font-mono">
            <span>
              {isNoFileChange
                ? 'No files changed'
                : (summary.filesModified?.length || 0) > 0
                ? `${summary.filesModified.length} file${summary.filesModified.length > 1 ? 's' : ''} modified`
                : `${summary.filesCreated?.length || 0} files created`}
            </span>
            {summary.visualScore !== undefined && summary.visualScore !== null && (
              <span className="text-amber-400/90 ml-1">
                · Visual Score {summary.visualScore}/5
              </span>
            )}
          </div>
        </div>

        {/* Export Folder Location */}
        {(summary.filePath || summary.fullPath || summary.folderName || (currentProject as any)?.filePath || (currentProject as any)?.folderName) && (
          <div className="flex items-center justify-between px-3 py-2 rounded-lg bg-cyan-950/30 border border-cyan-500/25 text-[11px] font-mono text-cyan-200">
            <div className="flex items-center gap-2 overflow-hidden mr-2">
              <Folder size={13} className="text-cyan-400 shrink-0" />
              <span className="text-slate-400 shrink-0">Saved to:</span>
              <span className="text-cyan-300 font-semibold truncate select-all" title={summary.fullPath || summary.filePath || (currentProject as any)?.fullPath || (currentProject as any)?.filePath}>
                {summary.folderName || summary.filePath || (currentProject as any)?.folderName || (currentProject as any)?.filePath}
              </span>
            </div>
            <button
              type="button"
              onClick={() => {
                const textToCopy = summary.fullPath || summary.filePath || (currentProject as any)?.fullPath || (currentProject as any)?.filePath || '';
                navigator.clipboard.writeText(textToCopy);
                setCopied(true);
                setTimeout(() => setCopied(false), 2000);
              }}
              className="flex items-center gap-1 px-2 py-0.5 rounded bg-cyan-500/15 hover:bg-cyan-500/25 text-cyan-300 border border-cyan-500/30 cursor-pointer shrink-0 transition-colors text-[10px]"
              title="Copy folder path to clipboard"
            >
              {copied ? <Check size={11} className="text-emerald-400" /> : <Copy size={11} />}
              <span>{copied ? 'Copied' : 'Copy Path'}</span>
            </button>
          </div>
        )}

        {/* Multi-Gate Validation Outcome */}
        <div className="space-y-1 text-slate-300">
          <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
            Validation
          </div>
          {isUnchanged ? (
            <div className="flex items-center gap-1.5 text-[11px] font-mono text-slate-400">
              <span className="w-1.5 h-1.5 rounded-full bg-slate-500" />
              <span>Validation status unchanged</span>
            </div>
          ) : (
            <div className="flex flex-wrap items-center gap-3 text-[11px] font-mono">
              {renderGateBadge('TypeScript', codeStatus)}
              {renderGateBadge('Production build', buildStatus)}
              {renderGateBadge('Contract check', contractStatus)}
              {renderGateBadge('Accessibility', accessibilityStatus)}
              {renderGateBadge('Motion policy', motionStatus)}
              {renderGateBadge('Preview runtime', previewStatus)}
            </div>
          )}
        </div>

        {summary.strategy === 'native' && (
          <div id="summary-native-code" className="text-[11px] text-slate-400 space-y-1">
            <div>
              <span className="font-semibold text-slate-300">Section code: </span>
              {(summary.nativeCodeSections || []).length} written by the model
              {Object.keys(summary.nativeCodeFallbacks || {}).length > 0 &&
                `, ${Object.keys(summary.nativeCodeFallbacks || {}).length} by the design kit (model code rejected)`}
            </div>
            {Object.entries(summary.nativeCodeFallbacks || {}).slice(0, 4).map(([section, reasons]) => (
              <div key={section} className="text-slate-500 font-mono">{section}: {(reasons || [])[0]}</div>
            ))}
          </div>
        )}

        {summary.generationScorecards && (
          <div className="space-y-2 text-[11px]">
            <div className="font-semibold text-slate-400">Generation evidence · {summary.generationScorecards.provenance.mode || 'unknown'} run</div>
            <table className="w-full text-left">
              <thead><tr className="text-slate-500"><th>Stage</th><th>Result</th><th>Evidence</th></tr></thead>
              <tbody>{summary.generationScorecards.stages.map(stage => (
                <tr key={stage.id} className="border-t border-white/5" title={stage.note}>
                  <td className="py-1.5">{stage.label}</td>
                  <td className={stage.status === 'failed' ? 'text-rose-400' : stage.status === 'passed' ? 'text-emerald-400' : 'text-slate-400'}>{stage.status.replace(/_/g, ' ')}</td>
                  <td className="text-slate-400">{stage.id === 'native' ? `${stage.first_attempt_sections}/${stage.required_sections} first attempts` : stage.id === 'model_repair' ? `${stage.section_retries} section retries · ${stage.project_attempts} project attempts` : stage.files ? `${stage.files.length} files changed` : 'Project gates'}</td>
                </tr>
              ))}</tbody>
            </table>
            <p className="text-slate-500">Section acceptance does not establish model-native visual or browser quality.</p>
          </div>
        )}

        {/* Motion Failures / Runtime Warnings if any */}
        {validation?.motion_failures && validation.motion_failures.length > 0 && (
          <div className="p-2.5 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-[11px] font-mono space-y-1">
            <div className="font-semibold text-rose-400 flex items-center gap-1">
              <XCircle size={13} />
              <span>Motion Runtime Violations Detected:</span>
            </div>
            <ul className="list-disc pl-4 space-y-0.5 text-[10px]">
              {validation.motion_failures.map((fail, i) => (
                <li key={i}>{fail}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Actions: View Preview / Review Changes */}
        <div className="flex items-center gap-2 pt-2 border-t border-white/[0.06]">
          <button
            onClick={handleOpenPreview}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-black font-semibold text-xs transition-colors shadow-sm cursor-pointer"
          >
            <Eye size={13} />
            <span>View preview</span>
          </button>

          <button
            onClick={handleOpenDiff}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/[0.06] hover:bg-white/[0.10] text-slate-200 font-medium text-xs border border-white/[0.06] transition-colors cursor-pointer"
          >
            <FileDiff size={13} />
            <span>Review changes</span>
          </button>
        </div>
      </div>
    </div>
  );
};
