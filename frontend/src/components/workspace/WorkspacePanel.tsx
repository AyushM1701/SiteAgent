import React, { Suspense } from 'react';
import { 
  Eye, 
  Code2, 
  FileDiff, 
  Terminal, 
  SquareTerminal,
  X,
  Layers,
  ArrowLeft
} from 'lucide-react';
import { useWorkspaceStore, WorkspaceTab } from '../../state/workspace-store';
import { useProjectStore } from '../../state/project-store';
import { useAgentStore } from '../../state/agent-store';
import { PreviewTab } from './PreviewTab';
import { useViewportWidth, maxWorkspaceWidth } from '../../hooks/useViewportWidth';
import { LogsTab } from './LogsTab';
const CodeTab = React.lazy(() => import('./CodeTab').then(module => ({ default: module.CodeTab })));
const DiffTab = React.lazy(() => import('./DiffTab').then(module => ({ default: module.DiffTab })));
const ShellTab = React.lazy(() => import('./ShellTab').then(module => ({ default: module.ShellTab })));

export const WorkspacePanel: React.FC = () => {
  const { 
    activeTab, 
    setActiveTab, 
    files, 
    setWorkspaceOpen, 
    workspaceOpen, 
    workspaceWidth, 
    isResizing,
    sidebarOpen,
    inspectorOpen,
  } = useWorkspaceStore();
  const viewport = useViewportWidth();
  const { currentProjectId } = useProjectStore();
  const { status } = useAgentStore();

  if (!workspaceOpen) return null;

  // The stored width is a preference; never let it crowd out the chat.
  const width = viewport < 768 ? undefined : Math.min(workspaceWidth, maxWorkspaceWidth(viewport, sidebarOpen, inspectorOpen));

  const isWorking = status === 'generating' || status === 'planning' || status === 'typechecking' || status === 'repairing';
  const fileCount = Object.keys(files).length;

  const tabs: { id: WorkspaceTab; label: string; icon: React.ReactNode; hasActivity?: boolean }[] = [
    { id: 'preview', label: 'Live Preview', icon: <Eye size={13} />, hasActivity: isWorking },
    { id: 'code', label: `Code${fileCount > 0 ? ` (${fileCount})` : ''}`, icon: <Code2 size={13} /> },
    { id: 'diff', label: 'Diff', icon: <FileDiff size={13} /> },
    { id: 'logs', label: 'Logs', icon: <Terminal size={13} />, hasActivity: isWorking },
    { id: 'shell', label: 'Shell', icon: <SquareTerminal size={13} /> },
  ];

  return (
    <div
      id="workspace-panel"
      style={width ? { width: `${width}px` } : undefined}
      className="fixed inset-0 md:relative md:inset-auto h-full bg-[#141414] border-l border-white/[0.06] flex flex-col overflow-hidden z-50 md:z-20 shrink-0 max-w-full"
    >
      {/* Workspace Tabs Header */}
      <div className="h-11 border-b border-white/[0.06] px-3 flex items-center justify-between bg-[#141414] shrink-0 select-none">
        {/* Mobile back button */}
        <button
          id="workspace-mobile-back-btn"
          onClick={() => setWorkspaceOpen(false)}
          className="md:hidden flex items-center gap-1.5 text-xs text-slate-400 hover:text-white mr-2"
        >
          <ArrowLeft size={14} />
          <span>Chat</span>
        </button>

        <div className="flex items-center gap-1 overflow-x-auto no-scrollbar py-1">
          {tabs.map((tab) => {
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                id={`workspace-tab-${tab.id}`}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors whitespace-nowrap shrink-0 ${
                  isActive
                    ? 'bg-white/[0.10] text-white shadow-sm'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]'
                }`}
              >
                {tab.icon}
                <span>{tab.label}</span>
                {tab.hasActivity && (
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                )}
              </button>
            );
          })}
        </div>

        <button
          id="workspace-close-btn"
          onClick={() => setWorkspaceOpen(false)}
          className="p-1 rounded-lg hover:bg-white/[0.06] text-slate-400 hover:text-slate-200 ml-2 cursor-pointer"
          title="Close Workspace"
        >
          <X size={15} />
        </button>
      </div>

      {/* Active Tab View (disabled pointer events during resizer drag) */}
      <div className={`flex-1 overflow-hidden ${isResizing ? 'pointer-events-none select-none' : ''}`}>
        <Suspense fallback={<div className="p-4 text-xs text-slate-400">Loading workspace tool…</div>}>
          {activeTab === 'preview' && <PreviewTab />}
          {activeTab === 'code' && <CodeTab />}
          {activeTab === 'diff' && <DiffTab />}
          {activeTab === 'logs' && <LogsTab />}
          {activeTab === 'shell' && <ShellTab />}
        </Suspense>
      </div>
    </div>
  );
};
