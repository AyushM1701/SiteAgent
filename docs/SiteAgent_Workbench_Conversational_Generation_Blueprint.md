# SiteAgent Workbench — Conversational Generation & Live Activity Blueprint

## 1. Purpose

This blueprint explains how to evolve the SiteAgent Workbench from a one-shot website generator into a persistent conversational AI coding environment powered by Qwen3-4B.

The target experience is similar to modern AI chat products, but specialized for website development and integrated directly with:

- React + TypeScript project generation
- Three.js / React Three Fiber
- persistent project chat
- live preview
- build and runtime diagnostics
- code diffs
- debugging
- file operations
- terminal execution
- preview inspection
- agent activity indicators
- automatic repair loops
- project history and undo

The core UX rule is:

> **The chat explains what SiteAgent is doing; the Logs panel shows exactly what the system is doing.**

---

# 2. Product Goal

The Workbench should feel like an AI software engineer inside an IDE.

Instead of:

```text
Prompt → Wait → Website appears
```

the experience should become:

```text
Conversation
    ↓
Plan
    ↓
Generate files
    ↓
Run
    ↓
Inspect
    ↓
Fix
    ↓
Preview
    ↓
Continue conversation
```

Generation is not the end of the workflow. It is the first development turn inside a persistent project conversation.

---

# 3. Recommended Workbench Layout

```text
┌────────────────┬───────────────────────────────┬──────────────────────────┐
│ PROJECTS       │ CHAT                          │ WORKSPACE                │
│                │                               │                          │
│ + New Project  │ You                           │ Live Preview             │
│                │ Build Lumina...               │ Code                     │
│ Lumina         │                               │ Diff                     │
│ Nexaflow       │ SiteAgent                     │ Logs                     │
│ Dashboard      │ ◌ Building your website...    │ Shell                    │
│ ApexCloud      │                               │                          │
│                │ ✓ Planning                    │                          │
│                │ ✓ Hero                        │                          │
│                │ ◉ Gallery                     │                          │
│                │ ○ Process                     │                          │
│                │ ○ Pricing                     │                          │
│                │                               │                          │
│                │ [composer always visible]     │                          │
└────────────────┴───────────────────────────────┴──────────────────────────┘
```

### Left panel

Rename `History` to `Projects`.

Each project can show a compact status:

```text
Lumina
React + TypeScript + R3F

✓ Build passed
2m ago
```

Internal metrics such as sanity score, token count, and turn count should move to Inspector / Advanced views.

---

# 4. Chat-First Interaction Model

Once the user submits the initial prompt, it should immediately become a chat message.

Before submit:

```text
Build a dark-mode React TypeScript site for "Lumina"...
```

Immediately after submit:

```text
You

Build a dark-mode React TypeScript site for "Lumina" — a
generative art studio that creates physical prints from 3D renders.


SiteAgent

◌ Understanding your request...
```

The composer should immediately reset and stay visible:

```text
┌──────────────────────────────────────────────────────┐
│ Ask SiteAgent to change, fix, or explain anything…  │
│                                                ↑     │
└──────────────────────────────────────────────────────┘
```

If the user sends a follow-up while a task is still running, queue it:

```text
You
Make the globe larger.

Queued — SiteAgent will apply this after the current task.
```

---

# 5. Do Not Show Raw Chain-of-Thought

Show concise activity summaries, not hidden reasoning.

Good:

```text
◌ Planning the site structure...
◌ Building the 3D hero...
◌ Checking the TypeScript build...
◌ Fixing 2 errors...
```

The chat should communicate action, status, progress, and result.

---

# 6. Activity Indicator / Throbber

Use a subtle spinner for live activity.

```css
.agent-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(82, 226, 181, 0.18);
  border-top-color: #52e2b5;
  border-radius: 50%;
  animation: siteagent-spin 0.75s linear infinite;
}

@keyframes siteagent-spin {
  to {
    transform: rotate(360deg);
  }
}

@media (prefers-reduced-motion: reduce) {
  .agent-spinner {
    animation: none;
  }
}
```

React component:

```tsx
export function AgentSpinner({ size = 14 }: { size?: number }) {
  return (
    <span
      className="agent-spinner"
      style={{ width: size, height: size }}
      aria-label="Working"
    />
  );
}
```

Accessible status:

```tsx
<div role="status" aria-live="polite">
  <AgentSpinner />
  <span>Building the hero...</span>
</div>
```

---

# 7. Contextual Agent Statuses

