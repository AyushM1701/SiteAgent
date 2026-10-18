import React, { useState, useRef, useEffect } from 'react';
import { 
  ArrowUp, 
  Clock, 
  Plus, 
  SlidersHorizontal, 
  X, 
  Palette, 
  LayoutTemplate,
  Box,
  Crosshair,
  ChevronDown,
  Check,
  Sparkles,
  Send
} from 'lucide-react';
import { useAgentStore } from '../../state/agent-store';
import { useChatStore } from '../../state/chat-store';
import { useProjectStore } from '../../state/project-store';
import { useWorkspaceStore } from '../../state/workspace-store';
import { useSelectionStore } from '../../state/selection-store';
import { api } from '../../services/api';
import { projectWsClient } from '../../services/project-ws';
import { QueuedPrompt } from '../../types/chat';
import { logEntryFromEvent } from '../../types/logs';

export interface StylePresetOption {
  id: string;
  label: string;
  tagline: string;
}

export const STYLE_PRESETS: StylePresetOption[] = [
  { id: 'auto', label: 'Auto', tagline: 'Smart domain-tailored aesthetic' },
  { id: 'editorial', label: 'Editorial', tagline: 'Typographic hierarchy & refined monochrome' },
  { id: 'brutalist', label: 'Brutalist', tagline: 'Bold borders, sharp shadows & stark layouts' },
  { id: 'minimal', label: 'Minimal', tagline: 'Ultra-clean whitespace & hairline clarity' },
  { id: 'technical', label: 'Technical', tagline: 'Developer dark theme & monospace metrics' },
  { id: 'luxury', label: 'Luxury', tagline: 'Warm alabaster, bronze & serif typography' },
  { id: 'experimental', label: 'Experimental', tagline: 'Dynamic aurora gradients & luminous glass' },
  { id: 'custom', label: 'Custom', tagline: 'User-defined :root tokens & Refero styling' },
];

export const STARTER_TEMPLATES = [
  {
    title: 'SaaS Landing Page',
    prompt: 'Build a modern SaaS landing page with navigation bar, high-impact hero, interactive feature highlights, social proof testimonials, and pricing comparison table.',
  },
  {
    title: 'Editorial Agency Portfolio',
    prompt: 'Build an agency portfolio website with a split hero showcase, selected client work gallery, service capabilities, case study highlights, and contact section.',
  },
  {
    title: 'E-Commerce Showcase',
    prompt: 'Build a responsive e-commerce storefront with category navigation, product cards, working cart state, customer reviews, and a cart review screen. Do not claim payment or checkout integration.',
  },
  {
    title: 'Developer Platform & Tools',
    prompt: 'Build an engineering platform website with live code block previews, system telemetry stats, API architecture breakdown, and interactive documentation tabs.',
  },
  { title: 'Restaurant', prompt: 'Build a restaurant website with a menu, story, opening hours, location, and reservation request form.' },
  { title: 'Museum Exhibition', prompt: 'Build an editorial museum exhibition website with artwork stories, event dates, visitor information, and an accessible gallery.' },
  { title: 'Community Event', prompt: 'Build a community event website with agenda, speakers, venue details, accessibility information, and registration interest form.' },
  { title: 'Education', prompt: 'Build a course website with curriculum, instructor profiles, learning outcomes, FAQs, and an inquiry form.' },
];

interface ChatComposerProps {
  initialPrompt?: string;
}

