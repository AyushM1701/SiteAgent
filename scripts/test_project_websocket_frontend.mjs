// scripts/test_project_websocket_frontend.mjs
// Verifies frontend Vite proxy config and ProjectWebSocketClient behaviors

import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT = path.resolve(__dirname, '..');

// ── Test 1: Vite Proxy Configuration ─────────────────────────────────────────
console.log('--- Test 1: Verify Vite dev server /ws proxy configuration ---');
const viteConfigContent = fs.readFileSync(path.join(ROOT, 'frontend', 'vite.config.ts'), 'utf-8');

assert.match(viteConfigContent, /'\/ws':\s*\{/, "Vite config must define '/ws' proxy entry");
assert.match(viteConfigContent, /target:\s*['"]ws:\/\/127\.0\.0\.1:5002['"]/, "Vite /ws proxy target must be ws://127.0.0.1:5002");
assert.match(viteConfigContent, /ws:\s*true/, "Vite /ws proxy must enable ws: true");
assert.match(viteConfigContent, /changeOrigin:\s*true/, "Vite /ws proxy must set changeOrigin: true");
console.log('✓ Vite /ws proxy configuration verified!');

// ── Setup Mock Environment for WebSocket Client ──────────────────────────────
class MockWebSocket {
  static OPEN = 1;
  static CLOSED = 3;

  constructor(url) {
    this.url = url;
    this.readyState = MockWebSocket.OPEN;
    this.sent = [];
    setTimeout(() => {
      if (this.onopen) this.onopen();
    }, 5);
  }

  send(data) {
    this.sent.push(JSON.parse(data));
  }

  close() {
    this.readyState = MockWebSocket.CLOSED;
    if (this.onclose) this.onclose({ code: 1000, reason: 'Normal Closure' });
  }

  receive(data) {
    if (this.onmessage) {
      this.onmessage({ data: typeof data === 'string' ? data : JSON.stringify(data) });
    }
  }
}

globalThis.WebSocket = MockWebSocket;
globalThis.window = {
  location: {
    protocol: 'http:',
    host: 'localhost:5173',
  },
};

const { ProjectWebSocketClient } = await import('../frontend/src/services/project-ws.ts');

// ── Test 2: Project WebSocket Connection and Monotonic Sequence Numbers ───────
console.log('--- Test 2: Connection URL & Monotonic Sequence Number Tracking ---');
const client = new ProjectWebSocketClient();
const receivedEvents = [];

client.connect('proj-test-101', {
  onEvent: (event) => receivedEvents.push(event),
  onResult: () => {},
  onDone: () => {},
});

// Wait for onopen
await new Promise((r) => setTimeout(r, 20));
assert.equal(client.getProjectId(), 'proj-test-101');
assert.equal(client.getLastEventId(), 0);

// Simulate server sending initial greeting
client['socket'].receive({
  type: 'connection.ready',
  project_id: 'proj-test-101',
  latest_seq: 0,
});

// Simulate server sending events with monotonic seq 1, 2, 3
client['socket'].receive({
  type: 'agent.status',
  seq: 1,
  data: { status: 'Planning' },
});
assert.equal(client.getLastEventId(), 1);

client['socket'].receive({
  type: 'activity.started',
  seq: 2,
  data: { activity: 'Building layout' },
});
assert.equal(client.getLastEventId(), 2);

client['socket'].receive({
  type: 'task.started',
  seq: 3,
  data: { task_id: 't-1', mode: 'site' },
});
assert.equal(client.getLastEventId(), 3);

// Verify monotonically advancing sequence
assert.equal(receivedEvents.length, 3);
assert.equal(receivedEvents[0].seq, 1);
assert.equal(receivedEvents[1].seq, 2);
assert.equal(receivedEvents[2].seq, 3);
console.log('✓ Monotonic sequence tracking verified!');

// ── Test 3: Bidirectional Client Messages ─────────────────────────────────────
console.log('--- Test 3: Bidirectional Client Message Dispatch ---');
client.sendTaskStart('Create a dashboard', 'site', { style_preset: 'modern' });
client.sendPromptQueue('Add dark mode switch');
client.sendPreviewSelection({ component: 'Header', elementId: 'logo' });
client.sendTaskCancel('user_stopped');

const sent = client['socket'].sent;
assert.equal(sent.length, 4);

assert.equal(sent[0].type, 'task.start');
assert.equal(sent[0].prompt, 'Create a dashboard');
assert.equal(sent[0].mode, 'site');

assert.equal(sent[1].type, 'prompt.queue');
assert.equal(sent[1].prompt, 'Add dark mode switch');

assert.equal(sent[2].type, 'preview.selection');
assert.equal(sent[2].selection.component, 'Header');

assert.equal(sent[3].type, 'task.cancel');
assert.equal(sent[3].reason, 'user_stopped');

console.log('✓ Bidirectional client messages verified!');

// ── Test 4: Reconnect and Missed Event Replay ────────────────────────────────
console.log('--- Test 4: Reconnect URL with lastEventId & Replay on subscribe.events ---');
// Remember current lastEventId was 3
assert.equal(client.getLastEventId(), 3);

// Simulate socket reconnecting
client.connect('proj-test-101', {
  onEvent: (event) => receivedEvents.push(event),
}, 'task-abc');

assert.match(client['socket'].url, /\?lastEventId=3$/, 'Reconnection URL must include ?lastEventId=3 query param');

// Wait for onopen
await new Promise((r) => setTimeout(r, 20));
const reconnectSent = client['socket'].sent;
assert.ok(reconnectSent.some((m) => m.type === 'subscribe.events' && m.lastEventId === 3), 'Must send subscribe.events on reconnect');

// Simulate server replaying missed events 4 and 5
client['socket'].receive({
  type: 'file.created',
  seq: 4,
  data: { path: 'src/Dashboard.tsx' },
});
client['socket'].receive({
  type: 'preview.ready',
  seq: 5,
  data: { url: 'http://localhost:5173' },
});

assert.equal(client.getLastEventId(), 5);
console.log('✓ Reconnect with missed event replay verified!');

// ── Test 5: Fallback to SSE when WebSocket Fails ─────────────────────────────
console.log('--- Test 5: Graceful SSE Fallback ---');
let fallbackTriggered = false;
client.setFallbackFactory((taskId, cb) => {
  fallbackTriggered = true;
  return { disconnect() {} };
});

// Force mock socket failure
client['startSSEFallback']();
assert.equal(fallbackTriggered, true, 'Fallback to SSE must be triggered when WebSocket is unavailable');
console.log('✓ SSE fallback mechanism verified!');

client.disconnect();
assert.equal(client.getProjectId(), null);
assert.equal(client.getLastEventId(), 0);

console.log('✅ ALL FRONTEND WEBSOCKET MIGRATION TESTS PASSED!');
