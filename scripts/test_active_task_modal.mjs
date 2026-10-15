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
import { requestNewProject, startNewProject } from '../frontend/src/services/session.ts';
import { api } from '../frontend/src/services/api.ts';

console.log('--- Test 1: requestNewProject() when agent is idle ---');
useAgentStore.getState().resetAgent();
useWorkspaceStore.getState().clearWorkspace();
useProjectStore.getState().addProject({
  id: 'proj-idle',
  title: 'Idle Project',
  createdAt: Date.now(),
  updatedAt: Date.now(),
  turnCount: 1,
  mode: 'component'
});
useProjectStore.getState().setCurrentProjectId('proj-idle');

assert.equal(useAgentStore.getState().status, 'idle');
assert.equal(useWorkspaceStore.getState().activeTaskModalOpen, false);

requestNewProject();

// Should have reset immediately without opening modal
assert.equal(useWorkspaceStore.getState().activeTaskModalOpen, false, 'Modal should remain closed when idle');
assert.equal(useProjectStore.getState().currentProjectId, null, 'currentProjectId should be reset to null');

console.log('✓ Idle transition verified!');

console.log('--- Test 2: requestNewProject() when generation is running ---');
useProjectStore.getState().setCurrentProjectId('proj-active');
useAgentStore.getState().setStatus('generating');
useAgentStore.getState().setActiveTaskId('task-gpu-1');

requestNewProject();

// Modal MUST be open, and session state must NOT be cleared yet
assert.equal(useWorkspaceStore.getState().activeTaskModalOpen, true, 'Modal must open during active generation');
assert.equal(useProjectStore.getState().currentProjectId, 'proj-active', 'Project should NOT be reset before user confirmation');

console.log('✓ Active generation conflict modal trigger verified!');

console.log('--- Test 3: Option "Stay here" ---');
// User clicks "Stay here"
useWorkspaceStore.getState().closeActiveTaskModal();
assert.equal(useWorkspaceStore.getState().activeTaskModalOpen, false);
assert.equal(useAgentStore.getState().status, 'generating');
assert.equal(useProjectStore.getState().currentProjectId, 'proj-active');

console.log('✓ "Stay here" leaves session and task intact!');

console.log('--- Test 4: Option "Cancel and start new project" ---');
// Track api.cancelTask call
let cancelledTaskId = null;
let cancelOptions = null;
api.cancelTask = async (taskId, opts) => {
  cancelledTaskId = taskId;
  cancelOptions = opts;
};

// Reopen modal
useWorkspaceStore.getState().openActiveTaskModal();
assert.equal(useWorkspaceStore.getState().activeTaskModalOpen, true);

// Execute Cancel and start new project flow
await api.cancelTask(useAgentStore.getState().activeTaskId, { clear_queue: true });
useWorkspaceStore.getState().closeActiveTaskModal();
startNewProject();

assert.equal(cancelledTaskId, 'task-gpu-1', 'Backend task must be cancelled');
assert.equal(cancelOptions?.clear_queue, true, 'clear_queue must be passed as true');
assert.equal(useWorkspaceStore.getState().activeTaskModalOpen, false, 'Modal must be closed');
assert.equal(useProjectStore.getState().currentProjectId, null, 'Project state must be cleanly reset');
assert.equal(useAgentStore.getState().status, 'idle', 'Agent status must be idle');

console.log('✓ "Cancel and start new project" cancels task, clears queue, and resets session!');

console.log('--- Test 5: Option "Keep running in background" ---');
// Set active generation again
useProjectStore.getState().setCurrentProjectId('proj-bg');
useAgentStore.getState().setStatus('generating');
useAgentStore.getState().setActiveTaskId('task-gpu-2');
cancelledTaskId = null;

// Reopen modal
useWorkspaceStore.getState().openActiveTaskModal();
assert.equal(useWorkspaceStore.getState().activeTaskModalOpen, true);

// User picks "Keep running in background"
useWorkspaceStore.getState().closeActiveTaskModal();
startNewProject();

assert.equal(cancelledTaskId, null, 'Backend task should NOT be cancelled when keeping in background');
assert.equal(useWorkspaceStore.getState().activeTaskModalOpen, false, 'Modal must be closed');
assert.equal(useProjectStore.getState().currentProjectId, null, 'UI resets into new project');

console.log('✓ "Keep running in background" transitions UI while leaving backend task running!');

console.log('✅ ALL FRONTEND MODAL & CONFLICT WORKFLOW TESTS PASSED!');