```ts
export type AgentStatus =
  | "idle"
  | "understanding"
  | "planning"
  | "coding"
  | "installing"
  | "building"
  | "testing"
  | "debugging"
  | "previewing"
  | "completed"
  | "failed"
  | "cancelled";
```

Map to user-facing text:

```ts
export const agentStatusLabels: Record<AgentStatus, string> = {
  idle: "Ready",
  understanding: "Understanding your request",
  planning: "Planning the project",
  coding: "Writing the website",
  installing: "Installing dependencies",
  building: "Checking the build",
  testing: "Testing the project",
  debugging: "Fixing an issue",
  previewing: "Preparing the preview",
  completed: "Website ready",
  failed: "Generation stopped because of an error",
  cancelled: "Generation cancelled",
};
```

More detailed live messages can include:

```text
◌ Writing Hero.tsx...
◌ Creating the 3D scene...
◌ Installing @react-three/fiber...
◌ Running TypeScript checks...
◌ Fixing 2 TypeScript errors...
◌ Starting Vite preview...
```

These should come from actual orchestrator actions, not fabricated model text.

---

# 8. Activity Card

Use one updating activity card rather than creating many messages.

Early:

```text
SiteAgent

◌ Building Lumina...

  ✓ Understanding requirements
  ◉ Planning project
  ○ Hero
  ○ Gallery
  ○ Process
  ○ Pricing
  ○ Footer
```

During generation:

```text
SiteAgent

◌ Building Lumina...

  ✓ Understanding requirements
  ✓ Planning project
  ✓ Hero
  ◉ Gallery
  ○ Process
  ○ Pricing
  ○ Footer

  6 files created · 2 dependencies added
```

During repair:

```text
SiteAgent

◌ Checking the build...

  ✓ TypeScript project created
  ! 2 issues found
  ◉ Repairing Gallery.tsx

  Repair attempt 1 / 3
```

Completion:

```text
SiteAgent

✓ Website ready

12 files created
5 sections
1 Three.js scene
2 build issues automatically fixed
Build passed in 41.8s

[View Preview] [Review Changes]
```

---

# 9. Structured Chat Message Model

Do not store every message as a plain string.

```ts
export type ChatMessage =
  | {
      id: string;
      role: "user";
      type: "text";
      content: string;
      createdAt: string;
    }
  | {
      id: string;
      role: "assistant";
      type: "text";
      content: string;
      createdAt: string;
    }
  | {
      id: string;
      role: "assistant";
      type: "activity";
      activityId: string;
      status: "running" | "success" | "error";
      title: string;
      detail?: string;
      steps?: ActivityStep[];
      createdAt: string;
    }
  | {
      id: string;
      role: "assistant";
      type: "change-summary";
      filesChanged: number;
      additions: number;
      deletions: number;
      paths: string[];
      createdAt: string;
    }
  | {
      id: string;
      role: "assistant";
      type: "error";
      content: string;
      recoverable: boolean;
      createdAt: string;
    };

export type ActivityStep = {
  id: string;
  label: string;
  state: "pending" | "running" | "success" | "error";
  detail?: string;
};
```

---

# 10. Agent Event Stream

The backend should publish structured events.

```ts
export type AgentEvent =
  | {
      type: "agent.status";
      taskId: string;
      status: AgentStatus;
      label?: string;
    }
  | {
      type: "activity.started";
      taskId: string;
      activityId: string;
      label: string;
    }
  | {
      type: "activity.updated";
      taskId: string;
      activityId: string;
      label?: string;
      detail?: string;
    }
  | {
      type: "activity.completed";
      taskId: string;
      activityId: string;
      detail?: string;
    }
  | {
      type: "activity.failed";
      taskId: string;
      activityId: string;
      error: string;
    }
  | {
      type: "file.created";
      taskId: string;
      path: string;
    }
  | {
      type: "file.modified";
      taskId: string;
      path: string;
    }
  | {
      type: "file.deleted";
      taskId: string;
      path: string;
    }
  | {
      type: "command.started";
      taskId: string;
      commandId: string;
      command: string;
    }
  | {
      type: "command.output";
      taskId: string;
      commandId: string;
      stream: "stdout" | "stderr";
      chunk: string;
    }
  | {
      type: "command.completed";
      taskId: string;
      commandId: string;
      exitCode: number;
    }
  | {
      type: "build.result";
      taskId: string;
      success: boolean;
      errors: number;
      warnings: number;
    }
  | {
      type: "preview.ready";
      taskId: string;
      url: string;
    }
  | {
      type: "task.completed";
      taskId: string;
      durationMs: number;
    }
  | {
      type: "task.failed";
      taskId: string;
      error: string;
    };
```

