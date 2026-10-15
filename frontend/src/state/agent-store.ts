import { create } from 'zustand';
import {
  AgentEvent,
  AgentEventType,
  AgentMetrics,
  AgentStatus,
  ActivityStep,
  ValidationResult,
  TriState,
  toTriState,
  GateTruthState,
  toGateTruthState,
} from '../types/agent';

interface AgentStoreState {
  activeTaskId: string | null;
  status: AgentStatus;
  statusMessage: string;
  queueDepth: number;
  startTime: number | null;
  elapsedSeconds: number;
  currentActivities: ActivityStep[];
  validationResult: ValidationResult | null;
  metrics: AgentMetrics;

  // Global system readiness state (preserved across project resets)
  modelLoaded: boolean;
  gpuReady: boolean;
  serverConnected: boolean;

  setActiveTaskId: (id: string | null) => void;
  setStatus: (status: AgentStatus, message?: string) => void;
  setSystemStatus: (status: {
    modelLoaded?: boolean;
    gpuReady?: boolean;
    serverConnected?: boolean;
    maxContextTokens?: number;
    max_context_tokens?: number;
    contextTokens?: number;
    context_tokens?: number;
    modelName?: string;
    model_name?: string;
    baseFingerprint?: string;
    base_fingerprint?: string;
    adapterFingerprint?: string;
    adapter_fingerprint?: string;
  }) => void;
  setQueueDepth: (depth: number) => void;
  startTimer: () => void;
  stopTimer: () => void;
  tickTimer: () => void;
  applyEvent: (event: AgentEvent) => void;
  setValidationResult: (res: ValidationResult | null) => void;
  resetAgent: () => void;
}

const defaultMetrics: AgentMetrics = {
  modelName: 'Connecting...',
  baseFingerprint: undefined,
  adapterFingerprint: undefined,
  contextTokens: 0,
  maxContextTokens: 8192,
  generationTokens: 0,
  toolCallsCount: 0,
  repairAttempts: 0,
  maxRepairAttempts: 3,
  turnCount: 0,
  visualScore: undefined,
};

