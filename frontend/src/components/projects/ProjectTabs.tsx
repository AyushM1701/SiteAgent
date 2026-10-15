import React from 'react';
import { Plus, X, Globe, Code } from 'lucide-react';
import { useProjectStore } from '../../state/project-store';
import { requestNewProject, loadProject, closeProjectTabAndSwitch } from '../../services/session';

export const ProjectTabs: React.FC = () => {
  const { 
    projects, 
    openProjectIds, 
    currentProjectId, 
  } = useProjectStore();

  // Active tabs strictly reflect the openProjectIds list
  const activeTabs = openProjectIds
    .map((id) => projects.find((p) => p.id === id))
    .filter((p): p is NonNullable<typeof p> => Boolean(p));

  const handleSelectTab = (id: string) => {
    if (id === currentProjectId) return;
    loadProject(id);
  };

  const handleCloseTab = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    e.preventDefault();
    closeProjectTabAndSwitch(id);
  };

  return (
    <div className="h-9 min-h-[36px] bg-[#141414] border-b border-white/[0.04] px-2 flex items-center gap-1 overflow-x-auto select-none no-scrollbar">
      {/* New Project / Tab Trigger */}
      <button
        type="button"
        onClick={() => requestNewProject()}
        className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs transition-colors shrink-0 ${
          currentProjectId === null
            ? 'bg-white/[0.08] text-white font-medium shadow-sm'
            : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]'
        }`}
        title="Start new project (⌘K)"
      >
        <Plus size={13} strokeWidth={2.5} />
        <span>New</span>
      </button>

      {/* Separator */}
      {activeTabs.length > 0 && (
        <div className="h-4 w-[1px] bg-white/[0.08] mx-1 shrink-0" />
      )}

      {/* Horizontal Project Tabs */}
      <div className="flex items-center gap-1 overflow-x-auto py-0.5">
        {activeTabs.map((proj) => {
          const isActive = proj.id === currentProjectId;
          return (
            <div
              key={proj.id}
              onClick={() => handleSelectTab(proj.id)}
              className={`group relative flex items-center gap-2 px-2.5 py-1 rounded-md text-xs cursor-pointer transition-all shrink-0 max-w-[200px] ${
                isActive
                  ? 'bg-white/[0.10] text-white font-medium border border-white/[0.06] shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.04] border border-transparent'
              }`}
              title={proj.title}
            >
              {proj.mode === 'site' ? (
                <Globe size={12} className="text-teal-400 shrink-0" />
              ) : (
                <Code size={12} className="text-indigo-400 shrink-0" />
              )}

              <span className="truncate text-[11px] pr-1">{proj.title}</span>

              <button
                type="button"
                onClick={(e) => handleCloseTab(proj.id, e)}
                className="opacity-50 hover:!opacity-100 group-hover:opacity-80 p-0.5 rounded hover:bg-white/[0.15] text-slate-300 hover:text-white transition-all shrink-0 ml-auto z-10"
                title="Close tab"
              >
                <X size={12} />
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
};

