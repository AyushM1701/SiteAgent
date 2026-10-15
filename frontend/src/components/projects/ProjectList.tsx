import React from 'react';
import { Project } from '../../types/project';
import { ProjectItem } from './ProjectItem';
import { FolderGit2 } from 'lucide-react';

interface ProjectListProps {
  projects: Project[];
  currentProjectId: string | null;
  searchQuery: string;
  onSelect: (id: string) => void;
  onDelete: (id: string, e: React.MouseEvent) => void;
}

export const ProjectList: React.FC<ProjectListProps> = ({
  projects,
  currentProjectId,
  searchQuery,
  onSelect,
  onDelete,
}) => {
  const filtered = projects.filter((p) =>
    p.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    p.id.toLowerCase().includes(searchQuery.toLowerCase())
  );

  if (filtered.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-6 text-center text-slate-500 space-y-2">
        <FolderGit2 size={24} className="text-slate-600" />
        <p className="text-xs">
          {searchQuery ? 'No matching projects found' : 'No projects yet'}
        </p>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto space-y-1.5 p-2">
      {filtered.map((proj) => (
        <ProjectItem
          key={proj.id}
          project={proj}
          isActive={proj.id === currentProjectId}
          onSelect={onSelect}
          onDelete={onDelete}
        />
      ))}
    </div>
  );
};
