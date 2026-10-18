import React, { useMemo, useState } from 'react';
import { ChevronRight, FileCode, FileText, FileJson, Folder, FolderOpen, Image as ImageIcon, Trash2, Palette } from 'lucide-react';

interface TreeNode {
  name: string;
  path: string;
  children?: TreeNode[];
}

function buildTree(paths: string[]): TreeNode[] {
  const root: TreeNode = { name: '', path: '', children: [] };
  for (const path of paths) {
    const parts = path.split('/');
    let node = root;
    parts.forEach((part, index) => {
      const isFile = index === parts.length - 1;
      const childPath = parts.slice(0, index + 1).join('/');
      let child = node.children!.find((c) => c.name === part && Boolean(c.children) !== isFile);
      if (!child) {
        child = isFile ? { name: part, path: childPath } : { name: part, path: childPath, children: [] };
        node.children!.push(child);
      }
      node = child;
    });
  }
  const sort = (nodes: TreeNode[]) => {
    nodes.sort((a, b) => (Boolean(b.children) === Boolean(a.children) ? a.name.localeCompare(b.name) : b.children ? 1 : -1));
    nodes.forEach((n) => n.children && sort(n.children));
  };
  sort(root.children!);
  return root.children!;
}

function iconFor(name: string, active: boolean) {
  const cls = active ? 'text-emerald-400' : 'text-slate-500';
  if (/\.(tsx?|jsx?)$/.test(name)) return <FileCode size={13} className={cls} />;
  if (/\.css$/.test(name)) return <Palette size={13} className={cls} />;
  if (/\.json$/.test(name)) return <FileJson size={13} className={cls} />;
  if (/\.(svg|png|jpe?g|webp|ico)$/.test(name)) return <ImageIcon size={13} className={cls} />;
  return <FileText size={13} className={cls} />;
}

interface FileTreeProps {
  files: string[];
  activeFile: string;
  isDirty: (path: string) => boolean;
  onSelect: (path: string) => void;
  onDelete: (path: string, event: React.MouseEvent) => void;
}

export const FileTree: React.FC<FileTreeProps> = ({ files, activeFile, isDirty, onSelect, onDelete }) => {
  const tree = useMemo(() => buildTree(files), [files]);
  // Folders start open; the user's collapses are remembered for the session.
  const [collapsed, setCollapsed] = useState<Set<string>>(() => new Set(['public']));

  const toggle = (path: string) =>
    setCollapsed((prev) => {
      const next = new Set(prev);
      next.has(path) ? next.delete(path) : next.add(path);
      return next;
    });

  const render = (nodes: TreeNode[], depth: number): React.ReactNode =>
    nodes.map((node) => {
      const indent = { paddingLeft: `${8 + depth * 12}px` };
      if (node.children) {
        const open = !collapsed.has(node.path);
        return (
          <div key={node.path} role="treeitem" aria-expanded={open}>
            <button
              type="button"
              onClick={() => toggle(node.path)}
              style={indent}
              className="w-full flex items-center gap-1.5 pr-2 py-1 rounded text-left text-slate-300 hover:bg-white/[0.04] cursor-pointer"
              title={node.path}
            >
              <ChevronRight size={12} className={`shrink-0 text-slate-500 transition-transform ${open ? 'rotate-90' : ''}`} />
              {open ? <FolderOpen size={13} className="shrink-0 text-amber-300/80" /> : <Folder size={13} className="shrink-0 text-amber-300/80" />}
              <span className="truncate">{node.name}</span>
            </button>
            {open && <div role="group">{render(node.children, depth + 1)}</div>}
          </div>
        );
      }
      const active = node.path === activeFile;
      const dirty = isDirty(node.path);
      const safeId = node.path.replace(/[^a-zA-Z0-9_-]/g, '_');
      return (
        <div
          key={node.path}
          id={`code-file-item-${safeId}`}
          role="treeitem"
          aria-selected={active}
          tabIndex={0}
          onClick={() => onSelect(node.path)}
          onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); onSelect(node.path); } }}
          style={{ paddingLeft: `${20 + depth * 12}px` }}
          className={`group flex items-center justify-between gap-1 pr-1.5 py-1 rounded cursor-pointer outline-none focus-visible:ring-1 focus-visible:ring-emerald-400 ${
            active ? 'bg-emerald-500/10 text-emerald-300 font-medium' : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]'
          }`}
          title={node.path}
        >
          <span className="flex items-center gap-1.5 min-w-0">
            {iconFor(node.name, active)}
            <span className="truncate">{node.name}</span>
          </span>
          <span className="flex items-center gap-1 shrink-0">
            {dirty && <span className="w-2 h-2 rounded-full bg-amber-400" title="Unsaved changes" />}
            <button
              type="button"
              id={`code-delete-file-btn-${safeId}`}
              onClick={(event) => onDelete(node.path, event)}
              className="opacity-0 group-hover:opacity-100 focus:opacity-100 p-0.5 rounded hover:bg-rose-500/20 hover:text-rose-300 text-slate-500 cursor-pointer"
              title={`Delete ${node.path}`}
              aria-label={`Delete ${node.path}`}
            >
              <Trash2 size={11} />
            </button>
          </span>
        </div>
      );
    });

  if (!files.length) return <div className="p-4 text-center text-slate-500 text-xs">No files generated yet</div>;
  return <div role="tree" aria-label="Project files">{render(tree, 0)}</div>;
};
