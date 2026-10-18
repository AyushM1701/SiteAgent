import React, { useEffect } from 'react';
import { Plus, Search, Trash } from 'lucide-react';
import { useProjectStore } from '../../state/project-store';
import { useWorkspaceStore } from '../../state/workspace-store';
import { ProjectList } from './ProjectList';
import { api } from '../../services/api';
import { requestNewProject, loadProject, closeProjectTabAndSwitch } from '../../services/session';
import { Project } from '../../types/project';
import { useConfirm } from '../../state/confirm-store';
import { toast } from '../../state/toast-store';

export const ProjectSidebar: React.FC = () => {
  const {
    projects,
    currentProjectId,
    searchQuery,
    setSearchQuery,
    setProjects,
    setCurrentProjectId,
    removeProject,
  } = useProjectStore();
  const { sidebarOpen } = useWorkspaceStore();

  const loadProjects = async () => {
    try {
      const raw = await api.getProjects();
      const data = Array.isArray(raw) ? raw : ((raw as any)?.projects || (raw as any)?.sessions || []);
      const mapped: Project[] = (data || []).map((item: any) => ({
        id: item.session_id || item.id || item.task_id,
        title: item.title || item.symbol || item.prompt || 'Untitled Project',
        description: item.prompt,
        createdAt: item.timestamp || item.created_at || Date.now(),
        updatedAt: item.timestamp || item.updated_at || Date.now(),
        turnCount: item.turn_count || item.checkpoints_count || (item.turns ? item.turns.length : 1),
        mode: item.mode || 'component',
        files: item.files || {},
        latestVisualScore: item.visual_score ?? item.heuristic_score,
        filePath: item.file_path || item.filePath,
        folderName: item.folder_name || item.folderName || (item.file_path ? item.file_path.replace(/^generated_components\//, '').replace(/\/$/, '') : ''),
        fullPath: item.full_path || item.fullPath || item.workspace_dir,
        uses3D: Boolean(item.uses_3d ?? item.uses3D),
      }));
      setProjects(mapped);
    } catch (err) {
      console.warn('Could not load projects:', err);
    }
  };

  useEffect(() => {
    loadProjects();
  }, []);

  const selectProject = async (id: string) => {
    loadProject(id);
  };

  const confirm = useConfirm();

  const handleNewProject = () => {
    requestNewProject();
  };

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const ok = await confirm({
      title: 'Delete Project',
      message: 'Are you sure you want to delete this project? All checkpoints, files, and generation history will be permanently removed.',
      confirmText: 'Delete Project',
      variant: 'danger',
    });
    if (!ok) return;

    try {
      await api.deleteProject(id);
      removeProject(id);
      if (currentProjectId === id) {
        closeProjectTabAndSwitch(id);
      }
      toast.success('Project Deleted', 'The project was successfully removed.');
    } catch (err: any) {
      console.error('Delete failed:', err);
      toast.error('Delete Failed', err.message || 'Could not delete project.');
    }
  };

  const handleClearAll = async () => {
    const ok = await confirm({
      title: 'Clear All Projects',
      message: 'Clear all project history from your workbench? This will permanently delete all projects and cannot be undone.',
      confirmText: 'Clear All',
      variant: 'danger',
    });
    if (!ok) return;

    try {
      await api.clearAllHistory();
      setProjects([]);
      handleNewProject();
      toast.success('History Cleared', 'All project records have been cleared.');
    } catch (err: any) {
      console.error('Clear all failed:', err);
      toast.error('Clear All Failed', err.message || 'Could not clear project history.');
    }
  };

  if (!sidebarOpen) return null;

  return (
    <aside className="fixed top-12 bottom-0 left-0 md:relative md:top-auto md:bottom-auto w-64 min-w-[256px] border-r border-white/[0.06] bg-[#141414] flex flex-col h-full select-none z-20">
      {/* Top action: + New project */}
      <div className="p-3 border-b border-white/[0.04] space-y-2">
        <button
          id="sidebar-new-project-btn"
          onClick={handleNewProject}
          className="w-full flex items-center justify-between py-2 px-3 rounded-lg bg-white/[0.06] hover:bg-white/[0.10] text-slate-100 font-medium text-xs transition-colors border border-white/[0.04] cursor-pointer"
        >
          <span className="flex items-center gap-2">
            <Plus size={14} strokeWidth={2.5} />
            <span>New project</span>
          </span>
          <span className="text-[10px] text-slate-500 font-mono">⌘K</span>
        </button>

        {/* Search */}
        <div className="relative">
          <Search size={13} className="absolute left-2.5 top-2.5 text-slate-500" />
          <input
            id="sidebar-search-input"
            type="text"
            placeholder="Search projects..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-[#1c1c1c] text-slate-200 pl-8 pr-3 py-1.5 rounded-lg border border-transparent focus:border-white/[0.12] focus:outline-none text-xs placeholder:text-slate-500"
          />
        </div>
      </div>

      {/* Section label */}
      <div className="px-3 pt-3 pb-1 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
        Projects
      </div>

      {/* Project list */}
      <ProjectList
        projects={projects}
        currentProjectId={currentProjectId}
        searchQuery={searchQuery}
        onSelect={(id) => selectProject(id)}
        onDelete={handleDelete}
      />

      {/* Footer / Clear All */}
      {projects.length > 0 && (
        <div className="p-2 border-t border-white/[0.04]">
          <button
            id="sidebar-clear-history-btn"
            onClick={handleClearAll}
            className="w-full flex items-center justify-center gap-1.5 py-1 rounded text-slate-500 hover:text-rose-400 text-xs transition-colors cursor-pointer"
          >
            <Trash size={11} />
            <span>Clear History</span>
          </button>
        </div>
      )}
    </aside>
  );
};
