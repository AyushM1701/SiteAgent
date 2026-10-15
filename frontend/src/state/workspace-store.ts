import { create } from 'zustand';
import { LogEntry, LogCategory, LogLevel } from '../types/logs';
import { useProjectStore } from './project-store';

const mobileViewport = () => typeof window !== 'undefined' && window.matchMedia('(max-width: 767px)').matches;
const savedSidebarOpen = (mobile: boolean) => {
  try {
    const value = localStorage.getItem(mobile ? 'slm_sidebar_mobile' : 'slm_sidebar_desktop');
    if (value === 'true' || value === 'false') return value === 'true';
  } catch (_) {}
  return !mobile;
};
const rememberSidebarOpen = (open: boolean) => {
  try { localStorage.setItem(mobileViewport() ? 'slm_sidebar_mobile' : 'slm_sidebar_desktop', String(open)); } catch (_) {}
};

export type WorkspaceTab = 'preview' | 'code' | 'diff' | 'logs' | 'shell';
export type PreviewDevice = 'desktop' | 'tablet' | 'mobile';

interface WorkspaceStoreState {
  workspaceOpen: boolean;
  activeTab: WorkspaceTab;
  activeFile: string;
  files: Record<string, string>;
  codeDrafts: Record<string, string>;
  previewDevice: PreviewDevice;
  previewKey: number;
  theme: 'dark' | 'light';
  inspectorOpen: boolean;
  sidebarOpen: boolean;

  // Diff state
  diffOriginal: string;
  diffModified: string;
  diffTurn: number;
  diffFilename: string;

  // Logs state
  logs: LogEntry[];
  logsByProject: Record<string, LogEntry[]>;
  logFilterLevel: LogLevel | 'all';
  logFilterCategory: LogCategory | 'all';
  logSearch: string;
  logAutoScroll: boolean;

  // Actions
  workspaceWidth: number;
  isResizing: boolean;
  setWorkspaceWidth: (width: number) => void;
  setIsResizing: (resizing: boolean) => void;

  toggleWorkspace: () => void;
  setWorkspaceOpen: (open: boolean) => void;
  setActiveTab: (tab: WorkspaceTab) => void;
  setActiveFile: (file: string) => void;
  setFiles: (files: Record<string, string>) => void;
  updateFileContent: (path: string, content: string) => void;
  setCodeDraft: (path: string, content: string) => void;
  clearCodeDraft: (path: string) => void;
  clearAllCodeDrafts: () => void;
  setPreviewDevice: (device: PreviewDevice) => void;
  reloadPreview: () => void;
  toggleTheme: () => void;
  setTheme: (theme: 'dark' | 'light') => void;
  toggleInspector: () => void;
  setInspectorOpen: (open: boolean) => void;
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
  syncSidebarViewport: (mobile: boolean) => void;

  setDiff: (original: string, modified: string, turn: number, filename?: string) => void;
  addLog: (entry: Omit<LogEntry, 'id' | 'timeStr'>, projectId?: string) => void;
  setLogsForProject: (projectId: string) => void;
  setLogFilterLevel: (lvl: LogLevel | 'all') => void;
  setLogFilterCategory: (cat: LogCategory | 'all') => void;
  setLogSearch: (search: string) => void;
  setLogAutoScroll: (auto: boolean) => void;
  clearLogs: (projectId?: string) => void;
  clearWorkspace: () => void;

  // Active generation conflict modal
  activeTaskModalOpen: boolean;
  openActiveTaskModal: () => void;
  closeActiveTaskModal: () => void;
}

