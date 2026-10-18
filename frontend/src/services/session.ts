import { useProjectStore } from '../state/project-store';
import { useWorkspaceStore } from '../state/workspace-store';
import { useAgentStore } from '../state/agent-store';
import { useChatStore } from '../state/chat-store';
import { useSelectionStore } from '../state/selection-store';
import { projectWsClient } from './project-ws';
import { api } from './api';
import { logEntryFromEvent } from '../types/logs';

/**
 * Safe entry point for requesting a new project.
 * If an active GPU generation or task is currently running, opens the conflict resolution modal.
 * If idle, executes startNewProject() immediately.
 */
export function requestNewProject() {
  const { status, activeTaskId } = useAgentStore.getState();
  const isWorking =
    status === 'generating' ||
    status === 'planning' ||
    status === 'typechecking' ||
    status === 'repairing' ||
    Boolean(activeTaskId);

  if (isWorking) {
    useWorkspaceStore.getState().openActiveTaskModal();
  } else {
    startNewProject();
  }
}

/**
 * First-class state transition for starting a new project / chat.
 * Completely resets project and task state while preserving global system state (model readiness, GPU).
 */
export function startNewProject() {
  // 1. Stop listening to previous task/session
  projectWsClient.disconnect();

  // 2. Clear project selection
  useProjectStore.getState().startNewProject();

  // 3. Reset workspace (files, drafts, preview, diffs, close workspace drawer)
  useWorkspaceStore.getState().clearWorkspace();
  useWorkspaceStore.getState().clearLogs();

  // 4. Reset task metrics, visual score, repair attempts, and activities
  useAgentStore.getState().resetAgent();

  // 5. Clear 2D DOM and 3D selection
  useSelectionStore.getState().clearSelection();

  // 6. Clear conversation view and queued prompts
  useChatStore.getState().clearMessages();
  useChatStore.getState().clearQueuedPrompts();
}

/**
 * Loads a project by ID, opening its tab and hydrating workspace files, conversation history, and preview.
 */
