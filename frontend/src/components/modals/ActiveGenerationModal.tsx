import React, { useEffect, useState } from 'react';
import { AlertCircle, X, Sparkles, Cpu } from 'lucide-react';
import { useWorkspaceStore } from '../../state/workspace-store';
import { useAgentStore } from '../../state/agent-store';
import { startNewProject } from '../../services/session';
import { api } from '../../services/api';
import { projectWsClient } from '../../services/project-ws';

export const ActiveGenerationModal: React.FC = () => {
  const { activeTaskModalOpen, closeActiveTaskModal } = useWorkspaceStore();
  const { activeTaskId, resetAgent } = useAgentStore();
  const [isCancelling, setIsCancelling] = useState(false);

  // Keyboard shortcut listener (Enter for Cancel & Start New, Esc for Stay Here)
  useEffect(() => {
    if (!activeTaskModalOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        closeActiveTaskModal();
      } else if (e.key === 'Enter') {
        e.preventDefault();
        handleCancelAndStart();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [activeTaskModalOpen, activeTaskId]);

  if (!activeTaskModalOpen) return null;

  const handleCancelAndStart = async () => {
    setIsCancelling(true);
    try {
      projectWsClient.sendTaskCancel('user_cancelled_for_new_project');
      if (activeTaskId) {
        await api.cancelTask(activeTaskId, { clear_queue: true });
      } else {
        await api.cancelAll();
      }
    } catch (err) {
      console.warn('Task cancellation error:', err);
    } finally {
      setIsCancelling(false);
      closeActiveTaskModal();
      startNewProject();
    }
  };

  const handleKeepRunning = () => {
    closeActiveTaskModal();
    startNewProject();
  };

  const handleStayHere = () => {
    closeActiveTaskModal();
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-xs animate-in fade-in duration-150"
      onClick={handleStayHere}
    >
      <div
        className="w-full max-w-md bg-[#181818] border border-white/[0.10] rounded-xl shadow-2xl overflow-hidden text-slate-100 font-sans select-none"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-5 pb-3 flex items-start justify-between gap-3 border-b border-white/[0.06]">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-amber-500/15 border border-amber-500/30 flex items-center justify-center text-amber-400 shrink-0">
              <Cpu size={18} />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-slate-100 leading-tight">
                A generation is still running.
              </h3>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Local GPU task is currently active.
              </p>
            </div>
          </div>
          <button
            onClick={handleStayHere}
            className="p-1 rounded-md text-slate-400 hover:text-slate-200 hover:bg-white/[0.06] transition-colors"
            title="Stay here (Esc)"
          >
            <X size={16} />
          </button>
        </div>

        {/* Body */}
        <div className="p-5 space-y-4">
          <p className="text-xs text-slate-300 leading-relaxed">
            Starting a new project while a task is running on your RTX 4050 may queue your next session behind the active model execution.
          </p>

          {/* Action options */}
          <div className="space-y-2 pt-1">
            {/* 1. Cancel and start new project (Recommended / Default) */}
            <button
              onClick={handleCancelAndStart}
              disabled={isCancelling}
              className="w-full group px-3.5 py-2.5 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-medium text-xs transition-all flex items-center justify-between shadow-sm cursor-pointer disabled:opacity-50"
            >
              <div className="flex items-center gap-2 font-semibold">
                <span>Cancel and start new project</span>
              </div>
              <span className="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded bg-black/20 text-slate-900 font-bold tracking-wider">
                Recommended
              </span>
            </button>

            {/* 2. Keep running in background */}
            <button
              onClick={handleKeepRunning}
              className="w-full px-3.5 py-2.5 rounded-lg bg-white/[0.05] hover:bg-white/[0.10] text-slate-200 border border-white/[0.08] text-xs font-medium transition-colors text-left flex items-center justify-between cursor-pointer"
            >
              <span>Keep running in background</span>
              <span className="text-[10px] text-slate-400">Leaves GPU job intact</span>
            </button>

            {/* 3. Stay here */}
            <button
              onClick={handleStayHere}
              className="w-full px-3.5 py-2 rounded-lg text-slate-400 hover:text-slate-200 text-xs transition-colors text-center cursor-pointer hover:bg-white/[0.03]"
            >
              <span>Stay here</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
