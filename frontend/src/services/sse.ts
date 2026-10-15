/**
 * frontend/src/services/sse.ts
 * 
 * COMPATIBILITY FALLBACK ONLY — SSE Transport Shim.
 * Authoritative primary transport is ProjectWebSocketClient (/ws/projects/:projectId)
 * in frontend/src/services/project-ws.ts.
 * 
 * SSE (/api/stream/:taskId) is retained strictly as a compatibility fallback
 * when WebSocket connection is rejected or unavailable.
 */

import { AgentEvent } from '../types/agent';
import { api } from './api';
import { projectWsClient } from './project-ws';

export interface SSEListenerCallbacks {
  onEvent: (event: AgentEvent) => void;
  onResult?: (result: any) => void;
  onDone?: () => void;
  onError?: (err: Error) => void;
}

export class TaskStreamManager {
  private eventSource: EventSource | null = null;
  private taskId: string | null = null;
  private projectId: string | null = null;
  private callbacks: SSEListenerCallbacks | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectTimeout: any = null;
  private pollingInterval: any = null;
  private isClosed = false;

  /**
   * Connects to the authoritative real-time stream.
   * Prefers WebSocket (/ws/projects/:projectId) and falls back to SSE (/api/stream/:taskId).
   */
  public connect(taskId: string, callbacks: SSEListenerCallbacks, projectId?: string) {
    this.disconnect();
    this.taskId = taskId;
    this.projectId = projectId || null;
    this.callbacks = callbacks;
    this.reconnectAttempts = 0;
    this.isClosed = false;

    if (this.projectId) {
      projectWsClient.connect(this.projectId, callbacks, taskId);
    } else {
      this.startSSE();
    }
  }

  public sendTaskCancel(reason: string = 'user_cancelled') {
    projectWsClient.sendTaskCancel(reason);
  }

  private startSSE() {
    if (this.isClosed || !this.taskId) return;

    const streamUrl = `/api/stream/${encodeURIComponent(this.taskId)}`;
    try {
      this.eventSource = new EventSource(streamUrl);

      this.eventSource.onmessage = (event) => {
        if (!event.data) return;
        try {
          const payload = JSON.parse(event.data);

          if (payload.type === 'heartbeat') {
            return;
          }

          if (payload.type === 'result') {
            this.callbacks?.onResult?.(payload.data);
            return;
          }

          if (payload.type === 'done') {
            this.callbacks?.onDone?.();
            this.disconnect();
            return;
          }

          // Structured event
          const agentEvent: AgentEvent = {
            type: payload.type || 'agent.status',
            timestamp: payload.timestamp ? payload.timestamp * 1000 : Date.now(),
            data: { ...payload, ...(payload.data || {}) },
            task_id: payload.task_id || this.taskId || undefined,
            chat: payload.chat,
            log: payload.log,
          };
          this.callbacks?.onEvent(agentEvent);
          if (payload.type === 'task.failed' || payload.type === 'task.completed') {
            if (payload.data?.result) this.callbacks?.onResult?.(payload.data.result);
            this.callbacks?.onDone?.();
            this.disconnect();
          }
        } catch (parseErr) {
          console.warn('[SSE] Parse error:', parseErr, event.data);
        }
      };

      this.eventSource.onerror = (err) => {
        console.warn('[SSE] Error on stream:', err);
        this.eventSource?.close();
        this.eventSource = null;

        if (this.reconnectAttempts < this.maxReconnectAttempts) {
          this.reconnectAttempts += 1;
          const delay = Math.min(1000 * Math.pow(1.5, this.reconnectAttempts), 5000);
          this.reconnectTimeout = setTimeout(() => this.startSSE(), delay);
        } else {
          // Fall back to polling status endpoint
          console.warn('[SSE] Falling back to polling status for task:', this.taskId);
          this.startPollingFallback();
        }
      };
    } catch (e: any) {
      this.callbacks?.onError?.(e);
      this.startPollingFallback();
    }
  }

  private startPollingFallback() {
    if (this.pollingInterval || this.isClosed || !this.taskId) return;

    this.pollingInterval = setInterval(async () => {
      if (!this.taskId || this.isClosed) {
        this.stopPollingFallback();
        return;
      }
      try {
        const res = await api.getTaskStatus(this.taskId);
        if ((res.status === 'completed' || res.status === 'blocked' || res.status === 'failed') && res.data) {
          this.callbacks?.onResult?.(res.data);
          this.callbacks?.onDone?.();
          this.disconnect();
        } else if (res.status === 'cancelled' || res.status === 'not_found') {
          this.callbacks?.onDone?.();
          this.disconnect();
        }
      } catch (pollErr) {
        console.warn('[SSE Polling Error]:', pollErr);
      }
    }, 2000);
  }

  private stopPollingFallback() {
    if (this.pollingInterval) {
      clearInterval(this.pollingInterval);
      this.pollingInterval = null;
    }
  }

  public disconnect() {
    this.isClosed = true;
    try {
      // A task-only fallback does not own the project WebSocket lifecycle.
      if (this.projectId && projectWsClient.getProjectId() === this.projectId) projectWsClient.disconnect();
    } catch (_) {}
    if (this.eventSource) {
      try {
        this.eventSource.close();
      } catch (_) {}
      this.eventSource = null;
    }
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
    this.stopPollingFallback();
    this.taskId = null;
    this.projectId = null;
    this.callbacks = null;
  }
}

export const streamManager = new TaskStreamManager();

projectWsClient.setFallbackFactory((taskId, callbacks) => {
  const fallback = new TaskStreamManager();
  fallback.connect(taskId, callbacks);
  return fallback;
});