export const useWorkspaceStore = create<WorkspaceStoreState>((set) => ({
  workspaceOpen: false, // Closed by default for ChatGPT feel!
  activeTab: 'preview',
  activeFile: '',
  files: {},
  codeDrafts: {},
  previewDevice: 'desktop',
  previewKey: 0,
  theme: (function(): 'dark' | 'light' {
    try {
      const saved = localStorage.getItem('slm_theme');
      if (saved === 'light' || saved === 'dark') {
        document.documentElement.setAttribute('data-theme', saved);
        if (saved === 'dark') {
          document.documentElement.classList.add('dark');
        } else {
          document.documentElement.classList.remove('dark');
        }
        return saved;
      }
    } catch (_) {}
    return 'dark';
  })(),
  inspectorOpen: false,
  sidebarOpen: savedSidebarOpen(mobileViewport()),

  diffOriginal: '',
  diffModified: '',
  diffTurn: 0,
  diffFilename: '',

  logs: [],
  logsByProject: {},
  logFilterLevel: 'all',
  logFilterCategory: 'all',
  logSearch: '',
  logAutoScroll: true,

  workspaceWidth: (function(): number {
    try {
      const saved = localStorage.getItem('slm_workspace_width');
      if (saved) {
        const parsed = parseInt(saved, 10);
        if (!isNaN(parsed) && parsed >= 320) return parsed;
      }
    } catch (_) {}
    return 620;
  })(),
  isResizing: false,
  setWorkspaceWidth: (workspaceWidth) => {
    try {
      localStorage.setItem('slm_workspace_width', String(workspaceWidth));
    } catch (_) {}
    set({ workspaceWidth });
  },
  setIsResizing: (isResizing) => set({ isResizing }),

  toggleWorkspace: () => set((state) => ({ workspaceOpen: !state.workspaceOpen })),
  setWorkspaceOpen: (workspaceOpen) => set({ workspaceOpen }),
  setActiveTab: (tab) => set({ activeTab: tab, workspaceOpen: true }),
  setActiveFile: (file) => set({ activeFile: file }),
  setFiles: (files) => {
    const filenames = Object.keys(files);
    set((state) => ({
      files,
      activeFile: filenames.includes(state.activeFile) && state.activeFile !== ''
        ? state.activeFile
        : filenames.find((f) => f.includes('App') || f.includes('Hero') || f.endsWith('.tsx')) || filenames[0] || '',
    }));
  },
  updateFileContent: (path, content) =>
    set((state) => ({
      files: { ...state.files, [path]: content },
    })),
  setCodeDraft: (path, content) =>
    set((state) => ({
      codeDrafts: { ...state.codeDrafts, [path]: content },
    })),
  clearCodeDraft: (path) =>
    set((state) => {
      const next = { ...state.codeDrafts };
      delete next[path];
      return { codeDrafts: next };
    }),
  clearAllCodeDrafts: () => set({ codeDrafts: {} }),
  setPreviewDevice: (previewDevice) => set({ previewDevice }),
  reloadPreview: () => set((state) => ({ previewKey: state.previewKey + 1 })),
  toggleTheme: () =>
    set((state) => {
      const next = state.theme === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      if (next === 'dark') {
        document.documentElement.classList.add('dark');
      } else {
        document.documentElement.classList.remove('dark');
      }
      try {
        localStorage.setItem('slm_theme', next);
      } catch (_) {}
      return { theme: next };
    }),
  setTheme: (theme) => {
    document.documentElement.setAttribute('data-theme', theme);
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
    try {
      localStorage.setItem('slm_theme', theme);
    } catch (_) {}
    set({ theme });
  },
  toggleInspector: () => set((state) => ({ inspectorOpen: !state.inspectorOpen })),
  setInspectorOpen: (inspectorOpen) => set({ inspectorOpen }),
  toggleSidebar: () => set((state) => {
    rememberSidebarOpen(!state.sidebarOpen);
    return { sidebarOpen: !state.sidebarOpen };
  }),
  setSidebarOpen: (sidebarOpen) => {
    rememberSidebarOpen(sidebarOpen);
    set({ sidebarOpen });
  },
  syncSidebarViewport: (mobile) => set({ sidebarOpen: savedSidebarOpen(mobile) }),

  setDiff: (diffOriginal, diffModified, diffTurn, filename) =>
    set((state) => ({
      diffOriginal,
      diffModified,
      diffTurn,
      diffFilename: filename !== undefined ? filename : state.diffFilename || state.activeFile,
    })),

  addLog: (entry, projectId) =>
    set((state) => {
      const now = new Date(entry.timestamp);
      const timeStr = `${now.getHours().toString().padStart(2, '0')}:${now
        .getMinutes()
        .toString()
        .padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`;
      const newLog: LogEntry = {
        ...entry,
        id: `${entry.timestamp}-${Math.random().toString(36).slice(2, 7)}`,
        timeStr,
      };
      const targetId = projectId || (entry as any).projectId;
      const currentProjId = useProjectStore.getState().currentProjectId;

      const nextLogsByProject = { ...state.logsByProject };
      if (targetId) {
        const projLogs = nextLogsByProject[targetId] || [];
        nextLogsByProject[targetId] = [...projLogs.slice(-2000), newLog];
      }

      const shouldDisplay = !targetId || !currentProjId || targetId === currentProjId;
      const nextLogs = shouldDisplay ? [...state.logs.slice(-2000), newLog] : state.logs;

      return {
        logs: nextLogs,
        logsByProject: nextLogsByProject,
      };
    }),

  setLogsForProject: (projectId) =>
    set((state) => ({
      logs: state.logsByProject[projectId] ? [...state.logsByProject[projectId]] : [],
      logFilterLevel: 'all',
      logFilterCategory: 'all',
      logSearch: '',
    })),

  setLogFilterLevel: (logFilterLevel) => set({ logFilterLevel }),
  setLogFilterCategory: (logFilterCategory) => set({ logFilterCategory }),
  setLogSearch: (logSearch) => set({ logSearch }),
  setLogAutoScroll: (logAutoScroll) => set({ logAutoScroll }),
  clearLogs: (projectId) =>
    set((state) => {
      const nextByProject = { ...state.logsByProject };
      if (projectId && nextByProject[projectId]) {
        nextByProject[projectId] = [];
      }
      return {
        logs: [],
        logsByProject: nextByProject,
      };
    }),

  activeTaskModalOpen: false,
  openActiveTaskModal: () => set({ activeTaskModalOpen: true }),
  closeActiveTaskModal: () => set({ activeTaskModalOpen: false }),

  clearWorkspace: () =>
    set({
      files: {},
      codeDrafts: {},
      activeFile: '',
      diffOriginal: '',
      diffModified: '',
      diffTurn: 0,
      diffFilename: '',
      previewKey: 0,
      previewDevice: 'desktop',
      activeTab: 'preview',
      workspaceOpen: false,
      inspectorOpen: false,
      activeTaskModalOpen: false,
      logs: [],
      logFilterLevel: 'all',
      logFilterCategory: 'all',
      logSearch: '',
      logAutoScroll: true,
    }),
}));