---

# 11. One Event Stream, Two Interfaces

```text
                       Agent Orchestrator
                              │
                              ▼
                       Agent Event Bus
                              │
                  ┌───────────┴───────────┐
                  ▼                       ▼
              Chat Mapper              Log Mapper
                  │                       │
                  ▼                       ▼
         Human-friendly status       Raw technical log
```

Example:

Backend:

```json
{
  "type": "command.started",
  "command": "npm run build"
}
```

Chat:

```text
◌ Checking the build...
```

Logs:

```text
15:41:09 [Shell] npm run build
```

---

# 12. Streaming Transport

Use WebSocket.

Suggested endpoint:

```text
ws://localhost:3001/ws/projects/:projectId
```

Client:

```json
{
  "type": "task.start",
  "payload": {
    "message": "Build Lumina..."
  }
}
```

Server:

```json
{
  "type": "activity.started",
  "taskId": "task_123",
  "activityId": "planning",
  "label": "Planning the site"
}
```

WebSocket is preferable because future features need bidirectional communication:

- Stop / cancel
- User interrupts
- Element selection
- Terminal interaction
- Browser inspection
- Queued prompts
- 3D object selection

---

# 13. Backend Orchestrator

```text
User Message
    ↓
Agent Controller
    ↓
Context Builder
    ↓
Qwen3-4B
    ↓
Tool Call
    ↓
Tool Executor
    ↓
Agent Event Bus
    ↓
Result returned to Qwen
    ↓
Next action
```

Suggested backend modules:

```text
server/
├── agent/
│   ├── agent-controller.ts
│   ├── agent-runner.ts
│   ├── context-builder.ts
│   ├── prompt-builder.ts
│   ├── tool-router.ts
│   └── repair-loop.ts
│
├── events/
│   ├── event-bus.ts
│   ├── chat-mapper.ts
│   └── log-mapper.ts
│
├── tools/
│   ├── file-tools.ts
│   ├── shell-tools.ts
│   ├── build-tools.ts
│   ├── browser-tools.ts
│   └── project-tools.ts
│
├── projects/
│   ├── project-service.ts
│   ├── project-state.ts
│   └── snapshots.ts
│
└── ws/
    └── socket-server.ts
```

---

# 14. Tools Exposed to Qwen

File tools:

```text
read_file(path)
write_file(path, content)
edit_file(path, patch)
delete_file(path)
list_files(path)
search_files(query)
```

Shell tools:

```text
run_command(command)
install_package(packageName)
run_build()
run_typecheck()
run_lint()
```

Browser tools:

```text
start_preview()
stop_preview()
get_console_errors()
get_preview_url()
capture_screenshot()
inspect_dom()
```

Project tools:

```text
get_project_structure()
get_project_metadata()
get_dependencies()
get_recent_changes()
create_snapshot()
restore_snapshot()
```

3D tools later:

```text
get_webgl_errors()
get_scene_metadata()
get_asset_manifest()
```

---

# 15. Automatic Debugging Loop

```text
Generate files
    ↓
npm run build
    ↓
Build successful?
    ├── Yes → Start Preview
    │
    └── No
         ↓
   Parse diagnostics
         ↓
   Send errors + relevant files to Qwen
         ↓
   Qwen patches files
         ↓
   npm run build
         ↓
      repeat
```

Use:

```ts
const MAX_REPAIR_ATTEMPTS = 3;
```

Chat:

```text
◌ Checking the build...
! 2 issues found
◌ Repairing build... 1/3
✓ Build passed
```

Logs:

```text
[Build] npm run build
[tsc] TS2322 src/components/Hero.tsx:42:13
[Repair] attempt 1/3
[Agent] edit_file(src/components/Hero.tsx)
[Build] npm run build
[Build] success
```

---

# 16. Persistent Project-Aware Chat

Each project gets its own conversation.

Recommended entities:

```text
Project
Conversation
Message
Task
AgentEvent
FileChange
Snapshot
```

Example:

```ts
type Project = {
  id: string;
  name: string;
  rootPath: string;
  framework: string;
  language: string;
  createdAt: string;
  updatedAt: string;
};

type Conversation = {
  id: string;
  projectId: string;
  createdAt: string;
};

type Message = {
  id: string;
  conversationId: string;
  role: "user" | "assistant";
  type: string;
  content: unknown;
  createdAt: string;
};

type Task = {
  id: string;
  projectId: string;
  messageId: string;
  status: string;
  startedAt: string;
  completedAt?: string;
};
```

