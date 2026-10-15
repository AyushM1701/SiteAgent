/**
 * frontend/src/services/project-ws.ts
 * Authoritative Project WebSocket Client (/ws/projects/:projectId).
 * 
 * Features:
 * - Monotonically increasing sequence numbers (seq / eventId)
 * - Missed event replay on reconnect (?lastEventId=N and subscribe.events)
 * - Bidirectional messaging:
 *     Client -> task.start, task.cancel, prompt.queue, preview.selection, subscribe.events
 *     Server -> connection.ready, agent.status, activity.*, file.*, command.*,
 *               build.result, preview.ready, task.started, task.completed, task.failed, task.cancelled
 * - Automatic exponential backoff reconnect
 * - Graceful fallback to SSE when WebSocket is unavailable
 */

import { AgentEvent, ClientMessageType } from '../types/agent';
import { api } from './api';

export interface ProjectStreamCallbacks {
  onEvent: (event: AgentEvent) => void;
  onResult?: (result: any) => void;
  onDone?: () => void;
  onError?: (err: Error) => void;
}

export class ProjectWebSocketClient {
  private socket: WebSocket | null = null;
  private projectId: string | null = null;
  private activeTaskId: string | null = null;
  private callbacks: ProjectStreamCallbacks | null = null;
  private lastEventId: number = 0;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectTimeout: any = null;
  private stableConnectionTimeout: ReturnType<typeof setTimeout> | null = null;
  private isClosed = false;
  private endpoint: string | null = null;
  private fallbackSSE: any = null;

  /**
   * Connects to the authoritative project WebSocket channel: /ws/projects/:projectId
   */
  public connect(projectId: string, callbacks: ProjectStreamCallbacks, taskId?: string) {
    const isSameProject = this.projectId === projectId;
    // Project selection effects must not replace an in-flight task's callbacks.
    if (isSameProject && this.activeTaskId && !taskId && !this.isClosed) return;
    if (!isSameProject) {
      this.disconnect();
      this.lastEventId = 0;
    } else {
      // Reconnecting to same project, close socket but preserve lastEventId for replay
      if (this.socket) {
        this.socket.onclose = null;
        try {
          this.socket.close();
        } catch (_) {}
        this.socket = null;
      }
      this.clearStableConnectionTimer();
      this.fallbackSSE?.disconnect();
      this.fallbackSSE = null;
      if (this.reconnectTimeout) {
        clearTimeout(this.reconnectTimeout);
        this.reconnectTimeout = null;
      }
    }
    this.projectId = projectId;
    this.activeTaskId = taskId || null;
    this.callbacks = callbacks;
    this.reconnectAttempts = 0;
    this.isClosed = false;

    this.initWebSocket();
  }

  public getProjectId(): string | null {
    return this.projectId;
  }

  public getLastEventId(): number {
    return this.lastEventId;
  }

  public getActiveTaskId(): string | null {
    return this.activeTaskId;
  }

  public setActiveTaskId(taskId: string | null) {
    this.activeTaskId = taskId;
  }

  public setEndpoint(endpoint: string | null) {
    this.endpoint = endpoint;
  }

  public setCallbacks(callbacks: ProjectStreamCallbacks | null) {
    this.callbacks = callbacks;
  }

  public getCallbacks(): ProjectStreamCallbacks | null {
    return this.callbacks;
  }

  /**
   * Connects to authoritative project channel for task streaming.
   * If projectId is provided, connects directly over WebSocket;
   * falls back to SSE only if WebSocket is unavailable.
   */
  public streamTask(taskId: string, callbacks: ProjectStreamCallbacks, projectId?: string) {
    if (projectId) {
      this.connect(projectId, callbacks, taskId);
    } else {
      this.callbacks = callbacks;
      this.activeTaskId = taskId;
      this.startSSEFallback();
    }
  }

  public isConnected(): boolean {
    return Boolean(this.socket && this.socket.readyState === WebSocket.OPEN);
  }

