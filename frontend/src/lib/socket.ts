import type { RunSocketEvent } from '@/types/contracts';

type Handler<TEvent> = (event: TEvent) => void;
type SocketStatus = 'connected' | 'disconnected' | 'reconnecting' | 'dead';
type StatusHandler = (status: SocketStatus) => void;

export class RunSocket<TEvent = RunSocketEvent> {
  private ws: WebSocket | null = null;
  private runId: string;
  private pathPrefix: string;
  private handlers: Array<Handler<TEvent>> = [];
  private statusHandlers: StatusHandler[] = [];
  private retryCount = 0;
  private maxRetries = 10;
  private destroyed = false;
  private retryTimer: ReturnType<typeof setTimeout> | null = null;

  constructor(runId: string, pathPrefix = '/ws/runs') {
    this.runId = runId;
    this.pathPrefix = pathPrefix;
  }

  connect() {
    if (this.destroyed) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const url = `${protocol}//${host}${this.pathPrefix}/${this.runId}`;

    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      this.retryCount = 0;
      this.notifyStatus('connected');
    };

    this.ws.onmessage = (e) => {
      try {
        const event = JSON.parse(e.data) as TEvent;
        this.handlers.forEach(h => h(event));
      } catch (error) {
        console.error('RunSocket failed to parse message', error);
      }
    };

    this.ws.onclose = () => {
      if (this.destroyed) return;
      this.notifyStatus('disconnected');
      this.scheduleReconnect();
    };

    this.ws.onerror = () => {
      this.ws?.close();
    };
  }

  private scheduleReconnect() {
    if (this.retryCount >= this.maxRetries) {
      this.notifyStatus('dead');
      return;
    }
    this.retryCount++;
    const delay = Math.min(1000 * Math.pow(1.5, this.retryCount), 15000);
    this.notifyStatus('reconnecting');
    this.retryTimer = setTimeout(() => {
      if (!this.destroyed) this.connect();
    }, delay);
  }

  onEvent(handler: Handler<TEvent>) {
    this.handlers.push(handler);
    return () => { this.handlers = this.handlers.filter(h => h !== handler); };
  }

  onStatus(handler: StatusHandler) {
    this.statusHandlers.push(handler);
    return () => { this.statusHandlers = this.statusHandlers.filter(h => h !== handler); };
  }

  private notifyStatus(status: SocketStatus) {
    this.statusHandlers.forEach(h => h(status));
  }

  destroy() {
    this.destroyed = true;
    if (this.retryTimer) clearTimeout(this.retryTimer);
    this.ws?.close();
    this.ws = null;
  }
}
