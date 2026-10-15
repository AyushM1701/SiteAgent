import { create } from 'zustand';

export type ToastType = 'success' | 'error' | 'warning' | 'info';

export interface ToastItem {
  id: string;
  type: ToastType;
  title: string;
  message?: string;
  duration?: number;
}

interface ToastStoreState {
  toasts: ToastItem[];
  addToast: (toast: Omit<ToastItem, 'id'>) => string;
  removeToast: (id: string) => void;
  clearToasts: () => void;
}

export const useToastStore = create<ToastStoreState>((set) => ({
  toasts: [],

  addToast: (toast) => {
    const id = `toast-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    const newItem: ToastItem = {
      ...toast,
      id,
      duration: toast.duration ?? (toast.type === 'error' ? 6000 : 4000),
    };

    set((state) => ({
      toasts: [...state.toasts, newItem],
    }));

    if (newItem.duration && newItem.duration > 0) {
      setTimeout(() => {
        set((state) => ({
          toasts: state.toasts.filter((t) => t.id !== id),
        }));
      }, newItem.duration);
    }

    return id;
  },

  removeToast: (id) =>
    set((state) => ({
      toasts: state.toasts.filter((t) => t.id !== id),
    })),

  clearToasts: () => set({ toasts: [] }),
}));

/**
 * Convenient imperative helper for triggering toasts anywhere in the codebase.
 */
export const toast = {
  success(title: string, message?: string, duration?: number) {
    return useToastStore.getState().addToast({ type: 'success', title, message, duration });
  },
  error(title: string, message?: string, duration?: number) {
    return useToastStore.getState().addToast({ type: 'error', title, message, duration });
  },
  warning(title: string, message?: string, duration?: number) {
    return useToastStore.getState().addToast({ type: 'warning', title, message, duration });
  },
  info(title: string, message?: string, duration?: number) {
    return useToastStore.getState().addToast({ type: 'info', title, message, duration });
  },
};
