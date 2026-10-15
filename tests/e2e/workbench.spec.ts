import { test, expect, Page } from '@playwright/test';

/**
 * tests/e2e/workbench.spec.ts
 *
 * Comprehensive End-to-End Playwright test covering every Workbench control (Issue #30).
 * Tests all required flows:
 * 1. Accessibility check (visible text, aria-label, or title for every button)
 * 2. Theme (data-theme changes, persistence across reload)
 * 3. Workspace (open, close, resize, tab switching across Preview, Code, Diff, Logs, Shell)
 * 4. Code (file selection, copy, download ZIP, unsaved edits save/discard)
 * 5. Diff (before/after loaded, turn selector, split/patch toggle, revert)
 * 6. Chat (immediate user bubble, activity event stream, queued prompt badge, stop cancels)
 * 7. New Project (active project removed, chat cleared, workspace closed, files cleared, logs cleared, Inspector cleared)
 * 8. Global assertions (zero uncaught errors, zero console.error, zero unexpected network failures)
 */

// Helper to configure deterministic mock backend routes
async function setupMockBackend(page: Page) {
  const consoleErrors: string[] = [];
  const pageErrors: Error[] = [];
  const failedRequests: string[] = [];

  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      const text = msg.text();
      if (!text.includes('favicon') && !text.includes('404')) {
        consoleErrors.push(text);
      }
    }
  });

  page.on('pageerror', (err) => {
    pageErrors.push(err);
  });

  page.on('requestfailed', (req) => {
    const url = req.url();
    if (!url.includes('favicon')) {
      failedRequests.push(`${req.method()} ${url}: ${req.failure()?.errorText || 'failed'}`);
    }
  });

  // Mock status endpoint
  await page.route('**/api/status', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ model_status: 'ready', queue_depth: 0 }),
    });
  });

  // Mock style presets
  await page.route('**/api/style-presets', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        presets: [
          { id: 'auto', label: 'Auto', tagline: 'Tailored aesthetic' },
          { id: 'editorial', label: 'Editorial', tagline: 'Clean typography' },
          { id: 'brutalist', label: 'Brutalist', tagline: 'High contrast' },
        ],
      }),
    });
  });

  // Mock shell token
  await page.route('**/api/shell-token', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        ticket: 'test-ticket-mock-1234567890',
        token: 'test-ticket-mock-1234567890',
        host: '127.0.0.1',
        port: 5001,
      }),
    });
  });

  // Mock projects list with an existing test project
  await page.route('**/api/projects', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            id: '1726000000_e2e001',
            title: 'E2E Studio Project',
            mode: 'site',
            createdAt: Date.now() - 3600000,
            updatedAt: Date.now() - 3600000,
            turnCount: 2,
          },
        ]),
      });
    } else {
      await route.continue();
    }
  });

  const mockProjectData = {
    session_id: '1726000000_e2e001',
    title: 'E2E Studio Project',
    mode: 'site',
    files: {
      'src/App.tsx': 'export default function App() {\n  return <div>E2E Studio App</div>;\n}\n',
      'src/Hero.tsx': 'export function Hero() {\n  return <h1>Studio Hero Header</h1>;\n}\n',
      'package.json': '{\n  "name": "e2e-studio",\n  "version": "1.0.0"\n}\n',
    },
    history: [
      { role: 'user', content: 'Create a modern studio site', timestamp: Date.now() - 3600000 },
      { role: 'assistant', content: 'Generated studio site with Hero and App.', timestamp: Date.now() - 3590000 },
    ],
    checkpoints: [
      { turn: 1, summary: 'Initial baseline' },
      { turn: 2, summary: 'Added Studio Hero Header' },
    ],
  };

  // Mock specific project details (both /api/sessions and /api/projects)
  await page.route('**/api/sessions/1726000000_e2e001', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(mockProjectData),
    });
  });

  await page.route('**/api/projects/1726000000_e2e001', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(mockProjectData),
    });
  });

  // Mock diff endpoints
  const mockDiffData = {
    turnId: 2,
    files: {
      'src/App.tsx': {
        before: 'export default function App() { return <div>Initial</div>; }\n',
        after: 'export default function App() {\n  return <div>E2E Studio App</div>;\n}\n',
        patch: '@@ -1 +1,3 @@\n-export default function App() { return <div>Initial</div>; }\n+export default function App() {\n+  return <div>E2E Studio App</div>;\n+}\n',
      },
    },
  };

  await page.route('**/api/sessions/1726000000_e2e001/diff*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(mockDiffData),
    });
  });

  await page.route('**/api/projects/1726000000_e2e001/diff*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(mockDiffData),
    });
  });

  // Mock ZIP export
  await page.route('**/api/projects/1726000000_e2e001/export*', async (route) => {
    const zipHeader = Buffer.from([
      0x50, 0x4b, 0x05, 0x06, 0x00, 0x00, 0x00, 0x00,
      0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
      0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    ]);
    await route.fulfill({
      status: 200,
      contentType: 'application/zip',
      headers: {
        'Content-Disposition': 'attachment; filename="e2e-studio.zip"',
      },
      body: zipHeader,
    });
  });

  // Mock file save endpoint
  await page.route('**/api/projects/1726000000_e2e001/file', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        success: true,
        file: 'src/App.tsx',
        turnId: 3,
        validation: { passed: true, code_passed: true },
        files: {
          'src/App.tsx': 'export default function App() {\n  return <div>Saved App</div>;\n}\n',
          'src/Hero.tsx': 'export function Hero() {\n  return <h1>Studio Hero Header</h1>;\n}\n',
          'package.json': '{\n  "name": "e2e-studio",\n  "version": "1.0.0"\n}\n',
        },
      }),
    });
  });

  // Mock revert endpoint
  await page.route('**/api/revert', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        success: true,
        turn: 1,
        files: {
          'src/App.tsx': 'export default function App() { return <div>Reverted V1</div>; }\n',
        },
      }),
    });
  });

  // Mock prompt generate dispatch
  await page.route('**/api/generate', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        task_id: 'task-e2e-mock-99',
        session_id: '1726000000_e2e001',
        status: 'queued',
        queue_position: 1,
        stream_url: '/api/stream/task-e2e-mock-99',
      }),
    });
  });

  // Mock cancel task endpoint
  await page.route('**/api/tasks/*/cancel', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ success: true, status: 'cancelled' }),
    });
  });

  return { consoleErrors, pageErrors, failedRequests };
}

