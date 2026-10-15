import { create } from 'zustand';

export type ConfirmVariant = 'danger' | 'warning' | 'default';

export interface ConfirmOptions {
  title: string;
  message: React.ReactNode;
  confirmText?: string;
  cancelText?: string;
  variant?: ConfirmVariant;
  destructive?: boolean;
}

interface ConfirmStoreState {
  isOpen: boolean;
  options: ConfirmOptions | null;
  resolveCallback: ((value: boolean) => void) | null;
  show: (options: ConfirmOptions) => Promise<boolean>;
  confirm: () => void;
  cancel: () => void;
}

export const useConfirmStore = create<ConfirmStoreState>((set, get) => ({
  isOpen: false,
  options: null,
  resolveCallback: null,

  show: (options) => {
    return new Promise<boolean>((resolve) => {
      set({
        isOpen: true,
        options: {
          ...options,
          variant: options.variant ?? (options.destructive ? 'danger' : 'default'),
          confirmText: options.confirmText ?? (options.variant === 'danger' || options.destructive ? 'Confirm' : 'OK'),
          cancelText: options.cancelText ?? 'Cancel',
        },
        resolveCallback: resolve,
      });
    });
  },

  confirm: () => {
    const { resolveCallback } = get();
    if (resolveCallback) {
      resolveCallback(true);
    }
    set({ isOpen: false, options: null, resolveCallback: null });
  },

  cancel: () => {
    const { resolveCallback } = get();
    if (resolveCallback) {
      resolveCallback(false);
    }
    set({ isOpen: false, options: null, resolveCallback: null });
  },
}));

/**
 * Convenient React hook to request confirmation dialogs asynchronously.
 */
export function useConfirm() {
  const show = useConfirmStore((s) => s.show);
  return show;
}
