import React, { useEffect } from 'react';
import { TopBar } from '../components/topbar/TopBar';
import { ProjectSidebar } from '../components/projects/ProjectSidebar';
import { ChatPanel } from '../components/chat/ChatPanel';
import { WorkspaceResizer } from '../components/workspace/WorkspaceResizer';
import { WorkspacePanel } from '../components/workspace/WorkspacePanel';
import { InspectorDrawer } from '../components/inspector/InspectorDrawer';
import { ActiveGenerationModal } from '../components/modals/ActiveGenerationModal';
import { ConfirmDialog } from '../components/common/ConfirmDialog';
import { ToastProvider } from '../components/common/ToastProvider';
import { useAgentStore } from '../state/agent-store';
import { useWorkspaceStore } from '../state/workspace-store';
import { requestNewProject } from '../services/session';
import { api } from '../services/api';
import { projectWsClient } from '../services/project-ws';
// Registers the real SSE fallback; tests importing it alone cannot establish
// that the production application includes the backup transport.
import '../services/sse';

export const App: React.FC = () => {
  const { startTime, tickTimer, setQueueDepth, setSystemStatus } = useAgentStore();
  const { toggleInspector, toggleWorkspace, sidebarOpen, setSidebarOpen, syncSidebarViewport } = useWorkspaceStore();

  useEffect(() => {
    const query = window.matchMedia('(max-width: 767px)');
    const sync = () => syncSidebarViewport(query.matches);
    sync();
    query.addEventListener('change', sync);
    return () => query.removeEventListener('change', sync);
  }, [syncSidebarViewport]);

  useEffect(() => {
    if (!sidebarOpen) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && window.matchMedia('(max-width: 767px)').matches) setSidebarOpen(false);
    };
    window.addEventListener('keydown', closeOnEscape);
    return () => window.removeEventListener('keydown', closeOnEscape);
  }, [sidebarOpen, setSidebarOpen]);

  // Generation timer ticker
  useEffect(() => {
    if (!startTime) return;
    const interval = setInterval(() => {
      tickTimer();
    }, 100);
    return () => clearInterval(interval);
  }, [startTime]);

  // Periodic status poll (syncs model readiness, GPU readiness, server connection & queue depth)
  useEffect(() => {
    const poll = async () => {
      try {
        const res = await api.getStatus();
        if (res.project_websocket_ready && res.project_websocket_url) projectWsClient.setEndpoint(res.project_websocket_url);
        setQueueDepth(res.queue_depth || 0);
        setSystemStatus({
          serverConnected: true,
          modelLoaded: res.model_loaded === true && res.adapter_compatible === true,
          gpuReady: res.gpu_ready === true,
          modelName: res.model_name || res.loaded_model_path || 'Unavailable',
          baseFingerprint: res.base_fingerprint,
          adapterFingerprint: res.adapter_fingerprint,
          maxContextTokens: res.max_context_tokens,
        });
      } catch (_) {
        setSystemStatus({
          serverConnected: false,
        });
      }
    };

    poll();
    const interval = setInterval(poll, 4000);
    return () => clearInterval(interval);
  }, []);

  // Keyboard shortcut listener (Alt+1 for inspector, Alt+2 for workspace, Cmd+K / Ctrl+K for new project)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.altKey && e.key === '1') {
        e.preventDefault();
        toggleInspector();
      } else if (e.altKey && e.key === '2') {
        e.preventDefault();
        toggleWorkspace();
      } else if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        requestNewProject();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-[#171717] text-slate-100 font-sans">
      {/* Streamlined TopBar */}
      <TopBar />

      {/* Main layout: Sidebar + Centered Chat + Draggable Workspace + Inspector */}
      <div className="flex flex-1 h-[calc(100vh-48px)] overflow-hidden relative">
        {/* Project History Sidebar */}
        <ProjectSidebar />

        {/* Mobile backdrop for sidebar */}
        {sidebarOpen && (
          <div
            onClick={() => setSidebarOpen(false)}
            aria-hidden="true"
            className="md:hidden fixed inset-0 bg-black/60 z-10 backdrop-blur-xs"
          />
        )}

        {/* Primary Conversational Interface (Full width / flex-1) */}
        <div className="flex-1 flex flex-col h-full overflow-hidden min-w-[320px]">
          <ChatPanel />
        </div>

        {/* Draggable Workspace Adjustor Splitter */}
        <WorkspaceResizer />

        {/* Dynamic / Responsive Workspace Panel (Preview / Code / Diff / Logs / Shell) */}
        <WorkspacePanel />

        {/* Collapsible Inspector Drawer */}
        <InspectorDrawer />
      </div>

      {/* Active Generation Conflict Modal */}
      <ActiveGenerationModal />

      {/* Global Accessible Confirmation Dialog */}
      <ConfirmDialog />

      {/* Global Toast Notifications */}
      <ToastProvider />
    </div>
  );
};
