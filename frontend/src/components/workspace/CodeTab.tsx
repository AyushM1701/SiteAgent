import React, { useState, useEffect, useRef, useCallback } from 'react';
import Editor, { OnMount } from '@monaco-editor/react';
import {
  FileCode,
  FolderCode,
  Copy,
  Check,
  Download,
  Folder,
  FileText,
  Save,
  Undo2,
  AlertCircle,
  Trash2,
} from 'lucide-react';
import { useWorkspaceStore } from '../../state/workspace-store';
import { useProjectStore } from '../../state/project-store';
import { useConfirm } from '../../state/confirm-store';
import { toast } from '../../state/toast-store';
import { api } from '../../services/api';

export const CodeTab: React.FC = () => {
  const {
    files,
    codeDrafts,
    setCodeDraft,
    clearCodeDraft,
    activeFile,
    setActiveFile,
    setFiles,
    theme,
    reloadPreview,
  } = useWorkspaceStore();
  const { currentProjectId } = useProjectStore();
  const confirm = useConfirm();

  const [copied, setCopied] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const fileList = Object.keys(files);

  // Reset editor status notifications when switching project
  useEffect(() => {
    setSaveError(null);
    setSaveSuccess(false);
  }, [currentProjectId]);

  // Derive current file content (draft takes precedence over persisted file)
  const activeContent = activeFile
    ? codeDrafts[activeFile] !== undefined
      ? codeDrafts[activeFile]
      : files[activeFile] || ''
    : '// Select a file from the explorer';

  // Dirty state checks
  const isCurrentDirty = Boolean(
    activeFile &&
      codeDrafts[activeFile] !== undefined &&
      codeDrafts[activeFile] !== (files[activeFile] || '')
  );

  const isFileDirty = useCallback(
    (path: string) => {
      return (
        codeDrafts[path] !== undefined &&
        codeDrafts[path] !== (files[path] || '')
      );
    },
    [codeDrafts, files]
  );

  // Warn on page unload if any drafts are dirty
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      const hasDirty = Object.keys(codeDrafts).some(
        (p) => codeDrafts[p] !== undefined && codeDrafts[p] !== (files[p] || '')
      );
      if (hasDirty) {
        e.preventDefault();
        e.returnValue = '';
      }
    };
    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [codeDrafts, files]);

  const handleFileSelect = async (file: string) => {
    if (file === activeFile) return;
    if (isCurrentDirty) {
      const ok = await confirm({
        title: 'Unsaved Changes',
        message: `"${activeFile}" has unsaved changes. Do you want to keep your draft and switch to "${file}"?`,
        confirmText: 'Keep Draft & Switch',
        cancelText: 'Stay on Current File',
        variant: 'warning',
      });
      if (!ok) return;
    }
    setActiveFile(file);
  };

  const getLanguage = (path: string) => {
    if (path.endsWith('.tsx') || path.endsWith('.ts')) return 'typescript';
    if (path.endsWith('.jsx') || path.endsWith('.js')) return 'javascript';
    if (path.endsWith('.css')) return 'css';
    if (path.endsWith('.json')) return 'json';
    if (path.endsWith('.html')) return 'html';
    if (path.endsWith('.md')) return 'markdown';
    return 'plaintext';
  };

  const handleCopy = async () => {
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(activeContent);
      } else {
        const textArea = document.createElement('textarea');
        textArea.value = activeContent;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
      }
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      try {
        const textArea = document.createElement('textarea');
        textArea.value = activeContent;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      } catch {
        toast.error('Copy Failed', 'Clipboard access denied.');
      }
    }
  };

  const handleEditorChange = (value?: string) => {
    if (!activeFile) return;
    const val = value ?? '';
    setCodeDraft(activeFile, val);
  };

  const handleDiscard = () => {
    if (!activeFile) return;
    clearCodeDraft(activeFile);
    setSaveError(null);
  };

  const handleSave = useCallback(async () => {
    if (!currentProjectId || !activeFile || !isCurrentDirty || isSaving) return;

    const ok = await confirm({
      title: 'Overwrite File',
      message: `Are you sure you want to overwrite "${activeFile}" on disk? This will save your editor changes and run workspace verification.`,
      confirmText: 'Overwrite File',
      variant: 'warning',
    });
    if (!ok) return;

    setIsSaving(true);
    setSaveError(null);
    try {
      const res = await api.saveProjectFile(currentProjectId, activeFile, activeContent);
      if (res.files) {
        setFiles(res.files);
      }
      // Remove draft on successful persist
      clearCodeDraft(activeFile);
      reloadPreview();
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 2000);

      // Check validation result from save
      if (res.validation && (!res.validation.build_passed || !res.validation.typecheck_passed)) {
        const errDetails = Array.isArray(res.validation.errors) && res.validation.errors.length > 0
          ? res.validation.errors.join('\n')
          : 'Workspace verification failed after save.';
        toast.error('Build Failure', errDetails);
      } else {
        toast.success('File Saved', `Successfully updated "${activeFile}".`);
      }
    } catch (err: any) {
      console.error('Failed to save file:', err);
      setSaveError(err.message || 'Failed to save file');
      toast.error('Build Failure', err.message || 'Failed to save and verify project file.');
    } finally {
      setIsSaving(false);
    }
  }, [currentProjectId, activeFile, isCurrentDirty, isSaving, activeContent, setFiles, reloadPreview, confirm]);

  const handleDeleteFile = async (fileToDelete: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!currentProjectId) return;

    const ok = await confirm({
      title: 'Delete File',
      message: `Are you sure you want to delete "${fileToDelete}"? This action cannot be undone.`,
      confirmText: 'Delete File',
      variant: 'danger',
    });
    if (!ok) return;

    try {
      const res = await api.deleteProjectFile(currentProjectId, fileToDelete);
      if (res.files) {
        setFiles(res.files);
      } else {
        const nextFiles = { ...files };
        delete nextFiles[fileToDelete];
        setFiles(nextFiles);
      }
      clearCodeDraft(fileToDelete);
      if (activeFile === fileToDelete) {
        const remaining = fileList.filter((f) => f !== fileToDelete);
        setActiveFile(remaining.length > 0 ? remaining[0] : '');
      }
      toast.success('File Deleted', `Deleted "${fileToDelete}".`);
      reloadPreview();
    } catch (err: any) {
      console.error('Failed to delete file:', err);
      toast.error('Delete Failed', err.message || 'Could not delete file.');
    }
  };

  const handleExportZip = async () => {
    if (!currentProjectId || isExporting) return;
    setIsExporting(true);
    try {
      const res = await fetch(api.getProjectExportUrl(currentProjectId));
      if (!res.ok) {
        const errData = await res.json().catch(() => ({ error: res.statusText }));
        throw new Error(errData.error || `Export failed with HTTP ${res.status}`);
      }
      const blob = await res.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = downloadUrl;
      a.download = `${currentProjectId}.zip`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(downloadUrl);
      toast.success('Export Ready', 'Project ZIP downloaded successfully.');
    } catch (err: any) {
      console.error('Export error:', err);
      toast.error('Export Failure', err.message || 'Could not export project ZIP.');
    } finally {
      setIsExporting(false);
    }
  };

  // Keep a ref to handleSave for Monaco command handler
  const saveRef = useRef(handleSave);
  useEffect(() => {
    saveRef.current = handleSave;
  }, [handleSave]);

  // Global Ctrl+S / Cmd+S shortcut
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') {
        e.preventDefault();
        saveRef.current();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const handleEditorDidMount = (editor: any, monaco: any) => {
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => {
      saveRef.current();
    });
  };

  return (
    <div
      id="code-tab-container"
      className="flex-1 flex h-full bg-[#0a0c10] overflow-hidden select-none"
    >
      {/* Left File Explorer */}
      <div
        id="code-file-explorer"
        className="w-56 min-w-[200px] border-r border-white/[0.08] bg-[#141619] flex flex-col h-full"
      >
        <div className="p-3 border-b border-white/[0.06] text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <FolderCode size={14} className="text-emerald-400" />
            <span>Project Files</span>
          </div>
          <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-white/[0.06] text-slate-400 font-mono">
            {fileList.length}
          </span>
        </div>

        <div className="flex-1 overflow-y-auto p-1.5 space-y-0.5 font-mono text-xs">
          {fileList.length === 0 ? (
            <div className="p-4 text-center text-slate-500 text-xs">
              No files generated yet
            </div>
          ) : (
            fileList.map((file) => {
              const isSelected = file === activeFile;
              const isDirty = isFileDirty(file);

              return (
                <div
                  key={file}
                  id={`code-file-item-${file.replace(/[^a-zA-Z0-9_-]/g, '_')}`}
                  onClick={() => handleFileSelect(file)}
                  className={`group w-full flex items-center justify-between px-2.5 py-1.5 rounded text-left transition-all truncate cursor-pointer ${
                    isSelected
                      ? 'bg-emerald-500/10 text-emerald-300 font-medium border border-emerald-500/25 shadow-sm'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.04] border border-transparent'
                  }`}
                  title={file}
                >
                  <div className="flex items-center gap-2 truncate min-w-0">
                    <FileCode
                      size={13}
                      className={isSelected ? 'text-emerald-400' : 'text-slate-500'}
                    />
                    <span className="truncate">{file}</span>
                  </div>

                  <div className="flex items-center gap-1.5 shrink-0 ml-1.5">
                    {/* Dirty bullet */}
                    {isDirty && (
                      <span
                        className="w-2 h-2 rounded-full bg-amber-400 shadow-[0_0_6px_rgba(251,191,36,0.6)]"
                        title="Unsaved changes"
                      />
                    )}

                    {/* Delete file button */}
                    <button
                      type="button"
                      id={`code-delete-file-btn-${file.replace(/[^a-zA-Z0-9_-]/g, '_')}`}
                      onClick={(e) => handleDeleteFile(file, e)}
                      className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-rose-500/20 hover:text-rose-300 text-slate-500 transition-opacity cursor-pointer"
                      title={`Delete ${file}`}
                      aria-label={`Delete ${file}`}
                    >
                      <Trash2 size={12} />
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Right Monaco Editor Area */}
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        {/* Editor Toolbar */}
        <div
          id="code-editor-toolbar"
          className="h-11 border-b border-white/[0.08] bg-[#141619] px-4 flex items-center justify-between text-xs"
        >
          <div className="flex items-center gap-2.5 font-mono text-slate-300">
            <FileText size={14} className="text-emerald-400" />
            <span className="font-medium">{activeFile || 'No file selected'}</span>

            {/* Unsaved changes indicator badge */}
            {isCurrentDirty && (
              <span
                id="code-unsaved-badge"
                className="flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] bg-amber-500/15 text-amber-300 border border-amber-500/30 font-sans font-medium"
                title="File has unsaved modifications (Ctrl+S to save)"
              >
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
                <span>Unsaved changes</span>
              </span>
            )}

            {saveError && (
              <span className="flex items-center gap-1 px-2 py-0.5 rounded text-[11px] bg-rose-500/15 text-rose-300 border border-rose-500/30 font-sans">
                <AlertCircle size={12} />
                <span>{saveError}</span>
              </span>
            )}
          </div>

          <div className="flex items-center gap-2">
            {/* Discard changes button */}
            {isCurrentDirty && (
              <button
                id="code-discard-btn"
                onClick={handleDiscard}
                disabled={isSaving}
                className="flex items-center gap-1 px-2.5 py-1 rounded bg-white/[0.04] hover:bg-rose-500/15 hover:text-rose-300 hover:border-rose-500/30 text-slate-400 text-xs border border-white/[0.08] transition-all cursor-pointer disabled:opacity-50"
                title="Discard unsaved changes and revert to disk version"
              >
                <Undo2 size={12} />
                <span>Discard</span>
              </button>
            )}

            {/* Save file button */}
            {isCurrentDirty && (
              <button
                id="code-save-btn"
                onClick={handleSave}
                disabled={isSaving}
                className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 border border-emerald-500/40 text-xs font-semibold transition-all cursor-pointer shadow-sm disabled:opacity-50"
                title="Save changes to disk and trigger verification (Ctrl+S)"
              >
                {saveSuccess ? (
                  <>
                    <Check size={12} className="text-emerald-400" />
                    <span>Saved!</span>
                  </>
                ) : (
                  <>
                    <Save size={12} className={isSaving ? 'animate-spin' : ''} />
                    <span>{isSaving ? 'Saving...' : 'Save'}</span>
                    <span className="text-[10px] text-emerald-400/60 font-mono">Ctrl+S</span>
                  </>
                )}
              </button>
            )}

            {/* Copy button */}
            <button
              id="code-copy-btn"
              onClick={handleCopy}
              className="flex items-center gap-1 px-2.5 py-1 rounded bg-white/[0.04] hover:bg-white/[0.08] text-slate-300 text-xs border border-white/[0.06] transition-colors cursor-pointer"
              title="Copy current code to clipboard"
            >
              {copied ? (
                <>
                  <Check size={12} className="text-emerald-400" />
                  <span className="text-emerald-400 font-medium">Copied</span>
                </>
              ) : (
                <>
                  <Copy size={12} />
                  <span>Copy</span>
                </>
              )}
            </button>

            {/* Download ZIP button */}
            <button
              id="code-download-zip-btn"
              onClick={handleExportZip}
              disabled={!currentProjectId || isExporting}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-white/[0.04] hover:bg-emerald-500/15 hover:text-emerald-300 hover:border-emerald-500/30 text-slate-300 text-xs border border-white/[0.06] transition-all cursor-pointer font-medium disabled:opacity-40 disabled:cursor-not-allowed"
              title={currentProjectId ? "Download complete runnable project as ZIP" : "Select or generate a project to download ZIP"}
            >
              <Download size={12} className={`text-emerald-400 ${isExporting ? 'animate-bounce' : ''}`} />
              <span>{isExporting ? 'Exporting...' : 'Download ZIP'}</span>
            </button>
          </div>
        </div>

        {/* Monaco Editor */}
        <div id="monaco-code-editor-container" className="flex-1 overflow-hidden">
          <Editor
            height="100%"
            path={activeFile || 'untitled.tsx'}
            language={getLanguage(activeFile)}
            value={activeContent}
            onChange={handleEditorChange}
            onMount={handleEditorDidMount}
            theme={theme === 'dark' ? 'vs-dark' : 'light'}
            options={{
              readOnly: !activeFile || !currentProjectId,
              minimap: { enabled: true },
              fontSize: 13,
              fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
              scrollBeyondLastLine: false,
              automaticLayout: true,
              tabSize: 2,
              wordWrap: 'on',
              lineNumbers: 'on',
            }}
          />
        </div>
      </div>
    </div>
  );
};