  private initWebSocket() {
    if (this.isClosed || !this.projectId) return;

    try {
      const protocol = typeof window !== 'undefined' && window.location?.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = typeof window !== 'undefined' && window.location?.host ? window.location.host : '127.0.0.1:5173';
      const queryParam = `?lastEventId=${this.lastEventId}`;
      const wsUrl = `${this.endpoint || `${protocol}//${host}/ws/projects`}/${encodeURIComponent(this.projectId)}${queryParam}`;

      const socket = new WebSocket(wsUrl);
      this.socket = socket;

      this.socket.onopen = () => {
        if (socket !== this.socket || this.isClosed) return;
        // An open handshake is insufficient: malformed frames may close immediately.
        this.stableConnectionTimeout = setTimeout(() => {
          if (socket === this.socket && socket.readyState === WebSocket.OPEN) this.reconnectAttempts = 0;
          this.stableConnectionTimeout = null;
        }, 10000);
        // If reconnecting with previous sequence position, request replayed events
        if (this.lastEventId > 0) {
          this.sendSubscribeEvents(this.lastEventId);
        }
      };

      this.socket.onmessage = (messageEvent) => {
        if (socket !== this.socket || this.isClosed) return;
        if (!messageEvent.data) return;
        try {
          const payload = typeof messageEvent.data === 'string' ? JSON.parse(messageEvent.data) : messageEvent.data;
          this.handleServerMessage(payload);
        } catch (parseErr) {
          console.warn('[Project WS] JSON parse error:', parseErr, messageEvent.data);
        }
      };

      this.socket.onerror = (errEvent) => {
        console.warn('[Project WS] Socket error:', errEvent);
      };

      this.socket.onclose = (closeEvent) => {
        if (socket !== this.socket) return;
        this.clearStableConnectionTimer();
        this.socket = null;
        if (!this.isClosed) {
          if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts += 1;
            this.reportTransport(`Live connection interrupted. Reconnecting (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
            const delay = Math.min(1000 * Math.pow(1.5, this.reconnectAttempts), 5000);
            this.reconnectTimeout = setTimeout(() => this.initWebSocket(), delay);
          } else {
            console.warn('[Project WS] Max reconnect attempts reached, falling back to SSE for task:', this.activeTaskId);
            this.reportTransport('Live connection unavailable. Switching to backup event stream.');
            this.startSSEFallback();
          }
        }
      };
    } catch (e: any) {
      console.warn('[Project WS] Failed to initialize WebSocket:', e);
      this.startSSEFallback();
    }
  }

  /**
   * Processes inbound server messages matching target architecture taxonomy.
   */
  private handleServerMessage(payload: any) {
    if (!payload || typeof payload !== 'object') return;

    // Track monotonic sequence counter
    const seq = payload.seq ?? payload.eventId;
    if (typeof seq === 'number' && seq <= this.lastEventId) return;
    if (typeof seq === 'number' && seq > this.lastEventId) {
      this.lastEventId = seq;
    }

    const type = payload.type || 'agent.status';

    // Heartbeats and greetings
    if (type === 'heartbeat' || type === 'pong') {
      return;
    }

    if (type === 'connection.ready') {
      if (typeof payload.latest_seq === 'number' && payload.latest_seq > this.lastEventId) {
        // Initial sync point
      }
      return;
    }

    if (type === 'task.acknowledged' || type === 'task.started') {
      const ackTaskId = payload.task_id || payload.taskId || payload.data?.task_id || payload.data?.taskId;
      if (ackTaskId) {
        this.activeTaskId = ackTaskId;
      }
    }

    // Done / finalization signals
    if (type === 'done' || type === 'task.completed') {
      if (payload.data?.files || payload.data?.result) {
        this.callbacks?.onResult?.(payload.data.result || payload.data);
      }
      this.callbacks?.onDone?.();
      return;
    }

    if (type === 'task.failed' && payload.data?.cancelled) {
      this.callbacks?.onDone?.();
      return;
    }

    if (type === 'task.cancelled') {
      this.callbacks?.onDone?.();
      return;
    }

    // Build structured AgentEvent
    const agentEvent: AgentEvent = {
      type: type,
      timestamp: payload.timestamp ? (payload.timestamp > 1e11 ? payload.timestamp : payload.timestamp * 1000) : Date.now(),
      data: { ...payload, ...(payload.data || {}) },
      task_id: payload.task_id || this.activeTaskId || undefined,
      project_id: payload.project_id || this.projectId || undefined,
      seq: typeof seq === 'number' ? seq : undefined,
      eventId: typeof seq === 'number' ? seq : undefined,
      chat: payload.chat,
      log: payload.log,
    };

    this.callbacks?.onEvent(agentEvent);

    if (type === 'task.failed') {
      if (payload.data?.result) this.callbacks?.onResult?.(payload.data.result);
      this.callbacks?.onDone?.();
      return;
    }

    // If result payload is attached directly
    if (payload.type === 'result' && payload.data) {
      this.callbacks?.onResult?.(payload.data);
    }
  }

  /**
   * Sends a typed message to the backend over WebSocket.
   */
  public send(message: { type: ClientMessageType | string; [key: string]: any }): boolean {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(message));
      return true;
    }
    return false;
  }

  /**
   * Client -> task.start
   */
  public sendTaskStart(prompt: string, mode?: string, options?: Record<string, any>): boolean {
    return this.send({
      type: 'task.start',
      prompt,
      mode,
      options: options || {},
    });
  }

  /**
   * Client -> task.cancel (Bidirectional cancellation)
   */
  public sendTaskCancel(reason: string = 'user_cancelled'): boolean {
    return this.send({
      type: 'task.cancel',
      reason,
    });
  }

  /**
   * Client -> prompt.queue
   */
  public sendPromptQueue(prompt: string, options?: Record<string, any>): boolean {
    return this.send({
      type: 'prompt.queue',
      prompt,
      options: options || {},
    });
  }

  /**
   * Client -> preview.selection
   */
  public sendPreviewSelection(selection: Record<string, any>): boolean {
    return this.send({
      type: 'preview.selection',
      selection,
    });
  }

  /**
   * Client -> subscribe.events (replays missed events after lastEventId)
   */
  public sendSubscribeEvents(lastEventId: number): boolean {
    return this.send({
      type: 'subscribe.events',
      lastEventId,
    });
  }

  private fallbackFactory: ((taskId: string, callbacks: ProjectStreamCallbacks) => { disconnect: () => void }) | null = null;

  public setFallbackFactory(factory: (taskId: string, callbacks: ProjectStreamCallbacks) => { disconnect: () => void }) {
    this.fallbackFactory = factory;
  }

  /**
   * Temporary SSE fallback if WebSocket is rejected or unavailable.
   */
  private startSSEFallback() {
    if (!this.activeTaskId || this.isClosed || this.fallbackSSE) return;
    if (this.fallbackFactory && this.callbacks) {
      try {
        this.fallbackSSE = this.fallbackFactory(this.activeTaskId, this.callbacks);
      } catch (e) {
        console.warn('[Project WS] Fallback factory error:', e);
      }
    }
  }

  private clearStableConnectionTimer() {
    if (this.stableConnectionTimeout) clearTimeout(this.stableConnectionTimeout);
    this.stableConnectionTimeout = null;
  }

  private reportTransport(message: string) {
    this.callbacks?.onEvent({type:'transport.status', timestamp:Date.now(), data:{message}});
  }

  /**
   * Disconnects the WebSocket channel and cancels pending reconnects.
   */
  public disconnect() {
    this.isClosed = true;
    this.clearStableConnectionTimer();
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
    if (this.socket) {
      try {
        this.socket.close();
      } catch (_) {}
      this.socket = null;
    }
    if (this.fallbackSSE) {
      try {
        this.fallbackSSE.disconnect();
      } catch (_) {}
      this.fallbackSSE = null;
    }
    this.projectId = null;
    this.activeTaskId = null;
    this.callbacks = null;
    this.lastEventId = 0;
  }
}

export const projectWsClient = new ProjectWebSocketClient();
