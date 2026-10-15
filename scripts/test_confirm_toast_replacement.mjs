/**
 * test_confirm_toast_replacement.mjs
 * 
 * Verifies Issue #11: Replace Native confirm() and alert()
 * 
 * Tests:
 * 1. Codebase Scan: Assert ZERO instances of window.confirm and window.alert in frontend/src
 * 2. Component Structure: ConfirmDialog and ToastProvider definitions and ARIA contracts
 * 3. 8 Required Use Cases Coverage:
 *    - Delete project (ConfirmDialog)
 *    - Clear projects (ConfirmDialog)
 *    - Cancel all (ConfirmDialog)
 *    - Revert checkpoint (ConfirmDialog)
 *    - Overwrite file (ConfirmDialog)
 *    - Delete file (ConfirmDialog)
 *    - Export failure (ToastProvider)
 *    - Build failure (ToastProvider)
 * 4. Dialog Accessibility & Focus Trap verification
 * 5. Toast Store & Provider verification
 */

import fs from 'fs';
import path from 'path';
import assert from 'assert';

console.log('=== Running Issue #11: ConfirmDialog & ToastProvider Tests ===\n');

const FRONTEND_SRC = path.resolve('frontend/src');

// ── Test 1: Codebase Audit for window.confirm and window.alert ────────────────
console.log('[Test 1] Auditing frontend/src for window.confirm and window.alert...');

function getFilesRecursively(dir) {
  let results = [];
  const list = fs.readdirSync(dir);
  for (const file of list) {
    const filePath = path.join(dir, file);
    const stat = fs.statSync(filePath);
    if (stat && stat.isDirectory()) {
      results = results.concat(getFilesRecursively(filePath));
    } else if (file.endsWith('.ts') || file.endsWith('.tsx') || file.endsWith('.js') || file.endsWith('.jsx')) {
      results.push(filePath);
    }
  }
  return results;
}

const allFrontendFiles = getFilesRecursively(FRONTEND_SRC);
let forbiddenFound = [];

