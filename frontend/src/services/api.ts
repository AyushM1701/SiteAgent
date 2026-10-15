/**
 * Typed client API service for the ReactAgent SLM server endpoints.
 */

import { CanonicalTurnDiff } from '../types/chat';

export interface GenerateParams {
  prompt: string;
  session_id?: string;
  mode?: 'component' | 'site';
  max_turns?: number;
  stylePreset?: string;
  style_preset?: string;
  max_tokens?: number;
}

export interface StylePresetItem {
  id: string;
  label: string;
  description: string;
  isDefault?: boolean;
}

export interface StylePresetsResponse {
  presets: StylePresetItem[];
  default: string;
}

export interface GenerateResponse {
  task_id: string;
  session_id: string;
  status: 'queued' | 'running' | 'completed';
  queue_position: number;
  stream_url: string;
  deduplicated?: boolean;
}

export interface TaskStatusResponse {
  task_id: string;
  status: 'completed' | 'blocked' | 'failed' | 'running' | 'queued' | 'cancelled' | 'not_found';
  data?: any;
  position?: number;
}

export const api = {
  async getStatus(): Promise<{
    model_status: string;
    model_loaded: boolean;
    adapter_compatible: boolean | null;
    gpu_ready: boolean;
    loaded_model_path?: string | null;
    configured_model_path?: string;
    promotion_gate_status?: string;
    queue_depth: number;
    max_context_tokens?: number;
    model_name?: string;
    model_path?: string;
    base_model?: string;
    base_fingerprint?: string;
    adapter_fingerprint?: string;
    is_qwen3_architecture?: boolean;
    mock?: boolean;
    project_websocket_url?: string;
    project_websocket_ready?: boolean;
  }> {
    const res = await fetch('/api/status');
    if (!res.ok) throw new Error(`Failed to fetch status: ${res.statusText}`);
    return res.json();
  },

  async getStylePresets(): Promise<StylePresetsResponse> {
    const res = await fetch('/api/style-presets');
    if (!res.ok) throw new Error('Failed to fetch style presets');
    return res.json();
  },

  async getProjects(): Promise<any[]> {
    const res = await fetch('/api/projects');
    if (!res.ok) {
      // Fallback to sessions endpoint
      const fallback = await fetch('/api/sessions');
      if (!fallback.ok) throw new Error('Failed to fetch projects');
      const fallbackData = await fallback.json();
      return Array.isArray(fallbackData) ? fallbackData : (fallbackData.projects || fallbackData.sessions || []);
    }
    const data = await res.json();
    return Array.isArray(data) ? data : (data.projects || data.sessions || []);
  },

  async getProject(id: string): Promise<any> {
    const res = await fetch(`/api/projects/${encodeURIComponent(id)}`);
    if (!res.ok) {
      const fallback = await fetch(`/api/sessions/${encodeURIComponent(id)}`);
      if (!fallback.ok) throw new Error(`Project ${id} not found`);
      return fallback.json();
    }
    return res.json();
  },

  async generate(params: GenerateParams): Promise<GenerateResponse> {
    const res = await fetch('/api/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ error: res.statusText }));
      throw new Error(err.error || 'Generation request failed');
    }
    return res.json();
  },

  async getTaskStatus(taskId: string): Promise<TaskStatusResponse> {
    const res = await fetch(`/api/generation/${encodeURIComponent(taskId)}/status`);
    if (!res.ok) throw new Error(`Task status failed: ${res.statusText}`);
    return res.json();
  },

  async cancelTask(taskId: string, options?: { clear_queue?: boolean }): Promise<void> {
    const clear_queue = options?.clear_queue ?? false;
    const res = await fetch(`/api/cancel/${encodeURIComponent(taskId)}?clear_queue=${clear_queue}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ clear_queue }),
    });
    if (!res.ok) throw new Error('Cancellation failed');
  },

  async cancelAll(): Promise<void> {
    const res = await fetch('/api/cancel/all', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ clear_queue: true }),
    });
    if (!res.ok) throw new Error('Failed to cancel all tasks');
  },

  async getDiff(sessionId: string, turnId: number): Promise<CanonicalTurnDiff> {
    const res = await fetch(`/api/sessions/${encodeURIComponent(sessionId)}/diff/${turnId}`);
    if (!res.ok) throw new Error('Failed to fetch diff');
    return res.json();
  },

  async revertTurn(sessionId: string, turnId: number): Promise<any> {
    const res = await fetch(`/api/sessions/${encodeURIComponent(sessionId)}/revert/${turnId}`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error('Revert failed');
    return res.json();
  },

  async deleteProject(id: string): Promise<void> {
    const res = await fetch(`/api/history/${encodeURIComponent(id)}`, { method: 'DELETE' });
    if (!res.ok) throw new Error('Failed to delete project');
  },

  async clearAllHistory(): Promise<void> {
    const res = await fetch('/api/history', { method: 'DELETE' });
    if (!res.ok) throw new Error('Failed to clear history');
  },

  async getShellToken(): Promise<{ ticket: string; host: string; port: number }> {
    const res = await fetch('/api/shell-token');
    if (!res.ok) throw new Error('Failed to mint shell token');
    const data = await res.json();
    return {
      ticket: data.ticket || data.token || '',
      host: data.host || (typeof window !== 'undefined' ? window.location.hostname : '127.0.0.1') || '127.0.0.1',
      port: data.port || 5001,
    };
  },

  getProjectExportUrl(projectId: string): string {
    return `/api/projects/${encodeURIComponent(projectId)}/export`;
  },

  async saveProjectFile(
    projectId: string,
    file: string,
    content: string
  ): Promise<{
    success: boolean;
    file: string;
    turnId: number;
    validation?: any;
    build_state?: any;
    files: Record<string, string>;
    preview?: any;
  }> {
    const res = await fetch(`/api/projects/${encodeURIComponent(projectId)}/file`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ file, content }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ error: 'Failed to save file' }));
      throw new Error(err.error || 'Failed to save file');
    }
    return res.json();
  },

  async deleteProjectFile(
    projectId: string,
    file: string
  ): Promise<{
    success: boolean;
    file: string;
    turnId: number;
    validation?: any;
    build_state?: any;
    files: Record<string, string>;
    preview?: any;
  }> {
    const res = await fetch(`/api/projects/${encodeURIComponent(projectId)}/file`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ file }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ error: 'Failed to delete file' }));
      throw new Error(err.error || 'Failed to delete file');
    }
    return res.json();
  },
};
