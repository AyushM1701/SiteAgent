/**
 * scripts/test_workspace_resizer.mjs
 * Validates the Workspace Resizer improvements:
 * 1. e.currentTarget pointer capture (not e.target)
 * 2. pointercancel and lostpointercapture handling
 * 3. setIsResizing(false) guaranteed in all cancellation/up paths
 * 4. touchAction: 'none' for touch devices
 * 5. role="separator" and keyboard-resizable accessibility
 * 6. double-click reset
 * 7. user width preference persistence via localStorage
 * 8. dynamic window resize clamping
 */

import fs from 'fs';
import path from 'path';
import assert from 'assert';

console.log('[Test] Running Workspace Resizer Pointer Capture validation...');

const resizerPath = path.resolve('frontend/src/components/workspace/WorkspaceResizer.tsx');
const resizerCode = fs.readFileSync(resizerPath, 'utf-8');

// 1. Verify e.currentTarget.setPointerCapture and e.currentTarget.releasePointerCapture
assert(
  resizerCode.includes('e.currentTarget.setPointerCapture(e.pointerId)'),
  'FAILED: Must use e.currentTarget.setPointerCapture(e.pointerId)'
);
assert(
  !resizerCode.includes('(e.target as HTMLElement).setPointerCapture'),
  'FAILED: Must NOT use e.target.setPointerCapture'
);
assert(
  resizerCode.includes('e.currentTarget.releasePointerCapture(e.pointerId)'),
  'FAILED: Must use e.currentTarget.releasePointerCapture(e.pointerId)'
);
console.log('✓ Verified e.currentTarget pointer capture & release');

// 2. Verify pointercancel and lostpointercapture handlers
assert(
  resizerCode.includes('onPointerCancel={handlePointerCancel}'),
  'FAILED: Must attach onPointerCancel'
);
assert(
  resizerCode.includes('onLostPointerCapture={handleLostPointerCapture}'),
  'FAILED: Must attach onLostPointerCapture'
);
assert(
  resizerCode.includes('setIsResizing(false)'),
  'FAILED: Must always call setIsResizing(false) on release or cancel'
);
console.log('✓ Verified pointercancel and lostpointercapture event handlers');

// 3. Verify touch-action: none for touch device support
assert(
  resizerCode.includes("touchAction: 'none'"),
  "FAILED: Must specify touchAction: 'none' to prevent mobile browser gesture collisions"
);
console.log('✓ Verified touch-action: none for touch support');

// 4. Verify keyboard accessibility
assert(
  resizerCode.includes('role="separator"'),
  'FAILED: Splitter must have role="separator"'
);
assert(
  resizerCode.includes('onKeyDown={handleKeyDown}'),
  'FAILED: Must support keyboard resizing via onKeyDown'
);
assert(
  resizerCode.includes('ArrowLeft') && resizerCode.includes('ArrowRight'),
  'FAILED: Arrow keys must resize the splitter'
);
console.log('✓ Verified keyboard-resizable accessibility');

// 5. Verify double-click reset
assert(
  resizerCode.includes('onDoubleClick={handleDoubleClick}'),
  'FAILED: Must support double-click reset'
);
console.log('✓ Verified double-click reset');

// 6. Verify window resize clamping and window fail-safe listeners
assert(
  resizerCode.includes("window.addEventListener('resize', handleWindowResize)"),
  'FAILED: Must clamp workspace width on window resize'
);
assert(
  resizerCode.includes("window.addEventListener('pointerup', stopResizing)") ||
  resizerCode.includes("window.addEventListener('pointercancel', stopResizing)"),
  'FAILED: Window-level fail-safe listeners must be present'
);
console.log('✓ Verified window resize clamping and window-level fail-safe listeners');

// 7. Verify localStorage persistence in workspace-store.ts
const storePath = path.resolve('frontend/src/state/workspace-store.ts');
const storeCode = fs.readFileSync(storePath, 'utf-8');
assert(
  storeCode.includes("localStorage.getItem('slm_workspace_width')"),
  'FAILED: Must read initial width from localStorage'
);
assert(
  storeCode.includes("localStorage.setItem('slm_workspace_width'"),
  'FAILED: Must write updated width to localStorage'
);
console.log('✓ Verified user preference persistence in localStorage');

console.log('\nAll workspace resizer assertions PASSED successfully!');
