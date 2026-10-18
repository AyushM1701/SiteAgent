import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import Editor, { DiffEditor } from '@monaco-editor/react';
import {
  RotateCcw,
  FileDiff,
  Check,
  Columns,
  FileText,
  File,
  Sparkles,
  Info,
  CheckCircle2,
} from 'lucide-react';
import { useWorkspaceStore } from '../../state/workspace-store';
import { useProjectStore } from '../../state/project-store';
import { api } from '../../services/api';
import { CanonicalTurnDiff, FileDiffEntry } from '../../types/chat';
import { useConfirm } from '../../state/confirm-store';
import { toast } from '../../state/toast-store';

function getLanguageForFile(filePath: string): string {
  const ext = filePath.split('.').pop()?.toLowerCase();
  switch (ext) {
    case 'ts':
    case 'tsx':
      return 'typescript';
    case 'js':
    case 'jsx':
      return 'javascript';
    case 'css':
      return 'css';
    case 'html':
      return 'html';
    case 'json':
      return 'json';
    case 'md':
      return 'markdown';
    default:
      return 'plaintext';
  }
}

export const DiffTab: React.FC = () => {
  const { currentProjectId, currentProject } = useProjectStore();
  const {
    diffOriginal,
    diffModified,
    diffTurn,
    diffFilename,
    setDiff,
    setFiles,
    reloadPreview,
    theme,
  } = useWorkspaceStore();

  const [selectedTurn, setSelectedTurn] = useState<number>(diffTurn || 1);
  const [turnDiff, setTurnDiff] = useState<CanonicalTurnDiff | null>(null);
  const [selectedFile, setSelectedFile] = useState<string>(diffFilename || '');
  const [viewMode, setViewMode] = useState<'split' | 'patch'>('split');
  const [isLoading, setIsLoading] = useState(false);
  const [reverting, setReverting] = useState(false);
  const [revertSuccess, setRevertSuccess] = useState(false);
  const confirm = useConfirm();
  const containerRef = useRef<HTMLDivElement>(null);
  const [narrow, setNarrow] = useState(false);

  useEffect(() => {
    const node = containerRef.current;
    if (!node) return;
    const observer = new ResizeObserver(() => setNarrow(node.clientWidth < 680));
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  const turnCount = currentProject?.turnCount || 1;
  // Reverting to the latest turn would change nothing.
  const isLatestTurn = selectedTurn >= turnCount;

  // Derive file entries map and list
  const filesMap: Record<string, FileDiffEntry> = useMemo(() => {
    return turnDiff?.files || {};
  }, [turnDiff]);

  const fileList = useMemo(() => {
    return Object.keys(filesMap);
  }, [filesMap]);

  const currentFileEntry = useMemo(() => {
    return selectedFile && filesMap[selectedFile] ? filesMap[selectedFile] : null;
  }, [selectedFile, filesMap]);

  // Load canonical turn diff
  const loadDiff = useCallback(
    async (turn: number) => {
      if (!currentProjectId) return;
      setIsLoading(true);
      try {
        const data = await api.getDiff(currentProjectId, turn);
        setTurnDiff(data);

        const loadedFiles = Object.keys(data.files || {});
        // Select first changed file by default, or preserve selectedFile if still present
        const targetFile =
          selectedFile && loadedFiles.includes(selectedFile)
            ? selectedFile
            : loadedFiles[0] || '';

        setSelectedFile(targetFile);

        if (targetFile && data.files && data.files[targetFile]) {
          const entry = data.files[targetFile];
          setDiff(entry.before || '', entry.after || '', turn, targetFile);
        } else {
          setDiff('', '', turn, targetFile);
        }
      } catch (err) {
        console.error('Failed to load turn diff:', err);
      } finally {
        setIsLoading(false);
      }
    },
    [currentProjectId, selectedFile, setDiff]
  );

  // Sync turn count changes
  useEffect(() => {
    if (diffTurn && diffTurn !== selectedTurn) {
      setSelectedTurn(diffTurn);
    }
  }, [diffTurn]);

  // Reset diff state if no project is active
  useEffect(() => {
    if (!currentProjectId) {
      setTurnDiff(null);
      setSelectedFile('');
      setSelectedTurn(1);
    }
  }, [currentProjectId]);

  // Fetch diff on project or turn change
  useEffect(() => {
    if (currentProjectId && turnCount > 0) {
      loadDiff(selectedTurn);
    }
  }, [currentProjectId, selectedTurn]);

  // Switch file directly from cached turnDiff without reloading network data
  const handleFileSelect = (file: string) => {
    if (file === selectedFile) return;
    setSelectedFile(file);
    const entry = filesMap[file];
    if (entry) {
      setDiff(entry.before || '', entry.after || '', selectedTurn, file);
    }
  };

  const handleRevert = async () => {
    if (!currentProjectId) return;
    const ok = await confirm({
      title: 'Revert Checkpoint',
      message: `Revert project back to Checkpoint Turn ${selectedTurn}? Any unsaved edits or later turns will be rolled back.`,
      confirmText: `Revert to Turn ${selectedTurn}`,
      variant: 'danger',
    });
    if (!ok) return;

    setReverting(true);
    try {
      const result = await api.revertTurn(currentProjectId, selectedTurn);
      if (result.files) {
        setFiles(result.files);
      }
      reloadPreview();
      loadDiff(selectedTurn);
      setRevertSuccess(true);
      setTimeout(() => setRevertSuccess(false), 2500);
      toast.success('Project Reverted', `Successfully restored project files to Turn ${selectedTurn}.`);
    } catch (err: any) {
      console.error('Revert failed:', err);
      toast.error('Revert Failed', err.message || String(err));
    } finally {
      setReverting(false);
    }
  };

  return (
    <div
      id="diff-tab-container"
      ref={containerRef}
      className="flex-1 flex flex-col h-full bg-[#0a0c10] overflow-hidden"
    >
      {/* Diff Toolbar */}
      <div
        id="diff-toolbar"
        className="h-11 border-b border-white/[0.08] bg-[#141619] px-3 flex items-center justify-between text-xs gap-2 select-none"
      >
        <div className="flex items-center gap-3 min-w-0">
          {!narrow && (
            <div className="flex items-center gap-1.5 font-semibold text-slate-200 whitespace-nowrap">
              <FileDiff size={15} className="text-emerald-400" />
              <span className="tracking-wide">Diff</span>
            </div>
          )}

          {/* Turn selector */}
          <div className="flex items-center gap-1.5 font-mono text-slate-400">
            <span className="text-[11px] uppercase tracking-wider text-slate-500 font-sans font-medium">
              Turn:
            </span>
            <select
              id="diff-turn-select"
              value={selectedTurn}
              onChange={(e) => setSelectedTurn(Number(e.target.value))}
              className="bg-[#1a1d22] text-slate-200 px-2.5 py-1 rounded border border-white/[0.1] focus:outline-none focus:border-emerald-500/50 transition-colors text-xs font-medium cursor-pointer"
            >
              {Array.from({ length: turnCount }, (_, i) => i + 1).map((t) => (
                <option key={t} value={t}>
                  Turn {t}{t === 1 ? ' (first)' : ` vs ${t - 1}`}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {/* View Mode Toggle (Split Diff vs Unified Patch) */}
          <div
            id="diff-view-mode-toggle"
            className="flex items-center bg-[#191c20] p-0.5 rounded border border-white/[0.08]"
          >
            <button
              id="diff-split-view-btn"
              onClick={() => setViewMode('split')}
              className={`flex items-center gap-1 px-2 py-1 rounded text-[11px] font-medium transition-all cursor-pointer ${
                viewMode === 'split'
                  ? 'bg-emerald-500/20 text-emerald-300 shadow-sm border border-emerald-500/30'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
              title="Side-by-side Monaco diff comparison"
            >
              <Columns size={12} />
              <span className={narrow ? 'sr-only' : 'whitespace-nowrap'}>Split</span>
            </button>
            <button
              id="diff-patch-view-btn"
              onClick={() => setViewMode('patch')}
              className={`flex items-center gap-1 px-2 py-1 rounded text-[11px] font-medium transition-all cursor-pointer ${
                viewMode === 'patch'
                  ? 'bg-emerald-500/20 text-emerald-300 shadow-sm border border-emerald-500/30'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
              title="Unified patch syntax view"
            >
              <FileText size={12} />
              <span className={narrow ? 'sr-only' : 'whitespace-nowrap'}>Patch</span>
            </button>
          </div>

          {/* Revert button */}
          <button
            id="diff-revert-btn"
            onClick={handleRevert}
            disabled={reverting || isLatestTurn}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-amber-500/15 hover:bg-amber-500/25 text-amber-300 border border-amber-500/30 text-xs font-medium transition-all cursor-pointer whitespace-nowrap disabled:opacity-40 disabled:cursor-not-allowed"
            title={isLatestTurn ? 'This is the current version; pick an earlier turn to revert to it' : `Revert workspace to Turn ${selectedTurn}`}
          >
            {revertSuccess ? (
              <>
                <Check size={13} className="text-emerald-400" />
                <span className="text-emerald-400 font-semibold">Reverted!</span>
              </>
            ) : (
              <>
                <RotateCcw size={12} className={reverting ? 'animate-spin' : ''} />
                <span>{narrow ? 'Revert' : `Revert to turn ${selectedTurn}`}</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Changed Files Bar */}
      <div
        id="diff-files-bar"
        className="min-h-9 border-b border-white/[0.06] bg-[#111316] px-3 flex items-center gap-2 overflow-x-auto scrollbar-thin"
      >
        <div className="flex items-center gap-1.5 text-slate-500 text-[11px] font-medium shrink-0 pr-1">
          <span>Changed Files:</span>
          <span className="px-1.5 py-0.2 rounded-full bg-white/[0.06] text-slate-300 font-mono text-[10px]">
            {fileList.length}
          </span>
        </div>

        {fileList.length === 0 ? (
          <span className="text-slate-500 text-xs italic">
            No files modified in this turn
          </span>
        ) : (
          <div className="flex items-center gap-1.5 py-1">
            {fileList.map((file) => {
              const isSelected = file === selectedFile;
              const entry = filesMap[file];
              const isNew = !entry?.before && Boolean(entry?.after);
              const isDeleted = Boolean(entry?.before) && !entry?.after;

              return (
                <button
                  key={file}
                  id={`diff-file-btn-${file.replace(/[^a-zA-Z0-9_-]/g, '_')}`}
                  onClick={() => handleFileSelect(file)}
                  className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-mono transition-all cursor-pointer border ${
                    isSelected
                      ? 'bg-emerald-500/15 border-emerald-500/40 text-emerald-200 shadow-sm'
                      : 'bg-[#181a1f] border-white/[0.06] text-slate-400 hover:text-slate-200 hover:border-white/[0.15]'
                  }`}
                  title={file}
                >
                  <File size={12} className={isSelected ? 'text-emerald-400' : 'text-slate-500'} />
                  <span className="truncate max-w-[200px]">{file.split('/').pop()}</span>
                  {isNew ? (
                    <span className="text-[10px] px-1 py-0.2 rounded bg-emerald-500/20 text-emerald-400 font-sans font-semibold">
                      +
                    </span>
                  ) : isDeleted ? (
                    <span className="text-[10px] px-1 py-0.2 rounded bg-rose-500/20 text-rose-400 font-sans font-semibold">
                      -
                    </span>
                  ) : null}
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* Editor Body */}
      <div className="flex-1 overflow-hidden relative">
        {isLoading ? (
          <div
            id="diff-loading-indicator"
            className="h-full flex flex-col items-center justify-center gap-2 text-slate-400 text-xs"
          >
            <div className="w-5 h-5 border-2 border-emerald-500/30 border-t-emerald-400 rounded-full animate-spin" />
            <span>Loading checkpoint diff for Turn {selectedTurn}...</span>
          </div>
        ) : fileList.length === 0 ? (
          <div
            id="diff-empty-turn-state"
            className="h-full flex flex-col items-center justify-center text-center p-6"
          >
            <div className="w-12 h-12 rounded-full bg-slate-800/80 border border-white/[0.08] flex items-center justify-center mb-3">
              <CheckCircle2 size={24} className="text-emerald-400" />
            </div>
            <h3 className="text-sm font-semibold text-slate-200 mb-1">
              No files changed in Turn {selectedTurn}
            </h3>
            <p className="text-xs text-slate-400 max-w-md mb-2 leading-relaxed">
              This turn completed without modifying project files (e.g. read-only dependency query
              or validation status check).
            </p>
            {turnDiff?.summary && (
              <div className="mt-2 p-3 bg-white/[0.03] border border-white/[0.06] rounded max-w-lg text-left text-xs font-mono text-slate-300">
                <span className="text-slate-500 block text-[10px] uppercase tracking-wider mb-1 font-sans">
                  Turn Summary
                </span>
                {turnDiff.summary}
              </div>
            )}
          </div>
        ) : viewMode === 'split' ? (
          <div id="monaco-diff-viewer" className="w-full h-full">
            <DiffEditor
              key={`${selectedTurn}:${selectedFile}`}
              keepCurrentOriginalModel
              keepCurrentModifiedModel
              originalModelPath={`diff-original/${selectedTurn}/${selectedFile}`}
              modifiedModelPath={`diff-modified/${selectedTurn}/${selectedFile}`}
              height="100%"
              original={currentFileEntry?.before ?? ''}
              modified={currentFileEntry?.after ?? ''}
              language={getLanguageForFile(selectedFile)}
              theme={theme === 'dark' ? 'vs-dark' : 'light'}
              options={{
                readOnly: true,
                renderSideBySide: true,
                fontSize: 13,
                fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
                automaticLayout: true,
                minimap: { enabled: false },
                scrollBeyondLastLine: false,
                renderWhitespace: 'selection',
              }}
            />
          </div>
        ) : (
          <div id="monaco-patch-viewer" className="w-full h-full">
            <Editor
              height="100%"
              value={currentFileEntry?.patch ?? ''}
              language="diff"
              theme={theme === 'dark' ? 'vs-dark' : 'light'}
              options={{
                readOnly: true,
                fontSize: 13,
                fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
                automaticLayout: true,
                minimap: { enabled: false },
                scrollBeyondLastLine: false,
                lineNumbers: 'on',
              }}
            />
          </div>
        )}
      </div>
    </div>
  );
};
