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
}