export const ChatComposer: React.FC<ChatComposerProps> = ({ initialPrompt }) => {
  const [promptText, setPromptText] = useState(initialPrompt || '');
  const [generationMode, setGenerationMode] = useState<'component' | 'site'>('site');
  const [stylePreset, setStylePreset] = useState<string>('auto');
  const [showStyleMenu, setShowStyleMenu] = useState(false);
  const [showTemplateMenu, setShowTemplateMenu] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  // Who writes a site's code: the design kit (fast) or the model itself (native).
  const [siteWriter, setSiteWriter] = useState<'kit' | 'native'>(() => {
    try {
      return localStorage.getItem('slm_site_writer') === 'native' ? 'native' : 'kit';
    } catch (_) {
      return 'kit';
    }
  });
  const chooseSiteWriter = (value: 'kit' | 'native') => {
    setSiteWriter(value);
    try { localStorage.setItem('slm_site_writer', value); } catch (_) {}
  };
  const [maxTurns, setMaxTurns] = useState(6);
  const [isCustomTurns, setIsCustomTurns] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const styleMenuRef = useRef<HTMLDivElement>(null);
  const templateMenuRef = useRef<HTMLDivElement>(null);

  const { status, setStatus, setActiveTaskId, startTimer, stopTimer, applyEvent, setQueueDepth } =
    useAgentStore();
  const {
    addMessage,
    addQueuedPrompt,
    promoteQueuedPrompt,
    updateQueuedPrompt,
    removeQueuedPrompt,
    clearQueuedPrompts,
  } = useChatStore();
  const { currentProjectId, setCurrentProjectId, addProject, updateProject } = useProjectStore();
  const { setFiles, reloadPreview, addLog, setWorkspaceOpen } = useWorkspaceStore();
  const { selectedElement, selected3DObject, clearSelection } = useSelectionStore();

  const isWorking =
    status === 'generating' || status === 'planning' || status === 'typechecking' || status === 'repairing';

  useEffect(() => {
    if (initialPrompt) {
      setPromptText(initialPrompt);
      if (textareaRef.current) {
        textareaRef.current.focus();
      }
    }
  }, [initialPrompt]);

  // "Edit with AI" in the inspector hands focus to the composer.
  useEffect(() => {
    const focus = () => textareaRef.current?.focus();
    window.addEventListener('workbench:focus-composer', focus);
    return () => window.removeEventListener('workbench:focus-composer', focus);
  }, []);

  // Dynamically resize chat box height as text lines are entered (scroll line appears ONLY after 6-7 lines)
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;

    // Reset height to auto to accurately read the current scrollHeight
    el.style.height = 'auto';

    // 6-7 lines threshold: text-sm (14px) with leading-relaxed is ~24px per line.
    // 7 lines = ~168px
    const singleLineHeight = 24;
    const maxLines = 7;
    const maxHeight = singleLineHeight * maxLines;

    if (el.scrollHeight > maxHeight) {
      el.style.height = `${maxHeight}px`;
      el.style.overflowY = 'auto';
    } else {
      el.style.height = `${Math.max(singleLineHeight, el.scrollHeight)}px`;
      el.style.overflowY = 'hidden';
    }
  }, [promptText]);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (styleMenuRef.current && !styleMenuRef.current.contains(e.target as Node)) {
        setShowStyleMenu(false);
      }
      if (templateMenuRef.current && !templateMenuRef.current.contains(e.target as Node)) {
        setShowTemplateMenu(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setPromptText(e.target.value);
  };

  const startStreamingTask = (taskId: string, targetProjectId?: string) => {
    setActiveTaskId(taskId);
    setStatus('generating');
    startTimer();

    projectWsClient.streamTask(
      taskId,
      {
        onEvent: (event) => {
          applyEvent(event);
          if (event.type === 'task.acknowledged' || event.type === 'task.started') {
            const realTaskId = event.task_id || event.data?.taskId || event.data?.task_id;
            if (realTaskId) {
              setActiveTaskId(realTaskId);
            }
          }
          const logEntry = logEntryFromEvent(event as any);
          if (logEntry) addLog(logEntry, targetProjectId || currentProjectId || undefined);

          // Authoritative backend queue state synchronization
          if (event.type === 'task.queued' || event.type === 'prompt.queued') {
            const qTaskId = (event as any).task_id || event.data?.taskId || event.data?.task_id || (event as any).taskId;
            const qPos = event.data?.position ?? event.data?.queue_position ?? (event as any).position;
            const queue = useChatStore.getState().queuedPrompts;
            const match = (qTaskId ? queue.find((q) => q.taskId === qTaskId) : null) || queue.find((q) => !q.taskId);
            if (match) {
              updateQueuedPrompt(match.id, {
                taskId: qTaskId || match.taskId,
                queuePosition: typeof qPos === 'number' ? qPos : match.queuePosition,
              });
            }
            if (typeof qPos === 'number') {
              setQueueDepth(qPos);
            }
          } else if (event.type === 'task.started') {
            const startedTaskId = (event as any).task_id || event.data?.taskId || event.data?.task_id || (event as any).taskId;
            const queue = useChatStore.getState().queuedPrompts;
            const match = (startedTaskId ? queue.find((q) => q.taskId === startedTaskId) : null) || queue[0];
            if (match) {
              promoteQueuedPrompt(match.id, startedTaskId || match.taskId || `task-${Date.now()}`);
            }
            if (startedTaskId) {
              setActiveTaskId(startedTaskId);
            }
            setStatus('generating');
            startTimer();
            setQueueDepth(Math.max(0, queue.length - 1));
          } else if (event.type === 'task.cancelled') {
            stopTimer();
            setStatus('idle');
            clearQueuedPrompts();
          }
        },
        onResult: (result) => {
          if (result.validation) useAgentStore.getState().applyEvent({ type: 'build.result', timestamp: Date.now(), data: result.validation });
          if (result.status === 'blocked' || result.blocked_sections?.length) setStatus('failed');
          if (result.files) {
            setFiles(result.files);
          }
          const folderName = result.folder_name || (result.file_path ? result.file_path.replace(/^generated_components\//, '').replace(/\/$/, '') : undefined);
          const filePath = result.file_path || (result.folder_name ? `generated_components/${result.folder_name}/` : undefined);
          const fullPath = result.full_path;

          if (result.session_id) {
            setCurrentProjectId(result.session_id);
            updateProject(result.session_id, {
              files: result.files,
              latestVisualScore: result.visual_score ?? result.heuristic_score,
              turnCount: result.turn_count || 1,
              filePath,
              folderName,
              fullPath,
            });
          }
          const currentVal = result.validation || useAgentStore.getState().validationResult;
          addMessage({
            id: `summary-${Date.now()}`,
            role: 'summary',
            timestamp: Date.now(),
            summary: {
              validation: currentVal,
              filesCreated: result.files_created || Object.keys(result.files || {}),
              completionStatus: result.completion_status,
              blockedSections: result.blocked_diagnostics || result.blocked_sections,
              sectionCompletion: result.section_completion,
              finalPassed: result.final_passed,
              generationScorecards: result.generation_scorecards,
              strategy: result.strategy,
              nativeCodeSections: result.native_code_sections,
              nativeCodeFallbacks: result.native_code_fallbacks,
              filesModified: result.files_modified || [],
              filePath,
              folderName,
              fullPath,
              visualScore: result.visual_score ?? result.heuristic_score,
              code_passed: currentVal?.code_passed ?? currentVal?.codePassed,
              build_passed: currentVal?.build_passed ?? currentVal?.buildPassed,
              contract_passed: currentVal?.contract_passed ?? currentVal?.contractPassed,
              accessibility_passed: currentVal?.accessibility_passed ?? currentVal?.accessibilityPassed,
              contractStatus: currentVal?.contract_status,
              accessibilityStatus: currentVal?.accessibility_status,
              runtime_passed: currentVal?.runtime_passed ?? currentVal?.runtimePassed,
              preview_running: currentVal?.preview_running ?? currentVal?.previewRunning,
              passed: result.final_passed ?? currentVal?.passed,
              validationStatus: result.validation_status ?? result.validationStatus ?? currentVal?.validationStatus,
            },
          });
          reloadPreview();
          if (generationMode === 'site' || result.mode === 'site') setWorkspaceOpen(true);
        },
        onDone: () => {
          stopTimer();
          // Backend owns queue promotion: only flip status to idle if backend queue is empty
          const remainingQueue = useChatStore.getState().queuedPrompts;
          if (remainingQueue.length === 0) {
            if (useAgentStore.getState().status !== 'failed') setStatus('idle');
          }
        },
        onError: (err) => {
          console.error('[Stream Error]:', err);
          addMessage({
            id: `error-${Date.now()}`,
            role: 'error',
            timestamp: Date.now(),
            content: err.message || 'Stream connection error',
          });
          stopTimer();
          setStatus('failed');
        },
      },
      targetProjectId || currentProjectId || undefined
    );
  };

  const handleSend = async () => {
    let text = promptText.trim();
    if (!text) return;

    // Attach explicit selection context if available
    if (selectedElement) {
      const where = selectedElement.componentHint ? ` in section #${selectedElement.componentHint}` : ` at ${selectedElement.selector}`;
      const quote = selectedElement.textContent ? ` with text "${selectedElement.textContent.slice(0, 120)}"` : '';
      text = `[Context: <${selectedElement.tagName.toLowerCase()}>${where}${quote}]\n${text}`;
      clearSelection();
    } else if (selected3DObject) {
      text = `[Context 3D: ${selected3DObject.name} (${selected3DObject.uuid})]\n${text}`;
      clearSelection();
    }

    setPromptText('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }

    if (isWorking) {
      // ── QUEUE FOLLOW-UP ──
      const promptId = `queued-${Date.now()}`;
      const queuedItem: QueuedPrompt = {
        id: promptId,
        projectId: currentProjectId || 'new-session',
        content: text,
        createdAt: Date.now(),
        status: 'queued',
      };

      addQueuedPrompt(queuedItem);

      const stylePayload = stylePreset !== 'auto' ? stylePreset : undefined;

      try {
        if (projectWsClient.isConnected() && currentProjectId) {
          const sent = projectWsClient.sendPromptQueue(text, {
            mode: generationMode,
            max_turns: maxTurns,
            stylePreset: stylePayload,
            style_preset: stylePayload,
            ...(generationMode === 'site' ? { strategy: siteWriter } : {}),
          });
          if (!sent) {
            throw new Error('WebSocket failed to send prompt.queue');
          }
        } else {
          const res = await api.generate({
            prompt: text,
            session_id: currentProjectId || undefined,
            mode: generationMode,
            max_turns: maxTurns,
            stylePreset: stylePayload,
            style_preset: stylePayload,
            ...(generationMode === 'site' ? { strategy: siteWriter } : {}),
          });

          updateQueuedPrompt(promptId, {
            taskId: res.task_id || (res as any).taskId,
            queuePosition: res.queue_position ?? (res as any).position,
          });
          if (typeof (res.queue_position ?? (res as any).position) === 'number') {
            setQueueDepth(res.queue_position ?? (res as any).position);
          }
        }
      } catch (err: any) {
        console.error('Failed to queue generation:', err);
        // Clean up failed submission immediately so no card is left permanently queued
        removeQueuedPrompt(promptId);
        addMessage({
          id: `error-${Date.now()}`,
          role: 'error',
          timestamp: Date.now(),
          content: err.message || 'Failed to submit prompt to queue',
        });
      }
    } else {
      // ── RUN DIRECTLY ──
      const userMsgId = `user-${Date.now()}`;
      addMessage({
        id: userMsgId,
        role: 'user',
        content: text,
        timestamp: Date.now(),
      });

      const stylePayload = stylePreset !== 'auto' ? stylePreset : undefined;

      try {
        if (projectWsClient.isConnected() && currentProjectId) {
          // Authoritative WebSocket path: dispatch task.start directly over /ws/projects/:projectId
          startStreamingTask('pending', currentProjectId);
          const sent = projectWsClient.sendTaskStart(text, generationMode, {
            max_turns: maxTurns,
            stylePreset: stylePayload,
            style_preset: stylePayload,
            ...(generationMode === 'site' ? { strategy: siteWriter } : {}),
          });
          if (!sent) {
            throw new Error('Failed to dispatch task.start over WebSocket');
          }
        } else {
          const res = await api.generate({
            prompt: text,
            session_id: currentProjectId || undefined,
            mode: generationMode,
            max_turns: maxTurns,
            stylePreset: stylePayload,
            style_preset: stylePayload,
            ...(generationMode === 'site' ? { strategy: siteWriter } : {}),
          });

          if (!currentProjectId && res.session_id) {
            setCurrentProjectId(res.session_id);
            addProject({
              id: res.session_id,
              title: text.slice(0, 32),
              createdAt: Date.now(),
              updatedAt: Date.now(),
              turnCount: 1,
              mode: generationMode,
            });
          }

          startStreamingTask(res.task_id, res.session_id || currentProjectId || undefined);
        }
      } catch (err: any) {
        console.error('Generation failed:', err);
        addMessage({
          id: `error-${Date.now()}`,
          role: 'error',
          timestamp: Date.now(),
          content: err.message || 'Generation request failed',
        });
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter') {
      if (e.shiftKey) return;
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="max-w-3xl mx-auto w-full px-4 pb-4 select-none">
      {/* Explicit context chip (ONLY when an element or 3D object was explicitly selected) */}
      {(selectedElement || selected3DObject) && (
        <div className="flex items-center gap-2 mb-2">
          {selectedElement && (
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 text-xs font-mono">
              <Crosshair size={12} />
              <span>&lt;{selectedElement.tagName.toLowerCase()}&gt; {selectedElement.componentHint || selectedElement.selector}</span>
              <button id="composer-context-chip-remove" onClick={clearSelection} className="ml-1 hover:text-white cursor-pointer" title="Remove context chip">
                <X size={12} />
              </button>
            </div>
          )}
          {selected3DObject && (
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-amber-500/10 text-amber-300 border border-amber-500/20 text-xs font-mono">
              <Box size={12} />
              <span>3D: {selected3DObject.name}</span>
              <button id="composer-context-chip-remove" onClick={clearSelection} className="ml-1 hover:text-white cursor-pointer" title="Remove context chip">
                <X size={12} />
              </button>
            </div>
          )}
        </div>
      )}

      {/* Advanced Settings Drawer/Popover */}
      {showAdvanced && (
        <div className="mb-2 p-3 bg-[#1e1e1e] rounded-xl border border-white/[0.08] text-xs space-y-2 text-slate-300 shadow-xl">
          <div className="flex items-center justify-between font-medium">
            <span>Engineering Controls</span>
            <button id="composer-advanced-close-btn" onClick={() => setShowAdvanced(false)} className="text-slate-400 hover:text-white cursor-pointer">
              <X size={13} />
            </button>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 font-mono text-[11px]">
            <div>
              <span className="text-slate-500 block mb-1">Max Turns:</span>
              {isCustomTurns ? (
                <div className="flex items-center gap-1.5">
                  <input
                    id="composer-turns-input"
                    type="number"
                    min={1}
                    max={100}
                    value={maxTurns}
                    onChange={(e) => setMaxTurns(Math.max(1, Math.min(100, Number(e.target.value) || 1)))}
                    className="w-full bg-[#141414] text-slate-200 px-2 py-1 rounded-lg border border-white/[0.04] focus:outline-none text-xs font-mono"
                    placeholder="e.g. 15"
                    autoFocus
                  />
                  <button
                    id="composer-turns-presets-btn"
                    type="button"
                    onClick={() => setIsCustomTurns(false)}
                    className="px-2 py-1 text-[10px] rounded bg-white/[0.08] hover:bg-white/[0.12] text-slate-300 shrink-0 transition-colors cursor-pointer"
                    title="Choose from presets"
                  >
                    Presets
                  </button>
                </div>
              ) : (
                <select
                  id="composer-turns-select"
                  value={maxTurns}
                  onChange={(e) => {
                    const val = Number(e.target.value);
                    if (val === -1) {
                      setIsCustomTurns(true);
                    } else {
                      setMaxTurns(val);
                    }
                  }}
                  className="w-full bg-[#141414] text-slate-200 px-2 py-1 rounded-lg border border-white/[0.04] focus:outline-none cursor-pointer"
                >
                  <option value={4}>4 turns (Quick)</option>
                  <option value={6}>6 turns (Default)</option>
                  <option value={8}>8 turns</option>
                  <option value={10}>10 turns</option>
                  <option value={12}>12 turns</option>
                  <option value={14}>14 turns</option>
                  <option value={16}>16 turns</option>
                  <option value={20}>20 turns (Deep)</option>
                  <option value={25}>25 turns</option>
                  <option value={30}>30 turns</option>
                  <option value={40}>40 turns</option>
                  <option value={50}>50 turns (Maximum)</option>
                  <option value={-1}>Custom...</option>
                </select>
              )}
            </div>
            <div className="col-span-2 sm:col-span-1">
              <span className="text-slate-500 block mb-1">Site code written by:</span>
              <select
                id="composer-site-writer-select"
                value={siteWriter}
                onChange={(e) => chooseSiteWriter(e.target.value === 'native' ? 'native' : 'kit')}
                className="w-full bg-[#141414] text-slate-200 px-2 py-1 rounded-lg border border-white/[0.04] focus:outline-none cursor-pointer"
                title="Design kit: the model writes the copy and the kit writes the code (fast). Model: the model writes each section's code too (slower; uses the fine-tuned adapter when loaded)."
              >
                <option value="kit">Design kit (fast)</option>
                <option value="native">The model (native)</option>
              </select>
            </div>
            <div className="col-span-2 sm:col-span-1">
              <span className="text-slate-500 block mb-1">Style Preset:</span>
              <select
                id="composer-advanced-style-select"
                value={stylePreset}
                onChange={(e) => setStylePreset(e.target.value)}
                className="w-full bg-[#141414] text-slate-200 px-2 py-1 rounded-lg border border-white/[0.04] focus:outline-none cursor-pointer"
              >
                {STYLE_PRESETS.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.label} {p.id === 'auto' ? '(Auto Heuristic)' : ''}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>
      )}

      {/* Clean ChatGPT-Style Composer Box */}
      <div className="relative flex flex-col bg-[#212121] rounded-2xl border border-white/[0.08] focus-within:border-white/[0.20] transition-colors p-3 shadow-lg">
        {/* Structured style preset active indicator chip */}
        {stylePreset !== 'auto' && (
          <div className="flex items-center gap-1.5 mb-2 px-2.5 py-1 rounded-lg bg-amber-500/10 border border-amber-500/20 text-xs text-amber-200 w-fit">
            <Palette size={12} className="text-amber-400" />
            <span>Style preset: <strong className="text-white font-medium">{STYLE_PRESETS.find(p => p.id === stylePreset)?.label || stylePreset}</strong></span>
            <button
              id="composer-style-reset-chip-btn"
              type="button"
              onClick={() => setStylePreset('auto')}
              className="p-0.5 ml-1 rounded hover:bg-amber-500/20 text-amber-400 hover:text-amber-200 transition-colors cursor-pointer"
              title="Reset style preset to Auto"
            >
              <X size={11} />
            </button>
          </div>
        )}

        <textarea
          id="composer-textarea"
          ref={textareaRef}
          value={promptText}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          placeholder="Ask SiteAgent to build, change, fix, or explain..."
          rows={1}
          className="w-full bg-transparent text-slate-100 text-sm placeholder:text-slate-500 resize-none outline-none leading-relaxed select-text"
        />

        {/* Bottom toolbar */}
        <div className="flex flex-wrap items-center justify-between gap-2 mt-3 pt-1">
          {/* Quick options (wrap instead of overlapping the send controls in a narrow chat column) */}
          <div className="flex flex-wrap items-center gap-1 text-slate-400 min-w-0">
            <div role="group" aria-label="Generation mode" className="flex gap-1 bg-[#141414] p-1 rounded-lg border border-white/[0.04]">
              <button id="composer-mode-site-btn" type="button" aria-pressed={generationMode === 'site'} onClick={() => setGenerationMode('site')}
                className={`px-1.5 sm:px-2 py-1 rounded text-[11px] sm:text-xs whitespace-nowrap cursor-pointer ${generationMode === 'site' ? 'bg-white/[0.12] text-white' : 'text-slate-400'}`}>Full Site</button>
              <button id="composer-mode-component-btn" type="button" aria-pressed={generationMode === 'component'} onClick={() => setGenerationMode('component')}
                className={`px-1.5 sm:px-2 py-1 rounded text-[11px] sm:text-xs whitespace-nowrap cursor-pointer ${generationMode === 'component' ? 'bg-white/[0.12] text-white' : 'text-slate-400'}`}>Component</button>
            </div>
            <button
              id="composer-advanced-toggle-btn"
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="hidden sm:inline-flex p-1.5 rounded-lg hover:bg-white/[0.06] hover:text-slate-200 transition-colors cursor-pointer"
              title="Advanced Controls"
            >
              <SlidersHorizontal size={14} />
            </button>

            {/* Structured Style Selector Popover */}
            <div className="relative" ref={styleMenuRef}>
              <button
                id="composer-style-selector-btn"
                type="button"
                onClick={() => {
                  setShowStyleMenu(!showStyleMenu);
                  setShowTemplateMenu(false);
                }}
                className={`flex items-center gap-1 px-1.5 sm:px-2.5 py-1 rounded-lg text-xs whitespace-nowrap transition-colors cursor-pointer ${
                  stylePreset !== 'auto'
                    ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                    : 'hover:bg-white/[0.06] text-slate-400 hover:text-slate-200'
                }`}
                title="Select structured style preset (sent as metadata)"
              >
                <Palette size={13} />
                <span><span className="hidden sm:inline">Style: </span>{STYLE_PRESETS.find((p) => p.id === stylePreset)?.label || 'Auto'}</span>
                <ChevronDown size={11} className={showStyleMenu ? 'rotate-180 transition-transform' : 'transition-transform'} />
              </button>

              {showStyleMenu && (
                <div className="absolute left-0 bottom-full mb-2 w-72 bg-[#1c1c1f] border border-white/[0.12] rounded-xl shadow-2xl p-1.5 z-50 text-xs backdrop-blur-md">
                  <div className="px-2.5 py-1.5 font-medium text-slate-400 text-[11px] border-b border-white/[0.06] flex items-center justify-between">
                    <span>Structured Style Preset</span>
                    <span className="text-[10px] text-slate-500">Metadata Payload</span>
                  </div>
                  <div className="max-h-64 overflow-y-auto py-1 space-y-0.5">
                    {STYLE_PRESETS.map((p) => {
                      const isSelected = stylePreset === p.id;
                      return (
                        <button
                          key={p.id}
                          id={`composer-style-option-${p.id}`}
                          type="button"
                          onClick={() => {
                            setStylePreset(p.id);
                            setShowStyleMenu(false);
                          }}
                          className={`w-full flex items-start gap-2 px-2.5 py-2 rounded-lg text-left transition-colors cursor-pointer ${
                            isSelected ? 'bg-white/[0.10] text-white' : 'hover:bg-white/[0.05] text-slate-300'
                          }`}
                        >
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-1.5">
                              <span className="font-medium text-xs text-white">{p.label}</span>
                              {p.id === 'auto' && (
                                <span className="text-[10px] px-1.5 py-0.2 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">Default</span>
                              )}
                            </div>
                            <div className="text-[10px] text-slate-400 truncate mt-0.5">{p.tagline}</div>
                          </div>
                          {isSelected && <Check size={13} className="text-amber-400 mt-0.5 shrink-0" />}
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>

            {/* Unbiased Starter Templates Popover */}
            <div className="relative" ref={templateMenuRef}>
              <button
                id="composer-templates-btn"
                type="button"
                onClick={() => {
                  setShowTemplateMenu(!showTemplateMenu);
                  setShowStyleMenu(false);
                }}
                className="flex items-center gap-1 px-1.5 sm:px-2.5 py-1 rounded-lg hover:bg-white/[0.06] hover:text-slate-200 text-xs transition-colors cursor-pointer"
                title="Starter templates"
              >
                <LayoutTemplate size={13} />
                <span className="hidden sm:inline">Templates</span>
                <ChevronDown size={11} className={showTemplateMenu ? 'rotate-180 transition-transform' : 'transition-transform'} />
              </button>

              {showTemplateMenu && (
                <div className="absolute left-0 bottom-full mb-2 w-80 bg-[#1c1c1f] border border-white/[0.12] rounded-xl shadow-2xl p-1.5 z-50 text-xs backdrop-blur-md">
                  <div className="px-2.5 py-1.5 font-medium text-slate-400 text-[11px] border-b border-white/[0.06] flex items-center justify-between">
                    <span>Clean Starter Templates</span>
                    <span className="text-[10px] text-slate-500">Unbiased</span>
                  </div>
                  <div className="py-1 space-y-0.5">
                    {STARTER_TEMPLATES.map((t, idx) => (
                      <button
                        key={t.title}
                        id={`composer-template-item-${idx}`}
                        type="button"
                        onClick={() => {
                          setPromptText(t.prompt);
                          setShowTemplateMenu(false);
                          if (textareaRef.current) textareaRef.current.focus();
                        }}
                        className="w-full flex flex-col items-start px-2.5 py-2 rounded-lg text-left hover:bg-white/[0.05] text-slate-300 transition-colors cursor-pointer"
                      >
                        <span className="font-medium text-xs text-white">{t.title}</span>
                        <span className="text-[10px] text-slate-400 line-clamp-2 mt-0.5">{t.prompt}</span>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Send / Queue button */}
          <div className="flex items-center justify-end gap-2 ml-auto">
            {isWorking ? (
              <button
                id="composer-queue-btn"
                onClick={handleSend}
                disabled={!promptText.trim()}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/30 font-medium text-xs transition-all disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer"
                title="Queue follow-up"
              >
                <Clock size={12} className="animate-spin-slow" />
                <span>Queue</span>
              </button>
            ) : (
              <>
                <button
                  id="composer-queue-btn"
                  onClick={handleSend}
                  disabled={!promptText.trim()}
                  className="flex items-center gap-1 px-2.5 py-1.5 rounded-full bg-white/[0.04] hover:bg-white/[0.08] text-slate-400 hover:text-slate-200 border border-white/[0.06] font-medium text-xs transition-all disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer"
                  title="Add prompt to queue"
                >
                  <Clock size={12} />
                  <span>Queue</span>
                </button>
                <button
                  id="composer-send-btn"
                  onClick={handleSend}
                  disabled={!promptText.trim()}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-semibold text-xs transition-all disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer shadow-lg shadow-emerald-500/20"
                >
                  <span>Send</span>
                  <Send size={12} />
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
