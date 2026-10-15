import React, { useState } from 'react';
import { Sparkles, ChevronDown, ChevronRight, Loader2 } from 'lucide-react';
import { ActivityStep as IActivityStep } from '../../types/agent';
import { ActivityStep } from './ActivityStep';
import { useAgentStore } from '../../state/agent-store';

interface ActivityMessageProps {
  steps: IActivityStep[];
  isActive?: boolean;
}

export const ActivityMessage: React.FC<ActivityMessageProps> = ({ steps, isActive }) => {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const { statusMessage } = useAgentStore();

  if (!steps || steps.length === 0) return null;

  return (
    <div className="flex items-start gap-3 my-3 select-text">
      <div className="w-6 h-6 rounded-md bg-emerald-500/15 text-emerald-400 border border-emerald-500/25 flex items-center justify-center shrink-0 mt-0.5">
        <Sparkles size={13} />
      </div>

      <div className="flex-1 max-w-xl rounded-2xl rounded-tl-sm border border-white/[0.06] bg-[#191919] overflow-hidden shadow-sm">
        <div
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="px-3.5 py-2.5 flex items-center justify-between cursor-pointer hover:bg-white/[0.02] transition-colors select-none"
        >
          <div className="flex items-center gap-2 text-xs font-medium text-slate-200">
            {isActive ? (
              <Loader2 size={13} className="animate-spin text-emerald-400" />
            ) : (
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            )}
            <span className="font-semibold">{statusMessage || 'Building website...'}</span>
            <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-white/[0.06] text-slate-400">
              {steps.length} {steps.length === 1 ? 'step' : 'steps'}
            </span>
          </div>

          <button className="text-slate-400 hover:text-slate-200">
            {isCollapsed ? <ChevronRight size={13} /> : <ChevronDown size={13} />}
          </button>
        </div>

        {!isCollapsed && (
          <div className="p-2 pt-0 space-y-0.5 border-t border-white/[0.04]">
            {steps.map((step) => (
              <ActivityStep key={step.id} step={step} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
