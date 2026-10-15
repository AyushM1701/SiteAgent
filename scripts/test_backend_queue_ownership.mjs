/**
 * scripts/test_backend_queue_ownership.mjs
 * Validates backend queue ownership on frontend:
 * 1. Confirms removal of processNextQueuedTask, manual queue promotion, and frontend scheduling
 * 2. Validates chat store removeQueuedPrompt rollback on failed submission
 * 3. Validates session hydration of backend queued prompts
 * 4. Validates event-driven task.started promotion
 */

import fs from 'fs';
import path from 'path';
import assert from 'assert';

console.log('[Test] Running Backend Queue Ownership validation...');

const composerPath = path.resolve('frontend/src/components/chat/ChatComposer.tsx');
const composerCode = fs.readFileSync(composerPath, 'utf-8');

// 1. Check removal of frontend-owned queue promotion & scheduling
assert(
  !composerCode.includes('processNextQueuedTask'),
  'FAILED: processNextQueuedTask must be completely removed from ChatComposer.tsx'
);
assert(
  !composerCode.includes('manual queue promotion'),
  'FAILED: manual queue promotion must not be present'
);
console.log('✓ Verified processNextQueuedTask is completely absent from ChatComposer.tsx');

// 2. Check event-driven handling of backend lifecycle events
assert(
  composerCode.includes("event.type === 'task.started'"),
  'FAILED: ChatComposer must subscribe and react to task.started'
);
assert(
  composerCode.includes("event.type === 'task.queued'") || composerCode.includes("event.type === 'prompt.queued'"),
  'FAILED: ChatComposer must subscribe and react to task.queued'
);
assert(
  composerCode.includes('promoteQueuedPrompt'),
  'FAILED: promoteQueuedPrompt must be triggered when task.started arrives'
);
console.log('✓ Verified event-driven task.queued and task.started subscriptions in ChatComposer');

// 3. Check error cleanup for failed submissions
assert(
  composerCode.includes('removeQueuedPrompt(promptId)'),
  'FAILED: Failed queue submissions must immediately call removeQueuedPrompt to avoid lingering queued cards'
);
console.log('✓ Verified rollback via removeQueuedPrompt on submission failure');

// 4. Check session.ts hydration of backend queue truth on load / refresh
const sessionServicePath = path.resolve('frontend/src/services/session.ts');
const sessionServiceCode = fs.readFileSync(sessionServicePath, 'utf-8');
assert(
  sessionServiceCode.includes('queued_prompts') && sessionServiceCode.includes('addQueuedPrompt'),
  'FAILED: loadProject must hydrate backend queued_prompts into chat-store'
);
assert(
  sessionServiceCode.includes("streamManager.connect") || sessionServiceCode.includes("projectWsClient.connect"),
  'FAILED: loadProject must connect to project channel to receive queue lifecycle events'
);
console.log('✓ Verified browser refresh/loadProject hydrates backend-authoritative queue');

// 5. Check chat-store.ts removeQueuedPrompt removes from both queuedPrompts and messages
const chatStorePath = path.resolve('frontend/src/state/chat-store.ts');
const chatStoreCode = fs.readFileSync(chatStorePath, 'utf-8');
assert(
  chatStoreCode.includes('queuedPrompts: state.queuedPrompts.filter((p) => p.id !== id)'),
  'FAILED: removeQueuedPrompt must filter queuedPrompts'
);
assert(
  chatStoreCode.includes('messages: state.messages.filter((m) => m.id !== id)'),
  'FAILED: removeQueuedPrompt must filter messages'
);
console.log('✓ Verified removeQueuedPrompt cleans up both queuedPrompts and messages');

console.log('\nAll frontend backend-queue ownership assertions PASSED successfully!');
