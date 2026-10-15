import React from 'react';
import { useAgentStore } from '../../state/agent-store';

export const AgentStatusPill: React.FC = () => {
  const { status, statusMessage, elapsedSeconds } = useAgentStore();

  const isWorking = status === 'generating' || status === 'planning' || status === 'typechecking' || status === 'repairing';

  const dotColor = {
    idle: 'bg-emerald-400',
    planning: 'bg-indigo-400 animate-pulse',
    generating: 'bg-emerald-400 animate-pulse',
    typechecking: 'bg-amber-400 animate-pulse',
    repairing: 'bg-purple-400 animate-pulse',
    completed: 'bg-emerald-500',
    failed: 'bg-rose-500',
    cancelled: 'bg-amber-500',
  }[status];

  const statusLabel = {
    idle: 'Ready',
    planning: 'Planning',
    generating: 'Generating',
    typechecking: 'Validating',
    repairing: 'Repairing',
    completed: 'Ready',
    failed: 'Failed',
    cancelled: 'Stopped',
  }[status];

  return (
    <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-white/[0.04] border border-white/[0.08] text-xs font-medium text-slate-300">
      <span className={`w-2 h-2 rounded-full ${dotColor}`} />
      <span>{statusLabel}</span>
      {isWorking && (
        <span className="font-mono text-emerald-400/90 pl-1 border-l border-white/[0.08]">
          {elapsedSeconds.toFixed(1)}s
        </span>
      )}
    </div>
  );
};
