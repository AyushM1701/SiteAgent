import { ActivityStep, ValidationResult, TriState } from './agent';

export type MessageVariant =
  | 'user'
  | 'assistant'
  | 'activity'
  | 'summary'
  | 'error';

export interface QueuedPrompt {
  id: string;
  projectId: string;
  content: string;
  createdAt: number;
  queuePosition?: number;
  status: 'queued' | 'running' | 'completed' | 'cancelled';
  taskId?: string;
}

export interface ChangeSummaryData {
  completionStatus?: string;
  blockedSections?: Array<string | { section?: string; name?: string; reason?: string; error?: string; errors?: string[] }>;
  sectionCompletion?: string;
  finalPassed?: boolean;
  /** Site writer used ('kit' or 'native') and, for native, the sections whose code the model wrote. */
  strategy?: string;
  nativeCodeSections?: string[];
  nativeCodeFallbacks?: Record<string, string[]>;
  generationScorecards?: { provenance: { mode?: string }; stages: Array<{ id: string; label: string; status: string; first_attempt_sections?: number; required_sections?: number; section_retries?: number; project_attempts?: number; files?: string[]; note?: string }> };
  filesCreated: string[];
  filesModified: string[];
  filePath?: string;
  folderName?: string;
  fullPath?: string;
  totalChars?: number;
  durationSec?: number;
  visualScore?: number;
  visualIssues?: string[];
  screenshotUrl?: string;
  turnId?: number;
  code_passed?: boolean;
  build_passed?: boolean;
  contract_passed?: boolean;
  accessibility_passed?: boolean;
  runtime_passed?: boolean;
  preview_running?: boolean;
  passed?: boolean;
  codeStatus?: TriState;
  buildStatus?: TriState;
  contractStatus?: TriState;
  accessibilityStatus?: TriState;
  runtimeStatus?: TriState;
  previewStatus?: TriState;
  overallStatus?: TriState;
  validationStatus?: 'unchanged' | 'passed' | 'failed';
  validation?: ValidationResult;
}

export interface ChatMessage {
  id: string;
  role: MessageVariant;
  content?: string;
  timestamp: number;
  taskId?: string;
  projectId?: string;
  turnId?: number;
  // Queued state for user message
  isQueued?: boolean;
  queuePosition?: number;
  // Activity state
  activitySteps?: ActivityStep[];
  currentActivityTitle?: string;
  // Summary state
  summary?: ChangeSummaryData;
  // Error state
  errorDetails?: {
    message: string;
    stage?: string;
    recoverable?: boolean;
  };
}

export interface FileDiffEntry {
  before: string;
  after: string;
  patch: string;
}

export interface CanonicalTurnDiff {
  turnId: number;
  files: Record<string, FileDiffEntry>;
  summary?: string;
  files_touched?: string[];
  original_files?: Record<string, string>;
  modified_files?: Record<string, string>;
  diffs?: Record<string, string>;
}
