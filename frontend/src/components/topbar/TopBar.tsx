import React from 'react';
import { 
  PanelLeft, 
  Square, 
  Info, 
  Sun, 
  Moon, 
  Sparkles,
  Layout,
  Inbox
} from 'lucide-react';
import { useAgentStore } from '../../state/agent-store';
import { useWorkspaceStore } from '../../state/workspace-store';
import { useProjectStore } from '../../state/project-store';
import { api } from '../../services/api';
import { projectWsClient } from '../../services/project-ws';
import { useConfirm } from '../../state/confirm-store';
import { toast } from '../../state/toast-store';

export const TopBar: React.FC = () => {
  const { status, statusMessage, activeTaskId, elapsedSeconds, queueDepth, resetAgent, validationResult, metrics,
          serverConnected, modelLoaded, modelStatus } = useAgentStore();
  const { 
    toggleSidebar, 
    sidebarOpen,
    theme, 
    toggleTheme, 
    inspectorOpen, 
    toggleInspector,
    workspaceOpen,
    toggleWorkspace,
    files
  } = useWorkspaceStore();
  const { currentProject } = useProjectStore();
  const confirm = useConfirm();

  const isWorking = status === 'generating' || status === 'planning' || status === 'typechecking' || status === 'repairing';
  // The dot reflects the real model state, not just that the page loaded.
  const modelState = !serverConnected
    ? { dot: 'bg-rose-500', label: 'Offline', title: 'The workbench server is not responding.' }
    : modelStatus === 'error'
    ? { dot: 'bg-rose-500', label: 'Model error', title: 'The model failed to load; check the server log.' }
    : modelStatus === 'loading' || modelStatus === 'unknown' || !modelLoaded
    ? { dot: 'bg-amber-400 animate-pulse', label: 'Loading model', title: 'The model is still loading onto the GPU.' }
    : modelStatus === 'busy' || isWorking
    ? { dot: 'bg-emerald-400 animate-pulse', label: 'Working', title: `${metrics.modelName} is generating.` }
    : { dot: 'bg-emerald-400', label: 'Ready', title: `${metrics.modelName} is loaded and ready.` };
  const fileCount = Object.keys(files).length;

  const handleStop = async () => {
    const ok = await confirm({
      title: 'Cancel All Tasks',
      message: 'Stop the active generation and clear any queued work?',
      confirmText: 'Cancel All',
      cancelText: 'Keep Running',
      variant: 'danger',
    });
    if (!ok) return;

    try {
      projectWsClient.sendTaskCancel('user_stopped');
      if (activeTaskId) {
        await api.cancelTask(activeTaskId, { clear_queue: true });
      } else {
        await api.cancelAll();
      }
      resetAgent();
      toast.info('Cancelled', 'Active task and queued operations have been stopped.');
    } catch (err: any) {
      console.error('Failed to cancel task:', err);
      toast.error('Cancel Failed', err.message || 'Could not cancel tasks.');
    }
  };

  return (
    <header className="h-12 min-h-[48px] border-b border-white/[0.06] bg-[#141414] px-3.5 flex items-center justify-between select-none z-30">
      {/* Left section: sidebar toggle, logo, active project */}
      <div className="flex items-center gap-3">
        <button
          id="topbar-sidebar-toggle"
          onClick={toggleSidebar}
          aria-label="Toggle project sidebar"
          aria-expanded={sidebarOpen}
          className="p-1.5 rounded-lg hover:bg-white/[0.06] text-slate-400 hover:text-slate-200 transition-colors cursor-pointer"
          title="Toggle Sidebar"
        >
          <PanelLeft size={16} />
        </button>

        <div className="flex items-center gap-2">
          <span className="font-semibold text-sm tracking-tight text-slate-100 flex items-center gap-2">
            SiteAgent
            <span className="text-slate-500 font-normal">·</span>
            <span className="font-normal text-slate-300">
              {currentProject ? currentProject.title : 'New chat'}
            </span>
          </span>

          {/* Model readiness */}
          <span
            id="topbar-model-status"
            data-state={modelState.label.toLowerCase().replace(' ', '-')}
            role="status"
            title={modelState.title}
            className="flex items-center gap-1.5 ml-2 text-[11px] text-slate-500 font-mono"
          >
            <span className={`w-1.5 h-1.5 rounded-full ${modelState.dot}`} />
            <span className="hidden sm:inline">{modelState.label}</span>
          </span>

          {/* Motion Capability Badge (Item 22) */}
          {(validationResult?.motion_status === 'passed' && (Boolean(validationResult?.motion_plan?.length) || Boolean(metrics?.hasMotion))) && (
            <span
              id="topbar-motion-badge"
              className="hidden lg:inline-flex items-center gap-1 ml-2 px-1.5 py-0.5 rounded text-[10px] font-mono bg-violet-500/15 text-violet-300 border border-violet-500/30"
              title="Source-level motion checks passed; browser motion behavior may still need review"
            >
              <Sparkles size={10} className="text-violet-400" />
              <span>Motion checks passed</span>
            </span>
          )}
        </div>
      </div>

      {/* Middle section: ONLY shown during generation or queuing */}
      <div className="flex items-center gap-3">
        {isWorking && (
          <div className="flex items-center gap-2 text-xs font-medium text-slate-300">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="max-w-[18rem] truncate" title={statusMessage}>{statusMessage || 'Building website'}</span>
            <span className="font-mono text-emerald-400/90 pl-1 border-l border-white/[0.08]">
              {elapsedSeconds.toFixed(1)}s
            </span>

            <button
              id="topbar-stop-btn"
              onClick={handleStop}
              className="flex items-center gap-1 ml-2 px-2 py-0.5 rounded bg-rose-500/15 text-rose-400 hover:bg-rose-500/25 border border-rose-500/30 transition-colors cursor-pointer text-[11px]"
              title="Stop generation"
            >
              <Square size={10} className="fill-rose-400" />
              <span>Stop</span>
            </button>
          </div>
        )}

        {!isWorking && (
          queueDepth > 0 ? (
            <div
              id="topbar-queue-status"
              className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-mono bg-amber-500/10 text-amber-400 border border-amber-500/20"
            >
              <Inbox size={11} />
              <span>Queue: {queueDepth}</span>
            </div>
          ) : (
            <div
              id="topbar-queue-status"
              className="hidden sm:flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-mono text-slate-500 hover:text-slate-400"
              title="Queue empty"
            >
              <Inbox size={11} />
              <span>Idle</span>
            </div>
          )
        )}
      </div>

      {/* Right section: Workspace Drawer toggle, Inspector toggle, Theme toggle */}
      <div className="flex items-center gap-1.5">
        <button
          id="topbar-workspace-toggle"
          onClick={toggleWorkspace}
          className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer ${
            workspaceOpen
              ? 'bg-white/[0.12] text-white shadow-sm'
              : 'hover:bg-white/[0.06] text-slate-400 hover:text-slate-200'
          }`}
          title="Toggle Workspace Panel"
        >
          <Layout size={14} />
          <span className="hidden sm:inline">Workspace</span>
          {fileCount > 0 && (
            <span className="text-[10px] font-mono px-1 rounded bg-white/[0.08] text-slate-300">
              {fileCount}
            </span>
          )}
        </button>

        <button
          id="topbar-inspector-toggle"
          onClick={toggleInspector}
          className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer ${
            inspectorOpen
              ? 'bg-white/[0.12] text-white shadow-sm'
              : 'hover:bg-white/[0.06] text-slate-400 hover:text-slate-200'
          }`}
          title="Toggle Inspector"
        >
          <Info size={14} />
          <span className="hidden sm:inline">Inspector</span>
        </button>

        <button
          id="topbar-theme-toggle"
          type="button"
          onClick={toggleTheme}
          className="p-1.5 rounded-lg hover:bg-white/[0.06] text-slate-400 hover:text-slate-200 transition-colors cursor-pointer"
          title={theme === 'dark' ? 'Switch to Light theme' : 'Switch to Dark theme'}
        >
          {theme === 'dark' ? <Sun size={15} /> : <Moon size={15} />}
        </button>
      </div>
    </header>
  );
};