export const useAgentStore = create<AgentStoreState>((set, get) => ({
  activeTaskId: null,
  status: 'idle',
  statusMessage: 'Ready',
  queueDepth: 0,
  startTime: null,
  elapsedSeconds: 0,
  currentActivities: [],
  validationResult: null,
  metrics: defaultMetrics,
  modelLoaded: false,
  gpuReady: false,
  serverConnected: false,

  setActiveTaskId: (id) => set({ activeTaskId: id }),
  setSystemStatus: (status) => set((state) => ({
    ...state,
    ...(status.modelLoaded !== undefined ? { modelLoaded: status.modelLoaded } : {}),
    ...(status.gpuReady !== undefined ? { gpuReady: status.gpuReady } : {}),
    ...(status.serverConnected !== undefined ? { serverConnected: status.serverConnected } : {}),
    metrics: {
      ...state.metrics,
      ...(status.maxContextTokens ? { maxContextTokens: status.maxContextTokens } : {}),
      ...(status.max_context_tokens ? { maxContextTokens: status.max_context_tokens } : {}),
      ...(status.contextTokens !== undefined ? { contextTokens: status.contextTokens } : {}),
      ...(status.context_tokens !== undefined ? { contextTokens: status.context_tokens } : {}),
      ...(status.model_name ? { modelName: status.model_name } : status.modelName ? { modelName: status.modelName } : {}),
      ...(status.base_fingerprint ? { baseFingerprint: status.base_fingerprint } : status.baseFingerprint ? { baseFingerprint: status.baseFingerprint } : {}),
      ...(status.adapter_fingerprint ? { adapterFingerprint: status.adapter_fingerprint } : status.adapterFingerprint ? { adapterFingerprint: status.adapterFingerprint } : {}),
    },
  })),
  setStatus: (status, message) => set({
    status,
    statusMessage: message || (
      status === 'idle' ? 'Ready' :
      status === 'generating' ? 'Generating...' :
      status === 'typechecking' ? 'Validating TypeScript...' :
      status === 'repairing' ? 'Applying visual repair...' :
      status === 'completed' ? 'Completed' :
      status === 'failed' ? 'Failed' :
      status === 'cancelled' ? 'Cancelled' : status
    )
  }),
  setQueueDepth: (depth) => set({ queueDepth: Math.max(0, depth) }),

  startTimer: () => set({ startTime: Date.now(), elapsedSeconds: 0 }),
  stopTimer: () => set({ startTime: null }),
  tickTimer: () => {
    const { startTime } = get();
    if (startTime) {
      set({ elapsedSeconds: Math.floor((Date.now() - startTime) / 100) / 10 });
    }
  },

  applyEvent: (event) => {
    const t = event.type;
    const d = { ...event, ...(event.data || {}) } as Record<string, any>;

    set((state) => {
      let nextStatus = state.status;
      let nextMsg = state.statusMessage;
      let nextActivities = [...state.currentActivities];
      let nextMetrics = { ...state.metrics };
      let nextValidation = state.validationResult;

      const anyEvt = event as any;
      const incomingMax = d.max_context_tokens || d.maxContextTokens || anyEvt.max_context_tokens || anyEvt.maxContextTokens;
      if (incomingMax) {
        nextMetrics.maxContextTokens = Number(incomingMax);
      }
      const incomingCtx = d.context_tokens || d.contextTokens || anyEvt.context_tokens || anyEvt.contextTokens;
      if (incomingCtx) {
        nextMetrics.contextTokens = Number(incomingCtx);
      }

      if (t === 'transport.status') {
        nextMsg = d.message || nextMsg;
      } else if (t === 'agent.status') {
        const rawStatus = (d.status || d.text || '').toLowerCase();
        if (rawStatus.includes('repair')) nextStatus = 'repairing';
        else if (rawStatus.includes('check') || rawStatus.includes('build') || rawStatus.includes('tsc')) nextStatus = 'typechecking';
        else if (rawStatus.includes('plan')) nextStatus = 'planning';
        else if (rawStatus.includes('complet')) nextStatus = 'completed';
        else if (rawStatus.includes('fail')) nextStatus = 'failed';
        else if (rawStatus.includes('cancel')) nextStatus = 'cancelled';
        else nextStatus = 'generating';
        nextMsg = d.status || d.text || state.statusMessage;
      } else if (t === 'activity.started') {
        const title = d.activity || d.title || 'Task Step';
        const stepId = d.id || `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
        nextActivities.push({
          id: stepId,
          title,
          status: 'running',
          startedAt: Date.now(),
          description: d.description,
          details: d,
        });
        nextMetrics.toolCallsCount += 1;
      } else if (t === 'activity.updated') {
        const lastIdx = nextActivities.length - 1;
        if (lastIdx >= 0) {
          nextActivities[lastIdx] = {
            ...nextActivities[lastIdx],
            description: d.step || d.status || nextActivities[lastIdx].description,
          };
        }
      } else if (t === 'activity.completed') {
        const lastIdx = nextActivities.length - 1;
        if (lastIdx >= 0) {
          nextActivities[lastIdx] = {
            ...nextActivities[lastIdx],
            status: 'completed',
            finishedAt: Date.now(),
            durationMs: d.duration_ms,
          };
        }
      } else if (t === 'file.created' || t === 'file.modified') {
        nextActivities.push({
          id: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
          title: t === 'file.created' ? `Created ${d.path || d.file || d.filename || 'file'}` : `Updated ${d.path || d.file || d.filename || 'file'}`,
          status: 'completed',
          startedAt: Date.now(),
          finishedAt: Date.now(),
          description: d.diff_summary || `${d.chars || 0} characters`,
          details: d,
        });
        nextMetrics.toolCallsCount += 1;
      } else if (t === 'build.result') {
        const rawTc = d.typecheck_passed ?? d.typecheckPassed;
        const rawBuild = d.build_passed ?? d.buildPassed;
        const rawLint = d.lint_passed ?? d.lintPassed;
        const rawContract = d.contract_passed ?? d.contractPassed;
        const rawA11y = d.accessibility_passed ?? d.accessibilityPassed;
        const rawRuntime = d.runtime_passed ?? d.runtimePassed;
        const rawPreview = d.preview_running ?? d.previewRunning;
        const rawInteraction = d.interaction_passed ?? d.interactionPassed;
        const rawCode = d.code_passed ?? d.codePassed;
        const rawUnverified = Boolean(d.runtime_unverified ?? d.runtimeUnverified ?? false);
        const rawMotion = d.motion_passed ?? d.motionPassed;
        const rawThreeD = d.three_d_passed ?? d.threeDPassed;

        const typecheckStatus: GateTruthState = toGateTruthState(d.typecheck_status ?? rawTc);
        const buildStatus: GateTruthState = toGateTruthState(d.build_status ?? rawBuild);
        const lintStatus: GateTruthState = toGateTruthState(d.lint_status ?? rawLint);
        const contractStatus: GateTruthState = toGateTruthState(d.contract_status ?? rawContract);
        const accessibilityStatus: GateTruthState = toGateTruthState(d.accessibility_status ?? rawA11y);
        const motionStatus: GateTruthState = toGateTruthState(d.motion_status ?? rawMotion);
        const threeDStatus: GateTruthState = toGateTruthState(d.three_d_status ?? rawThreeD);
        const runtimeStatus: GateTruthState = rawUnverified ? 'unverified' : toGateTruthState(d.runtime_status ?? rawRuntime);
        const previewStatus: GateTruthState = toGateTruthState(d.preview_status ?? rawPreview);
        const interactionStatus: GateTruthState = rawUnverified ? 'unverified' : toGateTruthState(d.interaction_status ?? rawInteraction);

        const motionPlan = d.motion_plan ?? d.motionPlan ?? [];
        const motionFailures = d.motion_failures ?? d.motionFailures ?? [];
        const interactionErrors = d.interaction_errors ?? d.interactionErrors ?? [];
        const interactionsTested = Number(d.interactions_tested ?? d.interactionsTested ?? 0);
        const interactionsRequired = Number(d.interactions_required ?? d.interactionsRequired ?? 0);
        const interactionEvidence = d.interaction_evidence ?? d.interactionEvidence ?? [];

        // Derive code status strictly across all static checks
        let codeStatus: GateTruthState = toGateTruthState(rawCode);
        if (rawCode === undefined || rawCode === null) {
          const staticChecks = [typecheckStatus, buildStatus, lintStatus, contractStatus, accessibilityStatus, motionStatus];
          if (staticChecks.some((s) => s === 'failed')) {
            codeStatus = 'failed';
          } else if (staticChecks.every((s) => s === 'passed')) {
            codeStatus = 'passed';
          } else {
            codeStatus = 'unknown';
          }
        }

        // Derive overall passed strictly: only true if all gates passed, not unverified, and interaction passed
        const allGatesPassed = (
          d.passed !== false && d.all_gates_passed !== false &&
          typecheckStatus === 'passed' &&
          buildStatus === 'passed' &&
          lintStatus === 'passed' &&
          contractStatus === 'passed' &&
          accessibilityStatus === 'passed' &&
          motionStatus === 'passed' &&
          (threeDStatus === 'passed' || threeDStatus === 'not_requested') &&
          runtimeStatus === 'passed' &&
          !rawUnverified &&
          previewStatus === 'passed' &&
          (interactionStatus === 'passed' || interactionStatus === 'not_requested')
        );

        nextValidation = {
          ...d,
          typecheck_passed: typecheckStatus === 'passed',
          build_passed: buildStatus === 'passed',
          lint_passed: lintStatus === 'passed',
          contract_passed: contractStatus === 'passed',
          accessibility_passed: accessibilityStatus === 'passed',
          motion_passed: motionStatus === 'passed',
          three_d_passed: threeDStatus === 'passed' || threeDStatus === 'not_requested',
          three_d_status: threeDStatus,
          runtime_passed: runtimeStatus === 'passed' && !rawUnverified,
          preview_running: previewStatus === 'passed',
          interaction_passed: interactionStatus === 'passed',
          interactions_tested: interactionsTested,
          interactions_required: interactionsRequired,
          interaction_evidence: interactionEvidence,
          interaction_errors: interactionErrors,
          runtime_unverified: rawUnverified,
          typecheck_status: typecheckStatus,
          build_status: buildStatus,
          lint_status: lintStatus,
          contract_status: contractStatus,
          accessibility_status: accessibilityStatus,
          motion_status: motionStatus,
          runtime_status: runtimeStatus,
          preview_status: previewStatus,
          interaction_status: interactionStatus,
          code_status: codeStatus,
          code_passed: codeStatus === 'passed',
          passed: allGatesPassed,
          all_gates_passed: allGatesPassed,
          motion_plan: motionPlan,
          motion_failures: motionFailures,
          errors: d.errors || [],
          warnings: d.warnings || [],
          repair_attempts: d.repair_attempts || 0,
        };
        nextMetrics.repairAttempts = d.repair_attempts || nextMetrics.repairAttempts;
        nextMetrics.hasMotion = motionPlan.length > 0;
        nextMetrics.motionVerified = motionStatus === 'passed' && motionPlan.length > 0;
      } else if (t === 'task.completed') {
        nextStatus = 'completed';
        nextMsg = 'Generation completed successfully';
      } else if (t === 'task.failed') {
        nextStatus = 'failed';
        nextMsg = d.error || 'Generation failed';
      }

      return {
        status: nextStatus,
        statusMessage: nextMsg,
        currentActivities: nextActivities,
        metrics: nextMetrics,
        validationResult: nextValidation,
      };
    });
  },

  setValidationResult: (res) => set({ validationResult: res }),

  resetAgent: () => set({
    activeTaskId: null,
    status: 'idle',
    statusMessage: 'Ready',
    currentActivities: [],
    validationResult: null,
    startTime: null,
    elapsedSeconds: 0,
    metrics: { ...defaultMetrics },
  }),
}));