For local development, SQLite + Drizzle ORM is a strong choice.

---

# 17. Project State

Keep project metadata separate from chat.

```json
{
  "framework": "react",
  "language": "typescript",
  "bundler": "vite",
  "styling": "tailwind",
  "uses3D": true,
  "threeLibrary": "@react-three/fiber",
  "packageManager": "npm",
  "entryPoint": "src/main.tsx",
  "previewPort": 5173,
  "importantFiles": [
    "src/App.tsx",
    "src/components/Hero.tsx",
    "src/three/Scene.tsx"
  ]
}
```

---

# 18. Context Builder

Do not send the whole repository to Qwen on every turn.

Build targeted context:

```text
SYSTEM
You are SiteAgent, an expert React, TypeScript and 3D web development agent.

PROJECT
React + TypeScript + Vite + Tailwind + React Three Fiber

USER REQUEST
Make the 3D object larger and move it slightly right.

RECENT CONVERSATION
...

SELECTED COMPONENT
Scene > Globe

RELEVANT FILES
src/three/Globe.tsx
src/three/Scene.tsx

RECENT BUILD STATUS
Build passed

RECENT CHANGES
...
```

Priority:

1. Selected file / component
2. Files explicitly mentioned by user
3. Semantic search matches
4. Recently changed files
5. Dependency-related files
6. Project metadata

---

# 19. Composer

Persistent bottom composer:

```text
┌───────────────────────────────────────────────────────┐
│ [Globe.tsx ×]                                        │
│                                                       │
│ Make this larger and rotate more slowly...            │
│                                                       │
│                          Ctrl+Enter to send      ↑     │
└───────────────────────────────────────────────────────┘
```

During generation:

```text
[■ Stop]   [Message will queue]
```

After:

```text
[↑ Send]
```

---

# 20. Top Status Bar

Replace:

```text
Generating (click to stop)
```

with:

```text
● Generating   42.4s        [■ Stop]
```

Move advanced metrics such as turn count and token count into Inspector.

Inspector can show:

```text
Model: Qwen3-4B
Context: 3,812 / 8,192
Tool calls: 7
Repair attempts: 1 / 3
GPU memory: 5.1 GB
Generation tokens: 2,340
```

---

# 21. Workspace Tabs

Recommended:

```text
Live Preview
Code
Diff
Logs
Shell
```

Later:

```text
Problems
Network
Assets
Scene
```

---

# 22. Preview Element Selection

Allow users to click a DOM element in preview.

Flow:

```text
User clicks Navbar
    ↓
Preview inspector resolves source
    ↓
Workbench stores selection
    ↓
Composer shows selection chip
```

UI:

```text
Selected
Navbar
src/components/Navbar.tsx
```

Then:

```text
Make this transparent.
```

Agent receives:

```json
{
  "selectedElement": {
    "component": "Navbar",
    "sourceFile": "src/components/Navbar.tsx",
    "tag": "nav"
  },
  "request": "Make this transparent."
}
```

---

# 23. Source Mapping

For V1, inject source metadata during development:

```tsx
<nav data-siteagent-source="src/components/Navbar.tsx:18">
```

The preview sends:

```ts
window.parent.postMessage(
  {
    type: "siteagent.element.selected",
    source: "src/components/Navbar.tsx:18",
    tag: "nav",
  },
  "*"
);
```

---

# 24. 3D Object Selection

For React Three Fiber:

```tsx
<mesh
  userData={{
    siteAgentName: "Globe",
    sourceFile: "src/three/Globe.tsx",
  }}
>
```

Raycast on click and emit:

```json
{
  "type": "siteagent.scene.selected",
  "name": "Globe",
  "sourceFile": "src/three/Globe.tsx"
}
```

Composer:

```text
[3D: Globe ×]

Make this larger and rotate slower.
```

---

# 25. Diff Integration

After changes:

```text
SiteAgent

✓ Updated the hero

Changed 2 files
+18 −7

Hero.tsx
Scene.tsx

[Review changes] [Undo]
```

Use Monaco Diff Editor if Monaco is already used for code editing.

---

# 26. Undo / Snapshots

Create a snapshot before every agent task.

Simple model:

```ts
type ProjectSnapshot = {
  id: string;
  projectId: string;
  taskId: string;
  createdAt: string;
  files: Record<string, string>;
};
```

Long-term, use Git commits for snapshots.

---

# 27. Logs Panel

Example:

```text
15:41:08 [Agent] task started
15:41:08 [Planner] sections: hero → gallery → process → pricing → footer
15:41:09 [Tool] write_file src/App.tsx
15:41:10 [Tool] write_file src/components/Hero.tsx
15:41:12 [Tool] write_file src/three/Scene.tsx
15:41:15 [Shell] npm install @react-three/fiber @react-three/drei three
15:41:23 [Shell] npm run build
15:41:25 [tsc] TS2322 src/components/Gallery.tsx:44
15:41:26 [Repair] attempt 1/3
15:41:29 [Tool] edit_file src/components/Gallery.tsx
15:41:33 [Shell] npm run build
15:41:35 [Build] success
```

Add:

- Clear
- Copy
- Search
- Filter
- Pause auto-scroll
- Timestamp
- Severity

Filters:

```text
All
Agent
Files
Shell
Build
Browser
Errors
```

---

# 28. Log Data Model

```ts
export type LogEntry = {
  id: string;
  timestamp: string;
  category:
    | "agent"
    | "planner"
    | "tool"
    | "file"
    | "shell"
    | "build"
    | "browser"
    | "repair";
  level: "debug" | "info" | "warn" | "error";
  message: string;
  metadata?: Record<string, unknown>;
};
```

Cap in-memory logs:

```ts
const MAX_LOG_ENTRIES = 5000;
```

---

# 29. Live Preview

Use Vite HMR so preview can update while files are generated.

```text
Write files
    ↓
Vite HMR
    ↓
Preview updates
```

Do not rebuild the whole project after every write.

A good schedule is:

```text
After major section
or
after a small batch of writes
or
before final completion
```

---

# 30. Runtime Error Capture

Inside preview:

```ts
window.addEventListener("error", (event) => {
  window.parent.postMessage(
    {
      type: "siteagent.runtime.error",
      message: event.message,
      filename: event.filename,
      line: event.lineno,
      column: event.colno,
    },
    "*"
  );
});

window.addEventListener("unhandledrejection", (event) => {
  window.parent.postMessage(
    {
      type: "siteagent.promise.error",
      message: String(event.reason),
    },
    "*"
  );
});
```

Feed diagnostics into the repair loop.

---

# 31. Browser Debugging Loop

```text
Preview loads
    ↓
Runtime error captured
    ↓
Chat shows:
"! Runtime issue found"
    ↓
Qwen receives error + relevant file
    ↓
Patch
    ↓
Vite HMR
    ↓
Recheck
```

Use:

```ts
const MAX_RUNTIME_REPAIRS = 3;
```

---

# 32. Qwen3-4B System Prompt

```text
You are SiteAgent, an expert web development agent.

You work on an existing project using tools.

Rules:
- Inspect relevant project files before making targeted changes.
- Prefer minimal changes.
- Do not rewrite unrelated files.
- Use React and TypeScript conventions.
- For 3D interfaces, prefer React Three Fiber and Drei when appropriate.
- After modifications, run the relevant build or type check.
- If a build fails, diagnose and repair it.
- Never claim success until verification succeeds.
- Use tool calls instead of dumping complete project code in chat.
```

---

# 33. Task Lifecycle

```text
CREATED
  ↓
QUEUED
  ↓
UNDERSTANDING
  ↓
PLANNING
  ↓
EXECUTING
  ↓
VERIFYING
  ↓
REPAIRING
  ↓
PREVIEWING
  ↓
COMPLETED
```

Failure states:

```text
FAILED
CANCELLED
TIMED_OUT
```

---

# 34. State Management

Use Zustand for frontend state.

Stores:

```text
agentStore
chatStore
projectStore
workspaceStore
selectionStore
```

Example:

```ts
type AgentStore = {
  activeTaskId: string | null;
  status: AgentStatus;
  activities: Record<string, ActivityStep>;
  setStatus: (status: AgentStatus) => void;
  applyEvent: (event: AgentEvent) => void;
};
```

---

# 35. Cancel Behavior

When user clicks Stop:

```json
{
  "type": "task.cancel",
  "taskId": "task_123"
}
```

Backend should:

1. stop model generation,
2. terminate active shell task if safe,
3. stop repair attempts,
4. preserve written files,
5. mark task cancelled,
6. keep chat history.

