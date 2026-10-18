export type LogLevel = 'info' | 'warn' | 'error' | 'debug';
export type LogCategory = 'agent' | 'build' | 'compiler' | 'shell' | 'network' | 'motion' | 'all';

export interface LogEntry {
  id: string;
  timestamp: number;
  timeStr: string;
  level: LogLevel;
  category: LogCategory;
  message: string;
  meta?: Record<string, any>;
  /** Server event sequence number, used to drop duplicate deliveries. */
  seq?: number;
}

/** Map a server event into a log entry (server timestamps are in seconds). */
export function logEntryFromEvent(event: { type?: string; timestamp?: number; log?: string; seq?: number }): Omit<LogEntry, 'id' | 'timeStr'> | null {
  if (!event.log) return null;
  const type = event.type || '';
  const raw = event.timestamp || Date.now();
  const level: LogLevel = /error|fail/.test(type) ? 'error' : /warn/.test(type) ? 'warn' : 'info';
  const category: LogCategory = type.startsWith('command') ? 'shell'
    : type.startsWith('build') ? 'build'
    : type.includes('motion') ? 'motion'
    : type.includes('compile') || type.includes('typecheck') ? 'compiler'
    : 'agent';
  // Server log lines start with their own HH:MM:SS stamp; the Logs tab shows the time separately.
  const message = event.log.replace(/^\d{2}:\d{2}:\d{2}\s+/, '');
  return { timestamp: raw < 1e12 ? raw * 1000 : raw, level, category, message, seq: event.seq };
}
