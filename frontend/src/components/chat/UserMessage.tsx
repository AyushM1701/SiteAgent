import React from 'react';
import { Clock, Check, Play } from 'lucide-react';
import { ChatMessage } from '../../types/chat';

interface UserMessageProps {
  message: ChatMessage;
}

export const UserMessage: React.FC<UserMessageProps> = ({ message }) => {
  return (
    <div className="flex flex-col items-end space-y-1 my-3 select-text">
      <div className="flex items-center gap-2 text-[11px] text-slate-400 font-medium mr-1">
        <span>You</span>
        {message.isQueued ? (
          <span className="flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono bg-amber-500/15 text-amber-400 border border-amber-500/30">
            <Clock size={10} className="animate-spin-slow" />
            <span>Queued{message.queuePosition ? ` (#${message.queuePosition})` : ''}</span>
          </span>
        ) : message.turnId ? (
          <span className="text-slate-500 font-mono text-[10px]">
            Turn {message.turnId}
          </span>
        ) : null}
      </div>

      <div className="max-w-[85%] bg-[#1e2228] text-slate-100 px-4 py-2.5 rounded-2xl rounded-tr-sm border border-white/[0.08] text-xs sm:text-sm leading-relaxed whitespace-pre-wrap break-words shadow-sm">
        {message.content}
      </div>
    </div>
  );
};
