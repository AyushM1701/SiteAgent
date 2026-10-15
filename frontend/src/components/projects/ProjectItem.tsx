import React from 'react';
import { Trash2 } from 'lucide-react';
import { Project } from '../../types/project';

interface ProjectItemProps {
  project: Project;
  isActive: boolean;
  onSelect: (id: string) => void;
  onDelete: (id: string, e: React.MouseEvent) => void;
}

export const ProjectItem: React.FC<ProjectItemProps> = ({
  project,
  isActive,
  onSelect,
  onDelete,
}) => {
  const parseTime = (timestamp: string | number) => {
    if (typeof timestamp === 'number') return new Date(timestamp < 1e12 ? timestamp * 1000 : timestamp);
    const numeric = Number(timestamp);
    if (timestamp.trim() && Number.isFinite(numeric)) return new Date(numeric < 1e12 ? numeric * 1000 : numeric);
    const parsed = Date.parse(timestamp.includes('T') ? timestamp : timestamp.replace(' ', 'T'));
    return Number.isFinite(parsed) ? new Date(parsed) : null;
  };
  const updated = parseTime(project.updatedAt);
  const getRelativeTime = (time: number | undefined) => {
    if (time === undefined || !Number.isFinite(time)) return 'time unknown';
    const diffMs = Date.now() - time;
    const diffMin = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMin / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMs < -60000) return 'in the future';
    if (diffMin < 1) return 'Just now';
    if (diffMin < 60) return `${diffMin}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays === 1) return 'Yesterday';
    return `${diffDays}d ago`;
  };

  return (
    <div
      id={`sidebar-project-item-${project.id}`}
      className={`group relative flex items-center justify-between px-3 py-2 rounded-lg transition-colors select-none ${
        isActive
          ? 'bg-white/[0.08] text-white font-medium'
          : 'hover:bg-white/[0.04] text-slate-300 hover:text-slate-100'
      }`}
    >
      <button type="button" onClick={() => onSelect(project.id)} aria-current={isActive ? 'page' : undefined}
        className="flex flex-col truncate pr-2 text-left flex-1 rounded focus-visible:outline focus-visible:outline-2 focus-visible:outline-emerald-400">
        <span className="text-xs truncate font-medium w-full">
          {project.title}
        </span>
        <div className="flex items-center gap-1 text-[10px] text-slate-500 font-normal truncate">
          <time className="shrink-0" dateTime={updated && !isNaN(updated.getTime()) ? updated.toISOString() : undefined}
            title={updated && !isNaN(updated.getTime()) ? updated.toLocaleString() : 'Update time unavailable'}>
            Updated {getRelativeTime(updated?.getTime())}
          </time>
          {(project.folderName || project.filePath) && (project.folderName || project.filePath) !== project.id && (
            <>
              <span className="shrink-0">·</span>
              <span className="text-cyan-400/80 font-mono truncate" title={project.filePath || project.folderName}>
                {project.folderName || project.filePath}
              </span>
            </>
          )}
        </div>
      </button>

      <button
        id={`sidebar-project-delete-btn-${project.id}`}
        onClick={(e) => onDelete(project.id, e)}
        className="opacity-100 sm:opacity-0 sm:group-hover:opacity-100 sm:group-focus-within:opacity-100 p-1 rounded hover:bg-rose-500/20 text-slate-400 hover:text-rose-400 focus-visible:opacity-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-rose-400 transition-opacity shrink-0 cursor-pointer"
        title="Delete project"
        aria-label={`Delete project ${project.title}`}
      >
        <Trash2 size={12} />
      </button>
    </div>
  );
};
