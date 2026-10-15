import { create } from 'zustand';
import { Project } from '../types/project';

interface ProjectStoreState {
  projects: Project[];
  openProjectIds: string[];
  currentProjectId: string | null;
  currentProject: Project | null;
  searchQuery: string;
  isLoading: boolean;

  setSearchQuery: (query: string) => void;
  setCurrentProjectId: (id: string | null) => void;
  setCurrentProject: (proj: Project | null) => void;
  setProjects: (projects: Project[]) => void;
  addProject: (proj: Project) => void;
  updateProject: (id: string, partial: Partial<Project>) => void;
  removeProject: (id: string) => void;
  openProjectTab: (id: string) => void;
  closeProjectTab: (id: string) => void;
  startNewProject: () => void;
  setIsLoading: (loading: boolean) => void;
}

export const useProjectStore = create<ProjectStoreState>((set, get) => ({
  projects: [],
  openProjectIds: [],
  currentProjectId: null,
  currentProject: null,
  searchQuery: '',
  isLoading: false,

  setSearchQuery: (searchQuery) => set({ searchQuery }),
  setCurrentProjectId: (id) => {
    if (!id) {
      set({ currentProjectId: null, currentProject: null });
      return;
    }
    const { projects, openProjectIds } = get();
    const proj = projects.find((p) => p.id === id) || null;
    const nextOpen = openProjectIds.includes(id) ? openProjectIds : [...openProjectIds, id];
    try {
      localStorage.setItem('slm_open_tabs', JSON.stringify(nextOpen));
    } catch (_) {}
    set({
      currentProjectId: id,
      currentProject: proj,
      openProjectIds: nextOpen,
    });
  },
  setCurrentProject: (proj) => {
    if (!proj) {
      set({ currentProject: null, currentProjectId: null });
      return;
    }
    const { openProjectIds } = get();
    const nextOpen = openProjectIds.includes(proj.id) ? openProjectIds : [...openProjectIds, proj.id];
    try {
      localStorage.setItem('slm_open_tabs', JSON.stringify(nextOpen));
    } catch (_) {}
    set({
      currentProject: proj,
      currentProjectId: proj.id,
      openProjectIds: nextOpen,
    });
  },
  setProjects: (projects) => {
    const { currentProjectId, openProjectIds } = get();
    // Check localStorage for saved open tabs
    let savedOpenIds: string[] | null = null;
    try {
      const raw = localStorage.getItem('slm_open_tabs');
      if (raw !== null) {
        savedOpenIds = JSON.parse(raw);
      }
    } catch (_) {}

    let validOpenIds: string[];
    if (savedOpenIds !== null) {
      validOpenIds = savedOpenIds.filter((id) => projects.some((p) => p.id === id));
    } else if (openProjectIds.length > 0) {
      validOpenIds = openProjectIds.filter((id) => projects.some((p) => p.id === id));
    } else {
      // First visit: initialize with first 3 projects if available
      validOpenIds = projects.slice(0, 3).map((p) => p.id);
      try {
        localStorage.setItem('slm_open_tabs', JSON.stringify(validOpenIds));
      } catch (_) {}
    }

    const current = currentProjectId ? projects.find((p) => p.id === currentProjectId) || null : null;
    set({
      projects,
      currentProject: current,
      currentProjectId: current ? current.id : null,
      openProjectIds: validOpenIds,
    });
  },
  addProject: (proj) =>
    set((state) => {
      const nextOpen = state.openProjectIds.includes(proj.id)
        ? state.openProjectIds
        : [...state.openProjectIds, proj.id];
      try {
        localStorage.setItem('slm_open_tabs', JSON.stringify(nextOpen));
      } catch (_) {}
      return {
        projects: [proj, ...state.projects.filter((p) => p.id !== proj.id)],
        currentProjectId: proj.id,
        currentProject: proj,
        openProjectIds: nextOpen,
      };
    }),
  updateProject: (id, partial) =>
    set((state) => {
      const updated = state.projects.map((p) => (p.id === id ? { ...p, ...partial } : p));
      return {
        projects: updated,
        currentProject: state.currentProjectId === id ? { ...state.currentProject!, ...partial } : state.currentProject,
      };
    }),
  removeProject: (id) =>
    set((state) => {
      const remaining = state.projects.filter((p) => p.id !== id);
      const remainingOpen = state.openProjectIds.filter((oid) => oid !== id);
      try {
        localStorage.setItem('slm_open_tabs', JSON.stringify(remainingOpen));
      } catch (_) {}
      const isCurrent = state.currentProjectId === id;
      const nextId = isCurrent ? (remainingOpen[0] || null) : state.currentProjectId;
      const nextProject = nextId ? remaining.find((p) => p.id === nextId) || null : null;
      return {
        projects: remaining,
        openProjectIds: remainingOpen,
        currentProject: nextProject,
        currentProjectId: nextId,
      };
    }),
  openProjectTab: (id) => {
    const { openProjectIds, projects } = get();
    const nextOpen = openProjectIds.includes(id) ? openProjectIds : [...openProjectIds, id];
    try {
      localStorage.setItem('slm_open_tabs', JSON.stringify(nextOpen));
    } catch (_) {}
    const proj = projects.find((p) => p.id === id) || null;
    set({
      openProjectIds: nextOpen,
      currentProjectId: id,
      currentProject: proj,
    });
  },
  closeProjectTab: (id) => {
    const { openProjectIds, currentProjectId, projects } = get();
    const remainingOpen = openProjectIds.filter((oid) => oid !== id);
    try {
      localStorage.setItem('slm_open_tabs', JSON.stringify(remainingOpen));
    } catch (_) {}

    if (currentProjectId === id) {
      const nextId = remainingOpen[remainingOpen.length - 1] || null;
      const nextProj = nextId ? projects.find((p) => p.id === nextId) || null : null;
      set({
        openProjectIds: remainingOpen,
        currentProjectId: nextId,
        currentProject: nextProj,
      });
    } else {
      set({ openProjectIds: remainingOpen });
    }
  },
  startNewProject: () =>
    set({
      currentProjectId: null,
      currentProject: null,
    }),
  setIsLoading: (isLoading) => set({ isLoading }),
}));
