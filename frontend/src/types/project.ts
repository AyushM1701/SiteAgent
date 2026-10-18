export interface FrameworkConfig {
  tailwind: boolean;
  three: boolean;
  lucide: boolean;
  packages: string[];
}

export interface SessionSnapshot {
  turn_num: number;
  timestamp: string | number;
  prompt: string;
  files: Record<string, string>;
  visual_score?: number;
  visual_issues?: string[];
  summary?: string;
}

export interface Project {
  id: string;
  title: string;
  description?: string;
  createdAt: string | number;
  updatedAt: string | number;
  turnCount: number;
  mode: 'component' | 'site';
  frameworkConfig?: FrameworkConfig;
  files?: Record<string, string>;
  activeTurn?: number;
  latestVisualScore?: number;
  prompt?: string;
  filePath?: string;
  folderName?: string;
  fullPath?: string;
  uses3D?: boolean;
}