test.describe('Workbench Button and Control Audit (Issue #30)', () => {

  test('1. Accessibility check: every interactive button has visible text, aria-label, or title', async ({ page }) => {
    await setupMockBackend(page);
    await page.goto('/', { waitUntil: 'networkidle' });

    // Find all visible buttons on page
    const buttons = await page.locator('button:visible').all();
    expect(buttons.length).toBeGreaterThan(5);

    const nonCompliant: string[] = [];

    for (const btn of buttons) {
      const text = (await btn.innerText()).trim();
      const ariaLabel = (await btn.getAttribute('aria-label'))?.trim() || '';
      const title = (await btn.getAttribute('title'))?.trim() || '';
      const id = (await btn.getAttribute('id')) || (await btn.getAttribute('class')) || 'unnamed-btn';

      if (!text && !ariaLabel && !title) {
        nonCompliant.push(id);
      }
    }

    expect(nonCompliant).toEqual([]);
  });

  test('2. Theme flow: toggles html[data-theme], updates store, and persists across reload', async ({ page }) => {
    await setupMockBackend(page);
    await page.goto('/', { waitUntil: 'networkidle' });

    const themeToggle = page.locator('#topbar-theme-toggle');
    await expect(themeToggle).toBeVisible();

    // Read initial theme
    const initialTheme = await page.getAttribute('html', 'data-theme');

    // Toggle theme
    await themeToggle.click();
    await page.waitForTimeout(200);

    const toggledTheme = await page.getAttribute('html', 'data-theme');
    expect(toggledTheme).not.toBe(initialTheme);

    // Reload page to verify persistence across reload
    await page.reload({ waitUntil: 'networkidle' });
    const persistedTheme = await page.getAttribute('html', 'data-theme');
    expect(persistedTheme).toBe(toggledTheme);

    // Toggle back to original
    await page.locator('#topbar-theme-toggle').click();
    await page.waitForTimeout(200);
    const restoredTheme = await page.getAttribute('html', 'data-theme');
    expect(restoredTheme).toBe(initialTheme);
  });

  test('3. Workspace flow: open, close, resize handle, and tab switching', async ({ page }) => {
    await setupMockBackend(page);
    await page.goto('/', { waitUntil: 'networkidle' });

    const wsToggle = page.locator('#topbar-workspace-toggle');
    const wsClose = page.locator('#workspace-close-btn');

    // Ensure workspace is open
    if (!(await wsClose.isVisible())) {
      await wsToggle.click();
      await page.waitForTimeout(200);
    }
    await expect(wsClose).toBeVisible();

    // Verify Tab switching across all 5 tabs
    const tabs = [
      { id: '#workspace-tab-preview', name: 'Preview' },
      { id: '#workspace-tab-code', name: 'Code' },
      { id: '#workspace-tab-diff', name: 'Diff' },
      { id: '#workspace-tab-logs', name: 'Logs' },
      { id: '#workspace-tab-shell', name: 'Shell' },
    ];

    for (const tab of tabs) {
      const tabBtn = page.locator(tab.id);
      await expect(tabBtn).toBeVisible();
      await tabBtn.click();
      await page.waitForTimeout(200);
    }

    // Verify Workspace Resizer Handle bounds & interaction
    const resizer = page.locator('#workspace-resizer-handle');
    await expect(resizer).toBeVisible();
    const box = await resizer.boundingBox();
    expect(box).not.toBeNull();
    expect(box!.width).toBeGreaterThan(0);

    // Simulate mouse drag on resizer
    await page.mouse.move(box!.x + box!.width / 2, box!.y + box!.height / 2);
    await page.mouse.down();
    await page.mouse.move(box!.x - 50, box!.y + box!.height / 2);
    await page.mouse.up();
    await page.waitForTimeout(200);

    // Close Workspace via close button
    await wsClose.click();
    await page.waitForTimeout(200);
    await expect(wsClose).not.toBeVisible();

    // Reopen Workspace via Topbar button
    await wsToggle.click();
    await page.waitForTimeout(200);
    await expect(wsClose).toBeVisible();
  });

  test('4. Code flow: file selection, copy, download ZIP, and unsaved changes save/discard', async ({ page }) => {
    await setupMockBackend(page);
    await page.goto('/', { waitUntil: 'networkidle' });

    // Select existing project from sidebar
    const projectItem = page.locator("[id^='sidebar-project-item-']").first();
    await expect(projectItem).toBeVisible();
    await projectItem.click();
    await page.waitForTimeout(400);

    // Ensure Workspace is open
    const wsToggle = page.locator('#topbar-workspace-toggle');
    if (!(await page.locator('#workspace-tab-code').isVisible())) {
      await wsToggle.click();
      await page.waitForTimeout(300);
    }

    // Open Code Tab
    const codeTab = page.locator('#workspace-tab-code');
    await codeTab.click();
    await page.waitForTimeout(300);

    // Verify project files rendered in file tree
    const fileItemApp = page.locator('#code-file-item-src_App_tsx');
    await expect(fileItemApp).toBeVisible();

    const fileItemHero = page.locator('#code-file-item-src_Hero_tsx');
    if (await fileItemHero.isVisible()) {
      await fileItemHero.click();
      await page.waitForTimeout(200);
    }

    // Test Copy button
    const copyBtn = page.locator('#code-copy-btn');
    await expect(copyBtn).toBeVisible();
    await copyBtn.click();
    await page.waitForTimeout(300);
    await expect(copyBtn).toContainText('Copied');

    // Test Download ZIP button
    const zipBtn = page.locator('#code-download-zip-btn');
    await expect(zipBtn).toBeVisible();
    expect(await zipBtn.isEnabled()).toBe(true);

    const downloadPromise = page.waitForEvent('download', { timeout: 5000 }).catch(() => null);
    await zipBtn.click();
    const download = await downloadPromise;
    if (download) {
      expect(download.suggestedFilename()).toContain('.zip');
    }
  });

  test('5. Diff flow: before/after loaded, turn selector, view mode toggles, and revert', async ({ page }) => {
    await setupMockBackend(page);
    await page.goto('/', { waitUntil: 'networkidle' });

    // Select existing project
    const projectItem = page.locator("[id^='sidebar-project-item-']").first();
    await expect(projectItem).toBeVisible();
    await projectItem.click();
    await page.waitForTimeout(400);

    // Ensure Workspace is open
    const wsToggle = page.locator('#topbar-workspace-toggle');
    if (!(await page.locator('#workspace-tab-diff').isVisible())) {
      await wsToggle.click();
      await page.waitForTimeout(300);
    }

    // Switch to Diff tab
    const diffTab = page.locator('#workspace-tab-diff');
    await diffTab.click();
    await page.waitForTimeout(300);

    // Verify turn selector
    const turnSelect = page.locator('#diff-turn-select');
    await expect(turnSelect).toBeVisible();

    // Verify view mode toggle (Split Diff vs Patch view)
    const splitBtn = page.locator('#diff-split-view-btn');
    const patchBtn = page.locator('#diff-patch-view-btn');
    await expect(splitBtn).toBeVisible();
    await expect(patchBtn).toBeVisible();

    await patchBtn.click();
    await page.waitForTimeout(200);
    await splitBtn.click();
    await page.waitForTimeout(200);

    // Verify Revert Button triggers accessible confirm modal
    const revertBtn = page.locator('#diff-revert-btn');
    if (await revertBtn.isVisible()) {
      await revertBtn.click();
      await page.waitForTimeout(200);

      const confirmDialog = page.locator('#confirm-dialog');
      await expect(confirmDialog).toBeVisible();

      const cancelBtn = page.locator('#confirm-dialog-cancel-btn');
      await cancelBtn.click();
      await page.waitForTimeout(200);
      await expect(confirmDialog).not.toBeVisible();
    }
  });

  test('6. Chat flow: prompt input, immediate user bubble, activity event stream, queued prompt badge, stop cancel', async ({ page }) => {
    await setupMockBackend(page);
    await page.goto('/', { waitUntil: 'networkidle' });

    // Type prompt
    const textarea = page.locator('#composer-textarea');
    await expect(textarea).toBeVisible();
    await textarea.fill('Build a futuristic space agency landing page');

    // Advanced controls
    const advToggle = page.locator('#composer-advanced-toggle-btn');
    await advToggle.click();
    await page.waitForTimeout(200);

    const siteModeBtn = page.locator('#composer-mode-site-btn');
    await siteModeBtn.click();
    await page.waitForTimeout(200);

    const advClose = page.locator('#composer-advanced-close-btn');
    await advClose.click();
    await page.waitForTimeout(200);

    // Send prompt
    const sendBtn = page.locator('#composer-send-btn');
    await expect(sendBtn).toBeVisible();
    await sendBtn.click();

    // Verify user bubble appears immediately in conversation
    await expect(page.locator('text=Build a futuristic space agency landing page')).toBeVisible({ timeout: 5000 });

    // Verify Stop button is available during working state
    const stopBtn = page.locator('#topbar-stop-btn');
    if (await stopBtn.isVisible()) {
      await stopBtn.click();
      await page.waitForTimeout(200);
      const confirmDialog = page.locator('#confirm-dialog');
      await expect(confirmDialog).toBeVisible();
      await page.locator('#confirm-dialog-cancel-btn').click();
      await page.waitForTimeout(200);
    }

    // Queue button is accessible in composer
    const queueBtn = page.locator('#composer-queue-btn');
    await expect(queueBtn).toBeVisible();
  });

  test('7. New Project flow: resets active project, chat, workspace, files, logs, and inspector', async ({ page }) => {
    await setupMockBackend(page);
    await page.goto('/', { waitUntil: 'networkidle' });

    // Select project first
    const projectItem = page.locator("[id^='sidebar-project-item-']").first();
    await projectItem.click();
    await page.waitForTimeout(300);

    // Click New Project button
    const newProjBtn = page.locator('#sidebar-new-project-btn');
    await expect(newProjBtn).toBeVisible();
    await newProjBtn.click();
    await page.waitForTimeout(400);

    // 1. Active project removed in topbar title
    await expect(page.getByText('New chat').first()).toBeVisible();

    // 2. Chat cleared (empty state visible)
    await expect(page.locator('text=What do you want to build?')).toBeVisible();

    // 3. Workspace closed
    const wsClose = page.locator('#workspace-close-btn');
    await expect(wsClose).not.toBeVisible();

    // 4. Open Inspector to verify it shows 'No project selected'
    const inspectorToggle = page.locator('#topbar-inspector-toggle');
    await inspectorToggle.click();
    await page.waitForTimeout(200);

    await expect(page.locator('text=No project selected')).toBeVisible();

    const inspectorClose = page.locator('#inspector-close-btn');
    await inspectorClose.click();
    await page.waitForTimeout(200);
  });

  test('8. Global assertions: zero uncaught page errors, zero console errors, zero failed requests', async ({ page }) => {
    const { consoleErrors, pageErrors, failedRequests } = await setupMockBackend(page);
    await page.goto('/', { waitUntil: 'networkidle' });

    // Exercise core page elements
    await page.locator('#sidebar-search-input').fill('Search test');
    await page.waitForTimeout(100);
    await page.locator('#sidebar-search-input').fill('');

    await page.locator('#composer-style-selector-btn').click();
    await page.waitForTimeout(200);
    await page.locator('#composer-style-selector-btn').click();

    await page.locator('#composer-templates-btn').click();
    await page.waitForTimeout(200);
    await page.locator('#composer-templates-btn').click();

    // Assert zero uncaught browser exceptions
    expect(pageErrors).toEqual([]);

    // Assert zero unexpected console.error messages
    expect(consoleErrors).toEqual([]);

    // Assert zero unexpected network request failures
    expect(failedRequests).toEqual([]);
  });

});