Then show:

```text
Generation stopped.

7 files were created before cancellation.

[Keep changes] [Restore previous version]
```

---

# 36. Message Queue

If user sends a message during generation:

```ts
type QueuedPrompt = {
  id: string;
  projectId: string;
  content: string;
  createdAt: string;
};
```

UI:

```text
You
Make the navbar transparent.

Queued
```

After current task:

```text
Applying your next request...
```

---

# 37. Inspector

Recommended sections:

```text
Project
Agent
Selection
Performance
3D
Environment
```

Project:

```text
React 19
TypeScript
Vite
Tailwind
R3F
```

Agent:

```text
Model: Qwen3-4B
Task: task_123
Tool calls: 18
Repair attempts: 1
Context size: 4,912
```

Selection:

```text
Component: Navbar
Source: src/components/Navbar.tsx
DOM: nav
```

3D:

```text
Object: Globe
Source: src/three/Globe.tsx
Meshes: 1
Triangles: 18,240
```

---

# 38. New Project Empty State

Keep:

```text
Give your next idea a place on the web.
```

only for:

- no active project,
- or new project creation.

Once a prompt is submitted, transition the center panel into persistent chat.

---

# 39. React Component Tree

```text
App
├── TopBar
│   ├── MenuButton
│   ├── Brand
│   ├── AgentStatus
│   ├── StopButton
│   └── InspectorButton
│
├── WorkbenchLayout
│   ├── ProjectSidebar
│   │   ├── NewProjectButton
│   │   ├── ProjectSearch
│   │   └── ProjectList
│   │
│   ├── ChatPanel
│   │   ├── ChatHeader
│   │   ├── MessageList
│   │   │   ├── UserMessage
│   │   │   ├── AssistantMessage
│   │   │   ├── ActivityMessage
│   │   │   ├── ChangeSummary
│   │   │   └── ErrorMessage
│   │   └── ChatComposer
│   │
│   └── WorkspacePanel
│       ├── WorkspaceTabs
│       ├── PreviewTab
│       ├── CodeTab
│       ├── DiffTab
│       ├── LogsTab
│       └── ShellTab
│
└── InspectorDrawer
```

---

# 40. Frontend Folder Structure

```text
src/
├── app/
│   ├── App.tsx
│   └── router.tsx
│
├── components/
│   ├── chat/
│   │   ├── ChatPanel.tsx
│   │   ├── MessageList.tsx
│   │   ├── ChatComposer.tsx
│   │   ├── UserMessage.tsx
│   │   ├── AssistantMessage.tsx
│   │   ├── ActivityMessage.tsx
│   │   ├── ActivityStep.tsx
│   │   ├── AgentSpinner.tsx
│   │   └── ChangeSummary.tsx
│   │
│   ├── projects/
│   │   ├── ProjectSidebar.tsx
│   │   ├── ProjectList.tsx
│   │   └── ProjectItem.tsx
│   │
│   ├── workspace/
│   │   ├── WorkspacePanel.tsx
│   │   ├── PreviewTab.tsx
│   │   ├── CodeTab.tsx
│   │   ├── DiffTab.tsx
│   │   ├── LogsTab.tsx
│   │   └── ShellTab.tsx
│   │
│   └── inspector/
│       └── InspectorDrawer.tsx
│
├── hooks/
│   ├── useAgentSocket.ts
│   ├── useConversation.ts
│   ├── useProject.ts
│   └── useSelection.ts
│
├── state/
│   ├── agent-store.ts
│   ├── chat-store.ts
│   ├── project-store.ts
│   └── workspace-store.ts
│
├── services/
│   ├── api.ts
│   ├── websocket.ts
│   └── projects.ts
│
└── types/
    ├── agent.ts
    ├── chat.ts
    ├── project.ts
    └── logs.ts
```

---

# 41. Chat Persistence

When user sends a message:

1. Add it to local UI immediately.
2. Persist to backend.
3. Create an agent task.
4. Start streaming events.

Optimistic UI:

```ts
async function sendMessage(content: string) {
  const tempMessage = {
    id: crypto.randomUUID(),
    role: "user" as const,
    type: "text" as const,
    content,
    createdAt: new Date().toISOString(),
  };

  chatStore.addMessage(tempMessage);

  socket.send(
    JSON.stringify({
      type: "chat.send",
      projectId,
      content,
      clientMessageId: tempMessage.id,
    })
  );
}
```

If send fails:

