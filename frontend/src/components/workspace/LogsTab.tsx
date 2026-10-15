import React, { useRef, useEffect } from 'react';
import { 
  Terminal, 
  Trash2, 
  Search, 
  ArrowDown, 
  Filter 
} from 'lucide-react';
import { useWorkspaceStore } from '../../state/workspace-store';
import { LogCategory, LogLevel } from '../../types/logs';

export const LogsTab: React.FC = () => {
  const {
    logs,
    logFilterLevel,
    logFilterCategory,
    logSearch,
    logAutoScroll,
    setLogFilterLevel,
    setLogFilterCategory,
    setLogSearch,
    setLogAutoScroll,
    clearLogs,
  } = useWorkspaceStore();

  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (logAutoScroll && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs, logAutoScroll]);

  const filteredLogs = logs.filter((log) => {
    if (logFilterLevel !== 'all' && log.level !== logFilterLevel) return false;
    if (logFilterCategory !== 'all' && log.category !== logFilterCategory) return false;
    if (logSearch && !log.message.toLowerCase().includes(logSearch.toLowerCase())) return false;
    return true;
  });

  const levelColor = {
    info: 'text-slate-300',
    warn: 'text-amber-400',
    error: 'text-rose-400 font-semibold',
    debug: 'text-slate-500',
  };

  const categoryBadge = {
    agent: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
    build: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20',
    compiler: 'bg-teal-500/10 text-teal-400 border-teal-500/20',
    shell: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
    network: 'bg-violet-500/10 text-violet-400 border-violet-500/20',
    motion: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
    all: 'bg-slate-500/10 text-slate-400 border-slate-500/20',
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-[#0a0c10] overflow-hidden select-none font-mono text-xs">
      {/* Logs Toolbar */}
      <div className="h-10 border-b border-white/[0.06] bg-[#141619] px-3 flex items-center justify-between gap-2">
        {/* Left: filters */}
        <div className="flex items-center gap-2">
          {/* Category Filter */}
          <select
            id="logs-category-filter"
            value={logFilterCategory}
            onChange={(e) => setLogFilterCategory(e.target.value as LogCategory)}
            className="bg-[#191c20] text-slate-300 px-2 py-0.5 rounded border border-white/[0.08] focus:outline-none text-[11px] cursor-pointer"
          >
            <option value="all">All Categories</option>
            <option value="agent">Agent</option>
            <option value="build">Build</option>
            <option value="compiler">Compiler</option>
            <option value="motion">Motion</option>
            <option value="shell">Shell</option>
          </select>

          {/* Severity Filter */}
          <select
            id="logs-level-filter"
            value={logFilterLevel}
            onChange={(e) => setLogFilterLevel(e.target.value as LogLevel)}
            className="bg-[#191c20] text-slate-300 px-2 py-0.5 rounded border border-white/[0.08] focus:outline-none text-[11px] cursor-pointer"
          >
            <option value="all">All Levels</option>
            <option value="info">Info</option>
            <option value="warn">Warnings</option>
            <option value="error">Errors</option>
          </select>

          {/* Search box */}
          <div className="relative">
            <Search size={11} className="absolute left-2 top-2 text-slate-500" />
            <input
              id="logs-search-input"
              type="text"
              placeholder="Search logs..."
              value={logSearch}
              onChange={(e) => setLogSearch(e.target.value)}
              className="bg-[#191c20] text-slate-200 pl-6 pr-2 py-0.5 rounded border border-white/[0.08] text-[11px] focus:outline-none w-32 sm:w-44"
            />
          </div>
        </div>

        {/* Right: Auto-scroll & Clear */}
        <div className="flex items-center gap-1.5">
          <button
            id="logs-autoscroll-btn"
            onClick={() => setLogAutoScroll(!logAutoScroll)}
            className={`flex items-center gap-1 px-2 py-0.5 rounded text-[11px] border transition-colors cursor-pointer ${
              logAutoScroll
                ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                : 'border-white/[0.06] text-slate-400'
            }`}
            title="Auto-scroll to latest log"
          >
            <ArrowDown size={11} />
            <span>Scroll</span>
          </button>

          <button
            id="logs-clear-btn"
            onClick={() => clearLogs()}
            className="p-1 rounded hover:bg-white/[0.06] text-slate-400 hover:text-slate-200 cursor-pointer"
            title="Clear all logs"
          >
            <Trash2 size={13} />
          </button>
        </div>
      </div>

      {/* Logs Stream */}
      <div id="logs-list-container" ref={scrollRef} className="flex-1 overflow-y-auto p-3 space-y-1 select-text">
        {filteredLogs.length === 0 ? (
          <div className="h-full flex items-center justify-center text-slate-500 text-xs">
            No logs to display
          </div>
        ) : (
          filteredLogs.map((log) => (
            <div key={log.id} className="flex items-start gap-2 leading-relaxed">
              <span className="text-slate-600 shrink-0 select-none">{log.timeStr}</span>
              <span
                className={`px-1.5 py-0.2 rounded text-[10px] uppercase tracking-wider shrink-0 border ${
                  categoryBadge[log.category] || categoryBadge.all
                }`}
              >
                {log.category}
              </span>
              <span className={`break-all ${levelColor[log.level]}`}>
                {log.message}
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
