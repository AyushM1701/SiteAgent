import { api } from './api';

export interface ShellSessionCallbacks {
  onData: (data: string) => void;
  onOpen?: () => void;
  onClose?: (code: number, reason: string) => void;
  onError?: (err: Event) => void;
}

export class ShellClient {
  private socket: WebSocket | null = null;
  private callbacks: ShellSessionCallbacks | null = null;

  public async connect(callbacks: ShellSessionCallbacks) {
    this.disconnect();
    this.callbacks = callbacks;

    try {
      const { ticket, host, port } = await api.getShellToken();
      // If we are in dev with Vite proxy or direct host:
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      // If port is 5001 or through Vite proxy
      const wsUrl = `${protocol}//${host || window.location.hostname}:${port || 5001}/?ticket=${encodeURIComponent(ticket)}`;

      this.socket = new WebSocket(wsUrl);

      this.socket.onopen = () => {
        this.callbacks?.onOpen?.();
      };

      this.socket.onmessage = (event) => {
        this.callbacks?.onData(event.data);
      };

      this.socket.onclose = (e) => {
        this.callbacks?.onClose?.(e.code, e.reason);
        this.socket = null;
      };

      this.socket.onerror = (e) => {
        this.callbacks?.onError?.(e);
      };
    } catch (err: any) {
      console.error('[Shell] Failed to connect to terminal socket:', err);
      callbacks.onData(`\r\n\x1b[31m[Shell Connection Error]\x1b[0m ${err.message}\r\n`);
    }
  }

  public send(data: string) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(data);
    }
  }

  public resize(cols: number, rows: number) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify({ type: 'resize', cols, rows }));
    }
  }

  public disconnect() {
    if (this.socket) {
      try {
        this.socket.close();
      } catch (_) {}
      this.socket = null;
    }
    this.callbacks = null;
  }
}

export const shellClient = new ShellClient();
