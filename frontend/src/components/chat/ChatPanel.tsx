import React, { useState } from 'react';
import { MessageList } from './MessageList';
import { ChatComposer } from './ChatComposer';

export const ChatPanel: React.FC = () => {
  const [selectedPrompt, setSelectedPrompt] = useState<string | undefined>(undefined);

  const handleSelectPrompt = (prompt: string) => {
    setSelectedPrompt(prompt);
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-[#171717] overflow-hidden relative">
      {/* Scrollable message thread */}
      <MessageList onSelectPrompt={handleSelectPrompt} />

      {/* Main bottom composer */}
      <ChatComposer initialPrompt={selectedPrompt} />
    </div>
  );
};
