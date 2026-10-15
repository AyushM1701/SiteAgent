import React, { useState } from 'react';
import { 
  CheckCircle2, 
  XCircle, 
  Loader2, 
  ChevronDown, 
  ChevronRight, 
  FileCode, 
  Terminal, 
  Package, 
  Sparkles 
} from 'lucide-react';
import { ActivityStep as IActivityStep } from '../../types/agent';

interface ActivityStepProps {
  step: IActivityStep;
}

export const ActivityStep: React.FC<ActivityStepProps> = ({ step }) => {
  const [isOpen, setIsOpen] = useState(false);

  const getStepIcon = () => {
    if (step.title.includes('Created') || step.title.includes('Updated') || step.title.includes('write')) {
      return <FileCode size={13} className="text-teal-400" />;
    }
    if (step.title.includes('npm') || step.title.includes('install')) {
      return <Package size={13} className="text-amber-400" />;
    }
    if (step.title.includes('command') || step.title.includes('Running')) {
      return <Terminal size={13} className="text-indigo-400" />;
    }
    return <Sparkles size={13} className="text-emerald-400" />;
  };

  const hasDetails = Boolean(step.description || step.details || step.args || step.output);

  return (
    <div className="border-b border-white/[0.04] last:border-b-0 py-2 font-mono text-xs">
      <div
        onClick={() => hasDetails && setIsOpen(!isOpen)}
        className={`flex items-center justify-between gap-2 px-2 py-1 rounded transition-colors ${
          hasDetails ? 'cursor-pointer hover:bg-white/[0.03]' : ''
        }`}
      >
        <div className="flex items-center gap-2 truncate">
          {step.status === 'running' ? (
            <Loader2 size={13} className="animate-spin text-emerald-400 shrink-0" />
          ) : step.status === 'completed' ? (
            <CheckCircle2 size={13} className="text-emerald-400 shrink-0" />
          ) : (
            <XCircle size={13} className="text-rose-400 shrink-0" />
          )}

          {getStepIcon()}

          <span className="truncate text-slate-200 font-sans font-medium text-xs">
            {step.title}
          </span>
        </div>

        <div className="flex items-center gap-2 shrink-0 text-[11px] text-slate-400">
          {step.durationMs !== undefined && (
            <span className="text-slate-500">{step.durationMs}ms</span>
          )}
          {hasDetails && (
            <span className="text-slate-500 hover:text-slate-300">
              {isOpen ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
            </span>
          )}
        </div>
      </div>

      {isOpen && hasDetails && (
        <div className="mt-1.5 ml-6 mr-2 p-2 rounded bg-black/40 border border-white/[0.04] space-y-1 text-[11px] text-slate-300 select-text overflow-x-auto">
          {step.description && (
            <div className="text-slate-400">{step.description}</div>
          )}
          {step.args && (
            <pre className="text-slate-300 whitespace-pre-wrap">
              {JSON.stringify(step.args, null, 2)}
            </pre>
          )}
          {step.output && (
            <pre className="text-slate-400 whitespace-pre-wrap">
              {step.output}
            </pre>
          )}
        </div>
      )}
    </div>
  );
};
