import React, { useEffect, useRef, useState } from 'react';
import { Terminal as XTerm } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import '@xterm/xterm/css/xterm.css';
import { Terminal, RefreshCw, Trash2 } from 'lucide-react';
import { shellClient } from '../../services/shell';
import { useProjectStore } from '../../state/project-store';

export const ShellTab: React.FC = () => {
  const terminalRef = useRef<HTMLDivElement>(null);
  const xtermInstance = useRef<XTerm | null>(null);
  const fitAddonInstance = useRef<FitAddon | null>(null);
  const [status, setStatus] = useState<'connecting' | 'connected' | 'disconnected'>('connecting');
  // Open the shell in the current project's folder.
  const projectDir = useProjectStore((state) => state.currentProject?.fullPath);
  const projectDirRef = useRef(projectDir);
  projectDirRef.current = projectDir;

  useEffect(() => {
    if (!terminalRef.current) return;

    const term = new XTerm({
      cursorBlink: true,
      fontSize: 13,
      fontFamily: "'JetBrains Mono', 'Cascadia Code', monospace",
      theme: {
        background: '#0a0c10',
        foreground: '#e2e8f0',
        cursor: '#6ee7b7',
        selectionBackground: 'rgba(110, 231, 183, 0.25)',
      },
    });

    const fitAddon = new FitAddon();
    term.loadAddon(fitAddon);
    term.open(terminalRef.current);
    fitAddon.fit();

    xtermInstance.current = term;
    fitAddonInstance.current = fitAddon;

    // Refit when the workspace panel is resized, not only the window, and tell the PTY.
    const handleResize = () => {
      try {
        fitAddon.fit();
        shellClient.resize(term.cols, term.rows);
      } catch (_) {}
    };
    const observer = new ResizeObserver(handleResize);
    observer.observe(terminalRef.current);

    // Wire up terminal data to shellClient
    term.onData((data) => {
      shellClient.send(data);
    });

    // Connect to backend WebSocket shell server
    connectShell(term);

    return () => {
      observer.disconnect();
      shellClient.disconnect();
      term.dispose();
    };
  }, []);

  // Reconnect in the new folder when the user switches project.
  const firstDir = useRef(true);
  useEffect(() => {
    if (firstDir.current) {
      firstDir.current = false;
      return;
    }
    if (xtermInstance.current) {
      xtermInstance.current.clear();
      connectShell(xtermInstance.current);
    }
  }, [projectDir]);

  const connectShell = (term: XTerm) => {
    setStatus('connecting');
    term.writeln('\x1b[38;5;244mConnecting to PowerShell terminal socket...\x1b[0m\r\n');

    shellClient.connect({
      onOpen: () => {
        setStatus('connected');
        term.writeln('\x1b[32m✔ Connected.\x1b[0m\r\n');
        const fit = fitAddonInstance.current;
        if (fit) {
          fit.fit();
          shellClient.resize(term.cols, term.rows);
        }
      },
      onData: (data) => {
        term.write(data);
      },
      onClose: () => {
        setStatus('disconnected');
        term.writeln('\r\n\x1b[33mTerminal connection closed.\x1b[0m\r\n');
      },
      onError: () => {
        setStatus('disconnected');
        term.writeln('\r\n\x1b[31mTerminal error occurred.\x1b[0m\r\n');
      },
    }, projectDirRef.current);
  };

  const handleReconnect = () => {
    if (xtermInstance.current) {
      xtermInstance.current.clear();
      connectShell(xtermInstance.current);
    }
  };

  const handleClear = () => {
    if (xtermInstance.current) {
      xtermInstance.current.clear();
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-[#0a0c10] overflow-hidden select-none">
      {/* Shell Toolbar */}
      <div className="h-10 border-b border-white/[0.06] bg-[#141619] px-3 flex items-center justify-between text-xs">
        <div className="flex items-center gap-2 text-slate-300">
          <Terminal size={14} className="text-amber-400" />
          <span className="font-semibold">PowerShell PTY</span>
          <span
            className={`w-2 h-2 rounded-full ${
              status === 'connected'
                ? 'bg-emerald-400'
                : status === 'connecting'
                ? 'bg-amber-400 animate-pulse'
                : 'bg-rose-500'
            }`}
          />
        </div>

        <div className="flex items-center gap-1.5">
          <button
            id="shell-reconnect-btn"
            onClick={handleReconnect}
            className="p-1 rounded hover:bg-white/[0.06] text-slate-400 hover:text-slate-200 cursor-pointer"
            title="Reconnect Terminal"
          >
            <RefreshCw size={13} />
          </button>
          <button
            id="shell-clear-btn"
            onClick={handleClear}
            className="p-1 rounded hover:bg-white/[0.06] text-slate-400 hover:text-slate-200 cursor-pointer"
            title="Clear Terminal"
          >
            <Trash2 size={13} />
          </button>
        </div>
      </div>

      {/* Terminal View */}
      <div id="shell-terminal-container" ref={terminalRef} className="flex-1 p-2 bg-[#0a0c10] overflow-hidden" />
    </div>
  );
};
