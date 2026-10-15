import React from 'react';
import { Sparkles } from 'lucide-react';
import { ChatMessage } from '../../types/chat';

interface AssistantMessageProps {
  message: ChatMessage;
}

export const AssistantMessage: React.FC<AssistantMessageProps> = ({ message }) => {
  return (
    <div className="flex items-start gap-3 my-3 select-text">
      <div className="w-6 h-6 rounded-md bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 flex items-center justify-center shrink-0 mt-0.5 shadow-sm">
        <Sparkles size={13} />
      </div>

      <div className="flex-1 space-y-1">
        <div className="text-[11px] text-slate-400 font-medium">ReactAgent</div>
        <div className="text-xs sm:text-sm text-slate-200 leading-relaxed bg-[#191c20] p-3.5 rounded-2xl rounded-tl-sm border border-white/[0.06] whitespace-pre-wrap break-words shadow-sm">
          {message.content}
        </div>
      </div>
    </div>
  );
};