for (const file of allFrontendFiles) {
  const content = fs.readFileSync(file, 'utf-8');
  const lines = content.split('\n');
  lines.forEach((line, index) => {
    // Check for native window.confirm or window.alert
    if (/window\.confirm\s*\(/.test(line)) {
      forbiddenFound.push({ file, line: index + 1, match: 'window.confirm', text: line.trim() });
    }
    if (/window\.alert\s*\(/.test(line)) {
      forbiddenFound.push({ file, line: index + 1, match: 'window.alert', text: line.trim() });
    }
    // Check for raw alert(...) calls (excluding CSS or attributes)
    if (/(?<![\.\w])alert\s*\(/.test(line) && !line.includes('role="alertdialog"') && !line.includes('alert_dialog')) {
      forbiddenFound.push({ file, line: index + 1, match: 'alert()', text: line.trim() });
    }
  });
}

assert.strictEqual(forbiddenFound.length, 0, `Found forbidden native dialogs: ${JSON.stringify(forbiddenFound, null, 2)}`);
console.log(`  ✓ Checked ${allFrontendFiles.length} files: 0 native confirm() or alert() calls found.\n`);

// ── Test 2: ConfirmDialog Component & ARIA Accessibility Contract ─────────────
console.log('[Test 2] Verifying ConfirmDialog Component & ARIA Attributes...');

const confirmDialogPath = path.join(FRONTEND_SRC, 'components/common/ConfirmDialog.tsx');
assert.ok(fs.existsSync(confirmDialogPath), 'ConfirmDialog.tsx must exist');
const confirmDialogCode = fs.readFileSync(confirmDialogPath, 'utf-8');

assert.ok(confirmDialogCode.includes('role="alertdialog"'), 'ConfirmDialog must have role="alertdialog"');
assert.ok(confirmDialogCode.includes('aria-modal="true"'), 'ConfirmDialog must have aria-modal="true"');
assert.ok(confirmDialogCode.includes('aria-labelledby='), 'ConfirmDialog must link aria-labelledby to title');
assert.ok(confirmDialogCode.includes('aria-describedby='), 'ConfirmDialog must link aria-describedby to message');

// Keyboard Focus Trap checks
assert.ok(confirmDialogCode.includes("e.key === 'Tab'"), 'ConfirmDialog must trap Tab key navigation');
assert.ok(confirmDialogCode.includes("e.shiftKey"), 'ConfirmDialog must handle Shift+Tab reverse wrapping');
assert.ok(confirmDialogCode.includes("e.key === 'Escape'"), 'ConfirmDialog must handle Escape to close/cancel');

// Defensive initial focus check for destructive actions
assert.ok(
  confirmDialogCode.includes("variant === 'danger'") && confirmDialogCode.includes("cancelBtnRef.current?.focus()"),
  'ConfirmDialog must focus cancel button first for danger/destructive actions to prevent accidental Enter'
);

console.log('  ✓ ConfirmDialog includes role="alertdialog", focus trapping, Escape handling, and safe default focus.\n');

// ── Test 3: ToastProvider Component & Accessibility Contract ──────────────────
console.log('[Test 3] Verifying ToastProvider Component & Accessibility...');

const toastProviderPath = path.join(FRONTEND_SRC, 'components/common/ToastProvider.tsx');
assert.ok(fs.existsSync(toastProviderPath), 'ToastProvider.tsx must exist');
const toastProviderCode = fs.readFileSync(toastProviderPath, 'utf-8');

assert.ok(toastProviderCode.includes('aria-live="polite"'), 'ToastProvider must have aria-live="polite"');
assert.ok(toastProviderCode.includes('role="status"'), 'Toasts must have role="status"');
assert.ok(toastProviderCode.includes('removeToast'), 'Toasts must support manual dismissal');

const toastStorePath = path.join(FRONTEND_SRC, 'state/toast-store.ts');
assert.ok(fs.existsSync(toastStorePath), 'toast-store.ts must exist');
const toastStoreCode = fs.readFileSync(toastStorePath, 'utf-8');
assert.ok(toastStoreCode.includes('duration'), 'Toasts must support auto-dismissal durations');

console.log('  ✓ ToastProvider includes aria-live="polite", role="status", and reactive store.\n');

// ── Test 4: Verify All 8 Required Use Cases ───────────────────────────────────
console.log('[Test 4] Verifying All 8 Required Use Cases...');

// Use Case 1: Delete project
const projectSidebarCode = fs.readFileSync(path.join(FRONTEND_SRC, 'components/projects/ProjectSidebar.tsx'), 'utf-8');
assert.ok(
  projectSidebarCode.includes("title: 'Delete Project'") && projectSidebarCode.includes("variant: 'danger'"),
  'ProjectSidebar must use confirm() for Delete Project with danger variant'
);
console.log('  ✓ 1. Delete project -> ConfirmDialog (danger variant)');

// Use Case 2: Clear projects
assert.ok(
  projectSidebarCode.includes("title: 'Clear All Projects'") && projectSidebarCode.includes("variant: 'danger'"),
  'ProjectSidebar must use confirm() for Clear All Projects with danger variant'
);
console.log('  ✓ 2. Clear projects -> ConfirmDialog (danger variant)');

// Use Case 3: Cancel all
const topBarCode = fs.readFileSync(path.join(FRONTEND_SRC, 'components/topbar/TopBar.tsx'), 'utf-8');
assert.ok(
  topBarCode.includes("title: 'Cancel All Tasks'") && topBarCode.includes("variant: 'danger'"),
  'TopBar must use confirm() for Cancel All Tasks with danger variant'
);
console.log('  ✓ 3. Cancel all -> ConfirmDialog (danger variant)');

// Use Case 4: Revert checkpoint
const diffTabCode = fs.readFileSync(path.join(FRONTEND_SRC, 'components/workspace/DiffTab.tsx'), 'utf-8');
assert.ok(
  diffTabCode.includes("title: 'Revert Checkpoint'") && diffTabCode.includes("variant: 'danger'"),
  'DiffTab must use confirm() for Revert Checkpoint with danger variant'
);
console.log('  ✓ 4. Revert checkpoint -> ConfirmDialog (danger variant)');

// Use Case 5: Overwrite file
const codeTabCode = fs.readFileSync(path.join(FRONTEND_SRC, 'components/workspace/CodeTab.tsx'), 'utf-8');
assert.ok(
  codeTabCode.includes("title: 'Overwrite File'") && codeTabCode.includes("variant: 'warning'"),
  'CodeTab must use confirm() for Overwrite File with warning variant'
);
console.log('  ✓ 5. Overwrite file -> ConfirmDialog (warning variant)');

// Use Case 6: Delete file
assert.ok(
  codeTabCode.includes("title: 'Delete File'") && codeTabCode.includes("variant: 'danger'"),
  'CodeTab must use confirm() for Delete File with danger variant'
);
console.log('  ✓ 6. Delete file -> ConfirmDialog (danger variant)');

// Use Case 7: Export failure
assert.ok(
  codeTabCode.includes("toast.error('Export Failure'"),
  'CodeTab must use toast.error for Export Failure'
);
console.log('  ✓ 7. Export failure -> ToastProvider (toast.error)');

// Use Case 8: Build failure
assert.ok(
  codeTabCode.includes("toast.error('Build Failure'"),
  'CodeTab must use toast.error for Build Failure'
);
console.log('  ✓ 8. Build failure -> ToastProvider (toast.error)');

// ── Test 5: Global Mount in App.tsx ───────────────────────────────────────────
console.log('\n[Test 5] Verifying Global Mount in App.tsx...');
const appCode = fs.readFileSync(path.join(FRONTEND_SRC, 'app/App.tsx'), 'utf-8');
assert.ok(appCode.includes('<ConfirmDialog />') || appCode.includes('<ConfirmDialog'), 'App.tsx must mount ConfirmDialog');
assert.ok(appCode.includes('<ToastProvider />') || appCode.includes('<ToastProvider'), 'App.tsx must mount ToastProvider');
console.log('  ✓ ConfirmDialog and ToastProvider are mounted at top-level in App.tsx');

console.log('\n=== ALL 5 TEST SUITES PASSED SUCCESSFULLY ===');