```text
Message failed to send. [Retry]
```

---

# 42. Auto-Scrolling

Only auto-scroll if the user is already near the bottom.

```ts
const shouldAutoScroll =
  scrollHeight - scrollTop - clientHeight < 120;
```

Otherwise show:

```text
↓ New activity
```

---

# 43. Progress Representation

Avoid fake percentages.

Use:

```text
3 / 5 sections
```

or:

```text
✓ Hero
✓ Gallery
◉ Process
○ Pricing
○ Footer
```

For unknown-duration work:

```text
◌ Checking the build...
```

---

# 44. Generation Plan

Planner output:

```json
{
  "projectName": "Lumina",
  "sections": [
    "hero",
    "gallery",
    "process",
    "pricing",
    "footer"
  ]
}
```

The orchestrator converts sections into activity steps.

---

# 45. Better User-Facing Labels

Replace:

```text
Turn 1 / 12
```

with meaningful progress such as:

```text
Hero
```

Replace:

```text
Sanity 5.0
```

with:

```text
✓ Build passed
```

Move token count and model settings to Inspector / Advanced.

---

# 46. 3D-Specific Activity

Useful statuses:

```text
◌ Creating Three.js scene...
◌ Loading geometry...
◌ Configuring lights...
◌ Optimizing pixel ratio...
◌ Checking WebGL output...
```

For GLB:

```text
◌ Loading model.glb...
```

For shaders:

```text
◌ Compiling shaders...
```

For performance repair:

```text
! High rendering cost detected
◌ Reducing particle density...
```

---

# 47. Three.js Performance Guardrails

Default guidance for the agent:

```text
- Use dpr={[1, 1.5]} unless high quality is requested.
- Avoid expensive shadows by default.
- Prefer simple lighting.
- Avoid excessive post-processing.
- Cap particle count.
- Respect prefers-reduced-motion.
- Provide static fallback when appropriate.
- Avoid unnecessary useFrame computations.
- Use instancing for repeated geometry.
```

---

# 48. Error UI

Chat:

```text
SiteAgent

! I hit a TypeScript issue in Gallery.tsx.

◌ Fixing it automatically... 1/3
```

Logs:

```text
TS2322: Type 'string' is not assignable to type 'number'
src/components/Gallery.tsx:44:19
```

If auto-repair fails:

```text
SiteAgent

I couldn't repair this automatically after 3 attempts.

The issue is in:
src/components/Gallery.tsx

[Open file] [View logs]
```

---

# 49. Completion Summary

Initial generation:

```text
SiteAgent

✓ Lumina is ready.

Created
• 12 files
• 5 page sections
• 1 interactive 3D scene

Validation
• TypeScript passed
• Production build passed
• Preview running

Changes
+734 −0

[View Preview] [Review Changes]
```

Modification:

```text
SiteAgent

✓ Updated the 3D hero.

Changed
• src/three/Globe.tsx
• src/components/Hero.tsx

The globe is now larger, positioned farther right, and rotates more slowly.

[Review changes] [Undo]
```

---

# 50. Keyboard Shortcuts

