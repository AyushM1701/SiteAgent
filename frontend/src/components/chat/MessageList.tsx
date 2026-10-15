import React, { useEffect, useRef, useState } from 'react';
import { useChatStore } from '../../state/chat-store';
import { useAgentStore } from '../../state/agent-store';
import { UserMessage } from './UserMessage';
import { AssistantMessage } from './AssistantMessage';
import { ActivityMessage } from './ActivityMessage';
import { ChangeSummary } from './ChangeSummary';

interface MessageListProps {
  onSelectPrompt?: (text: string) => void;
}

export const MessageList: React.FC<MessageListProps> = ({ onSelectPrompt }) => {
  const { messages } = useChatStore();
  const { currentActivities, status } = useAgentStore();
  const scrollRef = useRef<HTMLDivElement>(null);
  const [siteDetails, setSiteDetails] = useState({ topic: '', audience: '', pages: '', content: '', style: '', effects: '', assets: '' });

  const selectStructuredPrompt = () => {
    const fields: Array<[string, string]> = [
      ['Topic', siteDetails.topic], ['Audience', siteDetails.audience], ['Pages or sections', siteDetails.pages],
      ['Required content and interactions', siteDetails.content], ['Visual style', siteDetails.style],
      ['3D and motion', siteDetails.effects], ['Available assets', siteDetails.assets],
    ];
    const details = fields.filter(([, value]) => value.trim()).map(([label, value]) => `${label}: ${value.trim()}`);
    if (details.length) onSelectPrompt?.(`Build a complete, responsive website.\n${details.join('\n')}`);
  };

  const isWorking =
    status === 'generating' || status === 'planning' || status === 'typechecking' || status === 'repairing';

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, currentActivities, isWorking]);

  const suggestionChips = [
    { label: 'Build a portfolio', prompt: 'Build a dark modern portfolio site with work showcase, about me, and contact form' },
    { label: 'Create a 3D site', prompt: 'Create a 3D interactive landing page with a rotating globe using Three.js' },
    { label: 'SaaS landing page', prompt: 'Build a sleek SaaS landing page with hero, feature grid, pricing tiers, and testimonials' },
    { label: 'Interactive dashboard', prompt: 'Build an interactive analytics dashboard with KPI cards and chart placeholders' },
  ];

  return (
    <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-4 select-text">
      <div className="max-w-3xl mx-auto w-full space-y-4">
        {messages.length === 0 ? (
          <div className="min-h-[58vh] flex flex-col items-center justify-center text-center gap-5 select-none">
            <div className="space-y-2">
              <h1 className="text-2xl font-semibold tracking-tight text-white">
                What do you want to build?
              </h1>
              <p className="text-xs text-slate-400">
                Describe the site you have in mind, or start with a few details below.
              </p>
            </div>

            {/* Prompt suggestion chips */}
            <div className="flex flex-wrap items-center justify-center gap-2 max-w-lg">
              {suggestionChips.map((item) => (
                <button
                  key={item.label}
                  onClick={() => onSelectPrompt?.(item.prompt)}
                  className="px-3 py-1.5 rounded-full bg-white/[0.04] hover:bg-white/[0.08] text-slate-300 hover:text-white border border-white/[0.06] text-xs transition-colors cursor-pointer"
                >
                  {item.label}
                </button>
              ))}
            </div>
            <details className="w-full max-w-xl rounded-xl border border-white/[0.08] bg-white/[0.03] text-left group">
              <summary className="cursor-pointer list-none px-4 py-3 text-xs font-medium text-slate-300 focus-visible:outline focus-visible:outline-2 focus-visible:outline-sky-400">
                Help me describe my website <span aria-hidden="true" className="float-right text-slate-500 group-open:rotate-180">⌄</span>
              </summary>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 px-4 pb-4">
                {([
                  ['topic', 'Topic or business', 'e.g. ceramics studio'],
                  ['audience', 'Audience', 'e.g. local shoppers'],
                  ['pages', 'Pages or sections', 'e.g. home, catalog, about'],
                  ['content', 'Content and interactions', 'e.g. prices, filters, booking'],
                  ['style', 'Visual style', 'e.g. warm editorial'],
                  ['effects', '3D and motion', 'e.g. subtle scroll reveals'],
                  ['assets', 'Assets you have', 'e.g. logo and product photos'],
                ] as const).map(([key, label, placeholder]) => (
                  <label key={key} className="block text-[11px] text-slate-400">
                    {label}
                    <input
                      value={siteDetails[key]}
                      onChange={(event) => setSiteDetails((current) => ({ ...current, [key]: event.target.value }))}
                      placeholder={placeholder}
                      className="mt-1 block w-full rounded-md border border-white/[0.1] bg-slate-950/60 px-2.5 py-2 text-xs text-slate-100 placeholder:text-slate-600 focus:outline-none focus:ring-1 focus:ring-sky-400"
                    />
                  </label>
                ))}
                <div className="flex items-end">
                  <button type="button" onClick={selectStructuredPrompt} disabled={!Object.values(siteDetails).some((value) => value.trim())}
                    className="w-full rounded-md bg-sky-500 px-3 py-2 text-xs font-semibold text-slate-950 disabled:cursor-not-allowed disabled:opacity-40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-400">
                    Add details to prompt
                  </button>
                </div>
              </div>
            </details>
          </div>
        ) : (
          <>
            {messages.map((msg) => {
              if (msg.role === 'user') {
                return <UserMessage key={msg.id} message={msg} />;
              }
              if (msg.role === 'assistant') {
                return <AssistantMessage key={msg.id} message={msg} />;
              }
              if (msg.role === 'summary' && msg.summary) {
                return <ChangeSummary key={msg.id} summary={msg.summary} />;
              }
              if (msg.role === 'error') {
                return (
                  <div
                    key={msg.id}
                    className="my-2 p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs font-mono"
                  >
                    [Error] {msg.content}
                  </div>
                );
              }
              return null;
            })}

            {/* Live Activity Card for the currently active task */}
            {isWorking && currentActivities.length > 0 && (
              <ActivityMessage steps={currentActivities} isActive={true} />
            )}
          </>
        )}
      </div>
    </div>
  );
};
