// Mock browser environment for zustand stores
globalThis.localStorage = {
  _store: {},
  getItem(k) { return this._store[k] ?? null; },
  setItem(k, v) { this._store[k] = String(v); },
  removeItem(k) { delete this._store[k]; }
};
globalThis.document = {
  documentElement: {
    setAttribute() {},
    classList: { add() {}, remove() {} }
  }
};
globalThis.window = globalThis;

import assert from 'node:assert/strict';
import { useWorkspaceStore } from '../frontend/src/state/workspace-store.ts';
import { useAgentStore } from '../frontend/src/state/agent-store.ts';
import { useProjectStore } from '../frontend/src/state/project-store.ts';
import { useSelectionStore } from '../frontend/src/state/selection-store.ts';
import { useChatStore } from '../frontend/src/state/chat-store.ts';
import { startNewProject } from '../frontend/src/services/session.ts';

console.log('--- Setting dirty / active project state ---');

// 1. Workspace store
useWorkspaceStore.getState().setFiles({ 'src/App.tsx': 'export default function App() {}' });
useWorkspaceStore.getState().setActiveFile('src/App.tsx');
useWorkspaceStore.getState().setDiff('before', 'after', 3, 'src/App.tsx');
useWorkspaceStore.getState().addLog({ timestamp: Date.now(), level: 'info', category: 'agent', message: 'Building component' }, 'proj-123');
useWorkspaceStore.getState().setLogFilterLevel('error');
useWorkspaceStore.getState().setLogFilterCategory('compiler');
useWorkspaceStore.getState().setLogSearch('crash');
useWorkspaceStore.getState().setWorkspaceOpen(true);
useWorkspaceStore.getState().setInspectorOpen(true);

// 2. Project store
useProjectStore.getState().addProject({
  id: 'proj-123',
  title: 'Test Project',
  createdAt: Date.now(),
  updatedAt: Date.now(),
  turnCount: 4,
  mode: 'component'
});
useProjectStore.getState().setCurrentProjectId('proj-123');

// 3. Agent store
useAgentStore.getState().setStatus('repairing', 'Repairing layout');
useAgentStore.getState().setActiveTaskId('task-999');
useAgentStore.getState().setValidationResult({
  typecheck_passed: true,
  build_passed: true,
  lint_passed: true,
  runtime_passed: true,
  preview_running: true,
  passed: true,
  errors: [],
  warnings: [],
  repair_attempts: 2
});
useAgentStore.getState().applyEvent({
  type: 'activity.started',
  data: { activity: 'Repairing component' }
});
// Global state
useAgentStore.getState().setSystemStatus({
  modelLoaded: true,
  gpuReady: true,
  serverConnected: true
});

// 4. Selection store
useSelectionStore.getState().setSelectedElement({
  type: 'dom',
  tagName: 'BUTTON',
  selector: '#cta-btn'
});
useSelectionStore.getState().setInspectMode('dom');

// 5. Chat store
useChatStore.getState().addMessage({
  id: 'msg-1',
  role: 'user',
  content: 'Make a hero section',
  timestamp: Date.now()
});

// Verify state is populated before reset
assert.equal(useProjectStore.getState().currentProjectId, 'proj-123');
assert.equal(Object.keys(useWorkspaceStore.getState().files).length, 1);
assert.equal(useWorkspaceStore.getState().logs.length, 1);
assert.equal(useWorkspaceStore.getState().workspaceOpen, true);
assert.equal(useWorkspaceStore.getState().inspectorOpen, true);
assert.notEqual(useSelectionStore.getState().selectedElement, null);
assert.equal(useChatStore.getState().messages.length, 1);

console.log('--- Triggering startNewProject() ---');
startNewProject();

console.log('--- Verifying Acceptance Criteria ---');

// Criteria 1: currentProjectId = null
assert.equal(useProjectStore.getState().currentProjectId, null, 'currentProjectId must be null');
assert.equal(useProjectStore.getState().currentProject, null, 'currentProject must be null');

// Criteria 2: files = {}
assert.deepEqual(useWorkspaceStore.getState().files, {}, 'files must be empty object {}');
assert.equal(useWorkspaceStore.getState().activeFile, '', 'activeFile must be empty');

// Criteria 3: messages = []
assert.deepEqual(useChatStore.getState().messages, [], 'messages must be empty array []');
assert.deepEqual(useChatStore.getState().queuedPrompts, [], 'queuedPrompts must be empty array []');

// Criteria 4: logs = []
assert.deepEqual(useWorkspaceStore.getState().logs, [], 'active logs must be empty array []');
assert.equal(useWorkspaceStore.getState().logFilterLevel, 'all', 'logFilterLevel must be reset to "all"');
assert.equal(useWorkspaceStore.getState().logFilterCategory, 'all', 'logFilterCategory must be reset to "all"');
assert.equal(useWorkspaceStore.getState().logSearch, '', 'logSearch must be reset to empty string');

// Criteria 5: selection = null
assert.equal(useSelectionStore.getState().selectedElement, null, 'selectedElement must be null');
assert.equal(useSelectionStore.getState().selected3DObject, null, 'selected3DObject must be null');
assert.equal(useSelectionStore.getState().inspectMode, 'none', 'inspectMode must be "none"');

// Criteria 6: visualScore = null / undefined & turn metrics = 0
assert.equal(useAgentStore.getState().metrics.visualScore, undefined, 'visualScore must be undefined/null');
assert.equal(useAgentStore.getState().metrics.repairAttempts, 0, 'repairAttempts must be 0');
assert.equal(useAgentStore.getState().metrics.turnCount, 0, 'turnCount must be 0');
assert.equal(useAgentStore.getState().metrics.toolCallsCount, 0, 'toolCallsCount must be 0');

// Criteria 7: workspace closed
assert.equal(useWorkspaceStore.getState().workspaceOpen, false, 'workspace drawer must be closed');

// Criteria 8: Inspector project state cleared
assert.equal(useWorkspaceStore.getState().inspectorOpen, false, 'inspector drawer must be closed');
assert.equal(useAgentStore.getState().validationResult, null, 'validationResult must be null');
assert.equal(useAgentStore.getState().status, 'idle', 'agent status must be idle');
assert.equal(useAgentStore.getState().activeTaskId, null, 'activeTaskId must be null');

// Criteria 9: Diff selection cleared
assert.equal(useWorkspaceStore.getState().diffOriginal, '', 'diffOriginal must be empty');
assert.equal(useWorkspaceStore.getState().diffModified, '', 'diffModified must be empty');
assert.equal(useWorkspaceStore.getState().diffTurn, 0, 'diffTurn must be 0');
assert.equal(useWorkspaceStore.getState().diffFilename, '', 'diffFilename must be empty');

// Criteria 10: Preserve only global state
assert.equal(useAgentStore.getState().modelLoaded, true, 'global modelLoaded must be preserved');
assert.equal(useAgentStore.getState().gpuReady, true, 'global gpuReady must be preserved');
assert.equal(useAgentStore.getState().serverConnected, true, 'global serverConnected must be preserved');
assert.equal(useWorkspaceStore.getState().theme, 'dark', 'theme preference must be preserved');

console.log('✅ ALL ACCEPTANCE CRITERIA VERIFIED SUCCESSFULLY!');