export async function loadProject(id: string) {
  // 1. Stop any active streaming
  projectWsClient.disconnect();

  // 2. Open / activate tab in store
  useProjectStore.getState().openProjectTab(id);

  // 3. Reset selection, agent state, and queued prompts for the new project context
  useSelectionStore.getState().clearSelection();
  useAgentStore.getState().resetAgent();
  useChatStore.getState().clearQueuedPrompts();

  // 4. Switch to project-scoped logs and reset diff selection
  useWorkspaceStore.getState().setLogsForProject(id);
  useWorkspaceStore.getState().setDiff('', '', 0, '');

  // Restore the persisted log history for this project (best effort).
  api.getProjectLogs(id).then((entries) => {
    const mapped = entries.map((e) => logEntryFromEvent(e)).filter((e): e is NonNullable<typeof e> => Boolean(e));
    if (mapped.length) useWorkspaceStore.getState().hydrateLogs(id, mapped);
  }).catch(() => {});

  try {
    const details = await api.getProject(id);
    const projData = details.project || details.session || details;
    if (projData.files) {
      useWorkspaceStore.getState().setFiles(projData.files);
    }
    useProjectStore.getState().updateProject(id, { uses3D: Boolean(projData.uses_3d ?? projData.uses3D) });
    const turns = Array.isArray(projData.turns) ? projData.turns : (Array.isArray(projData.history) ? projData.history : []);
    if (turns.length) {
      const restored: any[] = [];
      turns.forEach((entry: any, index: number) => {
        const turn = {
          ...entry,
          user_prompt: entry.user_prompt || entry.prompt || (entry.role === 'user' ? entry.content : undefined),
          files_modified: entry.files_modified || entry.files_touched,
        };
        if (turn.user_prompt || turn.prompt) {
          restored.push({
            id: `user-${turn.turn_id || index}`,
            role: 'user',
            content: turn.user_prompt || turn.prompt,
            timestamp: Date.now() - (turns.length - index) * 60000,
            turnId: turn.turn_id || index + 1,
          });
        }
        if (turn.summary || turn.files_modified) {
          restored.push({
            id: `summary-${turn.turn_id || index}`,
            role: 'summary',
            timestamp: Date.now() - (turns.length - index) * 60000 + 1000,
            summary: {
              validation: turn.validation,
              filesCreated: turn.files_created || [],
              completionStatus: turn.completion_status,
              blockedSections: turn.blocked_diagnostics || turn.blocked_sections,
              sectionCompletion: turn.section_completion,
              finalPassed: turn.final_passed,
              generationScorecards: turn.generation_scorecards,
              strategy: turn.strategy,
              nativeCodeSections: turn.native_code_sections,
              nativeCodeFallbacks: turn.native_code_fallbacks,
              filesModified: turn.files_modified || [],
              filePath: turn.file_path || projData.file_path,
              folderName: turn.folder_name || projData.folder_name || (turn.file_path || projData.file_path ? (turn.file_path || projData.file_path).replace(/^generated_components\//, '').replace(/\/$/, '') : undefined),
              fullPath: turn.full_path || projData.full_path,
              visualScore: turn.visual_score,
              code_passed: turn.validation?.code_passed ?? turn.validation?.codePassed,
              build_passed: turn.validation?.build_passed ?? turn.validation?.buildPassed,
              contract_passed: turn.validation?.contract_passed ?? turn.validation?.contractPassed,
              accessibility_passed: turn.validation?.accessibility_passed ?? turn.validation?.accessibilityPassed,
              contractStatus: turn.validation?.contract_status,
              accessibilityStatus: turn.validation?.accessibility_status,
              runtime_passed: turn.validation?.runtime_passed ?? turn.validation?.runtimePassed,
              preview_running: turn.validation?.preview_running ?? turn.validation?.previewRunning,
              passed: turn.final_passed ?? turn.validation?.passed,
              validationStatus: turn.validation_status ?? turn.validationStatus ?? turn.validation?.validationStatus,
            },
          });
        }
      });
      useChatStore.getState().setMessages(restored);
    } else {
      useChatStore.getState().clearMessages();
    }

    const lastResult = [...turns].reverse().find((turn: any) => turn.validation);
    const validation = projData.last_validation || lastResult?.validation;
    if (validation) useAgentStore.getState().applyEvent({ type: 'build.result', timestamp: Date.now(), data: validation });
    if (lastResult?.completion_status === 'BLOCKED' || lastResult?.blocked_sections?.length) {
      useAgentStore.getState().setStatus('failed', 'Generation blocked; inspect the saved result for section details.');
    }

    // Hydrate context tokens & max context tokens
    const ctxTokens = projData.context_tokens ?? projData.contextTokens ?? 0;
    const maxCtxTokens = projData.max_context_tokens ?? projData.maxContextTokens ?? 8192;
    useAgentStore.getState().setSystemStatus({
      contextTokens: ctxTokens,
      maxContextTokens: maxCtxTokens,
    });

    // Hydrate backend-authoritative queued prompts on load/refresh
    const queuedPrompts = projData.queued_prompts || [];
    if (Array.isArray(queuedPrompts) && queuedPrompts.length > 0) {
      queuedPrompts.forEach((qp: any, idx: number) => {
        const text = typeof qp === 'string' ? qp : (qp.prompt || qp.content || '');
        const taskId = typeof qp === 'object' ? (qp.taskId || qp.task_id) : undefined;
        const position = typeof qp === 'object' ? (qp.position || qp.queue_position || idx + 1) : idx + 1;
        const qId = taskId || `queued-${id}-${idx}-${Date.now()}`;
        useChatStore.getState().addQueuedPrompt({
          id: qId,
          projectId: id,
          content: text,
          createdAt: Date.now(),
          status: 'queued',
          taskId,
          queuePosition: position,
        });
      });
      useAgentStore.getState().setQueueDepth(queuedPrompts.length);
    }

    // Reconnect to authoritative project channel so events stream to UI after refresh/tab switch
    projectWsClient.connect(
      id,
      {
        onEvent: (event) => {
          useAgentStore.getState().applyEvent(event);
          const logEntry = logEntryFromEvent(event as any);
          if (logEntry) useWorkspaceStore.getState().addLog(logEntry, id);
          if (event.type === 'task.queued' || event.type === 'prompt.queued') {
            const qTaskId = (event as any).task_id || event.data?.taskId || event.data?.task_id || (event as any).taskId;
            const qPos = event.data?.position ?? event.data?.queue_position;
            const queue = useChatStore.getState().queuedPrompts;
            const match = (qTaskId ? queue.find((q) => q.taskId === qTaskId) : null) || queue.find((q) => !q.taskId);
            if (match) {
              useChatStore.getState().updateQueuedPrompt(match.id, {
                taskId: qTaskId || match.taskId,
                queuePosition: typeof qPos === 'number' ? qPos : match.queuePosition,
              });
            }
            if (typeof qPos === 'number') {
              useAgentStore.getState().setQueueDepth(qPos);
            }
          } else if (event.type === 'task.started') {
            const startedTaskId = (event as any).task_id || event.data?.taskId || event.data?.task_id || (event as any).taskId;
            const queue = useChatStore.getState().queuedPrompts;
            const match = (startedTaskId ? queue.find((q) => q.taskId === startedTaskId) : null) || queue[0];
            if (match) {
              useChatStore.getState().promoteQueuedPrompt(match.id, startedTaskId || match.taskId || `task-${Date.now()}`);
            }
            if (startedTaskId) {
              useAgentStore.getState().setActiveTaskId(startedTaskId);
            }
            useAgentStore.getState().setStatus('generating');
            useAgentStore.getState().startTimer();
            useAgentStore.getState().setQueueDepth(Math.max(0, queue.length - 1));
          } else if (event.type === 'task.cancelled') {
            useAgentStore.getState().stopTimer();
            useAgentStore.getState().setStatus('idle');
            useChatStore.getState().clearQueuedPrompts();
          }
        },
        onResult: (result) => {
          if (result.validation) useAgentStore.getState().applyEvent({ type: 'build.result', timestamp: Date.now(), data: result.validation });
          if (result.files) {
            api.getProject(id).then((fresh) => {
              const data = fresh.project || fresh.session || fresh;
              useWorkspaceStore.getState().setFiles(data.files || result.files);
            }).catch(() => useWorkspaceStore.getState().setFiles(result.files));
          }
          if (result.status === 'blocked' || result.blocked_sections?.length) {
            useAgentStore.getState().setStatus('failed');
          }
          useWorkspaceStore.getState().reloadPreview();
        },
        onDone: () => {
          useAgentStore.getState().stopTimer();
          if (useChatStore.getState().queuedPrompts.length === 0) {
            if (useAgentStore.getState().status !== 'failed') useAgentStore.getState().setStatus('idle');
          }
        },
        onError: (err) => {
          console.warn('[Project WS Stream Error]:', err);
        },
      },
      projData.active_task_id || undefined
    );

    useWorkspaceStore.getState().reloadPreview();
  } catch (err) {
    console.error('Failed to load project details:', err);
  }
}

/**
 * Closes a project tab. If the closed tab was active, switches to the next adjacent open tab
 * or cleanly resets into startNewProject if no tabs remain open.
 */
export async function closeProjectTabAndSwitch(id: string) {
  const { openProjectIds, currentProjectId } = useProjectStore.getState();
  const currentIndex = openProjectIds.indexOf(id);
  const remaining = openProjectIds.filter((oid) => oid !== id);

  // Close the tab in store
  useProjectStore.getState().closeProjectTab(id);

  // If the closed tab was currently active, switch to adjacent or new project
  if (currentProjectId === id) {
    if (remaining.length > 0) {
      const nextIndex = Math.min(Math.max(0, currentIndex), remaining.length - 1);
      const nextId = remaining[nextIndex];
      await loadProject(nextId);
    } else {
      startNewProject();
    }
  }
}
