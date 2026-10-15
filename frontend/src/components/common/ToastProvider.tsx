import React from 'react';
import { CheckCircle2, AlertCircle, AlertTriangle, Info, X } from 'lucide-react';
import { useToastStore, ToastItem, ToastType } from '../../state/toast-store';

const toastConfig: Record<
  ToastType,
  {
    icon: React.ReactNode;
    borderColor: string;
    bgColor: string;
    textColor: string;
    iconColor: string;
  }
> = {
  success: {
    icon: <CheckCircle2 size={16} />,
    borderColor: 'border-emerald-500/30',
    bgColor: 'bg-[#161f1c]',
    textColor: 'text-emerald-200',
    iconColor: 'text-emerald-400',
  },
  error: {
    icon: <AlertCircle size={16} />,
    borderColor: 'border-rose-500/35',
    bgColor: 'bg-[#221618]',
    textColor: 'text-rose-200',
    iconColor: 'text-rose-400',
  },
  warning: {
    icon: <AlertTriangle size={16} />,
    borderColor: 'border-amber-500/35',
    bgColor: 'bg-[#221c13]',
    textColor: 'text-amber-200',
    iconColor: 'text-amber-400',
  },
  info: {
    icon: <Info size={16} />,
    borderColor: 'border-sky-500/30',
    bgColor: 'bg-[#141b24]',
    textColor: 'text-sky-200',
    iconColor: 'text-sky-400',
  },
};

export const ToastProvider: React.FC = () => {
  const { toasts, removeToast } = useToastStore();

  if (toasts.length === 0) return null;

  return (
    <div
      aria-live="polite"
      aria-atomic="true"
      className="fixed bottom-4 right-4 z-[9999] flex flex-col gap-2.5 max-w-sm w-full pointer-events-none select-none"
    >
      {toasts.map((t) => {
        const config = toastConfig[t.type] || toastConfig.info;

        return (
          <div
            key={t.id}
            role="status"
            className={`pointer-events-auto flex items-start gap-3 p-3.5 rounded-xl border ${config.borderColor} ${config.bgColor} shadow-2xl backdrop-blur-md transition-all duration-200 animate-in slide-in-from-bottom-3 fade-in`}
          >
            <div className={`mt-0.5 shrink-0 ${config.iconColor}`}>{config.icon}</div>

            <div className="flex-1 min-w-0">
              <div className={`text-xs font-semibold leading-tight ${config.textColor}`}>
                {t.title}
              </div>
              {t.message && (
                <div className="text-[11px] text-slate-300 mt-1 leading-relaxed break-words font-sans">
                  {t.message}
                </div>
              )}
            </div>

            <button
              onClick={() => removeToast(t.id)}
              className="text-slate-400 hover:text-white p-1 rounded transition-colors shrink-0 -mr-1 -mt-1 cursor-pointer"
              title="Dismiss notification"
              aria-label="Dismiss"
            >
              <X size={13} />
            </button>
          </div>
        );
      })}
    </div>
  );
};
