/**
 * Agent event taxonomy and status definitions matching Qwen3 blueprint and event_bus.py.
 */

export type AgentEventType =
  | 'connection.ready'
  | 'agent.status'
  | 'activity.started'
  | 'activity.updated'
  | 'activity.completed'
  | 'file.created'
  | 'file.modified'
  | 'command.started'
  | 'command.output'
  | 'command.completed'
  | 'build.result'
  | 'preview.ready'
  | 'task.started'
  | 'task.completed'
  | 'task.failed'
  | 'task.cancelled'
  | 'queued'
  | 'heartbeat'
  | 'done';

export type ClientMessageType =
  | 'task.start'
  | 'task.cancel'
  | 'prompt.queue'
  | 'preview.selection'
  | 'subscribe.events'
  | 'sync';

export interface AgentEvent {
  type: AgentEventType | string;
  timestamp: number;
  data: Record<string, any>;
  task_id?: string;
  project_id?: string;
  seq?: number;
  eventId?: number;
  chat?: string;
  log?: string;
}

export type AgentStatus =
  | 'idle'
  | 'planning'
  | 'generating'
  | 'typechecking'
  | 'repairing'
  | 'completed'
  | 'failed'
  | 'cancelled';

export interface ActivityStep {
  id: string;
  title: string;
  status: 'running' | 'completed' | 'failed';
  startedAt: number;
  finishedAt?: number;
  durationMs?: number;
  description?: string;
  details?: Record<string, any>;
  tool?: string;
  args?: Record<string, any>;
  output?: string;
}

export type GateTruthState = 'passed' | 'failed' | 'unverified' | 'not_requested' | 'unknown';

export function toGateTruthState(val: boolean | string | undefined | null): GateTruthState {
  if (val === true || val === 'passed') return 'passed';
  if (val === false || val === 'failed') return 'failed';
  if (val === 'unverified') return 'unverified';
  if (val === 'not_requested') return 'not_requested';
  return 'unknown';
}

export type TriState = GateTruthState;
export const toTriState = toGateTruthState;

export interface ValidationGate {
  name: 'typecheck' | 'build' | 'lint' | 'contract' | 'accessibility' | 'motion' | 'runtime' | 'preview' | 'interaction';
  passed: boolean;
  status: GateTruthState;
  errors?: string[];
  warnings?: string[];
}

export interface MotionPlanItem {
  type: string;
  section?: string;
  intensity?: 'subtle' | 'medium' | 'cinematic' | string;
  axis?: 'x' | 'y' | 'both' | 'none' | string;
  trigger?: 'viewport' | 'scroll-progress' | 'interaction' | string;
  reduced_motion_behavior?: 'static' | 'instant' | 'native-scroll' | string;
  mobile_fallback?: 'stack' | 'native-horizontal' | 'static' | string;
  implementation?: 'native' | 'gsap' | 'framer-motion' | string;
  verified?: boolean;
}

export interface InteractionEvidenceItem {
  requirement_id: string;
  locator: string;
  initial_state: any;
  action: string;
  expected_state: any;
  observed_state: any;
  passed: boolean;
  error?: string | null;
}

export interface ValidationResult {
  typecheck?: GateEvidence;
  build?: GateEvidence;
  lint?: GateEvidence;
  contract?: GateEvidence;
  accessibility?: GateEvidence;
  motion?: GateEvidence;
  three_d?: GateEvidence;
  runtime?: GateEvidence;
  interaction?: GateEvidence;
  preview?: GateEvidence;
  typecheck_passed: boolean;
  build_passed: boolean;
  lint_passed: boolean;
  contract_passed?: boolean;
  accessibility_passed?: boolean;
  motion_passed?: boolean;
  three_d_passed?: boolean;
  runtime_passed: boolean;
  preview_running?: boolean;
  interaction_passed?: boolean;
  runtime_unverified?: boolean;
  interactions_tested?: number;
  interactions_required?: number;
  interaction_evidence?: InteractionEvidenceItem[];
  interaction_errors?: string[];
  typecheck_status?: GateTruthState;
  build_status?: GateTruthState;
  lint_status?: GateTruthState;
  contract_status?: GateTruthState;
  accessibility_status?: GateTruthState;
  motion_status?: GateTruthState;
  motion_runtime_status?: GateTruthState;
  three_d_status?: GateTruthState;
  three_d_static_status?: GateTruthState;
  three_d_runtime_status?: GateTruthState;
  runtime_status?: GateTruthState;
  preview_status?: GateTruthState;
  interaction_status?: GateTruthState;
  code_status?: GateTruthState;
  code_passed?: boolean;
  passed?: boolean;
  all_gates_passed?: boolean;
  validationStatus?: 'unchanged' | 'passed' | 'failed';
  motion_plan?: MotionPlanItem[];
  motion_failures?: string[];
  errors: string[];
  warnings: string[];
  repair_attempts: number;
}

export type GateStatus = 'passed' | 'failed' | 'unverified' | 'not_requested';

export interface GateEvidence {
  status: GateStatus;
  checks_run: number;
  errors: string[];
  warnings: string[];
  evidence?: Array<Record<string, unknown>>;
}

const REQUIRED_GATES: (keyof Pick<ValidationResult,
  'typecheck' | 'build' | 'lint' | 'contract' | 'accessibility' |
  'motion' | 'three_d' | 'runtime' | 'interaction' | 'preview'>)[] = [
  'typecheck', 'build', 'lint', 'contract', 'accessibility',
  'motion', 'three_d', 'runtime', 'interaction', 'preview',
];

export function validationPassed(result: ValidationResult): boolean {
  return REQUIRED_GATES.every((name) => {
    const status = result[name]?.status;
    return status === 'passed' || status === 'not_requested';
  });
}

export interface AgentMetrics {
  modelName: string;
  baseFingerprint?: string;
  adapterFingerprint?: string;
  contextTokens: number;
  maxContextTokens: number;
  generationTokens: number;
  toolCallsCount: number;
  repairAttempts: number;
  maxRepairAttempts: number;
  turnCount: number;
  visualScore?: number;
  hasMotion?: boolean;
  motionVerified?: boolean;
}
