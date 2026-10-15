import React, { useEffect, useRef } from 'react';
import { AlertTriangle, AlertCircle, HelpCircle, X } from 'lucide-react';
import { useConfirmStore, ConfirmVariant } from '../../state/confirm-store';

export interface ConfirmDialogProps {
  open?: boolean;
  title?: string;
  message?: React.ReactNode;
  confirmText?: string;
  cancelText?: string;
  variant?: ConfirmVariant;
  onConfirm?: () => void;
  onCancel?: () => void;
}

export const ConfirmDialog: React.FC<ConfirmDialogProps> = (props) => {
  const store = useConfirmStore();

  // Support both declarative props and global store
  const isOpen = props.open !== undefined ? props.open : store.isOpen;
  const title = props.title || store.options?.title || 'Confirm Action';
  const message = props.message !== undefined ? props.message : store.options?.message;
  const confirmText = props.confirmText || store.options?.confirmText || 'Confirm';
  const cancelText = props.cancelText || store.options?.cancelText || 'Cancel';
  const variant: ConfirmVariant = props.variant || store.options?.variant || 'default';

  const dialogRef = useRef<HTMLDivElement>(null);
  const cancelBtnRef = useRef<HTMLButtonElement>(null);
  const confirmBtnRef = useRef<HTMLButtonElement>(null);

  const handleConfirm = () => {
    if (props.onConfirm) {
      props.onConfirm();
    } else {
      store.confirm();
    }
  };

  const handleCancel = () => {
    if (props.onCancel) {
      props.onCancel();
    } else {
      store.cancel();
    }
  };

  // Keyboard focus trap & Escape handling
  useEffect(() => {
    if (!isOpen) return;

    // Defensive initial focus:
    // For destructive/danger actions, focus Cancel button to prevent accidental confirmation
    // For safe/default actions, focus Confirm button
    const timer = setTimeout(() => {
      if (variant === 'danger') {
        cancelBtnRef.current?.focus();
      } else {
        confirmBtnRef.current?.focus();
      }
    }, 50);

    const handleKeyDown = (e: KeyboardEvent) => {
      // Escape closes safe dialogs
      if (e.key === 'Escape') {
        e.preventDefault();
        e.stopPropagation();
        handleCancel();
        return;
      }

      // Tab trap
      if (e.key === 'Tab' && dialogRef.current) {
        const focusable = Array.from(
          dialogRef.current.querySelectorAll<HTMLElement>(
            'button:not([disabled]), [href], input:not([disabled]), [tabindex]:not([tabindex="-1"])'
          )
        );

        if (focusable.length === 0) return;

        const first = focusable[0];
        const last = focusable[focusable.length - 1];

        if (e.shiftKey) {
          if (document.activeElement === first) {
            e.preventDefault();
            last.focus();
          }
        } else {
          if (document.activeElement === last) {
            e.preventDefault();
            first.focus();
          }
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown, true);
    return () => {
      clearTimeout(timer);
      window.removeEventListener('keydown', handleKeyDown, true);
    };
  }, [isOpen, variant]);

  if (!isOpen) return null;

  const variantStyles = {
    danger: {
      icon: <AlertTriangle size={18} className="text-rose-400 shrink-0" />,
      badgeBg: 'bg-rose-500/15 border-rose-500/30 text-rose-300',
      confirmBtn: 'bg-rose-600 hover:bg-rose-500 text-white shadow-lg shadow-rose-950/40 border-rose-500/50',
    },
    warning: {
      icon: <AlertCircle size={18} className="text-amber-400 shrink-0" />,
      badgeBg: 'bg-amber-500/15 border-amber-500/30 text-amber-300',
      confirmBtn: 'bg-amber-600 hover:bg-amber-500 text-white shadow-lg shadow-amber-950/40 border-amber-500/50',
    },
    default: {
      icon: <HelpCircle size={18} className="text-emerald-400 shrink-0" />,
      badgeBg: 'bg-emerald-500/15 border-emerald-500/30 text-emerald-300',
      confirmBtn: 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-950/40 border-emerald-500/50',
    },
  }[variant];

  return (
    <div
      className="fixed inset-0 z-[9990] flex items-center justify-center p-4 bg-black/75 backdrop-blur-xs select-none animate-in fade-in duration-150"
      onClick={handleCancel}
      role="presentation"
    >
      <div
        ref={dialogRef}
        id="confirm-dialog"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="confirm-dialog-title"
        aria-describedby="confirm-dialog-description"
        className="w-full max-w-md bg-[#181818] border border-white/[0.12] rounded-xl shadow-2xl overflow-hidden text-slate-100 font-sans"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-4 border-b border-white/[0.08] flex items-center justify-between">
          <div className="flex items-center gap-2.5 min-w-0">
            {variantStyles.icon}
            <h2 id="confirm-dialog-title" className="text-sm font-semibold truncate text-slate-100">
              {title}
            </h2>
          </div>

          <button
            onClick={handleCancel}
            className="p-1 rounded-md text-slate-400 hover:text-white hover:bg-white/[0.06] transition-colors cursor-pointer"
            aria-label="Close dialog"
            title="Close (Escape)"
          >
            <X size={15} />
          </button>
        </div>

        {/* Body */}
        <div className="p-5">
          <div id="confirm-dialog-description" className="text-xs leading-relaxed text-slate-300">
            {message}
          </div>
        </div>

        {/* Footer */}
        <div className="px-5 py-3.5 bg-white/[0.02] border-t border-white/[0.06] flex items-center justify-end gap-2.5">
          <button
            ref={cancelBtnRef}
            id="confirm-dialog-cancel-btn"
            onClick={handleCancel}
            className="px-3.5 py-1.5 rounded-lg border border-white/[0.1] bg-white/[0.04] hover:bg-white/[0.08] text-slate-300 text-xs font-medium transition-colors cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-white/30"
          >
            {cancelText}
          </button>

          <button
            ref={confirmBtnRef}
            id="confirm-dialog-confirm-btn"
            onClick={handleConfirm}
            className={`px-4 py-1.5 rounded-lg border text-xs font-semibold transition-all cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-white/40 ${variantStyles.confirmBtn}`}
          >
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  );
};