```text
Ctrl/Cmd + Enter    Send message
Ctrl/Cmd + K        Focus chat composer
Ctrl/Cmd + P        Open file search
Ctrl/Cmd + `        Toggle shell
Esc                 Close inspector/selection
```

---

# 51. Connection Handling

WebSocket states:

```text
connecting
connected
reconnecting
offline
```

Top bar:

```text
● Local agent connected
```

Failure:

```text
! Agent connection lost
Reconnecting...
```

Messages can remain queued during reconnection.

---

# 52. Recommended Build Milestones

## Phase 1 — Persistent Chat

Implement:

- project-specific chat history
- user message appears immediately
- persistent composer
- basic assistant messages

## Phase 2 — Activity UI

Implement:

- spinner
- activity cards
- activity steps
- completion summary

## Phase 3 — Structured Logs

Implement:

- event bus
- raw logs
- filters
- search
- auto-scroll control

## Phase 4 — Tool-Driven Qwen Agent

Implement:

- file tools
- terminal tools
- build tools
- context builder
- Qwen tool calls

## Phase 5 — Repair Loop

Implement:

- TypeScript diagnostics
- build parsing
- automatic repairs
- maximum repair count

## Phase 6 — Live Preview

Implement:

- Vite process manager
- preview iframe
- HMR
- runtime error capture

## Phase 7 — Diff + Undo

Implement:

- snapshots
- Monaco diff
- change summaries
- restore

## Phase 8 — Visual Selection

Implement:

- DOM source metadata
- preview selection
- selected-component context

## Phase 9 — 3D Selection

Implement:

- R3F metadata
- raycast selection
- 3D context-aware prompts

---

# 53. MVP Scope

A strong first version should include:

```text
✓ Project sidebar
✓ Persistent chat
✓ Immediate user message insertion
✓ Animated activity indicator
✓ Human-friendly generation steps
✓ Logs panel
✓ File tools
✓ npm build verification
✓ Auto-repair up to 3 attempts
✓ Live Vite preview
✓ Follow-up prompts
✓ Change summary
```

Skip initially:

```text
DOM selection
3D selection
Vision model
Git snapshots
Advanced inspector
Screenshot understanding
```

---

# 54. Recommended Technology Stack

Frontend:

```text
React
TypeScript
Vite
Tailwind CSS
Zustand
Monaco Editor
Monaco Diff Editor
```

Backend:

```text
Node.js
TypeScript
Fastify or Express
WebSocket
SQLite
Drizzle ORM
```

Agent:

```text
Qwen3-4B
4-bit inference
Tool-calling layer
Project context builder
```

Execution:

```text
child_process / spawn
isolated project directory
Vite
npm
TypeScript
ESLint
```

3D:

```text
Three.js
@react-three/fiber
@react-three/drei
```

---

# 55. Security

Do not blindly execute arbitrary model-generated shell commands.

Initial allowlist:

```text
npm install
npm run dev
npm run build
npm run lint
npm run typecheck
npx tsc
```

Block or require confirmation for dangerous operations:

```text
rm -rf
del /s
format
curl | bash
PowerShell downloads
sudo
system package installation
network tunneling
```

Enforce project-root path safety.

```ts
if (!resolvedPath.startsWith(projectRoot)) {
  throw new Error("Path outside project root");
}
```

---

# 56. Observability

Track:

```text
time to first activity
time to first file
time to preview
total generation time
build success rate
repair success rate
average repair attempts
cancel rate
follow-up prompt rate
undo rate
```

A key UX metric:

```text
Time To First Visible Progress
```

Target:

```text
< 500 ms
```

The user should quickly see:

```text
◌ Understanding your request...
```

---

# 57. End-to-End Example

```text
USER
Build a futuristic 3D SaaS website.
        │
        ▼
Message appears immediately in chat
        │
        ▼
SiteAgent
◌ Understanding your request...
        │
        ▼
✓ Planned site
◌ Creating interface...
        │
        ▼
Preview starts updating
        │
        ▼
✓ Interface
◌ Creating 3D scene...
        │
        ▼
Preview updates
        │
        ▼
◌ Checking build...
        │
    ┌───┴────┐
    │ ERROR  │
    ▼        │
◌ Fixing...  │
    │        │
    └────────┘
        │
        ▼
✓ Website ready

12 files · Build passed · 52s

[View Preview] [Review Changes]
```

Follow-up:

```text
USER
Make the globe larger and move it right.

SiteAgent
◌ Updating the 3D hero...

✓ Located Globe.tsx
◉ Adjusting scale and position
○ Checking build

✓ Updated the globe.

Changed 1 file
+3 −3

[Review changes] [Undo]
```

---

# 58. Final UX Layers

SiteAgent should communicate at three levels.

### Level 1 — Chat

```text
◌ Building the hero...
✓ Hero ready
◌ Checking the project...
```

### Level 2 — Logs

```text
write_file src/components/Hero.tsx
npm run build
TS2322 ...
repair attempt 1
```

### Level 3 — Inspector

```text
Model context
Tool calls
Task ID
GPU statistics
Selection metadata
Three.js object metadata
```

---

# 59. Final Architecture

```text
                           USER
                             │
                             ▼
                    ┌─────────────────┐
                    │   Chat Panel    │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ Agent Controller│
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ Context Builder │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │   Qwen3-4B      │
                    │   WebDev Agent  │
                    └────────┬────────┘
                             │
                  ┌──────────┼──────────┐
                  ▼          ▼          ▼
               Files      Terminal    Browser
                  │          │          │
                  └──────────┼──────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  Agent Event Bus│
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
           Chat UI         Logs UI       Inspector
              │
              ▼
         Live Preview
```

The most important behavioral change is:

> **The prompt becomes a chat message immediately, generation is represented as live structured activity, and the chat remains available after generation so the user can continue developing the project conversationally.**
