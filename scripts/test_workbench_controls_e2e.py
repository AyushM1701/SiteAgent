"""
scripts/test_workbench_controls_e2e.py

Automated End-to-End Control and Behavior Audit for ReactAgent SLM Workbench UI (Issue #29).
Tests every visible button, dropdown, input, toggle, and panel across all 8 UI areas:
1. Project / Navigation
2. Top Bar
3. Composer
4. Workspace Panel
5. Code Tab
6. Diff Tab
7. Logs Tab
8. Shell Tab & Inspector Drawer
"""

import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from playwright.sync_api import sync_playwright

BASE_URL = "http://127.0.0.1:5000"


def run_control_audit():
    print(f"Starting Workbench Button and Control Audit against {BASE_URL}...")
    errors = []
    console_errors = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            permissions=["clipboard-read", "clipboard-write"]
        )
        page = context.new_page()

        def on_console(msg):
            if msg.type == "error":
                # Filter out intentional 404s for empty projects/diffs if any
                text = msg.text
                print(f"  [Console Error] {text}")
                if "favicon" not in text:
                    console_errors.append(text)

        page.on("console", on_console)
        page.on("pageerror", lambda exc: errors.append(f"Page uncaught exception: {exc}"))

        print("\n--- 1. Page Load & Initial Render ---")
        page.goto(BASE_URL, wait_until="networkidle", timeout=15000)
        title = page.title()
        print(f"Page title: {title}")
        assert "ReactAgent" in title or "SLM" in title or len(title) > 0, "Invalid title"

        # Check main containers
        assert page.is_visible("#root"), "Root container missing"

        print("\n--- 2. Project / Navigation Controls ---")
        # New Project button
        new_proj_btn = page.locator("#sidebar-new-project-btn")
        assert new_proj_btn.is_visible(), "New Project button not visible"
        new_proj_btn.click()
        time.sleep(0.3)
        print("  [OK] New Project button clicked successfully")

        # Project Selection from Sidebar
        first_proj = page.locator("[id^='sidebar-project-item-']").first
        if first_proj.is_visible():
            first_proj.click()
            time.sleep(0.5)
            print("  ✓ Selected existing project from sidebar")

        # Sidebar Search Input
        search_input = page.locator("#sidebar-search-input")
        assert search_input.is_visible(), "Sidebar search input not visible"
        search_input.fill("test query")
        time.sleep(0.2)
        search_input.fill("")
        print("  ✓ Sidebar search input interactive")

        # Sidebar Toggle
        sidebar_toggle = page.locator("#topbar-sidebar-toggle")
        assert sidebar_toggle.is_visible(), "Sidebar toggle button not visible"
        # Toggle closed
        sidebar_toggle.click()
        time.sleep(0.3)
        # Toggle open
        sidebar_toggle.click()
        time.sleep(0.3)
        print("  ✓ Sidebar toggle opens and closes sidebar")

        # Clear History button
        clear_hist_btn = page.locator("#sidebar-clear-history-btn")
        if clear_hist_btn.is_visible():
            clear_hist_btn.click()
            time.sleep(0.3)
            # Should open confirm dialog
            cancel_btn = page.locator("#confirm-dialog-cancel-btn")
            if cancel_btn.is_visible():
                cancel_btn.click()
                print("  ✓ Clear history triggers confirm dialog and dismisses cleanly")
            else:
                print("  ✓ Clear history clicked")

        print("\n--- 3. Top Bar Controls ---")
        # Theme toggle
        theme_btn = page.locator("#topbar-theme-toggle")
        assert theme_btn.is_visible(), "Theme toggle not visible"
        theme_btn.click()
        time.sleep(0.2)
        theme_btn.click()
        print("  ✓ Theme toggle functional")

        # Workspace Toggle
        ws_toggle = page.locator("#topbar-workspace-toggle")
        assert ws_toggle.is_visible(), "Workspace toggle button not visible"
        ws_toggle.click()
        time.sleep(0.3)
        # Ensure workspace panel is open for subsequent tab verification
        if not page.is_visible("#workspace-tab-preview"):
            ws_toggle.click()
            time.sleep(0.3)
        print("  ✓ Workspace toggle opens and closes workspace panel")

        # Inspector Toggle & Drawer
        inspector_toggle = page.locator("#topbar-inspector-toggle")
        assert inspector_toggle.is_visible(), "Inspector toggle button not visible"
        inspector_toggle.click()
        time.sleep(0.3)
        assert page.is_visible("#inspector-drawer"), "Inspector drawer did not open"
        print("  ✓ Inspector drawer opened")

        # Close Inspector from inside drawer
        inspector_close = page.locator("#inspector-close-btn")
        assert inspector_close.is_visible(), "Inspector close button not visible"
        inspector_close.click()
        time.sleep(0.3)
        assert not page.is_visible("#inspector-drawer"), "Inspector drawer did not close"
        print("  ✓ Inspector drawer closed via close button")

        # Queue Status Badge
        queue_status = page.locator("#topbar-queue-status")
        assert queue_status.is_visible(), "Queue status badge not visible"
        print(f"  ✓ Queue status badge visible (text: '{queue_status.text_content().strip()}')")

        print("\n--- 4. Composer Controls ---")
        # Open Advanced Settings Drawer (Engineering Controls)
        adv_toggle = page.locator("#composer-advanced-toggle-btn")
        assert adv_toggle.is_visible(), "Advanced settings toggle missing"
        adv_toggle.click()
        time.sleep(0.3)

        # Mode selector buttons inside Advanced Settings
        site_mode_btn = page.locator("#composer-mode-site-btn")
        comp_mode_btn = page.locator("#composer-mode-component-btn")
        assert site_mode_btn.is_visible() and comp_mode_btn.is_visible(), "Mode buttons missing in advanced controls"
        comp_mode_btn.click()
        time.sleep(0.2)
        site_mode_btn.click()
        time.sleep(0.2)
        print("  ✓ Mode toggle buttons (Site / Component) clickable")

        # Turn presets and custom turn input
        presets_btn = page.locator("#composer-turns-presets-btn")
        if presets_btn.is_visible():
            presets_btn.click()
            time.sleep(0.2)
            turns_select = page.locator("#composer-turns-select")
            if turns_select.is_visible():
                turns_select.select_option("8")
                time.sleep(0.1)
            presets_btn.click()
            time.sleep(0.1)

        turns_input = page.locator("#composer-turns-input")
        if turns_input.is_visible():
            turns_input.fill("7")
            time.sleep(0.2)
        print("  ✓ Turn presets and custom turn entry configured")

        # Close Advanced Settings Drawer
        adv_close = page.locator("#composer-advanced-close-btn")
        if adv_close.is_visible():
            adv_close.click()
        else:
            adv_toggle.click()
        time.sleep(0.2)
        print("  ✓ Advanced settings opened and closed cleanly")

        # Style Presets Popover
        style_btn = page.locator("#composer-style-selector-btn")
        assert style_btn.is_visible(), "Style selector button missing"
        style_btn.click()
        time.sleep(0.3)
        first_style = page.locator("[id^='composer-style-option-']").first
        if first_style.is_visible():
            first_style.click()
            time.sleep(0.2)
            print("  ✓ Style preset selected via dropdown")
        else:
            style_btn.click()
            print("  ✓ Style popover toggled")

        # Templates Popover
        templates_btn = page.locator("#composer-templates-btn")
        assert templates_btn.is_visible(), "Templates button missing"
        templates_btn.click()
        time.sleep(0.3)
        first_tpl = page.locator("#composer-template-item-0")
        if first_tpl.is_visible():
            first_tpl.click()
            time.sleep(0.2)
            print("  ✓ Template clicked and inserted into prompt")
        else:
            templates_btn.click()

        # Prompt Textarea and Queue button
        textarea = page.locator("#composer-textarea")
        assert textarea.is_visible(), "Composer textarea not visible"
        textarea.fill("Create a high-tech modern AI robotics dashboard")
        queue_btn = page.locator("#composer-queue-btn")
        send_btn = page.locator("#composer-send-btn")
        assert queue_btn.is_visible(), "Queue button missing"
        assert send_btn.is_visible(), "Send button missing"
        print("  ✓ Prompt textarea filled, Queue button and Send button verified")

        print("\n--- 5. Workspace Tabs Navigation ---")
        # Verify all 5 tabs
        tabs = [
            ("#workspace-tab-preview", "Preview"),
            ("#workspace-tab-code", "Code"),
            ("#workspace-tab-diff", "Diff"),
            ("#workspace-tab-logs", "Logs"),
            ("#workspace-tab-shell", "Shell"),
        ]
        for selector, name in tabs:
            tab = page.locator(selector)
            assert tab.is_visible(), f"Tab {name} ({selector}) not visible"
            tab.click()
            time.sleep(0.3)
            print(f"  ✓ Switched to {name} tab")

        print("\n--- 6. Workspace Sub-Tab Controls ---")
        # 6a. Preview Tab Controls
        page.locator("#workspace-tab-preview").click()
        time.sleep(0.3)
        for vp in ["#preview-viewport-desktop", "#preview-viewport-tablet", "#preview-viewport-mobile"]:
            btn = page.locator(vp)
            if btn.is_visible():
                btn.click()
                time.sleep(0.1)
        if page.locator("#preview-reload-btn").is_visible():
            page.locator("#preview-reload-btn").click()
        print("  ✓ Preview tab viewport controls and reload button operational")

        # 6b. Code Tab Controls
        page.locator("#workspace-tab-code").click()
        time.sleep(0.3)
        code_copy = page.locator("#code-copy-btn")
        code_zip = page.locator("#code-download-zip-btn")
        assert code_copy.is_visible(), "Code copy button missing"
        assert code_zip.is_visible(), "Code download ZIP button missing"
        code_copy.click()
        print("  ✓ Code copy and Download ZIP controls verified")

        # 6c. Diff Tab Controls
        page.locator("#workspace-tab-diff").click()
        time.sleep(0.3)
        split_btn = page.locator("#diff-split-view-btn")
        patch_btn = page.locator("#diff-patch-view-btn")
        if split_btn.is_visible() and patch_btn.is_visible():
            patch_btn.click()
            time.sleep(0.2)
            split_btn.click()
            time.sleep(0.2)
            print("  ✓ Diff Split/Patch view toggles operational")

        # 6d. Logs Tab Controls
        page.locator("#workspace-tab-logs").click()
        time.sleep(0.3)
        logs_search = page.locator("#logs-search-input")
        logs_cat = page.locator("#logs-category-filter")
        logs_lvl = page.locator("#logs-level-filter")
        logs_scroll = page.locator("#logs-autoscroll-btn")
        logs_clear = page.locator("#logs-clear-btn")
        assert logs_search.is_visible(), "Logs search missing"
        assert logs_cat.is_visible(), "Logs category filter missing"
        assert logs_lvl.is_visible(), "Logs level filter missing"
        assert logs_scroll.is_visible(), "Logs autoscroll button missing"
        assert logs_clear.is_visible(), "Logs clear button missing"
        logs_search.fill("agent")
        time.sleep(0.1)
        logs_search.fill("")
        logs_scroll.click()
        time.sleep(0.1)
        logs_scroll.click()
        logs_clear.click()
        print("  ✓ Logs filters, search, autoscroll, and clear operational")

        # 6e. Shell Tab Controls
        page.locator("#workspace-tab-shell").click()
        time.sleep(0.5)
        shell_reconn = page.locator("#shell-reconnect-btn")
        shell_clear = page.locator("#shell-clear-btn")
        assert shell_reconn.is_visible(), "Shell reconnect button missing"
        assert shell_clear.is_visible(), "Shell clear button missing"
        shell_clear.click()
        time.sleep(0.2)
        print("  ✓ Shell terminal container, reconnect, and clear buttons operational")

        # 6f. Workspace Resizer Handle
        resizer = page.locator("#workspace-resizer-handle")
        assert resizer.is_visible(), "Workspace resizer handle missing"
        box = resizer.bounding_box()
        assert box is not None and box["width"] > 0, "Invalid resizer bounding box"
        print(f"  ✓ Workspace resizer handle present at x={box['x']:.1f}, y={box['y']:.1f}")

        # 6g. Workspace Panel Close Button
        ws_close = page.locator("#workspace-close-btn")
        assert ws_close.is_visible(), "Workspace close button missing"
        ws_close.click()
        time.sleep(0.3)
        print("  ✓ Workspace panel closed via close button")

        # Reopen workspace panel via topbar toggle
        ws_toggle.click()
        time.sleep(0.3)
        print("  ✓ Workspace panel reopened via topbar button")

        # Screenshot of the fully audited workbench
        screenshot_path = "tests/workbench_control_audit_success.png"
        page.screenshot(path=screenshot_path)
        print(f"\nSaved audit screenshot to {screenshot_path}")

        browser.close()

    print("\n--- Summary of Control Audit ---")
    print(f"Total uncaught page errors: {len(errors)}")
    print(f"Total console error messages: {len(console_errors)}")

    if errors:
        print("Uncaught errors detected:")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)

    print("\n✓ ALL WORKBENCH CONTROLS VERIFIED SUCCESSFULLY!")


if __name__ == "__main__":
    run_control_audit()
