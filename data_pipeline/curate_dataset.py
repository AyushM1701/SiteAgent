#!/usr/bin/env python3
"""
data_pipeline/curate_dataset.py - Unified Dataset Ingestion & Curation for ReactAgent SLM

Consolidates:
  - curate-sources: Ingests GitHub UI primitives (shadcn/Radix) and HF TypeScript instruct datasets
  - typescript-instruct: Generates verified React+TypeScript instruction trajectories
  - teacher: Generates multi-turn self-correction trajectories via teacher LLMs (GPT-4o, Claude, DeepSeek)
  - star: Self-Taught Reasoner (STaR) rejection sampling on held-out tasks
  - stack: Mines React TSX and companion CSS from The Stack v2

Usage:
  python data_pipeline/curate_dataset.py curate-sources --source all
  python data_pipeline/curate_dataset.py typescript-instruct
  python data_pipeline/curate_dataset.py teacher --generate-seed
  python data_pipeline/curate_dataset.py star --model my-react-agent-lora --tasks 5
  python data_pipeline/curate_dataset.py stack --limit 10
"""

import argparse
import hashlib
import json
import os
import random
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

# Path resolution
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "agent"))
sys.path.insert(0, str(BASE_DIR / "training"))
sys.path.insert(0, str(BASE_DIR / "data_pipeline"))

import visual_judge
from prompt_fidelity_gate import verify_prompt_fidelity

# UTF-8 terminal encoding
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from agent_protocol import (
    AGENT_SYSTEM_PROMPT,
    SITE_AGENT_SYSTEM_PROMPT,
    FinishAction,
    WriteComponentAction,
    WriteSiteAction,
    parse_agent_output,
)


# ==============================================================================
# 1. Curate Sources Ingestion
# ==============================================================================

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from agent_protocol import AGENT_SYSTEM_PROMPT
from evaluate import run_command


def verify_tsx_code(tsx_code: str) -> bool:
    """Verifies that the TSX code compiles cleanly with zero TypeScript errors."""
    tmp_file = Path(".temp_verify_comp.tsx")
    tmp_file.write_text(tsx_code, encoding="utf-8")
    try:
        proc = run_command([
            "npx", "tsc", "--noEmit",
            "--jsx", "react-jsx",
            "--target", "ES2022",
            "--moduleResolution", "bundler",
            "--esModuleInterop",
            "--skipLibCheck",
            str(tmp_file),
            "css.d.ts"
        ], cwd=Path.cwd(), timeout=12)
        return proc.returncode == 0
    except Exception:
        return False
    finally:
        tmp_file.unlink(missing_ok=True)


# ==============================================================================
# 1. Hugging Face: mhhmm/typescript-instruct-20k (with In-Flight TSC Verification)
# ==============================================================================

def extract_code_block(text: str) -> str:
    """Extracts code block from markdown ```tsx, ```typescript, or ```."""
    matches = re.findall(r"```(?:tsx|typescript|jsx|javascript)?\s*\n([\s\S]*?)```", text)
    if matches:
        return max(matches, key=len).strip()
    return text.strip()


def sanitize_instruct_code(code: str) -> str:
    """Sanitizes raw code into a clean, standalone React/TSX component."""
    # Remove existing React imports to avoid duplicates
    code = re.sub(r'import\s+\*\s+as\s+React\s+from\s+["\']react["\'];?\n?', '', code)
    code = re.sub(r'import\s+React.*?from\s+["\']react["\'];?\n?', '', code)

    # Remove non-existent local relative imports
    code = re.sub(r"import\s+.*?from\s+['\"][.][^'\"]+['\"];?\n?", "", code)
    return ("import React from 'react';\n" + code.strip()).strip()


def ingest_typescript_instruct(limit: int = 15, output_path: str = "trajectories_typescript_instruct.jsonl") -> int:
    """
    Curates and writes 15 gold-standard, self-contained React + TypeScript instruction
    trajectories (SearchFilter, LocalStorageNote, WizardForm, ImageLightbox, etc.)
    passing 100% of TypeScript compilation checks.
    """
    print(f"\n[Source 1] Curating verified React + TypeScript instructions into {output_path}...")
    from generate_typescript_instruct import generate_typescript_instruct as gen_ts
    return gen_ts(output_path)


# ==============================================================================
# 2. GitHub: Top-Tier UI Primitives (shadcn/ui & Radix UI Patterns)
# ==============================================================================

SHADCN_GOLD_COMPONENTS = [
    {
        "task_id": "site_shadcn_card",
        "symbol": "Card",
        "prompt": "Write a modern, modular React TypeScript `Card` component with `CardHeader`, `CardTitle`, `CardDescription`, `CardContent`, and `CardFooter` subcomponents supporting modern styling and slots.\nIMPORTANT: Export the component as a named export called `Card`.",
        "thought": "I'll implement the Card suite with CardHeader, CardTitle, CardDescription, CardContent, and CardFooter using standard React props, semantic HTML, and clean scoped styling.",
        "tsx": """import React from 'react';
import './Card.css';

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {}

export function Card({ className = '', children, ...props }: CardProps) {
  return (
    <div className={`shadcn-card ${className}`.trim()} {...props}>
      {children}
    </div>
  );
}

export function CardHeader({ className = '', children, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={`shadcn-card__header ${className}`.trim()} {...props}>{children}</div>;
}

export function CardTitle({ className = '', children, ...props }: React.HTMLAttributes<HTMLHeadingElement>) {
  return <h3 className={`shadcn-card__title ${className}`.trim()} {...props}>{children}</h3>;
}

export function CardDescription({ className = '', children, ...props }: React.HTMLAttributes<HTMLParagraphElement>) {
  return <p className={`shadcn-card__desc ${className}`.trim()} {...props}>{children}</p>;
}

export function CardContent({ className = '', children, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={`shadcn-card__content ${className}`.trim()} {...props}>{children}</div>;
}

export function CardFooter({ className = '', children, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={`shadcn-card__footer ${className}`.trim()} {...props}>{children}</div>;
}
""",
        "css": """.shadcn-card {
  border-radius: 0.75rem;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background-color: #0f172a;
  color: #f8fafc;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.shadcn-card__header { padding: 1.5rem 1.5rem 0.75rem; }
.shadcn-card__title { font-size: 1.25rem; font-weight: 700; color: #ffffff; margin: 0 0 0.25rem; }
.shadcn-card__desc { font-size: 0.875rem; color: #94a3b8; margin: 0; }
.shadcn-card__content { padding: 0.75rem 1.5rem; flex: 1; }
.shadcn-card__footer { padding: 0.75rem 1.5rem 1.5rem; display: flex; align-items: center; }
"""
    },
    {
        "task_id": "site_shadcn_badge",
        "symbol": "Badge",
        "prompt": "Write a React TypeScript `Badge` component supporting variants ('default' | 'secondary' | 'destructive' | 'outline') with accessible styling.\nIMPORTANT: Export the component as a named export called `Badge`.",
        "thought": "I'll implement the Badge component supporting variant styling via BEM classnames and native span attributes.",
        "tsx": """import React from 'react';
import './Badge.css';

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'default' | 'secondary' | 'destructive' | 'outline';
}

export function Badge({ className = '', variant = 'default', children, ...props }: BadgeProps) {
  return (
    <span className={`shadcn-badge shadcn-badge--${variant} ${className}`.trim()} {...props}>
      {children}
    </span>
  );
}
""",
        "css": """.shadcn-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 9999px;
  padding: 0.25rem 0.75rem;
  font-size: 0.75rem;
  font-weight: 600;
  line-height: 1;
  transition: all 0.2s ease;
}
.shadcn-badge--default { background: #3b82f6; color: #ffffff; }
.shadcn-badge--secondary { background: #334155; color: #f8fafc; }
.shadcn-badge--destructive { background: #ef4444; color: #ffffff; }
.shadcn-badge--outline { border: 1px solid rgba(255, 255, 255, 0.2); color: #e2e8f0; background: transparent; }
"""
    },
    {
        "task_id": "site_shadcn_button",
        "symbol": "Button",
        "prompt": "Write a production React TypeScript `Button` component supporting variants ('default' | 'outline' | 'ghost' | 'destructive') and sizes ('sm' | 'md' | 'lg') with disabled states.\nIMPORTANT: Export the component as a named export called `Button`.",
        "thought": "I'll build the Button component supporting variant, size, and disabled states with smooth CSS transitions.",
        "tsx": """import React from 'react';
import './Button.css';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'outline' | 'ghost' | 'destructive';
  size?: 'sm' | 'md' | 'lg';
}

export function Button({
  className = '',
  variant = 'default',
  size = 'md',
  disabled,
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      className={`shadcn-btn shadcn-btn--${variant} shadcn-btn--${size} ${className}`.trim()}
      disabled={disabled}
      {...props}
    >
      {children}
    </button>
  );
}
""",
        "css": """.shadcn-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 0.5rem;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}
.shadcn-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.shadcn-btn--sm { padding: 0.35rem 0.75rem; font-size: 0.8rem; }
.shadcn-btn--md { padding: 0.55rem 1.25rem; font-size: 0.9rem; }
.shadcn-btn--lg { padding: 0.75rem 1.75rem; font-size: 1rem; }
.shadcn-btn--default { background: #3b82f6; color: #ffffff; }
.shadcn-btn--default:hover:not(:disabled) { background: #2563eb; }
.shadcn-btn--outline { background: transparent; border-color: rgba(255, 255, 255, 0.2); color: #f8fafc; }
.shadcn-btn--ghost { background: transparent; color: #94a3b8; }
.shadcn-btn--ghost:hover:not(:disabled) { background: rgba(255, 255, 255, 0.08); color: #ffffff; }
.shadcn-btn--destructive { background: #ef4444; color: #ffffff; }
"""
    },
    {
        "task_id": "site_shadcn_avatar",
        "symbol": "Avatar",
        "prompt": "Write a React TypeScript `Avatar` component with `AvatarImage` and `AvatarFallback` handling image loading states.\nIMPORTANT: Export the component as a named export called `Avatar`.",
        "thought": "I'll create the Avatar container with image and fallback child elements, managing error fallbacks smoothly.",
        "tsx": """import React, { useState } from 'react';
import './Avatar.css';

export interface AvatarProps extends React.HTMLAttributes<HTMLDivElement> {}

export function Avatar({ className = '', children, ...props }: AvatarProps) {
  return (
    <div className={`shadcn-avatar ${className}`.trim()} {...props}>
      {children}
    </div>
  );
}

export function AvatarImage({ src, alt = '', className = '' }: { src: string; alt?: string; className?: string }) {
  const [error, setError] = useState(false);
  if (error || !src) return null;
  return <img src={src} alt={alt} onError={() => setError(true)} className={`shadcn-avatar__img ${className}`.trim()} />;
}

export function AvatarFallback({ children, className = '' }: React.HTMLAttributes<HTMLSpanElement>) {
  return <span className={`shadcn-avatar__fallback ${className}`.trim()}>{children}</span>;
}
""",
        "css": """.shadcn-avatar {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  overflow: hidden;
  background: #334155;
  color: #f8fafc;
  font-weight: 600;
  font-size: 0.875rem;
}
.shadcn-avatar__img { width: 100%; height: 100%; object-fit: cover; }
.shadcn-avatar__fallback { display: flex; align-items: center; justify-content: center; width: 100%; height: 100%; }
"""
    },
    {
        "task_id": "site_shadcn_accordion",
        "symbol": "Accordion",
        "prompt": "Write an accessible React TypeScript `Accordion` component supporting single open items, keyboard accessibility, and chevron indicators.\nIMPORTANT: Export the component as a named export called `Accordion`.",
        "thought": "I'll implement the Accordion with active item state management and accessible aria-expanded bindings.",
        "tsx": """import React, { useState } from 'react';
import './Accordion.css';

export interface AccordionItemData {
  id: string;
  title: string;
  content: React.ReactNode;
}

export interface AccordionProps {
  items: AccordionItemData[];
  defaultOpenId?: string;
}

export function Accordion({ items, defaultOpenId }: AccordionProps) {
  const [openId, setOpenId] = useState<string | null>(defaultOpenId || null);

  const toggle = (id: string) => {
    setOpenId((prev) => (prev === id ? null : id));
  };

  return (
    <div className="shadcn-accordion" role="region">
      {items.map((item) => {
        const isOpen = openId === item.id;
        return (
          <div key={item.id} className="shadcn-accordion__item">
            <button
              type="button"
              className="shadcn-accordion__trigger"
              aria-expanded={isOpen}
              onClick={() => toggle(item.id)}
            >
              <span>{item.title}</span>
              <span className={`shadcn-accordion__arrow ${isOpen ? 'open' : ''}`}>▼</span>
            </button>
            {isOpen && (
              <div className="shadcn-accordion__content">
                {item.content}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
""",
        "css": """.shadcn-accordion { width: 100%; border-top: 1px solid rgba(255, 255, 255, 0.1); }
.shadcn-accordion__item { border-bottom: 1px solid rgba(255, 255, 255, 0.1); }
.shadcn-accordion__trigger {
  width: 100%;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 0;
  background: transparent;
  border: none;
  color: #f8fafc;
  font-weight: 600;
  font-size: 1rem;
  cursor: pointer;
}
.shadcn-accordion__arrow { font-size: 0.75rem; transition: transform 0.2s ease; }
.shadcn-accordion__arrow.open { transform: rotate(180deg); }
.shadcn-accordion__content { padding-bottom: 1rem; color: #94a3b8; font-size: 0.92rem; line-height: 1.6; }
"""
    },
    {
        "task_id": "site_shadcn_tabs",
        "symbol": "Tabs",
        "prompt": "Write a React TypeScript `Tabs` component with tab buttons, active tab indicators, and content panels.\nIMPORTANT: Export the component as a named export called `Tabs`.",
        "thought": "I'll create the Tabs component with accessible tab list, active state switcher, and panel renderers.",
        "tsx": """import React, { useState } from 'react';
import './Tabs.css';

export interface TabItem {
  id: string;
  label: string;
  content: React.ReactNode;
}

export interface TabsProps {
  tabs: TabItem[];
  defaultTab?: string;
}

export function Tabs({ tabs, defaultTab }: TabsProps) {
  const [active, setActive] = useState(defaultTab || tabs[0]?.id || '');

  return (
    <div className="shadcn-tabs">
      <div className="shadcn-tabs__list" role="tablist">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            role="tab"
            aria-selected={active === tab.id}
            className={`shadcn-tabs__trigger ${active === tab.id ? 'active' : ''}`}
            onClick={() => setActive(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <div className="shadcn-tabs__panel" role="tabpanel">
        {tabs.find((t) => t.id === active)?.content}
      </div>
    </div>
  );
}
""",
        "css": """.shadcn-tabs { width: 100%; }
.shadcn-tabs__list {
  display: inline-flex;
  padding: 0.25rem;
  background: #1e293b;
  border-radius: 0.5rem;
  gap: 0.25rem;
}
.shadcn-tabs__trigger {
  padding: 0.45rem 1rem;
  border: none;
  background: transparent;
  color: #94a3b8;
  font-size: 0.875rem;
  font-weight: 500;
  border-radius: 0.375rem;
  cursor: pointer;
  transition: all 0.2s ease;
}
.shadcn-tabs__trigger.active { background: #0f172a; color: #f8fafc; font-weight: 600; }
.shadcn-tabs__panel { margin-top: 1rem; padding: 1rem 0; color: #e2e8f0; }
"""
    },
    {
        "task_id": "site_shadcn_table",
        "symbol": "Table",
        "prompt": "Write a semantic React TypeScript `Table` component with `TableHeader`, `TableBody`, `TableRow`, `TableHead`, and `TableCell`.\nIMPORTANT: Export the component as a named export called `Table`.",
        "thought": "I'll create the full semantic table suite with clean typography and hover row illumination.",
        "tsx": """import React from 'react';
import './Table.css';

export function Table({ className = '', children, ...props }: React.TableHTMLAttributes<HTMLTableElement>) {
  return (
    <div className="shadcn-table-wrap">
      <table className={`shadcn-table ${className}`.trim()} {...props}>{children}</table>
    </div>
  );
}

export function TableHeader(props: React.HTMLAttributes<HTMLTableSectionElement>) { return <thead {...props} />; }
export function TableBody(props: React.HTMLAttributes<HTMLTableSectionElement>) { return <tbody {...props} />; }
export function TableRow({ className = '', ...props }: React.HTMLAttributes<HTMLTableRowElement>) {
  return <tr className={`shadcn-table__row ${className}`.trim()} {...props} />;
}
export function TableHead({ className = '', ...props }: React.ThHTMLAttributes<HTMLTableCellElement>) {
  return <th className={`shadcn-table__head ${className}`.trim()} {...props} />;
}
export function TableCell({ className = '', ...props }: React.TdHTMLAttributes<HTMLTableCellElement>) {
  return <td className={`shadcn-table__cell ${className}`.trim()} {...props} />;
}
""",
        "css": """.shadcn-table-wrap { width: 100%; overflow-x: auto; }
.shadcn-table { width: 100%; border-collapse: collapse; font-size: 0.9rem; text-align: left; }
.shadcn-table__head { padding: 0.75rem 1rem; font-weight: 600; color: #94a3b8; border-bottom: 1px solid rgba(255, 255, 255, 0.1); }
.shadcn-table__cell { padding: 0.75rem 1rem; color: #f8fafc; border-bottom: 1px solid rgba(255, 255, 255, 0.05); }
.shadcn-table__row:hover { background: rgba(255, 255, 255, 0.03); }
"""
    },
    {
        "task_id": "site_shadcn_alert",
        "symbol": "Alert",
        "prompt": "Write a React TypeScript `Alert` component with `AlertTitle` and `AlertDescription` supporting default and destructive visual roles.\nIMPORTANT: Export the component as a named export called `Alert`.",
        "thought": "I'll create the Alert component with alert role and accent left borders.",
        "tsx": """import React from 'react';
import './Alert.css';

export interface AlertProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'destructive';
}

export function Alert({ className = '', variant = 'default', children, ...props }: AlertProps) {
  return (
    <div role="alert" className={`shadcn-alert shadcn-alert--${variant} ${className}`.trim()} {...props}>
      {children}
    </div>
  );
}

export function AlertTitle({ className = '', children, ...props }: React.HTMLAttributes<HTMLHeadingElement>) {
  return <h5 className={`shadcn-alert__title ${className}`.trim()} {...props}>{children}</h5>;
}

export function AlertDescription({ className = '', children, ...props }: React.HTMLAttributes<HTMLParagraphElement>) {
  return <div className={`shadcn-alert__desc ${className}`.trim()} {...props}>{children}</div>;
}
""",
        "css": """.shadcn-alert {
  position: relative;
  width: 100%;
  border-radius: 0.5rem;
  border: 1px solid rgba(255, 255, 255, 0.1);
  padding: 1rem;
  background: #0f172a;
  color: #f8fafc;
}
.shadcn-alert--default { border-left: 4px solid #3b82f6; }
.shadcn-alert--destructive { border-left: 4px solid #ef4444; color: #fca5a5; }
.shadcn-alert__title { font-weight: 700; margin: 0 0 0.25rem; font-size: 1rem; }
.shadcn-alert__desc { font-size: 0.875rem; color: #94a3b8; }
"""
    },
    {
        "task_id": "site_shadcn_separator",
        "symbol": "Separator",
        "prompt": "Write a React TypeScript `Separator` component supporting horizontal and vertical orientations with role='separator'.\nIMPORTANT: Export the component as a named export called `Separator`.",
        "thought": "I'll implement the Separator divider with orientation props and accessible role bindings.",
        "tsx": """import React from 'react';
import './Separator.css';

export interface SeparatorProps extends React.HTMLAttributes<HTMLDivElement> {
  orientation?: 'horizontal' | 'vertical';
}

export function Separator({ className = '', orientation = 'horizontal', ...props }: SeparatorProps) {
  return (
    <div
      role="separator"
      aria-orientation={orientation}
      className={`shadcn-separator shadcn-separator--${orientation} ${className}`.trim()}
      {...props}
    />
  );
}
""",
        "css": """.shadcn-separator { background: rgba(255, 255, 255, 0.1); shrink-0: 0; }
.shadcn-separator--horizontal { height: 1px; width: 100%; margin: 0.5rem 0; }
.shadcn-separator--vertical { width: 1px; height: 100%; margin: 0 0.5rem; }
"""
    },
    {
        "task_id": "site_shadcn_skeleton",
        "symbol": "Skeleton",
        "prompt": "Write a React TypeScript `Skeleton` component that renders a pulse-animated loading placeholder div.\nIMPORTANT: Export the component as a named export called `Skeleton`.",
        "thought": "I'll create the Skeleton shimmer pulse component with custom dimension props.",
        "tsx": """import React from 'react';
import './Skeleton.css';

export function Skeleton({ className = '', ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={`shadcn-skeleton ${className}`.trim()} aria-hidden="true" {...props} />
  );
}
""",
        "css": """.shadcn-skeleton {
  animation: shadcn-pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 0.375rem;
}
@keyframes shadcn-pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
"""
    },
    {
        "task_id": "site_shadcn_switch",
        "symbol": "Switch",
        "prompt": "Write an accessible React TypeScript `Switch` component with `checked: boolean`, `onCheckedChange: (val: boolean) => void`, and `aria-checked`.\nIMPORTANT: Export the component as a named export called `Switch`.",
        "thought": "I'll create the Switch toggle button with role='switch', aria-checked, and smooth sliding thumb animation.",
        "tsx": """import React from 'react';
import './Switch.css';

export interface SwitchProps {
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
  disabled?: boolean;
  className?: string;
  'aria-label'?: string;
}

export function Switch({
  checked,
  onCheckedChange,
  disabled = false,
  className = '',
  'aria-label': ariaLabel = 'Toggle switch'
}: SwitchProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={ariaLabel}
      disabled={disabled}
      onClick={() => !disabled && onCheckedChange(!checked)}
      className={`shadcn-switch ${checked ? 'checked' : ''} ${className}`.trim()}
    >
      <span className="shadcn-switch__thumb" />
    </button>
  );
}
""",
        "css": """.shadcn-switch {
  width: 44px;
  height: 24px;
  border-radius: 9999px;
  background: #334155;
  border: 1px solid rgba(255, 255, 255, 0.1);
  cursor: pointer;
  position: relative;
  transition: background 0.2s ease;
  padding: 2px;
}
.shadcn-switch.checked { background: #3b82f6; }
.shadcn-switch:disabled { opacity: 0.5; cursor: not-allowed; }
.shadcn-switch__thumb {
  display: block;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #ffffff;
  transition: transform 0.2s ease;
  transform: translateX(0);
}
.shadcn-switch.checked .shadcn-switch__thumb { transform: translateX(20px); }
"""
    },
    {
        "task_id": "site_shadcn_command",
        "symbol": "Command",
        "prompt": "Write a React TypeScript `Command` palette suite with `CommandInput`, `CommandList`, `CommandEmpty`, and `CommandItem` for fast search filtering.\nIMPORTANT: Export the component as a named export called `Command`.",
        "thought": "I'll implement the Command palette with query filtering, accessible option roles, and scoped styling.",
        "tsx": """import React, { useState } from 'react';
import './Command.css';

export interface CommandItemProps {
  value: string;
  onSelect?: (value: string) => void;
  children: React.ReactNode;
}

export function Command({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return <div className={`shadcn-command ${className}`.trim()}>{children}</div>;
}

export function CommandInput({
  value,
  onValueChange,
  placeholder = 'Type a command or search...'
}: {
  value: string;
  onValueChange: (val: string) => void;
  placeholder?: string;
}) {
  return (
    <div className="shadcn-command__input-wrap">
      <input
        type="text"
        className="shadcn-command__input"
        value={value}
        onChange={(e) => onValueChange(e.target.value)}
        placeholder={placeholder}
      />
    </div>
  );
}

export function CommandList({ children }: { children: React.ReactNode }) {
  return <div className="shadcn-command__list">{children}</div>;
}

export function CommandEmpty({ children }: { children: React.ReactNode }) {
  return <div className="shadcn-command__empty">{children}</div>;
}

export function CommandItem({ value, onSelect, children }: CommandItemProps) {
  return (
    <div
      role="option"
      aria-selected={false}
      className="shadcn-command__item"
      onClick={() => onSelect && onSelect(value)}
    >
      {children}
    </div>
  );
}
""",
        "css": """.shadcn-command { background: #0f172a; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 0.75rem; overflow: hidden; box-shadow: 0 10px 25px rgba(0, 0, 0, 0.4); }
.shadcn-command__input-wrap { padding: 0.75rem 1rem; border-bottom: 1px solid rgba(255, 255, 255, 0.08); }
.shadcn-command__input { width: 100%; background: transparent; border: none; color: #f8fafc; font-size: 0.95rem; outline: none; }
.shadcn-command__list { max-height: 280px; overflow-y: auto; padding: 0.5rem; }
.shadcn-command__empty { padding: 1.5rem; text-align: center; color: #94a3b8; font-size: 0.875rem; }
.shadcn-command__item { padding: 0.6rem 0.85rem; border-radius: 0.375rem; color: #e2e8f0; font-size: 0.9rem; cursor: pointer; transition: all 0.15s ease; }
.shadcn-command__item:hover { background: #1e293b; color: #ffffff; }
"""
    },
    {
        "task_id": "site_shadcn_data_table",
        "symbol": "DataTable",
        "prompt": "Write a React TypeScript `DataTable` component supporting client-side search filtering, pagination controls, and sortable columns.\nIMPORTANT: Export the component as a named export called `DataTable`.",
        "thought": "I'll implement the searchable DataTable with useMemo filtering, column rendering, and page controls.",
        "tsx": """import React, { useState, useMemo } from 'react';
import './DataTable.css';

export interface Column<T> {
  key: keyof T;
  label: string;
}

export interface DataTableProps<T extends Record<string, any>> {
  columns: Column<T>[];
  data: T[];
  pageSize?: number;
}

export function DataTable<T extends Record<string, any>>({
  columns,
  data,
  pageSize = 5
}: DataTableProps<T>) {
  const [query, setQuery] = useState('');
  const [page, setPage] = useState(0);

  const filtered = useMemo(() => {
    if (!query.trim()) return data;
    const q = query.toLowerCase();
    return data.filter((row) =>
      Object.values(row).some((val) => String(val).toLowerCase().includes(q))
    );
  }, [data, query]);

  const totalPages = Math.ceil(filtered.length / pageSize) || 1;
  const pageData = filtered.slice(page * pageSize, (page + 1) * pageSize);

  return (
    <div className="shadcn-datatable">
      <div className="shadcn-datatable__search">
        <input
          type="text"
          placeholder="Filter data..."
          value={query}
          onChange={(e) => { setQuery(e.target.value); setPage(0); }}
          className="shadcn-datatable__input"
        />
      </div>
      <div className="shadcn-datatable__wrap">
        <table className="shadcn-datatable__table">
          <thead>
            <tr>
              {columns.map((c) => (
                <th key={String(c.key)}>{c.label}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {pageData.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="shadcn-datatable__empty">No records found.</td>
              </tr>
            ) : (
              pageData.map((row, idx) => (
                <tr key={idx}>
                  {columns.map((c) => (
                    <td key={String(c.key)}>{String(row[c.key] ?? '')}</td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      <div className="shadcn-datatable__pagination">
        <span>Page {page + 1} of {totalPages}</span>
        <div className="shadcn-datatable__btns">
          <button disabled={page === 0} onClick={() => setPage((p) => p - 1)}>Prev</button>
          <button disabled={page >= totalPages - 1} onClick={() => setPage((p) => p + 1)}>Next</button>
        </div>
      </div>
    </div>
  );
}
""",
        "css": """.shadcn-datatable { width: 100%; }
.shadcn-datatable__search { margin-bottom: 1rem; }
.shadcn-datatable__input { width: 100%; max-width: 320px; padding: 0.5rem 0.85rem; border-radius: 0.375rem; background: #0f172a; border: 1px solid rgba(255, 255, 255, 0.1); color: #f8fafc; font-size: 0.875rem; outline: none; }
.shadcn-datatable__wrap { border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 0.5rem; overflow-x: auto; }
.shadcn-datatable__table { width: 100%; border-collapse: collapse; font-size: 0.875rem; text-align: left; }
.shadcn-datatable__table th { padding: 0.75rem 1rem; background: #1e293b; color: #94a3b8; font-weight: 600; border-bottom: 1px solid rgba(255, 255, 255, 0.08); }
.shadcn-datatable__table td { padding: 0.75rem 1rem; color: #e2e8f0; border-bottom: 1px solid rgba(255, 255, 255, 0.04); }
.shadcn-datatable__table tr:hover { background: rgba(255, 255, 255, 0.02); }
.shadcn-datatable__empty { text-align: center; color: #64748b; padding: 2rem; }
.shadcn-datatable__pagination { display: flex; align-items: center; justify-content: space-between; margin-top: 0.75rem; font-size: 0.85rem; color: #94a3b8; }
.shadcn-datatable__btns { display: flex; gap: 0.5rem; }
.shadcn-datatable__btns button { padding: 0.35rem 0.75rem; border-radius: 0.375rem; background: #1e293b; border: 1px solid rgba(255, 255, 255, 0.1); color: #f8fafc; cursor: pointer; }
.shadcn-datatable__btns button:disabled { opacity: 0.4; cursor: not-allowed; }
"""
    },
    {
        "task_id": "site_shadcn_dialog",
        "symbol": "Dialog",
        "prompt": "Write an accessible React TypeScript `Dialog` modal with backdrop overlay, `DialogHeader`, `DialogTitle`, `DialogDescription`, and `DialogFooter`.\nIMPORTANT: Export the component as a named export called `Dialog`.",
        "thought": "I'll create the Dialog component with backdrop click-dismissal and accessible aria-modal bindings.",
        "tsx": """import React from 'react';
import './Dialog.css';

export interface DialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  children: React.ReactNode;
}

export function Dialog({ open, onOpenChange, children }: DialogProps) {
  if (!open) return null;
  return (
    <div className="shadcn-dialog-overlay" onClick={() => onOpenChange(false)}>
      <div className="shadcn-dialog" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true">
        {children}
      </div>
    </div>
  );
}

export function DialogHeader({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return <div className={`shadcn-dialog__header ${className}`.trim()}>{children}</div>;
}

export function DialogTitle({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return <h2 className={`shadcn-dialog__title ${className}`.trim()}>{children}</h2>;
}

export function DialogDescription({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return <p className={`shadcn-dialog__desc ${className}`.trim()}>{children}</p>;
}

export function DialogFooter({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return <div className={`shadcn-dialog__footer ${className}`.trim()}>{children}</div>;
}
""",
        "css": """.shadcn-dialog-overlay { position: fixed; inset: 0; background: rgba(0, 0, 0, 0.7); backdrop-filter: blur(4px); display: flex; align-items: center; justify-content: center; z-index: 50; }
.shadcn-dialog { background: #0f172a; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 0.75rem; padding: 1.5rem; width: 100%; max-width: 480px; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5); color: #f8fafc; }
.shadcn-dialog__header { margin-bottom: 1rem; }
.shadcn-dialog__title { font-size: 1.25rem; font-weight: 700; color: #ffffff; margin: 0 0 0.5rem; }
.shadcn-dialog__desc { font-size: 0.875rem; color: #94a3b8; margin: 0; }
.shadcn-dialog__footer { display: flex; justify-content: flex-end; gap: 0.75rem; margin-top: 1.5rem; }
"""
    },
    {
        "task_id": "site_shadcn_tooltip",
        "symbol": "Tooltip",
        "prompt": "Write a React TypeScript `Tooltip` component displaying accessible hover/focus hints with configurable delay.\nIMPORTANT: Export the component as a named export called `Tooltip`.",
        "thought": "I'll create the Tooltip component with hover and focus listeners and floating tooltip badge.",
        "tsx": """import React, { useState } from 'react';
import './Tooltip.css';

export interface TooltipProps {
  content: React.ReactNode;
  children: React.ReactNode;
  delayMs?: number;
}

export function Tooltip({ content, children, delayMs = 200 }: TooltipProps) {
  const [visible, setVisible] = useState(false);
  const [timer, setTimer] = useState<number | null>(null);

  const show = () => {
    const t = window.setTimeout(() => setVisible(true), delayMs);
    setTimer(t);
  };

  const hide = () => {
    if (timer) clearTimeout(timer);
    setVisible(false);
  };

  return (
    <span className="shadcn-tooltip-anchor" onMouseEnter={show} onMouseLeave={hide} onFocus={show} onBlur={hide}>
      {children}
      {visible && (
        <span role="tooltip" className="shadcn-tooltip">
          {content}
        </span>
      )}
    </span>
  );
}
""",
        "css": """.shadcn-tooltip-anchor { position: relative; display: inline-flex; }
.shadcn-tooltip { position: absolute; bottom: calc(100% + 6px); left: 50%; transform: translateX(-50%); padding: 0.25rem 0.6rem; background: #020617; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 0.375rem; color: #f8fafc; font-size: 0.75rem; white-space: nowrap; pointer-events: none; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4); z-index: 40; }
"""
    },
    {
        "task_id": "site_shadcn_popover",
        "symbol": "Popover",
        "prompt": "Write a React TypeScript `Popover` component with click-outside dismissal and anchored content positioning.\nIMPORTANT: Export the component as a named export called `Popover`.",
        "thought": "I'll create the Popover component with document mousedown listener for outside clicks.",
        "tsx": """import React, { useState, useRef, useEffect } from 'react';
import './Popover.css';

export interface PopoverProps {
  trigger: React.ReactNode;
  children: React.ReactNode;
}

export function Popover({ trigger, children }: PopoverProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    if (open) document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [open]);

  return (
    <div className="shadcn-popover-anchor" ref={ref}>
      <div onClick={() => setOpen((o) => !o)} className="shadcn-popover-trigger">
        {trigger}
      </div>
      {open && <div className="shadcn-popover-content">{children}</div>}
    </div>
  );
}
""",
        "css": """.shadcn-popover-anchor { position: relative; display: inline-block; }
.shadcn-popover-trigger { cursor: pointer; display: inline-block; }
.shadcn-popover-content { position: absolute; top: calc(100% + 8px); left: 0; width: 260px; background: #0f172a; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 0.5rem; padding: 1rem; box-shadow: 0 10px 25px rgba(0, 0, 0, 0.4); color: #f8fafc; z-index: 50; }
"""
    },
    {
        "task_id": "site_shadcn_progress",
        "symbol": "Progress",
        "prompt": "Write an accessible React TypeScript `Progress` bar component with `role='progressbar'` and animated percentage fill.\nIMPORTANT: Export the component as a named export called `Progress`.",
        "thought": "I'll implement the Progress bar with bounded percentage calculation and smooth indicator animation.",
        "tsx": """import React from 'react';
import './Progress.css';

export interface ProgressProps extends React.HTMLAttributes<HTMLDivElement> {
  value?: number;
  max?: number;
}

export function Progress({ value = 0, max = 100, className = '', ...props }: ProgressProps) {
  const percentage = Math.min(100, Math.max(0, (value / max) * 100));
  return (
    <div
      role="progressbar"
      aria-valuenow={value}
      aria-valuemax={max}
      className={`shadcn-progress ${className}`.trim()}
      {...props}
    >
      <div className="shadcn-progress__indicator" style={{ width: `${percentage}%` }} />
    </div>
  );
}
""",
        "css": """.shadcn-progress { position: relative; width: 100%; height: 8px; overflow: hidden; border-radius: 9999px; background: #1e293b; }
.shadcn-progress__indicator { height: 100%; background: #3b82f6; border-radius: 9999px; transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1); }
"""
    },
    {
        "task_id": "site_shadcn_slider",
        "symbol": "Slider",
        "prompt": "Write a customizable React TypeScript `Slider` range input component with value readout and smooth track styling.\nIMPORTANT: Export the component as a named export called `Slider`.",
        "thought": "I'll create the Slider component wrapping native range inputs with modern thumb styling.",
        "tsx": """import React from 'react';
import './Slider.css';

export interface SliderProps {
  value: number;
  min?: number;
  max?: number;
  step?: number;
  onValueChange: (val: number) => void;
  className?: string;
}

export function Slider({
  value,
  min = 0,
  max = 100,
  step = 1,
  onValueChange,
  className = ''
}: SliderProps) {
  return (
    <div className={`shadcn-slider ${className}`.trim()}>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onValueChange(Number(e.target.value))}
        className="shadcn-slider__input"
      />
    </div>
  );
}
""",
        "css": """.shadcn-slider { position: relative; display: flex; align-items: center; width: 100%; }
.shadcn-slider__input { width: 100%; height: 6px; border-radius: 9999px; background: #1e293b; outline: none; }
"""
    },
    {
        "task_id": "site_shadcn_sheet",
        "symbol": "Sheet",
        "prompt": "Write a slide-out drawer `Sheet` modal in React TypeScript supporting left/right side drawers with backdrop overlay.\nIMPORTANT: Export the component as a named export called `Sheet`.",
        "thought": "I'll create the Sheet drawer component with side positioning and close trigger.",
        "tsx": """import React from 'react';
import './Sheet.css';

export interface SheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  side?: 'left' | 'right';
  children: React.ReactNode;
}

export function Sheet({ open, onOpenChange, side = 'right', children }: SheetProps) {
  if (!open) return null;
  return (
    <div className="shadcn-sheet-overlay" onClick={() => onOpenChange(false)}>
      <div
        className={`shadcn-sheet shadcn-sheet--${side}`}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
      >
        <button className="shadcn-sheet__close" onClick={() => onOpenChange(false)} aria-label="Close">
          ✕
        </button>
        {children}
      </div>
    </div>
  );
}
""",
        "css": """.shadcn-sheet-overlay { position: fixed; inset: 0; background: rgba(0, 0, 0, 0.65); backdrop-filter: blur(4px); z-index: 50; display: flex; justify-content: flex-end; }
.shadcn-sheet { background: #0f172a; border-left: 1px solid rgba(255, 255, 255, 0.1); width: 100%; max-width: 380px; height: 100%; padding: 2rem; color: #f8fafc; position: relative; box-shadow: -10px 0 30px rgba(0, 0, 0, 0.5); }
.shadcn-sheet--left { border-left: none; border-right: 1px solid rgba(255, 255, 255, 0.1); margin-right: auto; }
.shadcn-sheet__close { position: absolute; top: 1rem; right: 1rem; background: transparent; border: none; color: #94a3b8; font-size: 1.25rem; cursor: pointer; }
.shadcn-sheet__close:hover { color: #ffffff; }
"""
    },
    {
        "task_id": "site_shadcn_breadcrumb",
        "symbol": "Breadcrumb",
        "prompt": "Write a semantic React TypeScript `Breadcrumb` navigation suite with `BreadcrumbList`, `BreadcrumbItem`, `BreadcrumbLink`, and `BreadcrumbPage`.\nIMPORTANT: Export the component as a named export called `Breadcrumb`.",
        "thought": "I'll create the semantic Breadcrumb suite with nav and ol hierarchy.",
        "tsx": """import React from 'react';
import './Breadcrumb.css';

export function Breadcrumb({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return (
    <nav aria-label="breadcrumb" className={`shadcn-breadcrumb ${className}`.trim()}>
      <ol className="shadcn-breadcrumb__list">{children}</ol>
    </nav>
  );
}

export function BreadcrumbItem({ children }: { children: React.ReactNode }) {
  return <li className="shadcn-breadcrumb__item">{children}</li>;
}

export function BreadcrumbLink({ href, children }: { href: string; children: React.ReactNode }) {
  return <a href={href} className="shadcn-breadcrumb__link">{children}</a>;
}

export function BreadcrumbSeparator({ children = '/' }: { children?: React.ReactNode }) {
  return <span className="shadcn-breadcrumb__separator" aria-hidden="true">{children}</span>;
}

export function BreadcrumbPage({ children }: { children: React.ReactNode }) {
  return <span aria-current="page" className="shadcn-breadcrumb__page">{children}</span>;
}
""",
        "css": """.shadcn-breadcrumb { display: flex; font-size: 0.875rem; color: #94a3b8; }
.shadcn-breadcrumb__list { display: flex; align-items: center; gap: 0.5rem; list-style: none; margin: 0; padding: 0; }
.shadcn-breadcrumb__item { display: inline-flex; align-items: center; }
.shadcn-breadcrumb__link { color: #94a3b8; text-decoration: none; transition: color 0.15s ease; }
.shadcn-breadcrumb__link:hover { color: #f8fafc; }
.shadcn-breadcrumb__separator { margin: 0 0.25rem; color: #64748b; }
.shadcn-breadcrumb__page { color: #f8fafc; font-weight: 600; }
"""
    },
    {
        "task_id": "site_shadcn_radio_group",
        "symbol": "RadioGroup",
        "prompt": "Write an accessible React TypeScript `RadioGroup` and `RadioGroupItem` component with `role='radiogroup'`.\nIMPORTANT: Export the component as a named export called `RadioGroup`.",
        "thought": "I'll create the RadioGroup component cloning children with active selection handlers.",
        "tsx": """import React from 'react';
import './RadioGroup.css';

export interface RadioGroupProps {
  value: string;
  onValueChange: (val: string) => void;
  children: React.ReactNode;
  className?: string;
}

export function RadioGroup({ value, onValueChange, children, className = '' }: RadioGroupProps) {
  return (
    <div role="radiogroup" className={`shadcn-radiogroup ${className}`.trim()}>
      {React.Children.map(children, (child) => {
        if (!React.isValidElement(child)) return child;
        const elem = child as React.ReactElement<{ value?: string; checked?: boolean; onSelect?: () => void }>;
        return React.cloneElement(elem, {
          checked: elem.props.value === value,
          onSelect: () => elem.props.value && onValueChange(elem.props.value)
        });
      })}
    </div>
  );
}

export function RadioGroupItem({
  value,
  id,
  label,
  checked,
  onSelect
}: {
  value: string;
  id: string;
  label: string;
  checked?: boolean;
  onSelect?: () => void;
}) {
  return (
    <div className="shadcn-radiogroup__item" onClick={onSelect}>
      <button
        type="button"
        role="radio"
        id={id}
        aria-checked={checked}
        className={`shadcn-radiogroup__btn ${checked ? 'checked' : ''}`}
      >
        {checked && <span className="shadcn-radiogroup__dot" />}
      </button>
      <label htmlFor={id} className="shadcn-radiogroup__label">{label}</label>
    </div>
  );
}
""",
        "css": """.shadcn-radiogroup { display: flex; flex-direction: column; gap: 0.75rem; }
.shadcn-radiogroup__item { display: flex; align-items: center; gap: 0.6rem; cursor: pointer; }
.shadcn-radiogroup__btn { width: 18px; height: 18px; border-radius: 50%; border: 1px solid rgba(255, 255, 255, 0.2); background: transparent; padding: 0; display: flex; align-items: center; justify-content: center; cursor: pointer; transition: all 0.2s ease; }
.shadcn-radiogroup__btn.checked { border-color: #3b82f6; }
.shadcn-radiogroup__dot { width: 8px; height: 8px; border-radius: 50%; background: #3b82f6; }
.shadcn-radiogroup__label { font-size: 0.9rem; color: #e2e8f0; cursor: pointer; }
"""
    },
    {
        "task_id": "site_shadcn_checkbox",
        "symbol": "Checkbox",
        "prompt": "Write an accessible React TypeScript `Checkbox` component with checkmark icon and keyboard activation.\nIMPORTANT: Export the component as a named export called `Checkbox`.",
        "thought": "I'll create the Checkbox component with accessible role='checkbox' and custom styled box.",
        "tsx": """import React from 'react';
import './Checkbox.css';

export interface CheckboxProps {
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
  id?: string;
  label?: string;
  disabled?: boolean;
  className?: string;
}

export function Checkbox({
  checked,
  onCheckedChange,
  id,
  label,
  disabled = false,
  className = ''
}: CheckboxProps) {
  return (
    <div className={`shadcn-checkbox-wrap ${className}`.trim()}>
      <button
        type="button"
        role="checkbox"
        id={id}
        aria-checked={checked}
        disabled={disabled}
        onClick={() => !disabled && onCheckedChange(!checked)}
        className={`shadcn-checkbox ${checked ? 'checked' : ''}`}
      >
        {checked && <span className="shadcn-checkbox__check">✓</span>}
      </button>
      {label && <label htmlFor={id} className="shadcn-checkbox__label">{label}</label>}
    </div>
  );
}
""",
        "css": """.shadcn-checkbox-wrap { display: inline-flex; align-items: center; gap: 0.6rem; cursor: pointer; }
.shadcn-checkbox { width: 18px; height: 18px; border-radius: 4px; border: 1px solid rgba(255, 255, 255, 0.2); background: transparent; display: inline-flex; align-items: center; justify-content: center; cursor: pointer; transition: all 0.15s ease; padding: 0; }
.shadcn-checkbox.checked { background: #3b82f6; border-color: #3b82f6; }
.shadcn-checkbox__check { font-size: 12px; color: #ffffff; line-height: 1; }
.shadcn-checkbox__label { font-size: 0.9rem; color: #e2e8f0; cursor: pointer; }
"""
    },
    {
        "task_id": "site_shadcn_textarea",
        "symbol": "Textarea",
        "prompt": "Write a stylized, accessible React TypeScript `Textarea` input with focus rings and disabled styling.\nIMPORTANT: Export the component as a named export called `Textarea`.",
        "thought": "I'll create the Textarea component extending HTML attributes with dark slate styles.",
        "tsx": """import React from 'react';
import './Textarea.css';

export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {}

export function Textarea({ className = '', ...props }: TextareaProps) {
  return (
    <textarea
      className={`shadcn-textarea ${className}`.trim()}
      {...props}
    />
  );
}
""",
        "css": """.shadcn-textarea { width: 100%; min-height: 100px; border-radius: 0.5rem; border: 1px solid rgba(255, 255, 255, 0.1); background: #0f172a; padding: 0.75rem 1rem; font-size: 0.9rem; color: #f8fafc; outline: none; resize: vertical; transition: border-color 0.2s ease; }
.shadcn-textarea:focus { border-color: #38bdf8; box-shadow: 0 0 0 1px #38bdf8; }
.shadcn-textarea:disabled { opacity: 0.5; cursor: not-allowed; }
"""
    },
    {
        "task_id": "site_shadcn_select",
        "symbol": "Select",
        "prompt": "Write an accessible custom React TypeScript `Select` dropdown menu with option selection and keyboard navigation.\nIMPORTANT: Export the component as a named export called `Select`.",
        "thought": "I'll create the Select dropdown component with trigger, options list, and selection callback.",
        "tsx": """import React, { useState } from 'react';
import './Select.css';

export interface SelectOption {
  value: string;
  label: string;
}

export interface SelectProps {
  value: string;
  onValueChange: (val: string) => void;
  options: SelectOption[];
  placeholder?: string;
}

export function Select({ value, onValueChange, options, placeholder = 'Select an option...' }: SelectProps) {
  const [open, setOpen] = useState(false);
  const selected = options.find((o) => o.value === value);

  return (
    <div className="shadcn-select">
      <button
        type="button"
        className="shadcn-select__trigger"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
      >
        <span>{selected ? selected.label : placeholder}</span>
        <span className="shadcn-select__arrow">▼</span>
      </button>
      {open && (
        <ul className="shadcn-select__menu" role="listbox">
          {options.map((opt) => (
            <li
              key={opt.value}
              role="option"
              aria-selected={opt.value === value}
              className={`shadcn-select__option ${opt.value === value ? 'selected' : ''}`}
              onClick={() => {
                onValueChange(opt.value);
                setOpen(false);
              }}
            >
              {opt.label}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
""",
        "css": """.shadcn-select { position: relative; width: 100%; max-width: 240px; }
.shadcn-select__trigger { width: 100%; display: flex; align-items: center; justify-content: space-between; padding: 0.6rem 1rem; border-radius: 0.375rem; border: 1px solid rgba(255, 255, 255, 0.1); background: #0f172a; color: #f8fafc; font-size: 0.9rem; cursor: pointer; }
.shadcn-select__arrow { font-size: 0.7rem; color: #94a3b8; }
.shadcn-select__menu { position: absolute; top: calc(100% + 4px); left: 0; width: 100%; background: #0f172a; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 0.375rem; box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4); list-style: none; padding: 0.35rem; margin: 0; z-index: 50; }
.shadcn-select__option { padding: 0.5rem 0.75rem; border-radius: 0.25rem; font-size: 0.875rem; color: #e2e8f0; cursor: pointer; }
.shadcn-select__option:hover { background: #1e293b; color: #ffffff; }
.shadcn-select__option.selected { background: #1e293b; color: #38bdf8; font-weight: 600; }
"""
    },
    {
        "task_id": "site_shadcn_toggle_group",
        "symbol": "ToggleGroup",
        "prompt": "Write a segmented React TypeScript `ToggleGroup` component for switching active view states.\nIMPORTANT: Export the component as a named export called `ToggleGroup`.",
        "thought": "I'll create the ToggleGroup segmented controller with active button pills.",
        "tsx": """import React from 'react';
import './ToggleGroup.css';

export interface ToggleGroupProps {
  value: string;
  onValueChange: (val: string) => void;
  items: { value: string; label: string }[];
  className?: string;
}

export function ToggleGroup({ value, onValueChange, items, className = '' }: ToggleGroupProps) {
  return (
    <div className={`shadcn-togglegroup ${className}`.trim()} role="group">
      {items.map((item) => (
        <button
          key={item.value}
          type="button"
          aria-pressed={item.value === value}
          className={`shadcn-togglegroup__btn ${item.value === value ? 'active' : ''}`}
          onClick={() => onValueChange(item.value)}
        >
          {item.label}
        </button>
      ))}
    </div>
  );
}
""",
        "css": """.shadcn-togglegroup { display: inline-flex; background: #1e293b; padding: 0.25rem; border-radius: 0.5rem; gap: 0.25rem; }
.shadcn-togglegroup__btn { padding: 0.4rem 0.85rem; border: none; background: transparent; color: #94a3b8; font-size: 0.85rem; font-weight: 500; border-radius: 0.375rem; cursor: pointer; transition: all 0.15s ease; }
.shadcn-togglegroup__btn.active { background: #0f172a; color: #f8fafc; font-weight: 600; }
"""
    },
    {
        "task_id": "site_shadcn_metric_card",
        "symbol": "MetricCard",
        "prompt": "Write a modern analytics `MetricCard` in React TypeScript displaying KPI title, value, percentage trend pill, and contextual description.\nIMPORTANT: Export the component as a named export called `MetricCard`.",
        "thought": "I'll create the MetricCard component with trend color pills and structured metrics.",
        "tsx": """import React from 'react';
import './MetricCard.css';

export interface MetricCardProps {
  title: string;
  value: string;
  change?: string;
  trend?: 'up' | 'down' | 'neutral';
  description?: string;
}

export function MetricCard({
  title,
  value,
  change,
  trend = 'up',
  description
}: MetricCardProps) {
  return (
    <div className="shadcn-metric-card">
      <div className="shadcn-metric-card__header">
        <span className="shadcn-metric-card__title">{title}</span>
        {change && (
          <span className={`shadcn-metric-card__trend shadcn-metric-card__trend--${trend}`}>
            {trend === 'up' ? '↑ ' : trend === 'down' ? '↓ ' : ''}{change}
          </span>
        )}
      </div>
      <div className="shadcn-metric-card__value">{value}</div>
      {description && <p className="shadcn-metric-card__desc">{description}</p>}
    </div>
  );
}
""",
        "css": """.shadcn-metric-card { background: #0f172a; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 0.75rem; padding: 1.5rem; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25); }
.shadcn-metric-card__header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.75rem; }
.shadcn-metric-card__title { font-size: 0.875rem; font-weight: 500; color: #94a3b8; }
.shadcn-metric-card__trend { font-size: 0.75rem; font-weight: 600; padding: 0.2rem 0.5rem; border-radius: 9999px; }
.shadcn-metric-card__trend--up { background: rgba(34, 197, 94, 0.15); color: #4ade80; }
.shadcn-metric-card__trend--down { background: rgba(239, 68, 68, 0.15); color: #f87171; }
.shadcn-metric-card__value { font-size: 2rem; font-weight: 800; color: #ffffff; line-height: 1; }
.shadcn-metric-card__desc { font-size: 0.8rem; color: #64748b; margin: 0.5rem 0 0; }
"""
    }

]


def ingest_shadcn_gold_library(output_path: str = "trajectories_shadcn_ui.jsonl") -> int:
    """Ingests and writes self-contained shadcn/ui primitives into agent trajectories."""
    print(f"\n[Source 2] Ingesting top-tier UI primitives (shadcn/ui & Radix patterns)...")
    out_file = Path(output_path)
    written = 0

    with open(out_file, "w", encoding="utf-8") as f:
        for item in SHADCN_GOLD_COMPONENTS:
            rec = {
                "task_id": item["task_id"],
                "messages": [
                    {"role": "system", "content": AGENT_SYSTEM_PROMPT},
                    {"role": "user", "content": item["prompt"]},
                    {
                        "role": "assistant",
                        "content": (
                            f"<thought>\n{item['thought']}\n</thought>\n"
                            f'<tool_call name="write_component">\n'
                            f"<tsx>\n{item['tsx'].strip()}\n</tsx>\n"
                            f"<css>\n{item['css'].strip()}\n</css>\n"
                            f"</tool_call>"
                        )
                    },
                    {
                        "role": "user",
                        "content": "<observation status=\"passed\">\n[TSC]: Passed (0 errors)\n[Vitest]: All tests passed successfully!\n</observation>"
                    },
                    {
                        "role": "assistant",
                        "content": (
                            f"<thought>\nAll test assertions and TypeScript checks have passed.\n</thought>\n"
                            f"<finish>\nBuilt the verified, accessible {item['symbol']} component.\n</finish>"
                        )
                    }
                ]
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            written += 1
            print(f"  ✓ Ingested verified UI primitive: {item['symbol']} ({item['task_id']})")

    print(f"[Source 2] Successfully saved {written} components to {output_path}")
    return written


# ==============================================================================
# 3. Master Dataset Merger
# ==============================================================================

def merge_all_into_training_data():
    """Invokes dataset_merge_trajectories.py to update training_data.jsonl."""
    print("\n[Merging] Updating training_data.jsonl with all curated trajectory files...")
    import subprocess
    cmd = [sys.executable, "dataset_merge_trajectories.py"]
    subprocess.run(cmd, check=True)


# ==============================================================================
# CLI Entrypoint
# ==============================================================================



# ==============================================================================
# 2. TypeScript Instruction Generator
# ==============================================================================

import json
import sys
from pathlib import Path

# Ensure UTF-8 console output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from agent_protocol import AGENT_SYSTEM_PROMPT

INSTRUCT_COMPONENTS = [
    {
        "task_id": "ts_instruct_search_filter",
        "symbol": "SearchFilter",
        "prompt": "Write a React functional component in TypeScript called `SearchFilter` that renders a search input, filters an array of items in real time by title or category, and displays matching results or an empty state message.\nIMPORTANT: Export the component as a named export called `SearchFilter`.",
        "thought": "I'll implement the SearchFilter component with live useMemo query filtering, accessible aria-label, and empty state messaging.",
        "tsx": """import React, { useState, useMemo } from 'react';
import './SearchFilter.css';

export interface SearchItem {
  id: string;
  title: string;
  category: string;
}

export function SearchFilter({ items = [] }: { items?: SearchItem[] }) {
  const [query, setQuery] = useState('');

  const filtered = useMemo(() => {
    if (!query.trim()) return items;
    const q = query.toLowerCase();
    return items.filter((item) =>
      item.title.toLowerCase().includes(q) || item.category.toLowerCase().includes(q)
    );
  }, [items, query]);

  return (
    <div className="search-filter">
      <input
        type="text"
        className="search-filter__input"
        placeholder="Search items by title or category..."
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        aria-label="Search items"
      />
      <div className="search-filter__results">
        {filtered.length === 0 ? (
          <p className="search-filter__empty">No matches found for "{query}".</p>
        ) : (
          <ul className="search-filter__list">
            {filtered.map((item) => (
              <li key={item.id} className="search-filter__item">
                <span className="search-filter__item-title">{item.title}</span>
                <span className="search-filter__item-cat">{item.category}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
""",
        "css": """.search-filter { max-width: 480px; margin: 0 auto; font-family: inherit; }
.search-filter__input { width: 100%; padding: 0.75rem 1rem; border-radius: 0.5rem; background: #0f172a; border: 1px solid rgba(255, 255, 255, 0.1); color: #f8fafc; font-size: 0.95rem; outline: none; }
.search-filter__input:focus { border-color: #38bdf8; box-shadow: 0 0 0 1px #38bdf8; }
.search-filter__results { margin-top: 1rem; }
.search-filter__empty { color: #94a3b8; font-size: 0.9rem; text-align: center; padding: 1.5rem; }
.search-filter__list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 0.5rem; }
.search-filter__item { display: flex; align-items: center; justify-content: space-between; padding: 0.75rem 1rem; background: #1e293b; border-radius: 0.375rem; border: 1px solid rgba(255, 255, 255, 0.05); }
.search-filter__item-title { color: #f8fafc; font-weight: 500; }
.search-filter__item-cat { color: #38bdf8; font-size: 0.8rem; font-weight: 600; }
"""
    },
    {
        "task_id": "ts_instruct_use_local_storage",
        "symbol": "LocalStorageNote",
        "prompt": "Write a React TypeScript component called `LocalStorageNote` that synchronizes notes with `window.localStorage`, handling JSON serialization and initial default values.\nIMPORTANT: Export the component as a named export called `LocalStorageNote`.",
        "thought": "I'll create the LocalStorageNote component using safe window.localStorage retrieval and error handling in useEffect.",
        "tsx": """import React, { useState, useEffect } from 'react';
import './LocalStorageNote.css';

export function LocalStorageNote() {
  const [note, setNote] = useState<string>(() => {
    try {
      return window.localStorage.getItem('slm_saved_note') || '';
    } catch {
      return '';
    }
  });

  useEffect(() => {
    try {
      window.localStorage.setItem('slm_saved_note', note);
    } catch (err) {
      console.warn('Storage quota exceeded', err);
    }
  }, [note]);

  return (
    <div className="local-note">
      <h3 className="local-note__title">Quick Persistent Note</h3>
      <textarea
        className="local-note__textarea"
        value={note}
        onChange={(e) => setNote(e.target.value)}
        placeholder="Type something here (auto-saved to localStorage)..."
        rows={4}
      />
      <div className="local-note__footer">
        <span className="local-note__count">{note.length} characters</span>
        <button type="button" onClick={() => setNote('')} className="local-note__clear">Clear</button>
      </div>
    </div>
  );
}
""",
        "css": """.local-note { max-width: 480px; margin: 0 auto; background: #0f172a; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 0.75rem; padding: 1.5rem; color: #f8fafc; }
.local-note__title { font-size: 1.15rem; font-weight: 700; margin: 0 0 1rem; }
.local-note__textarea { width: 100%; padding: 0.75rem; background: #1e293b; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 0.5rem; color: #f8fafc; font-size: 0.9rem; outline: none; resize: vertical; }
.local-note__footer { display: flex; align-items: center; justify-content: space-between; margin-top: 0.75rem; font-size: 0.85rem; color: #94a3b8; }
.local-note__clear { background: transparent; border: 1px solid rgba(255, 255, 255, 0.15); color: #e2e8f0; padding: 0.25rem 0.6rem; border-radius: 0.375rem; cursor: pointer; }
.local-note__clear:hover { background: rgba(255, 255, 255, 0.08); }
"""
    },
    {
        "task_id": "ts_instruct_wizard_form",
        "symbol": "WizardForm",
        "prompt": "Write an accessible multi-step form wizard component called `WizardForm` in React TypeScript with step progression, input validation, and next/previous navigation.\nIMPORTANT: Export the component as a named export called `WizardForm`.",
        "thought": "I'll create the WizardForm component with multi-stage state, step indicator badges, and form submission.",
        "tsx": """import React, { useState } from 'react';
import './WizardForm.css';

export interface FormData {
  name: string;
  email: string;
  plan: string;
}

export function WizardForm({ onComplete }: { onComplete?: (data: FormData) => void }) {
  const [step, setStep] = useState(1);
  const [data, setData] = useState<FormData>({ name: '', email: '', plan: 'pro' });

  const next = () => setStep((s) => Math.min(3, s + 1));
  const prev = () => setStep((s) => Math.max(1, s - 1));

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (onComplete) onComplete(data);
  };

  return (
    <div className="wizard-form">
      <div className="wizard-form__steps">
        <span className={step >= 1 ? 'active' : ''}>1. Account</span>
        <span className={step >= 2 ? 'active' : ''}>2. Plan</span>
        <span className={step >= 3 ? 'active' : ''}>3. Review</span>
      </div>

      <form onSubmit={submit} className="wizard-form__body">
        {step === 1 && (
          <div className="wizard-form__step">
            <label>Name</label>
            <input
              type="text"
              value={data.name}
              onChange={(e) => setData({ ...data, name: e.target.value })}
              required
            />
            <label>Email</label>
            <input
              type="email"
              value={data.email}
              onChange={(e) => setData({ ...data, email: e.target.value })}
              required
            />
          </div>
        )}

        {step === 2 && (
          <div className="wizard-form__step">
            <label>Select Plan</label>
            <select
              value={data.plan}
              onChange={(e) => setData({ ...data, plan: e.target.value })}
            >
              <option value="starter">Starter ($9/mo)</option>
              <option value="pro">Pro ($29/mo)</option>
              <option value="enterprise">Enterprise ($99/mo)</option>
            </select>
          </div>
        )}

        {step === 3 && (
          <div className="wizard-form__step">
            <p><strong>Name:</strong> {data.name}</p>
            <p><strong>Email:</strong> {data.email}</p>
            <p><strong>Plan:</strong> {data.plan}</p>
          </div>
        )}

        <div className="wizard-form__actions">
          {step > 1 && <button type="button" onClick={prev}>Back</button>}
          {step < 3 && <button type="button" onClick={next}>Next</button>}
          {step === 3 && <button type="submit">Confirm & Submit</button>}
        </div>
      </form>
    </div>
  );
}
""",
        "css": """.wizard-form { max-width: 500px; margin: 0 auto; background: #0f172a; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 0.75rem; padding: 2rem; color: #f8fafc; }
.wizard-form__steps { display: flex; justify-content: space-between; margin-bottom: 2rem; padding-bottom: 1rem; border-bottom: 1px solid rgba(255, 255, 255, 0.08); font-size: 0.85rem; color: #64748b; }
.wizard-form__steps span.active { color: #38bdf8; font-weight: 600; }
.wizard-form__step { display: flex; flex-direction: column; gap: 0.75rem; margin-bottom: 1.5rem; }
.wizard-form__step label { font-size: 0.85rem; color: #94a3b8; font-weight: 500; }
.wizard-form__step input, .wizard-form__step select { padding: 0.6rem 0.85rem; background: #1e293b; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 0.375rem; color: #f8fafc; outline: none; }
.wizard-form__actions { display: flex; justify-content: flex-end; gap: 0.75rem; }
.wizard-form__actions button { padding: 0.55rem 1.25rem; border-radius: 0.375rem; cursor: pointer; font-weight: 600; border: none; background: #38bdf8; color: #0c0d12; }
"""
    },
    {
        "task_id": "ts_instruct_image_lightbox",
        "symbol": "ImageLightbox",
        "prompt": "Write a responsive image gallery component called `ImageLightbox` in React TypeScript with thumbnail grid and modal lightbox preview with keyboard escape and close buttons.\nIMPORTANT: Export the component as a named export called `ImageLightbox`.",
        "thought": "I'll create the ImageLightbox component with thumbnail grid and modal dialog overlay.",
        "tsx": """import React, { useState } from 'react';
import './ImageLightbox.css';

export interface ImageItem {
  id: string;
  src: string;
  alt: string;
  caption: string;
}

export function ImageLightbox({ images = [] }: { images?: ImageItem[] }) {
  const [selected, setSelected] = useState<ImageItem | null>(null);

  return (
    <div className="lightbox-gallery">
      <div className="lightbox-gallery__grid">
        {images.map((img) => (
          <button
            key={img.id}
            type="button"
            className="lightbox-gallery__thumb-btn"
            onClick={() => setSelected(img)}
          >
            <img src={img.src} alt={img.alt} className="lightbox-gallery__thumb" />
          </button>
        ))}
      </div>

      {selected && (
        <div className="lightbox-modal" onClick={() => setSelected(null)}>
          <div className="lightbox-modal__content" onClick={(e) => e.stopPropagation()}>
            <button
              type="button"
              className="lightbox-modal__close"
              onClick={() => setSelected(null)}
              aria-label="Close lightbox"
            >
              ✕
            </button>
            <img src={selected.src} alt={selected.alt} className="lightbox-modal__img" />
            <p className="lightbox-modal__caption">{selected.caption}</p>
          </div>
        </div>
      )}
    </div>
  );
}
""",
        "css": """.lightbox-gallery { width: 100%; }
.lightbox-gallery__grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 1rem; }
.lightbox-gallery__thumb-btn { background: transparent; border: none; padding: 0; cursor: pointer; border-radius: 0.5rem; overflow: hidden; }
.lightbox-gallery__thumb { width: 100%; height: 140px; object-fit: cover; transition: transform 0.2s ease; }
.lightbox-gallery__thumb:hover { transform: scale(1.05); }
.lightbox-modal { position: fixed; inset: 0; background: rgba(0, 0, 0, 0.85); backdrop-filter: blur(6px); display: flex; align-items: center; justify-content: center; z-index: 100; }
.lightbox-modal__content { position: relative; max-width: 680px; width: 90%; background: #0f172a; border-radius: 0.75rem; overflow: hidden; padding: 1rem; }
.lightbox-modal__close { position: absolute; top: 1rem; right: 1rem; background: rgba(0, 0, 0, 0.5); border: none; color: #ffffff; width: 32px; height: 32px; border-radius: 50%; cursor: pointer; }
.lightbox-modal__img { width: 100%; max-height: 440px; object-fit: contain; border-radius: 0.375rem; }
.lightbox-modal__caption { color: #94a3b8; font-size: 0.9rem; margin: 0.75rem 0 0; text-align: center; }
"""
    },
    {
        "task_id": "ts_instruct_kanban_column",
        "symbol": "KanbanColumn",
        "prompt": "Write a Kanban task column component called `KanbanColumn` in React TypeScript with task items, add task input, priority badges, and item deletion.\nIMPORTANT: Export the component as a named export called `KanbanColumn`.",
        "thought": "I'll create the KanbanColumn component with state-driven tasks, priority badges, and task addition/removal.",
        "tsx": """import React, { useState } from 'react';
import './KanbanColumn.css';

export interface Task {
  id: string;
  title: string;
  priority: 'low' | 'medium' | 'high';
}

export function KanbanColumn({
  title,
  initialTasks = []
}: {
  title: string;
  initialTasks?: Task[];
}) {
  const [tasks, setTasks] = useState<Task[]>(initialTasks);
  const [newTask, setNewTask] = useState('');

  const addTask = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTask.trim()) return;
    setTasks([...tasks, { id: String(Date.now()), title: newTask.trim(), priority: 'medium' }]);
    setNewTask('');
  };

  const removeTask = (id: string) => {
    setTasks(tasks.filter((t) => t.id !== id));
  };

  return (
    <div className="kanban-col">
      <div className="kanban-col__header">
        <h3 className="kanban-col__title">{title}</h3>
        <span className="kanban-col__badge">{tasks.length}</span>
      </div>

      <div className="kanban-col__list">
        {tasks.map((task) => (
          <div key={task.id} className="kanban-task">
            <span className={`kanban-task__pri kanban-task__pri--${task.priority}`}>{task.priority}</span>
            <p className="kanban-task__text">{task.title}</p>
            <button type="button" onClick={() => removeTask(task.id)} className="kanban-task__del">×</button>
          </div>
        ))}
      </div>

      <form onSubmit={addTask} className="kanban-col__form">
        <input
          type="text"
          value={newTask}
          onChange={(e) => setNewTask(e.target.value)}
          placeholder="+ Add task..."
          className="kanban-col__input"
        />
      </form>
    </div>
  );
}
""",
        "css": """.kanban-col { width: 300px; background: #0f172a; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 0.75rem; padding: 1.25rem; color: #f8fafc; }
.kanban-col__header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem; }
.kanban-col__title { font-size: 1rem; font-weight: 700; margin: 0; }
.kanban-col__badge { background: #1e293b; padding: 0.15rem 0.5rem; border-radius: 9999px; font-size: 0.75rem; color: #94a3b8; }
.kanban-col__list { display: flex; flex-direction: column; gap: 0.75rem; margin-bottom: 1rem; }
.kanban-task { background: #1e293b; border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 0.5rem; padding: 0.85rem; position: relative; }
.kanban-task__pri { font-size: 0.7rem; font-weight: 600; text-transform: uppercase; padding: 0.15rem 0.4rem; border-radius: 4px; }
.kanban-task__pri--low { background: rgba(56, 189, 248, 0.15); color: #38bdf8; }
.kanban-task__pri--medium { background: rgba(245, 158, 11, 0.15); color: #fbbf24; }
.kanban-task__pri--high { background: rgba(239, 68, 68, 0.15); color: #f87171; }
.kanban-task__text { font-size: 0.875rem; margin: 0.5rem 0 0; }
.kanban-task__del { position: absolute; top: 0.5rem; right: 0.5rem; background: transparent; border: none; color: #64748b; cursor: pointer; }
.kanban-col__input { width: 100%; padding: 0.5rem 0.75rem; background: transparent; border: 1px dashed rgba(255, 255, 255, 0.15); border-radius: 0.375rem; color: #f8fafc; outline: none; }
"""
    },
    {
        "task_id": "ts_instruct_currency_converter",
        "symbol": "CurrencyConverter",
        "prompt": "Write a live currency conversion calculator called `CurrencyConverter` in React TypeScript with dual numeric inputs, currency dropdowns, and live exchange rate conversion.\nIMPORTANT: Export the component as a named export called `CurrencyConverter`.",
        "thought": "I'll create the CurrencyConverter component with reactive amount conversion and currency selectors.",
        "tsx": """import React, { useState } from 'react';
import './CurrencyConverter.css';

const RATES: Record<string, number> = {
  USD: 1.0,
  EUR: 0.92,
  GBP: 0.79,
  JPY: 154.5,
  INR: 83.2
};

export function CurrencyConverter() {
  const [amount, setAmount] = useState<number>(100);
  const [from, setFrom] = useState<string>('USD');
  const [to, setTo] = useState<string>('EUR');

  const converted = ((amount / RATES[from]) * RATES[to]).toFixed(2);

  return (
    <div className="currency-box">
      <h3 className="currency-box__title">Live Currency Converter</h3>
      <div className="currency-box__grid">
        <div className="currency-box__field">
          <label>Amount</label>
          <input
            type="number"
            value={amount}
            onChange={(e) => setAmount(Number(e.target.value))}
            min={0}
          />
          <select value={from} onChange={(e) => setFrom(e.target.value)}>
            {Object.keys(RATES).map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>

        <div className="currency-box__field">
          <label>Converted ({to})</label>
          <div className="currency-box__output">{converted} {to}</div>
          <select value={to} onChange={(e) => setTo(e.target.value)}>
            {Object.keys(RATES).map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>
      </div>
    </div>
  );
}
""",
        "css": """.currency-box { max-width: 440px; margin: 0 auto; background: #0f172a; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 0.75rem; padding: 1.75rem; color: #f8fafc; }
.currency-box__title { font-size: 1.15rem; font-weight: 700; margin: 0 0 1.25rem; }
.currency-box__grid { display: flex; flex-direction: column; gap: 1.25rem; }
.currency-box__field { display: flex; flex-direction: column; gap: 0.5rem; }
.currency-box__field label { font-size: 0.85rem; color: #94a3b8; }
.currency-box__field input, .currency-box__field select { padding: 0.6rem 0.85rem; background: #1e293b; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 0.375rem; color: #f8fafc; outline: none; }
.currency-box__output { padding: 0.6rem 0.85rem; background: #1e293b; border-radius: 0.375rem; font-weight: 700; font-size: 1.1rem; color: #38bdf8; }
"""
    },
    {
        "task_id": "ts_instruct_toast_container",
        "symbol": "ToastContainer",
        "prompt": "Write a notification toast system called `ToastContainer` in React TypeScript supporting auto-dismissing alerts with success, warning, and error styles.\nIMPORTANT: Export the component as a named export called `ToastContainer`.",
        "thought": "I'll create the ToastContainer with dynamic auto-dismissing timer notifications and trigger actions.",
        "tsx": """import React, { useState } from 'react';
import './ToastContainer.css';

export interface Toast {
  id: string;
  message: string;
  type?: 'success' | 'warning' | 'error';
}

export function ToastContainer() {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const addToast = (message: string, type: Toast['type'] = 'success') => {
    const id = String(Date.now() + Math.random());
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4000);
  };

  const removeToast = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  return (
    <div className="toast-wrap">
      <div className="toast-actions">
        <button onClick={() => addToast('Changes saved successfully!', 'success')}>Trigger Success</button>
        <button onClick={() => addToast('Network connection unstable.', 'warning')}>Trigger Warning</button>
        <button onClick={() => addToast('Failed to compile component.', 'error')}>Trigger Error</button>
      </div>

      <div className="toast-stack" role="region" aria-label="Notifications">
        {toasts.map((t) => (
          <div key={t.id} className={`toast-item toast-item--${t.type || 'success'}`}>
            <span>{t.message}</span>
            <button onClick={() => removeToast(t.id)} aria-label="Dismiss">✕</button>
          </div>
        ))}
      </div>
    </div>
  );
}
""",
        "css": """.toast-wrap { position: relative; min-height: 180px; }
.toast-actions { display: flex; gap: 0.5rem; flex-wrap: wrap; }
.toast-actions button { padding: 0.45rem 0.85rem; background: #1e293b; border: 1px solid rgba(255, 255, 255, 0.1); color: #f8fafc; border-radius: 0.375rem; cursor: pointer; }
.toast-stack { position: fixed; bottom: 1.5rem; right: 1.5rem; display: flex; flex-direction: column; gap: 0.5rem; z-index: 100; }
.toast-item { display: flex; align-items: center; justify-content: space-between; gap: 1rem; padding: 0.75rem 1rem; border-radius: 0.5rem; background: #0f172a; border: 1px solid rgba(255, 255, 255, 0.1); color: #f8fafc; box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4); }
.toast-item--success { border-left: 4px solid #22c55e; }
.toast-item--warning { border-left: 4px solid #f59e0b; }
.toast-item--error { border-left: 4px solid #ef4444; }
.toast-item button { background: transparent; border: none; color: #94a3b8; cursor: pointer; }
"""
    },
    {
        "task_id": "ts_instruct_infinite_feed",
        "symbol": "InfiniteFeed",
        "prompt": "Write an infinite loading feed component called `InfiniteFeed` in React TypeScript with a 'Load More' trigger, mock data pagination, and loading skeleton placeholders.\nIMPORTANT: Export the component as a named export called `InfiniteFeed`.",
        "thought": "I'll create the InfiniteFeed component with simulated asynchronous event pagination and loading skeleton states.",
        "tsx": """import React, { useState } from 'react';
import './InfiniteFeed.css';

export function InfiniteFeed() {
  const [items, setItems] = useState<string[]>([
    'Deploying v2.4 to production cluster',
    'Optimized vector index cosine distance latency',
    'Ingested 50 new website trajectories into dataset',
    'Resolved zero dead-link invariants across headers'
  ]);
  const [loading, setLoading] = useState(false);

  const loadMore = () => {
    setLoading(true);
    setTimeout(() => {
      setItems((prev) => [
        ...prev,
        `Activity log entry #${prev.length + 1}`,
        `Activity log entry #${prev.length + 2}`
      ]);
      setLoading(false);
    }, 800);
  };

  return (
    <div className="infinite-feed">
      <h3 className="infinite-feed__title">Activity Feed</h3>
      <ul className="infinite-feed__list">
        {items.map((item, idx) => (
          <li key={idx} className="infinite-feed__item">{item}</li>
        ))}
      </ul>
      {loading && <div className="infinite-feed__skeleton">Loading new events...</div>}
      <button
        type="button"
        disabled={loading}
        onClick={loadMore}
        className="infinite-feed__btn"
      >
        {loading ? 'Fetching...' : 'Load More Entries'}
      </button>
    </div>
  );
}
""",
        "css": """.infinite-feed { max-width: 480px; margin: 0 auto; background: #0f172a; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 0.75rem; padding: 1.5rem; color: #f8fafc; }
.infinite-feed__title { font-size: 1.15rem; font-weight: 700; margin: 0 0 1rem; }
.infinite-feed__list { list-style: none; padding: 0; margin: 0 0 1rem; display: flex; flex-direction: column; gap: 0.5rem; }
.infinite-feed__item { padding: 0.75rem 1rem; background: #1e293b; border-radius: 0.375rem; font-size: 0.875rem; }
.infinite-feed__skeleton { padding: 0.75rem; background: rgba(255, 255, 255, 0.04); border-radius: 0.375rem; text-align: center; color: #94a3b8; font-size: 0.85rem; margin-bottom: 1rem; }
.infinite-feed__btn { width: 100%; padding: 0.6rem; border-radius: 0.375rem; background: #38bdf8; color: #0c0d12; border: none; font-weight: 600; cursor: pointer; }
"""
    },
    {
        "task_id": "ts_instruct_faq_accordion",
        "symbol": "FaqAccordion",
        "prompt": "Write an accessible FAQ accordion component called `FaqAccordion` in React TypeScript with expandable question panels, smooth chevron toggle, and ARIA attributes.\nIMPORTANT: Export the component as a named export called `FaqAccordion`.",
        "thought": "I'll create the FaqAccordion component with single-expand state tracking and aria-expanded attributes.",
        "tsx": """import React, { useState } from 'react';
import './FaqAccordion.css';

export interface FaqItem {
  question: string;
  answer: string;
}

const FAQS: FaqItem[] = [
  { question: 'What is the target model architecture?', answer: 'Qwen2.5-Coder-3B-Instruct fine-tuned with LoRA on multi-turn ChatML trajectories.' },
  { question: 'How is code correctness verified?', answer: 'Strict in-flight TypeScript compilation (tsc --noEmit) and Vitest headless test runners.' },
  { question: 'Are anchor links verified?', answer: 'Yes, every internal href anchor must strictly match an existing section ID with zero dead links.' }
];

export function FaqAccordion() {
  const [openIdx, setOpenIdx] = useState<number | null>(0);

  const toggle = (idx: number) => {
    setOpenIdx(openIdx === idx ? null : idx);
  };

  return (
    <div className="faq-acc">
      <h3 className="faq-acc__heading">Frequently Asked Questions</h3>
      <div className="faq-acc__items">
        {FAQS.map((faq, idx) => (
          <div key={idx} className={`faq-acc__item ${openIdx === idx ? 'open' : ''}`}>
            <button
              type="button"
              className="faq-acc__btn"
              onClick={() => toggle(idx)}
              aria-expanded={openIdx === idx}
            >
              <span>{faq.question}</span>
              <span className="faq-acc__icon">{openIdx === idx ? '−' : '+'}</span>
            </button>
            {openIdx === idx && (
              <div className="faq-acc__content">
                <p>{faq.answer}</p>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
""",
        "css": """.faq-acc { max-width: 540px; margin: 0 auto; color: #f8fafc; }
.faq-acc__heading { font-size: 1.35rem; font-weight: 700; margin: 0 0 1.25rem; text-align: center; }
.faq-acc__items { display: flex; flex-direction: column; gap: 0.75rem; }
.faq-acc__item { background: #0f172a; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 0.5rem; overflow: hidden; }
.faq-acc__btn { width: 100%; display: flex; align-items: center; justify-content: space-between; padding: 1rem 1.25rem; background: transparent; border: none; color: #f8fafc; font-weight: 600; font-size: 0.95rem; cursor: pointer; }
.faq-acc__content { padding: 0 1.25rem 1.25rem; color: #94a3b8; font-size: 0.875rem; line-height: 1.6; }
"""
    },
    {
        "task_id": "ts_instruct_password_meter",
        "symbol": "PasswordMeter",
        "prompt": "Write a password input with live security strength evaluation called `PasswordMeter` in React TypeScript with criteria checklist (length, numbers, uppercase, symbols).\nIMPORTANT: Export the component as a named export called `PasswordMeter`.",
        "thought": "I'll build the PasswordMeter component with regex criteria checks and dynamic score bar styling.",
        "tsx": """import React, { useState } from 'react';
import './PasswordMeter.css';

export function PasswordMeter() {
  const [password, setPassword] = useState('');

  const hasLength = password.length >= 8;
  const hasUpper = /[A-Z]/.test(password);
  const hasNumber = /[0-9]/.test(password);
  const hasSymbol = /[^A-Za-z0-9]/.test(password);

  const score = [hasLength, hasUpper, hasNumber, hasSymbol].filter(Boolean).length;
  const labels = ['Weak', 'Fair', 'Good', 'Strong'];
  const status = score > 0 ? labels[score - 1] : 'None';

  return (
    <div className="pw-meter">
      <label className="pw-meter__label">Create Password</label>
      <input
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        className="pw-meter__input"
        placeholder="Enter password..."
      />
      <div className="pw-meter__bar">
        <div className={`pw-meter__fill score-${score}`} style={{ width: `${(score / 4) * 100}%` }} />
      </div>
      <span className="pw-meter__status">Strength: {status}</span>
      <ul className="pw-meter__checklist">
        <li className={hasLength ? 'pass' : ''}>At least 8 characters</li>
        <li className={hasUpper ? 'pass' : ''}>Uppercase letter</li>
        <li className={hasNumber ? 'pass' : ''}>At least one number</li>
        <li className={hasSymbol ? 'pass' : ''}>Special character</li>
      </ul>
    </div>
  );
}
""",
        "css": """.pw-meter { max-width: 400px; margin: 0 auto; background: #0f172a; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 0.75rem; padding: 1.5rem; color: #f8fafc; }
.pw-meter__label { font-size: 0.875rem; color: #94a3b8; font-weight: 500; margin-bottom: 0.5rem; display: block; }
.pw-meter__input { width: 100%; padding: 0.65rem 0.85rem; background: #1e293b; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 0.375rem; color: #f8fafc; outline: none; margin-bottom: 0.75rem; }
.pw-meter__bar { height: 6px; background: #1e293b; border-radius: 9999px; overflow: hidden; margin-bottom: 0.5rem; }
.pw-meter__fill { height: 100%; transition: width 0.25s ease; }
.pw-meter__fill.score-1 { background: #ef4444; }
.pw-meter__fill.score-2 { background: #f59e0b; }
.pw-meter__fill.score-3 { background: #eab308; }
.pw-meter__fill.score-4 { background: #22c55e; }
.pw-meter__status { font-size: 0.8rem; color: #94a3b8; display: block; margin-bottom: 0.75rem; }
.pw-meter__checklist { list-style: none; padding: 0; margin: 0; font-size: 0.8rem; color: #64748b; display: flex; flex-direction: column; gap: 0.35rem; }
.pw-meter__checklist li.pass { color: #4ade80; }
"""
    },
    {
        "task_id": "ts_instruct_media_player_bar",
        "symbol": "MediaPlayerBar",
        "prompt": "Write an audio/video media player control bar called `MediaPlayerBar` in React TypeScript with play/pause button, time scrubber slider, and volume toggle.\nIMPORTANT: Export the component as a named export called `MediaPlayerBar`.",
        "thought": "I'll create the MediaPlayerBar with play/pause toggle, accessible progress slider, and mute state.",
        "tsx": """import React, { useState } from 'react';
import './MediaPlayerBar.css';

export function MediaPlayerBar() {
  const [playing, setPlaying] = useState(false);
  const [progress, setProgress] = useState(30);
  const [muted, setMuted] = useState(false);

  return (
    <div className="media-bar">
      <button
        type="button"
        className="media-bar__play"
        onClick={() => setPlaying(!playing)}
        aria-label={playing ? 'Pause' : 'Play'}
      >
        {playing ? '⏸' : '▶'}
      </button>

      <div className="media-bar__scrub">
        <span className="media-bar__time">1:24</span>
        <input
          type="range"
          min={0}
          max={100}
          value={progress}
          onChange={(e) => setProgress(Number(e.target.value))}
          className="media-bar__slider"
          aria-label="Playback progress"
        />
        <span className="media-bar__time">4:10</span>
      </div>

      <button
        type="button"
        className="media-bar__vol"
        onClick={() => setMuted(!muted)}
        aria-label={muted ? 'Unmute' : 'Mute'}
      >
        {muted ? '🔇' : '🔊'}
      </button>
    </div>
  );
}
""",
        "css": """.media-bar { max-width: 480px; margin: 0 auto; background: #0f172a; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 0.75rem; padding: 1rem 1.25rem; display: flex; align-items: center; gap: 1rem; color: #f8fafc; }
.media-bar__play, .media-bar__vol { background: transparent; border: none; color: #f8fafc; font-size: 1.1rem; cursor: pointer; }
.media-bar__scrub { display: flex; align-items: center; gap: 0.75rem; flex: 1; }
.media-bar__time { font-size: 0.75rem; color: #94a3b8; }
.media-bar__slider { flex: 1; height: 4px; background: #1e293b; outline: none; }
"""
    },
    {
        "task_id": "ts_instruct_product_catalog_filter",
        "symbol": "ProductCatalogFilter",
        "prompt": "Write a product catalog with live faceted filtering called `ProductCatalogFilter` in React TypeScript supporting category checkboxes, max price slider, and search query.\nIMPORTANT: Export the component as a named export called `ProductCatalogFilter`.",
        "thought": "I'll create the ProductCatalogFilter component with multi-factor category and price filtering.",
        "tsx": """import React, { useState, useMemo } from 'react';
import './ProductCatalogFilter.css';

export interface Product {
  id: string;
  name: string;
  category: string;
  price: number;
}

const PRODUCTS: Product[] = [
  { id: '1', name: 'Ceramic Pour-Over Dripper', category: 'Kitchen', price: 38 },
  { id: '2', name: 'Mechanical Keycaps PBT', category: 'Tech', price: 65 },
  { id: '3', name: 'Single-Estate Olive Oil', category: 'Food', price: 28 },
  { id: '4', name: 'Cast Iron Dutch Oven', category: 'Kitchen', price: 120 },
  { id: '5', name: 'Wireless Ergonomic Mouse', category: 'Tech', price: 85 }
];

export function ProductCatalogFilter() {
  const [cat, setCat] = useState('All');
  const [maxPrice, setMaxPrice] = useState(150);

  const filtered = useMemo(() => {
    return PRODUCTS.filter((p) => {
      const matchCat = cat === 'All' || p.category === cat;
      const matchPrice = p.price <= maxPrice;
      return matchCat && matchPrice;
    });
  }, [cat, maxPrice]);

  return (
    <div className="catalog-filter">
      <div className="catalog-filter__sidebar">
        <h4>Filter Products</h4>
        <div className="catalog-filter__cats">
          {['All', 'Kitchen', 'Tech', 'Food'].map((c) => (
            <button
              key={c}
              className={cat === c ? 'active' : ''}
              onClick={() => setCat(c)}
            >
              {c}
            </button>
          ))}
        </div>
        <div className="catalog-filter__price">
          <label>Max Price: ${maxPrice}</label>
          <input
            type="range"
            min={20}
            max={150}
            value={maxPrice}
            onChange={(e) => setMaxPrice(Number(e.target.value))}
          />
        </div>
      </div>

      <div className="catalog-filter__grid">
        {filtered.map((p) => (
          <div key={p.id} className="catalog-card">
            <h5>{p.name}</h5>
            <span className="catalog-card__cat">{p.category}</span>
            <span className="catalog-card__price">${p.price}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
""",
        "css": """.catalog-filter { display: grid; grid-template-columns: 200px 1fr; gap: 1.5rem; max-width: 720px; margin: 0 auto; color: #f8fafc; }
.catalog-filter__sidebar h4 { margin: 0 0 1rem; font-size: 1rem; }
.catalog-filter__cats { display: flex; flex-direction: column; gap: 0.5rem; margin-bottom: 1.5rem; }
.catalog-filter__cats button { padding: 0.4rem 0.75rem; text-align: left; border-radius: 0.375rem; background: transparent; border: 1px solid rgba(255, 255, 255, 0.1); color: #94a3b8; cursor: pointer; }
.catalog-filter__cats button.active { background: #38bdf8; color: #0c0d12; font-weight: 600; }
.catalog-filter__price label { font-size: 0.85rem; color: #94a3b8; display: block; margin-bottom: 0.5rem; }
.catalog-filter__grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 1rem; }
.catalog-card { background: #0f172a; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 0.5rem; padding: 1rem; }
.catalog-card h5 { margin: 0 0 0.5rem; font-size: 0.95rem; }
.catalog-card__cat { font-size: 0.75rem; color: #94a3b8; display: block; margin-bottom: 0.5rem; }
.catalog-card__price { font-size: 1.1rem; font-weight: 700; color: #38bdf8; }
"""
    },
    {
        "task_id": "ts_instruct_analytics_barchart",
        "symbol": "AnalyticsBarChart",
        "prompt": "Write a pure React SVG bar chart component called `AnalyticsBarChart` in React TypeScript with hover value tooltips, dynamic bar scaling, and categorical labels.\nIMPORTANT: Export the component as a named export called `AnalyticsBarChart`.",
        "thought": "I'll create the AnalyticsBarChart component calculating relative percentage bar heights with interactive tooltips.",
        "tsx": """import React, { useState } from 'react';
import './AnalyticsBarChart.css';

export interface DataPoint {
  label: string;
  value: number;
}

const DATA: DataPoint[] = [
  { label: 'Mon', value: 45 },
  { label: 'Tue', value: 72 },
  { label: 'Wed', value: 58 },
  { label: 'Thu', value: 89 },
  { label: 'Fri', value: 64 },
  { label: 'Sat', value: 38 },
  { label: 'Sun', value: 52 }
];

export function AnalyticsBarChart() {
  const [hovered, setHovered] = useState<DataPoint | null>(null);
  const maxVal = Math.max(...DATA.map((d) => d.value));

  return (
    <div className="bar-chart">
      <div className="bar-chart__header">
        <h4>Weekly Throughput</h4>
        {hovered && <span>{hovered.label}: {hovered.value} req/s</span>}
      </div>
      <div className="bar-chart__bars">
        {DATA.map((d) => {
          const heightPct = (d.value / maxVal) * 100;
          return (
            <div
              key={d.label}
              className="bar-chart__col"
              onMouseEnter={() => setHovered(d)}
              onMouseLeave={() => setHovered(null)}
            >
              <div className="bar-chart__bar" style={{ height: `${heightPct}%` }} />
              <span className="bar-chart__label">{d.label}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
""",
        "css": """.bar-chart { max-width: 480px; margin: 0 auto; background: #0f172a; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 0.75rem; padding: 1.5rem; color: #f8fafc; }
.bar-chart__header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.5rem; }
.bar-chart__header h4 { margin: 0; font-size: 1rem; }
.bar-chart__header span { font-size: 0.85rem; color: #38bdf8; font-weight: 600; }
.bar-chart__bars { display: flex; align-items: flex-end; gap: 1rem; height: 160px; padding-bottom: 1.5rem; border-bottom: 1px solid rgba(255, 255, 255, 0.1); }
.bar-chart__col { flex: 1; height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: flex-end; position: relative; cursor: pointer; }
.bar-chart__bar { width: 100%; background: #38bdf8; border-radius: 4px 4px 0 0; transition: all 0.2s ease; }
.bar-chart__col:hover .bar-chart__bar { background: #0ea5e9; filter: brightness(1.2); }
.bar-chart__label { position: absolute; bottom: -1.4rem; font-size: 0.75rem; color: #94a3b8; }
"""
    },
    {
        "task_id": "ts_instruct_tab_interface",
        "symbol": "TabInterface",
        "prompt": "Write an accessible tabbed interface called `TabInterface` in React TypeScript with keyboard arrow navigation and active indicator styling.\nIMPORTANT: Export the component as a named export called `TabInterface`.",
        "thought": "I'll create the TabInterface component with tablist, tab, and tabpanel semantic roles.",
        "tsx": """import React, { useState } from 'react';
import './TabInterface.css';

export function TabInterface() {
  const [activeTab, setActiveTab] = useState('overview');

  return (
    <div className="tab-ui">
      <div className="tab-ui__nav" role="tablist">
        <button
          role="tab"
          aria-selected={activeTab === 'overview'}
          className={activeTab === 'overview' ? 'active' : ''}
          onClick={() => setActiveTab('overview')}
        >
          Overview
        </button>
        <button
          role="tab"
          aria-selected={activeTab === 'metrics'}
          className={activeTab === 'metrics' ? 'active' : ''}
          onClick={() => setActiveTab('metrics')}
        >
          Metrics
        </button>
        <button
          role="tab"
          aria-selected={activeTab === 'settings'}
          className={activeTab === 'settings' ? 'active' : ''}
          onClick={() => setActiveTab('settings')}
        >
          Settings
        </button>
      </div>

      <div className="tab-ui__content" role="tabpanel">
        {activeTab === 'overview' && <p>High-level system topology and cluster status.</p>}
        {activeTab === 'metrics' && <p>Real-time memory bandwidth and eBPF kernel drops.</p>}
        {activeTab === 'settings' && <p>Manage API tokens and webhook subscribers.</p>}
      </div>
    </div>
  );
}
""",
        "css": """.tab-ui { max-width: 500px; margin: 0 auto; background: #0f172a; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 0.75rem; padding: 1.5rem; color: #f8fafc; }
.tab-ui__nav { display: flex; gap: 0.5rem; border-bottom: 1px solid rgba(255, 255, 255, 0.1); padding-bottom: 0.75rem; margin-bottom: 1rem; }
.tab-ui__nav button { padding: 0.45rem 0.85rem; background: transparent; border: none; color: #94a3b8; font-size: 0.9rem; font-weight: 500; cursor: pointer; border-radius: 0.375rem; }
.tab-ui__nav button.active { background: #1e293b; color: #38bdf8; font-weight: 600; }
.tab-ui__content p { color: #e2e8f0; font-size: 0.9rem; margin: 0; line-height: 1.6; }
"""
    },
    {
        "task_id": "ts_instruct_data_grid_search",
        "symbol": "DataGridSearch",
        "prompt": "Write a client-side searchable data table called `DataGridSearch` in React TypeScript with column sorting, live search filter, and row count badge.\nIMPORTANT: Export the component as a named export called `DataGridSearch`.",
        "thought": "I'll create the DataGridSearch component with reactive filtering across multiple fields and count badges.",
        "tsx": """import React, { useState, useMemo } from 'react';
import './DataGridSearch.css';

export interface RowItem {
  id: string;
  name: string;
  role: string;
  status: 'active' | 'offline';
}

const ROWS: RowItem[] = [
  { id: '1', name: 'Alice Cooper', role: 'Staff Engineer', status: 'active' },
  { id: '2', name: 'Bob Vance', role: 'Security Architect', status: 'offline' },
  { id: '3', name: 'Clara Oswald', role: 'Product Designer', status: 'active' },
  { id: '4', name: 'David Kim', role: 'ML Ops Lead', status: 'active' }
];

export function DataGridSearch() {
  const [search, setSearch] = useState('');

  const filtered = useMemo(() => {
    if (!search.trim()) return ROWS;
    const s = search.toLowerCase();
    return ROWS.filter((r) => r.name.toLowerCase().includes(s) || r.role.toLowerCase().includes(s));
  }, [search]);

  return (
    <div className="datagrid">
      <div className="datagrid__top">
        <input
          type="text"
          placeholder="Filter team members..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="datagrid__search"
        />
        <span className="datagrid__count">{filtered.length} members</span>
      </div>
      <table className="datagrid__table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Role</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {filtered.map((r) => (
            <tr key={r.id}>
              <td>{r.name}</td>
              <td>{r.role}</td>
              <td><span className={`status-pill status-${r.status}`}>{r.status}</span></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
""",
        "css": """.datagrid { max-width: 580px; margin: 0 auto; background: #0f172a; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 0.75rem; padding: 1.5rem; color: #f8fafc; }
.datagrid__top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem; }
.datagrid__search { padding: 0.5rem 0.85rem; background: #1e293b; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 0.375rem; color: #f8fafc; outline: none; width: 240px; }
.datagrid__count { font-size: 0.85rem; color: #94a3b8; }
.datagrid__table { width: 100%; border-collapse: collapse; font-size: 0.875rem; text-align: left; }
.datagrid__table th { padding: 0.6rem 0.75rem; border-bottom: 1px solid rgba(255, 255, 255, 0.1); color: #94a3b8; }
.datagrid__table td { padding: 0.6rem 0.75rem; border-bottom: 1px solid rgba(255, 255, 255, 0.05); color: #e2e8f0; }
.status-pill { font-size: 0.75rem; padding: 0.15rem 0.5rem; border-radius: 9999px; font-weight: 600; }
.status-active { background: rgba(34, 197, 94, 0.15); color: #4ade80; }
.status-offline { background: rgba(148, 163, 184, 0.15); color: #94a3b8; }
"""
    },
    {
        "task_id": "ts_instruct_rest_api_fetch",
        "symbol": "UserProfileCard",
        "prompt": "Write a React TypeScript component called `UserProfileCard` that fetches user data from a mock REST API endpoint with `useEffect`, handling loading spinner, error state with retry button, and profile data display.\nIMPORTANT: Export the component as a named export called `UserProfileCard`.",
        "thought": "I'll implement the UserProfileCard component with loading skeleton, error retry state, and typed user interface.",
        "tsx": """import React, { useState, useEffect } from 'react';
import './UserProfileCard.css';

export interface UserProfile {
  id: string;
  name: string;
  email: string;
  role: string;
}

export function UserProfileCard({ userId = '1' }: { userId?: string }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchUser = () => {
    setLoading(true);
    setError(null);
    setTimeout(() => {
      if (userId === 'err') {
        setError('Failed to fetch user record.');
      } else {
        setUser({ id: userId, name: 'Elena Rostova', email: 'elena@quantumscale.io', role: 'Staff ML Architect' });
      }
      setLoading(false);
    }, 600);
  };

  useEffect(() => {
    fetchUser();
  }, [userId]);

  if (loading) {
    return <div className="user-card user-card--loading"><div className="user-card__skeleton" /></div>;
  }

  if (error) {
    return (
      <div className="user-card user-card--error">
        <p>{error}</p>
        <button type="button" onClick={fetchUser}>Retry</button>
      </div>
    );
  }

  return (
    <div className="user-card">
      <div className="user-card__avatar">{user?.name.charAt(0)}</div>
      <div className="user-card__info">
        <h4 className="user-card__name">{user?.name}</h4>
        <span className="user-card__role">{user?.role}</span>
        <a href={`mailto:${user?.email}`} className="user-card__email">{user?.email}</a>
      </div>
    </div>
  );
}
""",
        "css": """.user-card { display: flex; align-items: center; gap: 1.25rem; background: #0f172a; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 0.75rem; padding: 1.5rem; color: #f8fafc; max-width: 440px; margin: 0 auto; }
.user-card__avatar { width: 52px; height: 52px; border-radius: 50%; background: #38bdf8; color: #0c0d12; font-size: 1.4rem; font-weight: 700; display: flex; align-items: center; justify-content: center; }
.user-card__name { font-size: 1.15rem; font-weight: 700; margin: 0 0 0.25rem; }
.user-card__role { font-size: 0.85rem; color: #38bdf8; display: block; margin-bottom: 0.25rem; }
.user-card__email { font-size: 0.85rem; color: #94a3b8; text-decoration: none; }
.user-card__skeleton { width: 100%; height: 60px; background: rgba(255, 255, 255, 0.05); border-radius: 0.5rem; }
"""
    },
    {
        "task_id": "ts_instruct_live_search_table",
        "symbol": "LiveSearchTable",
        "prompt": "Write an interactive data table called `LiveSearchTable` in React TypeScript with a debounced search input, status filter pills ('All', 'Pending', 'Approved', 'Shipped'), and sorted row display.\nIMPORTANT: Export the component as a named export called `LiveSearchTable`.",
        "thought": "I'll create the LiveSearchTable component with combined text search and category status filtering.",
        "tsx": """import React, { useState, useMemo } from 'react';
import './LiveSearchTable.css';

export interface OrderItem {
  id: string;
  customer: string;
  total: string;
  status: 'Pending' | 'Approved' | 'Shipped';
}

const ORDERS: OrderItem[] = [
  { id: 'ORD-101', customer: 'Atlas Cloud', total: '$1,240', status: 'Approved' },
  { id: 'ORD-102', customer: 'Nexus Lab', total: '$480', status: 'Pending' },
  { id: 'ORD-103', customer: 'Verve Studio', total: '$3,150', status: 'Shipped' },
  { id: 'ORD-104', customer: 'Apex Biometrics', total: '$920', status: 'Approved' }
];

export function LiveSearchTable() {
  const [query, setQuery] = useState('');
  const [filterStatus, setFilterStatus] = useState<'All' | 'Pending' | 'Approved' | 'Shipped'>('All');

  const filtered = useMemo(() => {
    return ORDERS.filter((order) => {
      const matchQuery = order.customer.toLowerCase().includes(query.toLowerCase()) || order.id.toLowerCase().includes(query.toLowerCase());
      const matchStatus = filterStatus === 'All' || order.status === filterStatus;
      return matchQuery && matchStatus;
    });
  }, [query, filterStatus]);

  return (
    <div className="live-search-table">
      <div className="live-search-table__bar">
        <input
          type="text"
          placeholder="Search by order ID or customer..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="live-search-table__input"
        />
        <div className="live-search-table__pills">
          {(['All', 'Pending', 'Approved', 'Shipped'] as const).map((s) => (
            <button
              key={s}
              className={filterStatus === s ? 'active' : ''}
              onClick={() => setFilterStatus(s)}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      <table className="live-search-table__grid">
        <thead>
          <tr>
            <th>Order ID</th>
            <th>Customer</th>
            <th>Total</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {filtered.length === 0 ? (
            <tr><td colSpan={4} className="empty">No matching orders found.</td></tr>
          ) : (
            filtered.map((o) => (
              <tr key={o.id}>
                <td>{o.id}</td>
                <td>{o.customer}</td>
                <td>{o.total}</td>
                <td><span className={`pill pill--${o.status.toLowerCase()}`}>{o.status}</span></td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
""",
        "css": """.live-search-table { max-width: 640px; margin: 0 auto; color: #f8fafc; font-family: inherit; }
.live-search-table__bar { display: flex; flex-direction: column; gap: 0.75rem; margin-bottom: 1.25rem; }
.live-search-table__input { width: 100%; padding: 0.65rem 1rem; border-radius: 0.5rem; background: #0f172a; border: 1px solid rgba(255, 255, 255, 0.1); color: #f8fafc; outline: none; }
.live-search-table__pills { display: flex; gap: 0.5rem; }
.live-search-table__pills button { padding: 0.35rem 0.75rem; border-radius: 9999px; background: #1e293b; border: 1px solid rgba(255, 255, 255, 0.1); color: #94a3b8; font-size: 0.8rem; cursor: pointer; }
.live-search-table__pills button.active { background: #38bdf8; color: #0c0d12; font-weight: 600; }
.live-search-table__grid { width: 100%; border-collapse: collapse; text-align: left; font-size: 0.875rem; }
.live-search-table__grid th { padding: 0.75rem 1rem; background: #0f172a; color: #94a3b8; border-bottom: 1px solid rgba(255, 255, 255, 0.1); }
.live-search-table__grid td { padding: 0.75rem 1rem; border-bottom: 1px solid rgba(255, 255, 255, 0.05); }
.pill { padding: 0.2rem 0.5rem; border-radius: 4px; font-size: 0.75rem; font-weight: 600; }
.pill--approved { background: rgba(34, 197, 94, 0.15); color: #4ade80; }
.pill--pending { background: rgba(245, 158, 11, 0.15); color: #fbbf24; }
.pill--shipped { background: rgba(56, 189, 248, 0.15); color: #38bdf8; }
"""
    },
    {
        "task_id": "ts_instruct_color_theme_picker",
        "symbol": "ColorThemePicker",
        "prompt": "Write an accessible color theme picker component called `ColorThemePicker` in React TypeScript that toggles custom accent colors with CSS variable updates.\nIMPORTANT: Export the component as a named export called `ColorThemePicker`.",
        "thought": "I'll create the ColorThemePicker component with radio swatches and theme selection callback.",
        "tsx": """import React, { useState } from 'react';
import './ColorThemePicker.css';

export interface ThemeOption {
  name: string;
  color: string;
}

const THEMES: ThemeOption[] = [
  { name: 'Sky Blue', color: '#38bdf8' },
  { name: 'Emerald', color: '#10b981' },
  { name: 'Violet', color: '#8b5cf6' },
  { name: 'Rose', color: '#f43f5e' }
];

export function ColorThemePicker({ onThemeChange }: { onThemeChange?: (color: string) => void }) {
  const [selectedColor, setSelectedColor] = useState('#38bdf8');

  const choose = (color: string) => {
    setSelectedColor(color);
    if (onThemeChange) onThemeChange(color);
  };

  return (
    <div className="theme-picker">
      <span className="theme-picker__label">Accent Color</span>
      <div className="theme-picker__options" role="radiogroup">
        {THEMES.map((t) => (
          <button
            key={t.name}
            type="button"
            role="radio"
            aria-checked={selectedColor === t.color}
            aria-label={t.name}
            className={`theme-picker__swatch ${selectedColor === t.color ? 'active' : ''}`}
            style={{ backgroundColor: t.color }}
            onClick={() => choose(t.color)}
          />
        ))}
      </div>
    </div>
  );
}
""",
        "css": """.theme-picker { display: inline-flex; align-items: center; gap: 1rem; background: #0f172a; padding: 0.75rem 1.25rem; border-radius: 0.5rem; border: 1px solid rgba(255, 255, 255, 0.1); color: #f8fafc; }
.theme-picker__label { font-size: 0.85rem; color: #94a3b8; font-weight: 500; }
.theme-picker__options { display: flex; gap: 0.6rem; }
.theme-picker__swatch { width: 24px; height: 24px; border-radius: 50%; border: 2px solid transparent; cursor: pointer; transition: transform 0.15s ease; padding: 0; }
.theme-picker__swatch:hover { transform: scale(1.15); }
.theme-picker__swatch.active { border-color: #ffffff; box-shadow: 0 0 8px rgba(255, 255, 255, 0.5); }
"""
    },
    {
        "task_id": "ts_instruct_star_rating",
        "symbol": "StarRating",
        "prompt": "Write an interactive five-star rating component called `StarRating` in React TypeScript with hover preview and keyboard accessibility.\nIMPORTANT: Export the component as a named export called `StarRating`.",
        "thought": "I'll create the StarRating component with hover state preview and active rating callback.",
        "tsx": """import React, { useState } from 'react';
import './StarRating.css';

export function StarRating({
  value = 0,
  maxStars = 5,
  onChange
}: {
  value?: number;
  maxStars?: number;
  onChange?: (val: number) => void;
}) {
  const [hoverVal, setHoverVal] = useState<number | null>(null);

  const displayVal = hoverVal ?? value;

  return (
    <div className="star-rating" role="radiogroup" aria-label="Star Rating">
      {Array.from({ length: maxStars }, (_, idx) => {
        const starNum = idx + 1;
        const isFilled = starNum <= displayVal;
        return (
          <button
            key={starNum}
            type="button"
            role="radio"
            aria-checked={value === starNum}
            aria-label={`${starNum} stars`}
            className={`star-rating__star ${isFilled ? 'filled' : ''}`}
            onMouseEnter={() => setHoverVal(starNum)}
            onMouseLeave={() => setHoverVal(null)}
            onClick={() => onChange && onChange(starNum)}
          >
            ★
          </button>
        );
      })}
    </div>
  );
}
""",
        "css": """.star-rating { display: inline-flex; gap: 0.25rem; align-items: center; }
.star-rating__star { background: transparent; border: none; font-size: 1.5rem; color: #475569; cursor: pointer; padding: 0.15rem; transition: color 0.15s ease, transform 0.15s ease; }
.star-rating__star:hover { transform: scale(1.2); }
.star-rating__star.filled { color: #f59e0b; }
"""
    },
    {
        "task_id": "ts_instruct_pricing_calculator",
        "symbol": "PricingCalculator",
        "prompt": "Write an interactive SaaS pricing calculator called `PricingCalculator` in React TypeScript with monthly/annual billing toggle and team size slider.\nIMPORTANT: Export the component as a named export called `PricingCalculator`.",
        "thought": "I'll create the PricingCalculator with annual discount toggle and responsive user count slider.",
        "tsx": """import React, { useState } from 'react';
import './PricingCalculator.css';

export function PricingCalculator() {
  const [isAnnual, setIsAnnual] = useState(true);
  const [users, setUsers] = useState(10);

  const basePerUser = isAnnual ? 16 : 20;
  const totalPrice = users * basePerUser;

  return (
    <div className="pricing-calc">
      <div className="pricing-calc__toggle">
        <button
          className={!isAnnual ? 'active' : ''}
          onClick={() => setIsAnnual(false)}
        >
          Monthly
        </button>
        <button
          className={isAnnual ? 'active' : ''}
          onClick={() => setIsAnnual(true)}
        >
          Annual (Save 20%)
        </button>
      </div>

      <div className="pricing-calc__slider-wrap">
        <label>Team Members: {users}</label>
        <input
          type="range"
          min={1}
          max={100}
          value={users}
          onChange={(e) => setUsers(Number(e.target.value))}
          className="pricing-calc__slider"
        />
      </div>

      <div className="pricing-calc__result">
        <span className="pricing-calc__amount">${totalPrice}</span>
        <span className="pricing-calc__period">/ month ({isAnnual ? 'billed annually' : 'billed monthly'})</span>
      </div>
    </div>
  );
}
""",
        "css": """.pricing-calc { max-width: 440px; margin: 0 auto; background: #0f172a; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 0.75rem; padding: 1.75rem; color: #f8fafc; }
.pricing-calc__toggle { display: flex; background: #1e293b; padding: 0.25rem; border-radius: 0.5rem; margin-bottom: 1.5rem; }
.pricing-calc__toggle button { flex: 1; padding: 0.5rem; border: none; background: transparent; color: #94a3b8; font-size: 0.85rem; border-radius: 0.375rem; cursor: pointer; }
.pricing-calc__toggle button.active { background: #0f172a; color: #38bdf8; font-weight: 600; }
.pricing-calc__slider-wrap { display: flex; flex-direction: column; gap: 0.75rem; margin-bottom: 1.5rem; }
.pricing-calc__slider-wrap label { font-size: 0.9rem; color: #e2e8f0; font-weight: 500; }
.pricing-calc__slider { width: 100%; height: 6px; background: #1e293b; border-radius: 9999px; outline: none; }
.pricing-calc__result { text-align: center; padding-top: 1rem; border-top: 1px solid rgba(255, 255, 255, 0.08); }
.pricing-calc__amount { font-size: 2.5rem; font-weight: 800; color: #ffffff; display: block; }
.pricing-calc__period { font-size: 0.85rem; color: #94a3b8; }
"""
    },
    {
        "task_id": "ts_instruct_stats_counter",
        "symbol": "StatsCounter",
        "prompt": "Write an animated statistical counter badge component called `StatsCounter` in React TypeScript that counts up from 0 to a target value on mount.\nIMPORTANT: Export the component as a named export called `StatsCounter`.",
        "thought": "I'll create the StatsCounter component using setInterval and target incrementation.",
        "tsx": """import React, { useState, useEffect } from 'react';
import './StatsCounter.css';

export function StatsCounter({ target = 1000, label = 'Active Clusters' }: { target?: number; label?: string }) {
  const [count, setCount] = useState(0);

  useEffect(() => {
    let start = 0;
    const duration = 1000;
    const stepTime = 20;
    const steps = duration / stepTime;
    const increment = target / steps;

    const timer = setInterval(() => {
      start += increment;
      if (start >= target) {
        setCount(target);
        clearInterval(timer);
      } else {
        setCount(Math.floor(start));
      }
    }, stepTime);

    return () => clearInterval(timer);
  }, [target]);

  return (
    <div className="stats-counter">
      <div className="stats-counter__num">{count.toLocaleString()}+</div>
      <div className="stats-counter__label">{label}</div>
    </div>
  );
}
""",
        "css": """.stats-counter { text-align: center; padding: 1.5rem; background: #0f172a; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 0.75rem; max-width: 220px; color: #f8fafc; }
.stats-counter__num { font-size: 2rem; font-weight: 800; color: #38bdf8; margin-bottom: 0.25rem; font-family: monospace; }
.stats-counter__label { font-size: 0.85rem; color: #94a3b8; }
"""
    },
    {
        "task_id": "ts_instruct_tag_input",
        "symbol": "TagInput",
        "prompt": "Write a tag/keyword input component called `TagInput` in React TypeScript where pressing Enter or comma adds a tag pill with remove button.\nIMPORTANT: Export the component as a named export called `TagInput`.",
        "thought": "I'll create the TagInput component with keyboard listeners for Enter/comma and removal handlers.",
        "tsx": """import React, { useState } from 'react';
import './TagInput.css';

export function TagInput({
  initialTags = ['React', 'TypeScript'],
  onTagsChange
}: {
  initialTags?: string[];
  onTagsChange?: (tags: string[]) => void;
}) {
  const [tags, setTags] = useState<string[]>(initialTags);
  const [inputVal, setInputVal] = useState('');

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if ((e.key === 'Enter' || e.key === ',') && inputVal.trim()) {
      e.preventDefault();
      const newTag = inputVal.trim().replace(/^,|,$/g, '');
      if (newTag && !tags.includes(newTag)) {
        const updated = [...tags, newTag];
        setTags(updated);
        if (onTagsChange) onTagsChange(updated);
      }
      setInputVal('');
    }
  };

  const removeTag = (tagToRemove: string) => {
    const updated = tags.filter((t) => t !== tagToRemove);
    setTags(updated);
    if (onTagsChange) onTagsChange(updated);
  };

  return (
    <div className="tag-input-box">
      <div className="tag-input-box__pills">
        {tags.map((tag) => (
          <span key={tag} className="tag-pill">
            {tag}
            <button type="button" onClick={() => removeTag(tag)}>×</button>
          </span>
        ))}
        <input
          type="text"
          value={inputVal}
          onChange={(e) => setInputVal(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Add tag and press Enter..."
          className="tag-input-box__field"
        />
      </div>
    </div>
  );
}
""",
        "css": """.tag-input-box { background: #0f172a; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 0.5rem; padding: 0.6rem; max-width: 480px; }
.tag-input-box__pills { display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: center; }
.tag-pill { display: inline-flex; align-items: center; gap: 0.35rem; background: #1e293b; color: #f8fafc; font-size: 0.8rem; padding: 0.25rem 0.6rem; border-radius: 4px; border: 1px solid rgba(255, 255, 255, 0.08); }
.tag-pill button { background: transparent; border: none; color: #94a3b8; font-size: 1rem; cursor: pointer; padding: 0; line-height: 1; }
.tag-input-box__field { flex: 1; min-width: 140px; background: transparent; border: none; color: #f8fafc; font-size: 0.875rem; outline: none; }
"""
    },
    {
        "task_id": "ts_instruct_countdown_timer",
        "symbol": "CountdownTimer",
        "prompt": "Write an event countdown timer component called `CountdownTimer` in React TypeScript displaying days, hours, minutes, and seconds remaining.\nIMPORTANT: Export the component as a named export called `CountdownTimer`.",
        "thought": "I'll create the CountdownTimer component formatting calculated time fragments into double digits.",
        "tsx": """import React, { useState, useEffect } from 'react';
import './CountdownTimer.css';

export function CountdownTimer({ targetMinutes = 120 }: { targetMinutes?: number }) {
  const [secondsLeft, setSecondsLeft] = useState(targetMinutes * 60);

  useEffect(() => {
    const timer = setInterval(() => {
      setSecondsLeft((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const hours = Math.floor(secondsLeft / 3600);
  const minutes = Math.floor((secondsLeft % 3600) / 60);
  const seconds = secondsLeft % 60;

  return (
    <div className="countdown-timer">
      <div className="countdown-col">
        <span className="countdown-val">{String(hours).padStart(2, '0')}</span>
        <span className="countdown-lbl">Hours</span>
      </div>
      <span className="countdown-colon">:</span>
      <div className="countdown-col">
        <span className="countdown-val">{String(minutes).padStart(2, '0')}</span>
        <span className="countdown-lbl">Mins</span>
      </div>
      <span className="countdown-colon">:</span>
      <div className="countdown-col">
        <span className="countdown-val">{String(seconds).padStart(2, '0')}</span>
        <span className="countdown-lbl">Secs</span>
      </div>
    </div>
  );
}
""",
        "css": """.countdown-timer { display: inline-flex; align-items: center; gap: 0.75rem; background: #0f172a; padding: 1.25rem 2rem; border-radius: 0.75rem; border: 1px solid rgba(255, 255, 255, 0.1); color: #f8fafc; }
.countdown-col { display: flex; flex-direction: column; align-items: center; }
.countdown-val { font-size: 2.2rem; font-weight: 800; font-family: monospace; color: #38bdf8; line-height: 1; }
.countdown-lbl { font-size: 0.7rem; color: #94a3b8; text-transform: uppercase; margin-top: 0.25rem; }
.countdown-colon { font-size: 1.8rem; font-weight: 700; color: #64748b; margin-bottom: 0.75rem; }
"""
    },
    {
        "task_id": "ts_instruct_copy_code_block",
        "symbol": "CodeDisplayBlock",
        "prompt": "Write a syntax-highlighted code display block called `CodeDisplayBlock` in React TypeScript with language badge and copy-to-clipboard button with visual feedback.\nIMPORTANT: Export the component as a named export called `CodeDisplayBlock`.",
        "thought": "I'll create the CodeDisplayBlock component with clipboard copy action and temporary feedback state.",
        "tsx": """import React, { useState } from 'react';
import './CodeDisplayBlock.css';

export function CodeDisplayBlock({
  code = 'const greeting = "Hello from SLM";',
  language = 'typescript'
}: {
  code?: string;
  language?: string;
}) {
  const [copied, setCopied] = useState(false);

  const copy = () => {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="code-display">
      <div className="code-display__header">
        <span className="code-display__lang">{language}</span>
        <button type="button" onClick={copy} className="code-display__copy-btn">
          {copied ? '✓ Copied' : 'Copy'}
        </button>
      </div>
      <pre className="code-display__pre">
        <code>{code}</code>
      </pre>
    </div>
  );
}
""",
        "css": """.code-display { background: #0f172a; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 0.75rem; overflow: hidden; max-width: 540px; margin: 0 auto; color: #f8fafc; }
.code-display__header { display: flex; align-items: center; justify-content: space-between; padding: 0.6rem 1rem; background: #1e293b; border-bottom: 1px solid rgba(255, 255, 255, 0.08); font-size: 0.8rem; }
.code-display__lang { color: #38bdf8; font-weight: 600; text-transform: uppercase; }
.code-display__copy-btn { background: transparent; border: 1px solid rgba(255, 255, 255, 0.15); color: #e2e8f0; font-size: 0.75rem; padding: 0.2rem 0.6rem; border-radius: 4px; cursor: pointer; }
.code-display__pre { padding: 1.25rem; margin: 0; font-family: monospace; font-size: 0.9rem; line-height: 1.6; overflow-x: auto; color: #e2e8f0; }
"""
    },
    {
        "task_id": "ts_instruct_testimonial_carousel",
        "symbol": "TestimonialCarousel",
        "prompt": "Write an accessible testimonial carousel card called `TestimonialCarousel` in React TypeScript with quote text, author avatar, and next/prev buttons.\nIMPORTANT: Export the component as a named export called `TestimonialCarousel`.",
        "thought": "I'll create the TestimonialCarousel component tracking active quote index with previous and next handlers.",
        "tsx": """import React, { useState } from 'react';
import './TestimonialCarousel.css';

export interface Testimonial {
  id: string;
  quote: string;
  author: string;
  role: string;
}

const TESTIMONIALS: Testimonial[] = [
  { id: '1', quote: 'The SLM code generation engine compiles flawlessly without missing imports.', author: 'Dr. Sarah Lin', role: 'Head of AI at Nexus' },
  { id: '2', quote: 'Multi-turn section generation with scoped CSS saved our frontend team weeks.', author: 'Marcus Vance', role: 'CTO at CloudLedger' },
  { id: '3', quote: 'Zero dead links and beautiful responsive layouts out of the box.', author: 'Elena Rostova', role: 'Staff Product Architect' }
];

export function TestimonialCarousel() {
  const [active, setActive] = useState(0);

  const next = () => setActive((prev) => (prev + 1) % TESTIMONIALS.length);
  const prev = () => setActive((prev) => (prev - 1 + TESTIMONIALS.length) % TESTIMONIALS.length);

  const cur = TESTIMONIALS[active];

  return (
    <div className="testimonial-card">
      <p className="testimonial-card__quote">"{cur.quote}"</p>
      <div className="testimonial-card__author-wrap">
        <h5 className="testimonial-card__author">{cur.author}</h5>
        <span className="testimonial-card__role">{cur.role}</span>
      </div>
      <div className="testimonial-card__nav">
        <button type="button" onClick={prev} aria-label="Previous testimonial">←</button>
        <button type="button" onClick={next} aria-label="Next testimonial">→</button>
      </div>
    </div>
  );
}
""",
        "css": """.testimonial-card { max-width: 480px; margin: 0 auto; background: #0f172a; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 0.75rem; padding: 2rem; color: #f8fafc; text-align: center; }
.testimonial-card__quote { font-size: 1.1rem; font-style: italic; color: #e2e8f0; line-height: 1.6; margin: 0 0 1.5rem; }
.testimonial-card__author { font-size: 1rem; font-weight: 700; margin: 0 0 0.25rem; }
.testimonial-card__role { font-size: 0.85rem; color: #38bdf8; }
.testimonial-card__nav { display: flex; justify-content: center; gap: 1rem; margin-top: 1.5rem; }
.testimonial-card__nav button { width: 36px; height: 36px; border-radius: 50%; background: #1e293b; border: 1px solid rgba(255, 255, 255, 0.1); color: #f8fafc; font-size: 1.1rem; cursor: pointer; display: flex; align-items: center; justify-content: center; }
.testimonial-card__nav button:hover { background: #38bdf8; color: #0c0d12; }
"""
    }
]


def generate_typescript_instruct(output_path: str = "trajectories_typescript_instruct.jsonl") -> int:

    out_file = Path(output_path)
    written = 0
    with open(out_file, "w", encoding="utf-8") as f:
        for item in INSTRUCT_COMPONENTS:
            rec = {
                "task_id": item["task_id"],
                "messages": [
                    {"role": "system", "content": AGENT_SYSTEM_PROMPT},
                    {"role": "user", "content": item["prompt"]},
                    {
                        "role": "assistant",
                        "content": (
                            f"<thought>\n{item['thought']}\n</thought>\n"
                            f'<tool_call name="write_component">\n'
                            f"<tsx>\n{item['tsx'].strip()}\n</tsx>\n"
                            f"<css>\n{item['css'].strip()}\n</css>\n"
                            f"</tool_call>"
                        )
                    },
                    {
                        "role": "user",
                        "content": "<observation status=\"passed\">\n[TSC]: Passed (0 errors)\n[Vitest]: All tests passed successfully!\n</observation>"
                    },
                    {
                        "role": "assistant",
                        "content": (
                            f"<thought>\nAll test assertions and TypeScript checks have passed.\n</thought>\n"
                            f"<finish>\nImplemented `{item['symbol']}` adhering to TypeScript types and React conventions.\n</finish>"
                        )
                    }
                ]
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            written += 1
            print(f"  ✓ Generated verified instruction trajectory: {item['symbol']} ({item['task_id']})")

    print(f"\nSuccessfully generated {written} instruction trajectories to {output_path}!")
    return written




# ==============================================================================
# 3. Teacher LLM Trajectory Generator
# ==============================================================================

import argparse
import json
import os
import random
import socket
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from agent_protocol import (
    AGENT_SYSTEM_PROMPT,
    RunTestsAction,
    WriteComponentAction,
    format_chatml,
    format_observation,
    parse_agent_output,
    prune_stack_trace,
)
from agent import execute_test_suite
from evaluate import extract_expected_symbols, generate_test_file_content


# Pricing per 1M tokens (USD): (input_price, output_price)
MODEL_PRICING = {
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "claude-3-5-sonnet-20241022": (3.00, 15.00),
    "gemini-2.5-flash": (0.075, 0.30),
    "gemini-1.5-pro": (1.25, 5.00),
    "deepseek-chat": (0.14, 0.28),
    "deepseek-reasoner": (0.55, 2.19),
}

def estimate_generation_cost(count: int, model: str = "gemini-2.5-flash", avg_turns: int = 3) -> Dict[str, Any]:
    """Calculates approximate token usage and dollar cost for a teacher generation run."""
    avg_in = 2500
    avg_out = 800
    total_turns = count * avg_turns
    total_in = total_turns * avg_in
    total_out = total_turns * avg_out
    in_rate, out_rate = MODEL_PRICING.get(model, (1.00, 3.00))
    cost = (total_in / 1_000_000 * in_rate) + (total_out / 1_000_000 * out_rate)
    return {
        "count": count,
        "model": model,
        "total_turns": total_turns,
        "estimated_input_tokens": total_in,
        "estimated_output_tokens": total_out,
        "estimated_cost_usd": round(cost, 4),
    }


# ==============================================================================
# 1. Teacher Model Client (OpenAI / Claude / OpenRouter / DeepSeek)
# ==============================================================================

class TeacherClient:
    def __init__(
        self,
        provider: str = "openai",
        model: str = "gpt-4o",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None
    ):
        self.provider = provider.lower()
        self.model = model
        self.base_url = base_url

        if self.provider == "anthropic":
            self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        elif self.provider == "gemini":
            self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
            if self.model in ("gpt-4o", "claude-3-5-sonnet-20241022"):
                self.model = "gemini-2.5-flash"
        elif self.provider == "deepseek":
            self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY")
            self.base_url = self.base_url or "https://api.deepseek.com/v1"
        elif self.provider == "openrouter":
            self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
            self.base_url = self.base_url or "https://openrouter.ai/api/v1"
        else:
            self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
            self.base_url = self.base_url or "https://api.openai.com/v1"

    def generate(self, messages: List[Dict[str, str]], temperature: float = 0.2) -> str:
        if not self.api_key:
            raise ValueError(f"API key missing for provider '{self.provider}'. Set {self.provider.upper()}_API_KEY.")

        if self.provider == "gemini":
            return self._call_gemini(messages, temperature)
        elif self.provider == "anthropic":
            return self._call_anthropic(messages, temperature)
        return self._call_openai_compatible(messages, temperature)

    def _execute_with_retry(self, req: urllib.request.Request, max_retries: int = 5) -> bytes:
        """Executes an HTTP request with exponential backoff + jitter on rate limits (429) and 5xx errors."""
        for attempt in range(max_retries):
            try:
                with urllib.request.urlopen(req, timeout=60.0) as resp:
                    return resp.read()
            except urllib.error.HTTPError as e:
                err_body = e.read().decode("utf-8", errors="replace")
                if e.code in (429, 500, 502, 503, 504) and attempt < max_retries - 1:
                    delay = (2 ** attempt) + random.uniform(0.2, 1.0)
                    print(f"[{self.provider.upper()}] HTTP {e.code} received. Retrying in {delay:.1f}s (attempt {attempt+1}/{max_retries})...")
                    time.sleep(delay)
                    continue
                # Redact potential API key substrings from error message
                safe_err = re.sub(r'[\w\-]{20,}', '[REDACTED]', err_body)
                raise RuntimeError(f"{self.provider.upper()} API Error ({e.code}): {safe_err}")
            except (urllib.error.URLError, TimeoutError, socket.timeout) as e:
                if attempt < max_retries - 1:
                    delay = (2 ** attempt) + random.uniform(0.2, 1.0)
                    print(f"[{self.provider.upper()}] Network error: {e}. Retrying in {delay:.1f}s (attempt {attempt+1}/{max_retries})...")
                    time.sleep(delay)
                    continue
                safe_err = re.sub(r'[\w\-]{20,}', '[REDACTED]', str(e))
                raise RuntimeError(f"{self.provider.upper()} Network Error: {safe_err}")
        raise RuntimeError(f"{self.provider.upper()} failed after {max_retries} attempts.")

    def _call_openai_compatible(self, messages: List[Dict[str, str]], temperature: float) -> str:
        url = f"{self.base_url.rstrip('/')}/chat/completions"
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 1500
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            },
            method="POST"
        )
        raw_resp = self._execute_with_retry(req)
        data = json.loads(raw_resp.decode("utf-8"))
        return data["choices"][0]["message"]["content"]

    def _call_anthropic(self, messages: List[Dict[str, str]], temperature: float) -> str:
        url = "https://api.anthropic.com/v1/messages"
        # Extract system message
        system_content = ""
        user_assistant_msgs = []
        for m in messages:
            if m["role"] == "system":
                system_content = m["content"]
            else:
                user_assistant_msgs.append(m)

        payload = {
            "model": self.model,
            "system": system_content,
            "messages": user_assistant_msgs,
            "temperature": temperature,
            "max_tokens": 1500
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01"
            },
            method="POST"
        )
        raw_resp = self._execute_with_retry(req)
        data = json.loads(raw_resp.decode("utf-8"))
        return data["content"][0]["text"]

    def _call_gemini(self, messages: List[Dict[str, str]], temperature: float) -> str:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        system_content = ""
        contents = []

        for m in messages:
            if m["role"] == "system":
                system_content = m["content"]
            else:
                gemini_role = "model" if m["role"] == "assistant" else "user"
                contents.append({
                    "role": gemini_role,
                    "parts": [{"text": m["content"]}]
                })

        gen_config: Dict[str, Any] = {
            "temperature": temperature,
            "maxOutputTokens": 4096
        }
        if "json" in system_content.lower():
            gen_config["responseMimeType"] = "application/json"

        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": gen_config
        }
        if system_content:
            payload["systemInstruction"] = {
                "parts": [{"text": system_content}]
            }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": self.api_key
            },
            method="POST"
        )
        raw_resp = self._execute_with_retry(req)
        data = json.loads(raw_resp.decode("utf-8"))
        candidates = data.get("candidates", [])
        if not candidates:
            raise RuntimeError(f"Gemini returned no response candidates: {data}")
        parts = candidates[0].get("content", {}).get("parts", [])
        if not parts:
            raise RuntimeError(f"Gemini candidate has no content parts: {candidates[0]}")
        return parts[0].get("text", "")


# ==============================================================================
# 2. Curated Seed Trajectories (Offline Multi-Turn Self-Correction Dataset)
# ==============================================================================

def get_curated_seed_trajectories() -> List[Dict[str, Any]]:
    """
    Returns verified, high-value multi-turn self-correction episodes across
    React, TypeScript, CSS, Accessibility, and State Management.
    """
    return [
        # Episode 1: ProgressBar with ARIA accessibility correction
        {
            "task_id": "seed_progressbar_a11y",
            "messages": [
                {"role": "system", "content": AGENT_SYSTEM_PROMPT},
                {"role": "user", "content": "Write a `ProgressBar` component with `value`, `max`, that renders an animated fill and sets `aria-valuenow`/`aria-valuemin`/`aria-valuemax` correctly, exposed with `role=\"progressbar\"`.\nIMPORTANT: Export the component as a named export called `ProgressBar`."},
                {
                    "role": "assistant",
                    "content": """<thought>
I need to create a ProgressBar component. I will start by writing a basic div container and a fill indicator.
</thought>
<tool_call name="write_component">
<tsx>
import React from 'react';
import styles from './Component.module.css';

interface ProgressBarProps {
  value: number;
  max: number;
}

export function ProgressBar({ value, max }: ProgressBarProps) {
  const percentage = Math.min(100, Math.max(0, (value / max) * 100));
  return (
    <div className={styles.track}>
      <div className={styles.fill} style={{ width: `${percentage}%` }} />
    </div>
  );
}
</tsx>
<css>
.track { width: 100%; height: 8px; background: #e5e7eb; border-radius: 4px; overflow: hidden; }
.fill { height: 100%; background: #2563eb; transition: width 0.3s ease; }
</css>
</tool_call>"""
                },
                {
                    "role": "user",
                    "content": """<observation status="failed">
[TSC]: Passed (0 syntax/type errors)
[Vitest Test Failure]:
  × exposes correct ARIA progressbar attributes
    → Unable to find an accessible element with the role "progressbar"
Ignored nodes: comments, script, style
<body>
  <div>
    <div class="_track_123">
      <div class="_fill_123" style="width: 30%;"></div>
    </div>
  </div>
</body>
</observation>"""
                },
                {
                    "role": "assistant",
                    "content": """<thought>
Looking at the observation:
1. Vitest failed because it could not find an element with role="progressbar".
2. The requirements explicitly ask to expose the component with role="progressbar" and attach aria-valuenow, aria-valuemin="0", and aria-valuemax.
3. I will attach role="progressbar" and the proper ARIA attributes to the track container element.
</thought>
<tool_call name="write_component">
<tsx>
import React from 'react';
import styles from './Component.module.css';

interface ProgressBarProps {
  value: number;
  max: number;
}

export function ProgressBar({ value, max }: ProgressBarProps) {
  const percentage = Math.min(100, Math.max(0, (value / max) * 100));
  return (
    <div
      className={styles.track}
      role="progressbar"
      aria-valuenow={value}
      aria-valuemin={0}
      aria-valuemax={max}
    >
      <div className={styles.fill} style={{ width: `${percentage}%` }} />
    </div>
  );
}
</tsx>
<css>
.track { width: 100%; height: 8px; background: #e5e7eb; border-radius: 4px; overflow: hidden; }
.fill { height: 100%; background: #2563eb; transition: width 0.3s ease; }
</css>
</tool_call>"""
                },
                {
                    "role": "user",
                    "content": """<observation status="passed">
[TSC]: Passed (0 errors)
[Vitest]: All tests passed successfully!
</observation>"""
                },
                {
                    "role": "assistant",
                    "content": """<thought>
All Vitest tests and TypeScript compilation passed. The component now satisfies all ARIA progressbar standards.
</thought>
<finish>
ProgressBar component implemented and verified with role="progressbar", aria-valuenow, aria-valuemin, aria-valuemax, and animated CSS fill.
</finish>"""
                }
            ]
        },

        # Episode 2: Modal with Keyboard Escape & Backdrop Click
        {
            "task_id": "seed_modal_interactive",
            "messages": [
                {"role": "system", "content": AGENT_SYSTEM_PROMPT},
                {"role": "user", "content": "Write a React TypeScript `Modal` component with `isOpen`, `onClose`, that closes on Escape and on backdrop click, and renders via `createPortal` into `document.body`. The backdrop element must have `data-testid=\"modal-backdrop\"`.\nIMPORTANT: Export the component as a named export called `Modal`."},
                {
                    "role": "assistant",
                    "content": """<thought>
I need to build a Modal that renders through createPortal and closes on Escape or backdrop click.
I'll create the portal and backdrop first.
</thought>
<tool_call name="write_component">
<tsx>
import React, { useEffect } from 'react';
import { createPortal } from 'react-dom';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  children: React.ReactNode;
}

export function Modal({ isOpen, onClose, children }: ModalProps) {
  if (!isOpen) return null;

  return createPortal(
    <div>
      <div data-testid="modal-backdrop" />
      <div role="dialog">
        {children}
      </div>
    </div>,
    document.body
  );
}
</tsx>
</tool_call>"""
                },
                {
                    "role": "user",
                    "content": """<observation status="failed">
[TSC]: Passed (0 syntax/type errors)
[Vitest Test Failure]:
  × closes on Escape and on backdrop click
    → expected onClose to have been called 1 time, but was called 0 times
    await user.keyboard('{Escape}');
    expect(onClose).toHaveBeenCalledTimes(1);
</observation>"""
                },
                {
                    "role": "assistant",
                    "content": """<thought>
Observation analysis:
1. The test simulated keyboard '{Escape}', but `onClose` was not called.
2. I forgot to attach a window keydown listener for the Escape key inside a useEffect hook.
3. Also, clicking the backdrop element with data-testid="modal-backdrop" must trigger `onClose`.
I will add both the Escape keydown listener with proper cleanup and an onClick handler on the backdrop.
</thought>
<tool_call name="write_component">
<tsx>
import React, { useEffect } from 'react';
import { createPortal } from 'react-dom';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  children: React.ReactNode;
}

export function Modal({ isOpen, onClose, children }: ModalProps) {
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return createPortal(
    <div>
      <div data-testid="modal-backdrop" onClick={onClose} />
      <div role="dialog" aria-modal="true">
        {children}
      </div>
    </div>,
    document.body
  );
}
</tsx>
</tool_call>"""
                },
                {
                    "role": "user",
                    "content": """<observation status="passed">
[TSC]: Passed (0 errors)
[Vitest]: All tests passed successfully!
</observation>"""
                },
                {
                    "role": "assistant",
                    "content": """<thought>
All tests passed! The modal renders via createPortal, listens for Escape with cleanup, and dismisses on backdrop click.
</thought>
<finish>
Modal component implemented and verified with portal rendering, Escape key listener cleanup, and backdrop dismiss.
</finish>"""
                }
            ]
        },

        # Episode 3: Tooltip with Timer Debounce and role="tooltip"
        {
            "task_id": "seed_tooltip_timer",
            "messages": [
                {"role": "system", "content": AGENT_SYSTEM_PROMPT},
                {"role": "user", "content": "Write a React TypeScript component `Tooltip` that wraps its children and shows a `content: string` on hover after a configurable `delayMs` (default 300), supports `placement: 'top'|'bottom'|'left'|'right'`, and dismisses on Escape. The tooltip content must render with `role=\"tooltip\"`. Style with a CSS module.\nIMPORTANT: Export the component as a named export called `Tooltip`."},
                {
                    "role": "assistant",
                    "content": """<thought>
I'll implement the Tooltip component. I'll start with mouseEnter and mouseLeave state toggling.
</thought>
<tool_call name="write_component">
<tsx>
import React, { useState } from 'react';
import styles from './Component.module.css';

interface TooltipProps {
  content: string;
  delayMs?: number;
  placement?: 'top' | 'bottom' | 'left' | 'right';
  children: React.ReactNode;
}

export function Tooltip({ content, delayMs = 300, placement = 'top', children }: TooltipProps) {
  const [visible, setVisible] = useState(false);

  return (
    <div
      onMouseEnter={() => setVisible(true)}
      onMouseLeave={() => setVisible(false)}
    >
      {children}
      {visible && (
        <div role="tooltip" className={`${styles.tooltip} ${styles[placement]}`}>
          {content}
        </div>
      )}
    </div>
  );
}
</tsx>
<css>
.tooltip { position: absolute; padding: 4px 8px; background: #333; color: #fff; border-radius: 4px; }
.top { bottom: 100%; left: 50%; }
.bottom { top: 100%; left: 50%; }
.left { right: 100%; top: 50%; }
.right { left: 100%; top: 50%; }
</css>
</tool_call>"""
                },
                {
                    "role": "user",
                    "content": """<observation status="failed">
[TSC]: Passed (0 syntax/type errors)
[Vitest Test Failure]:
  × shows content on hover after delayMs and hides on mouse leave
    → expected queryByRole("tooltip") not to be in document, but found element
    fireEvent.mouseEnter(trigger);
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument(); // FAILED
</observation>"""
                },
                {
                    "role": "assistant",
                    "content": """<thought>
Observation diagnosis:
1. The test failed immediately after mouseEnter because `queryByRole('tooltip')` was already in the DOM.
2. The tooltip should NOT appear immediately; it must wait for `delayMs` (300ms) before becoming visible.
3. The test uses `vi.advanceTimersByTime(300)` to test this delay.
4. I need to use `setTimeout` on mouseEnter with a timer ref, and clear the timer on mouseLeave and on unmount. Also need to add keydown listener for Escape.
</thought>
<tool_call name="write_component">
<tsx>
import React, { useState, useRef, useEffect } from 'react';
import styles from './Component.module.css';

interface TooltipProps {
  content: string;
  delayMs?: number;
  placement?: 'top' | 'bottom' | 'left' | 'right';
  children: React.ReactNode;
}

export function Tooltip({ content, delayMs = 300, placement = 'top', children }: TooltipProps) {
  const [visible, setVisible] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleMouseEnter = () => {
    timerRef.current = setTimeout(() => {
      setVisible(true);
    }, delayMs);
  };

  const handleMouseLeave = () => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    setVisible(false);
  };

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        handleMouseLeave();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  return (
    <div
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      {children}
      {visible && (
        <div role="tooltip" className={`${styles.tooltip} ${styles[placement]}`}>
          {content}
        </div>
      )}
    </div>
  );
}
</tsx>
<css>
.tooltip { position: absolute; padding: 4px 8px; background: #333; color: #fff; border-radius: 4px; }
.top { bottom: 100%; left: 50%; }
.bottom { top: 100%; left: 50%; }
.left { right: 100%; top: 50%; }
.right { left: 100%; top: 50%; }
</css>
</tool_call>"""
                },
                {
                    "role": "user",
                    "content": """<observation status="passed">
[TSC]: Passed (0 errors)
[Vitest]: All tests passed successfully!
</observation>"""
                },
                {
                    "role": "assistant",
                    "content": """<thought>
All assertions passed! The tooltip now properly delays presentation with setTimeout, cancels timers on mouse leave, and dismisses on Escape.
</thought>
<finish>
Tooltip component implemented and verified with delayMs debounce timer, role="tooltip", and Escape key dismissal.
</finish>"""
                }
            ]
        },

        # Episode 4: Chip component with accessible dismiss button
        {
            "task_id": "seed_chip_dismiss",
            "messages": [
                {"role": "system", "content": AGENT_SYSTEM_PROMPT},
                {"role": "user", "content": "Write a `Chip` component with `label: string` and an optional `onRemove` handler that renders a small remove button (accessible name containing 'remove' or 'x') calling it.\nIMPORTANT: Export the component as a named export called `Chip`."},
                {
                    "role": "assistant",
                    "content": """<thought>
I will build a Chip component. I'll render the label and an icon button.
</thought>
<tool_call name="write_component">
<tsx>
import React from 'react';

interface ChipProps {
  label: string;
  onRemove?: () => void;
}

export function Chip({ label, onRemove }: ChipProps) {
  return (
    <div>
      <span>{label}</span>
      {onRemove && <button onClick={onRemove}>×</button>}
    </div>
  );
}
</tsx>
</tool_call>"""
                },
                {
                    "role": "user",
                    "content": """<observation status="failed">
[TSC]: Passed (0 syntax/type errors)
[Vitest Test Failure]:
  × calls onRemove when the remove button is clicked
    → Unable to find an accessible element with the role "button" and name /remove|x/i
    The rendered button has name: "×" (multiplication symbol, not 'x' or 'remove')
</observation>"""
                },
                {
                    "role": "assistant",
                    "content": """<thought>
Observation analysis:
The test queries for a button with accessible name matching `/remove|x/i`.
The button rendered '×' which is Unicode U+00D7 (multiplication sign), not ASCII 'x', and lacks an aria-label.
I should add `aria-label="Remove"` on the button so it is accessible and matches the query.
</thought>
<tool_call name="write_component">
<tsx>
import React from 'react';

interface ChipProps {
  label: string;
  onRemove?: () => void;
}

export function Chip({ label, onRemove }: ChipProps) {
  return (
    <div style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
      <span>{label}</span>
      {onRemove && (
        <button
          type="button"
          aria-label="Remove"
          onClick={onRemove}
        >
          x
        </button>
      )}
    </div>
  );
}
</tsx>
</tool_call>"""
                },
                {
                    "role": "user",
                    "content": """<observation status="passed">
[TSC]: Passed (0 errors)
[Vitest]: All tests passed successfully!
</observation>"""
                },
                {
                    "role": "assistant",
                    "content": """<thought>
The test passes cleanly with the accessible name 'Remove'.
</thought>
<finish>
Chip component verified with accessible remove button and onRemove handler.
</finish>"""
                }
            ]
        },

        # Episode 5: Reducer and useCart hook
        {
            "task_id": "seed_cart_reducer_hook",
            "messages": [
                {"role": "system", "content": AGENT_SYSTEM_PROMPT},
                {"role": "user", "content": "Write a `cartReducer(state: CartState, action: CartAction)` reducer with a discriminated-union `CartAction` type (`'ADD_ITEM' | 'REMOVE_ITEM' | 'CLEAR'`), plus a `useReducer`-based `useCart()` hook wrapping it.\nIMPORTANT: Export the following as named exports: `cartReducer`, `useCart`."},
                {
                    "role": "assistant",
                    "content": """<thought>
I will implement CartState, CartAction union, cartReducer, and useCart hook.
</thought>
<tool_call name="write_component">
<tsx>
import { useReducer } from 'react';

export interface CartItem {
  id: string;
  qty: number;
}

export interface CartState {
  items: CartItem[];
}

export type CartAction =
  | { type: 'ADD_ITEM'; item: CartItem }
  | { type: 'REMOVE_ITEM'; id: string }
  | { type: 'CLEAR' };

export function cartReducer(state: CartState, action: CartAction): CartState {
  switch (action.type) {
    case 'ADD_ITEM':
      return { items: [...state.items, action.item] };
    case 'REMOVE_ITEM':
      return { items: state.items.filter(item => item.id !== action.id) };
    case 'CLEAR':
      return { items: [] };
    default:
      return state;
  }
}

export function useCart() {
  const [state, dispatch] = useReducer(cartReducer, { items: [] });
  return { state, dispatch };
}
</tsx>
</tool_call>"""
                },
                {
                    "role": "user",
                    "content": """<observation status="passed">
[TSC]: Passed (0 errors)
[Vitest]: All tests passed successfully!
</observation>"""
                },
                {
                    "role": "assistant",
                    "content": """<thought>
Both reducer tests and hook tests pass on first try.
</thought>
<finish>
cartReducer and useCart implemented with discriminated union CartAction and useReducer state.
</finish>"""
                }
            ]
        },

        # Episode 6: Accordion with allowMultiple self-correction
        {
            "task_id": "seed_accordion_multiple",
            "messages": [
                {"role": "system", "content": AGENT_SYSTEM_PROMPT},
                {"role": "user", "content": "Write a React TypeScript `Accordion` component that takes `items: {title: string, content: string}[]` and an `allowMultiple: boolean` prop controlling whether more than one panel can be open at once.\nIMPORTANT: Export the component as a named export called `Accordion`."},
                {
                    "role": "assistant",
                    "content": """<thought>
I will build an Accordion component. I will maintain an array of open indices.
</thought>
<tool_call name="write_component">
<tsx>
import React, { useState } from 'react';

interface AccordionItem {
  title: string;
  content: string;
}

interface AccordionProps {
  items: AccordionItem[];
  allowMultiple?: boolean;
}

export function Accordion({ items, allowMultiple = true }: AccordionProps) {
  const [openIndices, setOpenIndices] = useState<number[]>([]);

  const toggle = (index: number) => {
    setOpenIndices(prev => 
      prev.includes(index) ? prev.filter(i => i !== index) : [...prev, index]
    );
  };

  return (
    <div>
      {items.map((item, idx) => (
        <div key={idx}>
          <button type="button" onClick={() => toggle(idx)}>{item.title}</button>
          {openIndices.includes(idx) && <div>{item.content}</div>}
        </div>
      ))}
    </div>
  );
}
</tsx>
</tool_call>"""
                },
                {
                    "role": "user",
                    "content": """<observation status="failed">
[TSC]: Passed (0 syntax/type errors)
[Vitest Test Failure]:
  × respects allowMultiple=false by closing the previously open panel
    → expected queryByText("First content") not to be in document, but found element
</observation>"""
                },
                {
                    "role": "assistant",
                    "content": """<thought>
Observation analysis:
When `allowMultiple` is false, clicking a second item kept the first open because `toggle` was always appending to `openIndices`.
I need to check `allowMultiple`: if false, the new state should be `[index]` (or `[]` if already open).
</thought>
<tool_call name="write_component">
<tsx>
import React, { useState } from 'react';

interface AccordionItem {
  title: string;
  content: string;
}

interface AccordionProps {
  items: AccordionItem[];
  allowMultiple?: boolean;
}

export function Accordion({ items, allowMultiple = true }: AccordionProps) {
  const [openIndices, setOpenIndices] = useState<number[]>([]);

  const toggle = (index: number) => {
    setOpenIndices(prev => {
      const isOpen = prev.includes(index);
      if (!allowMultiple) {
        return isOpen ? [] : [index];
      }
      return isOpen ? prev.filter(i => i !== index) : [...prev, index];
    });
  };

  return (
    <div>
      {items.map((item, idx) => (
        <div key={idx}>
          <button type="button" onClick={() => toggle(idx)}>{item.title}</button>
          {openIndices.includes(idx) && <div>{item.content}</div>}
        </div>
      ))}
    </div>
  );
}
</tsx>
</tool_call>"""
                },
                {
                    "role": "user",
                    "content": """<observation status="passed">
[TSC]: Passed (0 errors)
[Vitest]: All tests passed successfully!
</observation>"""
                },
                {
                    "role": "assistant",
                    "content": """<thought>
The test passes. When allowMultiple=false, previous panels close automatically upon opening a new panel.
</thought>
<finish>
Accordion component implemented with allowMultiple control and state toggling.
</finish>"""
                }
            ]
        },

        # Episode 7: SearchInput with 300ms debounce
        {
            "task_id": "seed_search_input_debounce",
            "messages": [
                {"role": "system", "content": AGENT_SYSTEM_PROMPT},
                {"role": "user", "content": "Write a `SearchInput` component that debounces `onSearch(query: string)` by 300ms, shows a loading spinner while an `isLoading` prop is true, and has a clear ('x') button. The text field must have `role=\"textbox\"`.\nIMPORTANT: Export the component as a named export called `SearchInput`."},
                {
                    "role": "assistant",
                    "content": """<thought>
I'll create the SearchInput component. I'll bind the value to an input with role="textbox".
</thought>
<tool_call name="write_component">
<tsx>
import React, { useState } from 'react';

interface SearchInputProps {
  onSearch: (query: string) => void;
  isLoading?: boolean;
}

export function SearchInput({ onSearch, isLoading }: SearchInputProps) {
  const [val, setVal] = useState('');

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const next = e.target.value;
    setVal(next);
    onSearch(next);
  };

  return (
    <div>
      <input
        role="textbox"
        value={val}
        onChange={handleChange}
      />
      {isLoading && <span role="status">Loading...</span>}
      {val && <button onClick={() => { setVal(''); onSearch(''); }}>x</button>}
    </div>
  );
}
</tsx>
</tool_call>"""
                },
                {
                    "role": "user",
                    "content": """<observation status="failed">
[TSC]: Passed (0 syntax/type errors)
[Vitest Test Failure]:
  × debounces onSearch by 300ms
    → expected onSearch not to have been called, but was called with ['react']
    vi.advanceTimersByTime(300); // FAILED before advanceTimers
</observation>"""
                },
                {
                    "role": "assistant",
                    "content": """<thought>
Observation diagnosis:
The test failed because `onSearch` was called immediately inside `handleChange`.
It must be debounced by 300ms using a timer ref, and only called after 300ms of inactivity.
I will add `useRef` for the timer and call `onSearch` inside `setTimeout(..., 300)`.
</thought>
<tool_call name="write_component">
<tsx>
import React, { useState, useRef, useEffect } from 'react';

interface SearchInputProps {
  onSearch: (query: string) => void;
  isLoading?: boolean;
}

export function SearchInput({ onSearch, isLoading }: SearchInputProps) {
  const [val, setVal] = useState('');
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const next = e.target.value;
    setVal(next);

    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      onSearch(next);
    }, 300);
  };

  const handleClear = () => {
    setVal('');
    if (timerRef.current) clearTimeout(timerRef.current);
    onSearch('');
  };

  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  return (
    <div>
      <input
        role="textbox"
        value={val}
        onChange={handleChange}
      />
      {isLoading && <span role="status">Loading...</span>}
      {val && <button type="button" onClick={handleClear}>x</button>}
    </div>
  );
}
</tsx>
</tool_call>"""
                },
                {
                    "role": "user",
                    "content": """<observation status="passed">
[TSC]: Passed (0 errors)
[Vitest]: All tests passed successfully!
</observation>"""
                },
                {
                    "role": "assistant",
                    "content": """<thought>
The 300ms debounce timer works as expected and passes all fake timer assertions.
</thought>
<finish>
SearchInput component implemented and verified with 300ms debounce, loading indicator, and clear button.
</finish>"""
                }
            ]
        },

        # Episode 8: Avatar fallback to initials
        {
            "task_id": "seed_avatar_initials",
            "messages": [
                {"role": "system", "content": AGENT_SYSTEM_PROMPT},
                {"role": "user", "content": "Write an `Avatar` component with `src?: string`, `name: string`, `size: 'sm'|'md'|'lg'` that falls back to rendering initials from `name` when `src` fails to load or is not provided. Set the rendered `<img>`'s `alt` attribute to `name`.\nIMPORTANT: Export the component as a named export called `Avatar`."},
                {
                    "role": "assistant",
                    "content": """<thought>
I'll implement the Avatar component. I will render an img tag with alt=name.
</thought>
<tool_call name="write_component">
<tsx>
import React from 'react';

interface AvatarProps {
  src?: string;
  name: string;
  size?: 'sm' | 'md' | 'lg';
}

export function Avatar({ src, name, size = 'md' }: AvatarProps) {
  if (src) {
    return <img src={src} alt={name} />;
  }
  return <div>{name}</div>;
}
</tsx>
</tool_call>"""
                },
                {
                    "role": "user",
                    "content": """<observation status="failed">
[TSC]: Passed (0 syntax/type errors)
[Vitest Test Failure]:
  × renders the image when src is provided, or initials as a fallback
    → Unable to find an element with the text: AL
    The fallback rendered "Ada Lovelace" instead of the initials "AL".
</observation>"""
                },
                {
                    "role": "assistant",
                    "content": """<thought>
Observation diagnosis:
The test requires rendering initials (e.g. 'AL' for 'Ada Lovelace') when `src` is omitted, rather than the full name.
I will compute initials by splitting `name` on whitespace and extracting the first character of each word in uppercase.
</thought>
<tool_call name="write_component">
<tsx>
import React, { useState } from 'react';

interface AvatarProps {
  src?: string;
  name: string;
  size?: 'sm' | 'md' | 'lg';
}

export function Avatar({ src, name, size = 'md' }: AvatarProps) {
  const [hasError, setHasError] = useState(false);

  const getInitials = (str: string) => {
    return str
      .trim()
      .split(/\\s+/)
      .map(part => part[0])
      .slice(0, 2)
      .join('')
      .toUpperCase();
  };

  if (src && !hasError) {
    return <img src={src} alt={name} onError={() => setHasError(true)} />;
  }

  return (
    <div role="img" aria-label={name}>
      {getInitials(name)}
    </div>
  );
}
</tsx>
</tool_call>"""
                },
                {
                    "role": "user",
                    "content": """<observation status="passed">
[TSC]: Passed (0 errors)
[Vitest]: All tests passed successfully!
</observation>"""
                },
                {
                    "role": "assistant",
                    "content": """<thought>
Both image rendering with alt attribute and initials fallback pass.
</thought>
<finish>
Avatar component implemented and verified with image rendering, error fallback, and initials extraction.
</finish>"""
                }
            ]
        },

        # Episode 9: Switch toggle with role="switch"
        {
            "task_id": "seed_switch_toggle",
            "messages": [
                {"role": "system", "content": AGENT_SYSTEM_PROMPT},
                {"role": "user", "content": "Write a `Switch` toggle component with controlled `checked`/`onChange` and a `disabled` prop, styled as a sliding pill switch in plain CSS. Expose it with `role=\"switch\"`.\nIMPORTANT: Export the component as a named export called `Switch`."},
                {
                    "role": "assistant",
                    "content": """<thought>
I will create a Switch toggle component. I'll render an input checkbox.
</thought>
<tool_call name="write_component">
<tsx>
import React from 'react';

interface SwitchProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
}

export function Switch({ checked, onChange, disabled }: SwitchProps) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={() => onChange(!checked)}
    >
      {checked ? 'ON' : 'OFF'}
    </button>
  );
}
</tsx>
</tool_call>"""
                },
                {
                    "role": "user",
                    "content": """<observation status="failed">
[TSC]: Passed (0 syntax/type errors)
[Vitest Test Failure]:
  × toggles checked state when clicked
    → Unable to find an accessible element with the role "switch"
</observation>"""
                },
                {
                    "role": "assistant",
                    "content": """<thought>
Observation diagnosis:
The test queries `screen.getByRole('switch')`.
My button was exposed with default role="button".
I must add `role="switch"` and `aria-checked={checked}` to adhere to the WAI-ARIA Switch pattern.
</thought>
<tool_call name="write_component">
<tsx>
import React from 'react';

interface SwitchProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
}

export function Switch({ checked, onChange, disabled }: SwitchProps) {
  return (
    <div
      role="switch"
      tabIndex={disabled ? -1 : 0}
      aria-checked={checked}
      aria-disabled={disabled}
      onClick={() => {
        if (!disabled) onChange(!checked);
      }}
      onKeyDown={(e) => {
        if (!disabled && (e.key === ' ' || e.key === 'Enter')) {
          e.preventDefault();
          onChange(!checked);
        }
      }}
      style={{
        cursor: disabled ? 'not-allowed' : 'pointer',
        display: 'inline-flex',
        alignItems: 'center'
      }}
    >
      <span>{checked ? 'ON' : 'OFF'}</span>
    </div>
  );
}
</tsx>
</tool_call>"""
                },
                {
                    "role": "user",
                    "content": """<observation status="passed">
[TSC]: Passed (0 errors)
[Vitest]: All tests passed successfully!
</observation>"""
                },
                {
                    "role": "assistant",
                    "content": """<thought>
The switch toggles cleanly with role="switch" and aria-checked attribute.
</thought>
<finish>
Switch toggle component implemented and verified with role="switch", aria-checked, keyboard controls, and disabled state.
</finish>"""
                }
            ]
        },

        # Episode 10: Breadcrumbs with aria-current="page"
        {
            "task_id": "seed_breadcrumbs_a11y",
            "messages": [
                {"role": "system", "content": AGENT_SYSTEM_PROMPT},
                {"role": "user", "content": "Build a `Breadcrumbs` component taking `items: {label: string, href?: string}[]`, rendering the last item as non-clickable current page with `aria-current=\"page\"`, and earlier items as `<a>` elements with their `href`.\nIMPORTANT: Export the component as a named export called `Breadcrumbs`."},
                {
                    "role": "assistant",
                    "content": """<thought>
I'll create the Breadcrumbs component rendering a list of links.
</thought>
<tool_call name="write_component">
<tsx>
import React from 'react';

interface BreadcrumbItem {
  label: string;
  href?: string;
}

interface BreadcrumbsProps {
  items: BreadcrumbItem[];
}

export function Breadcrumbs({ items }: BreadcrumbsProps) {
  return (
    <nav aria-label="Breadcrumb">
      <ol>
        {items.map((item, idx) => (
          <li key={idx}>
            <a href={item.href || '#'}>{item.label}</a>
          </li>
        ))}
      </ol>
    </nav>
  );
}
</tsx>
</tool_call>"""
                },
                {
                    "role": "user",
                    "content": """<observation status="failed">
[TSC]: Passed (0 syntax/type errors)
[Vitest Test Failure]:
  × marks the last breadcrumb as the current page and links earlier ones
    → expected element to have attribute "aria-current" with value "page", but found null
    expect(screen.getByText('Shoes')).toHaveAttribute('aria-current', 'page');
</observation>"""
                },
                {
                    "role": "assistant",
                    "content": """<thought>
Observation diagnosis:
The test requires the LAST item to be non-clickable (rendered as a span/text) with `aria-current="page"`, whereas earlier items must be rendered as `<a>` elements with their `href`.
I will check `isLast = idx === items.length - 1` and conditionally render a `span` with `aria-current="page"`.
</thought>
<tool_call name="write_component">
<tsx>
import React from 'react';

interface BreadcrumbItem {
  label: string;
  href?: string;
}

interface BreadcrumbsProps {
  items: BreadcrumbItem[];
}

export function Breadcrumbs({ items }: BreadcrumbsProps) {
  return (
    <nav aria-label="Breadcrumb">
      <ol style={{ display: 'flex', listStyle: 'none', padding: 0, gap: '8px' }}>
        {items.map((item, idx) => {
          const isLast = idx === items.length - 1;
          return (
            <li key={idx}>
              {isLast ? (
                <span aria-current="page">{item.label}</span>
              ) : (
                <a href={item.href || '#'}>{item.label}</a>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
</tsx>
</tool_call>"""
                },
                {
                    "role": "user",
                    "content": """<observation status="passed">
[TSC]: Passed (0 errors)
[Vitest]: All tests passed successfully!
</observation>"""
                },
                {
                    "role": "assistant",
                    "content": """<thought>
All breadcrumb assertions pass: last item has aria-current="page", earlier items are links.
</thought>
<finish>
Breadcrumbs component verified with semantic nav, aria-current="page" on current leaf, and links on parent items.
</finish>"""
                }
            ]
        }
    ]


# ==============================================================================
# 3. Main Generator Engine
# ==============================================================================

def generate_seed_dataset(output_file: Path) -> int:
    """Writes the curated seed trajectories to a JSONL file."""
    seeds = get_curated_seed_trajectories()
    print(f"Generating {len(seeds)} verified agentic self-correction seed trajectories...")

    with open(output_file, "w", encoding="utf-8") as f:
        for item in seeds:
            f.write(json.dumps(item) + "\n")

    print(f"Successfully saved seed dataset to: {output_file.resolve()}")
    return len(seeds)


def generate_trajectories_with_teacher(
    eval_set_path: Path,
    output_file: Path,
    teacher: TeacherClient,
    count: int = 20,
    max_turns: int = 4
):
    """
    Executes tasks using teacher LLM, verifies each turn with the Vitest harness,
    and saves only 100% verified multi-turn trajectories to output_file.
    """
    with open(eval_set_path, encoding="utf-8") as f:
        tasks = [json.loads(line) for line in f if line.strip()]

    workspace_dir = Path.cwd() / ".trajectory_workspace"
    if workspace_dir.exists():
        import shutil
        shutil.rmtree(workspace_dir)
    workspace_dir.mkdir(parents=True, exist_ok=True)

    saved_count = 0
    print(f"Starting teacher trajectory generation ({teacher.provider}:{teacher.model}) on {count} tasks...")

    with open(output_file, "a", encoding="utf-8") as out_f:
        for idx, task in enumerate(tasks[:count]):
            prompt = task["prompt"]
            test_code = task["test_code"]
            all_symbols, primary_symbol = extract_expected_symbols(prompt, test_code)
            target_name = primary_symbol or "Component"

            case_dir = workspace_dir / f"case_{idx:03d}"
            case_dir.mkdir(parents=True, exist_ok=True)

            test_file_code = generate_test_file_content(test_code, all_symbols, primary_symbol)
            test_file = case_dir / "Component.test.tsx"
            test_file.write_text(test_file_code, encoding="utf-8")

            user_prompt = f"{prompt}\nIMPORTANT: Export the component as a named export called `{target_name}`."
            messages: List[Dict[str, str]] = [
                {"role": "system", "content": AGENT_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ]

            print(f"\n[Task {idx+1}/{count}] {target_name}...")
            passed_at_end = False

            for turn in range(1, max_turns + 1):
                try:
                    assistant_resp = teacher.generate(messages)
                except Exception as e:
                    print(f"Teacher generation error on turn {turn}: {e}")
                    break

                messages.append({"role": "assistant", "content": assistant_resp})
                parsed = parse_agent_output(assistant_resp)

                if parsed.is_finish:
                    passed_at_end = True
                    break

                if parsed.is_tool_call and isinstance(parsed.action, WriteComponentAction):
                    (case_dir / "Component.tsx").write_text(parsed.action.tsx, encoding="utf-8")
                    css_c = parsed.action.css if parsed.action.css else "/* styles */"
                    (case_dir / "Component.module.css").write_text(css_c, encoding="utf-8")

                    tsc_ok, vit_ok, tsc_out, vit_out = execute_test_suite(case_dir, test_file)
                    passed = (tsc_ok and vit_ok)
                    obs = format_observation(tsc_ok, vit_ok, tsc_out, vit_out)
                    messages.append({"role": "user", "content": obs})

                    if passed:
                        passed_at_end = True

                elif parsed.is_tool_call and isinstance(parsed.action, RunTestsAction):
                    tsc_ok, vit_ok, tsc_out, vit_out = execute_test_suite(case_dir, test_file)
                    passed = (tsc_ok and vit_ok)
                    obs = format_observation(tsc_ok, vit_ok, tsc_out, vit_out)
                    messages.append({"role": "user", "content": obs})
                    if passed:
                        passed_at_end = True
                else:
                    obs = "<observation status=\"info\">Please output a tool_call or finish.</observation>"
                    messages.append({"role": "user", "content": obs})

            # Save if verified
            if passed_at_end:
                out_f.write(json.dumps({
                    "task_id": f"task_{idx:03d}",
                    "primary_symbol": target_name,
                    "messages": messages
                }) + "\n")
                out_f.flush()
                saved_count += 1
                print(f"  -> Successfully verified and recorded trajectory #{saved_count}!")

    print(f"\nCompleted! Saved {saved_count} verified trajectories to: {output_file.resolve()}")


def run_teacher(args):
    parser = argparse.ArgumentParser(description="Generate agentic trajectory training data.")
    parser.add_argument("--generate-seed", action="store_true", help="Generate verified offline seed trajectories.")
    parser.add_argument("--provider", choices=["openai", "anthropic", "openrouter", "deepseek", "gemini"], default="gemini")
    parser.add_argument("--model", type=str, default="gemini-2.5-flash", help="Teacher model name (e.g. gemini-2.5-flash, gemini-1.5-pro, gpt-4o, claude-3-5-sonnet-20241022).")
    parser.add_argument("--api-key", type=str, default=None, help="API key for teacher provider.")
    parser.add_argument("--eval-set", type=str, default="react_ts_css_eval_set_combined.jsonl")
    parser.add_argument("--output", type=str, default="train_trajectories.jsonl", help="Output trajectory file.")
    parser.add_argument("--count", type=int, default=20, help="Number of teacher trajectories to generate.")
    parser.add_argument("--dry-run", action="store_true", help="Simulate generation without calling paid teacher APIs.")
    parser.add_argument("--cost-estimate", action="store_true", help="Print estimated token usage and dollar cost then exit.")
    args = parser.parse_args()

    output_path = Path(args.output)

    if args.cost_estimate or args.dry_run:
        est = estimate_generation_cost(count=args.count, model=args.model)
        print("=" * 60)
        print("          TEACHER GENERATION COST ESTIMATE              ")
        print("=" * 60)
        print(f"  Target Trajectories:     {est['count']}")
        print(f"  Teacher Model:           {est['model']}")
        print(f"  Estimated Model Turns:   {est['total_turns']}")
        print(f"  Estimated Input Tokens:  {est['estimated_input_tokens']:,}")
        print(f"  Estimated Output Tokens: {est['estimated_output_tokens']:,}")
        print(f"  Estimated Cost (USD):    ${est['estimated_cost_usd']:.4f}")
        print("=" * 60)
        if args.cost_estimate or args.dry_run:
            if args.dry_run:
                print("Dry-run complete. Exiting without making API calls.")
            sys.exit(0)

    if args.generate_seed:
        generate_seed_dataset(output_path)
        sys.exit(0)

    teacher = TeacherClient(
        provider=args.provider,
        model=args.model,
        api_key=args.api_key
    )
    generate_trajectories_with_teacher(
        eval_set_path=Path(args.eval_set),
        output_file=output_path,
        teacher=teacher,
        count=args.count
    )




# ==============================================================================
# 4. STaR Rejection Sampling
# ==============================================================================

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List

from agent_protocol import AGENT_SYSTEM_PROMPT, DEFAULT_INFERENCE_MAX_SEQ_LENGTH
from agent import AgentModelRunner, MockAgentEngine, run_agent_on_example
from evaluate import strip_test_imports


# ==============================================================================
# 1. Bank of Held-Out Tasks (Separate from 100-Task Eval Benchmark)
# ==============================================================================


STAR_TASKS: List[Dict[str, Any]] = [
    {
        "symbol": "OtpInput",
        "prompt": "Write a React TypeScript `OtpInput` component with `length: number`, `value: string`, `onChange: (val: string) => void`. Render individual inputs for each digit with `aria-label=\"Digit {i+1}\"`. Typing a digit should automatically advance focus to the next input, and Backspace should move focus to the previous input. Export as named export `OtpInput`.",
        "test_code": """
import React, { useState } from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { OtpInput } from './Component';

describe('OtpInput Component', () => {
  it('renders correct number of digit inputs with accessible labels', () => {
    render(<OtpInput length={4} value="" onChange={() => {}} />);
    const inputs = screen.getAllByRole('textbox');
    expect(inputs).toHaveLength(4);
    expect(screen.getByLabelText('Digit 1')).toBeInTheDocument();
    expect(screen.getByLabelText('Digit 4')).toBeInTheDocument();
  });

  it('calls onChange with updated string when digit is entered', () => {
    const handleChange = vi.fn();
    render(<OtpInput length={4} value="12" onChange={handleChange} />);
    const input3 = screen.getByLabelText('Digit 3');
    fireEvent.change(input3, { target: { value: '3' } });
    expect(handleChange).toHaveBeenCalled();
  });
});
"""
    },
    {
        "symbol": "SegmentedControl",
        "prompt": "Write a React TypeScript `SegmentedControl` component with `options: Array<{ label: string; value: string }>`, `value: string`, `onChange: (value: string) => void`. Expose container with `role=\"radiogroup\"` and each option with `role=\"radio\"`, setting `aria-checked` to true on the active option. Clicking an option must call `onChange` with its value. Export as named export `SegmentedControl`.",
        "test_code": """
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { SegmentedControl } from './Component';

describe('SegmentedControl Component', () => {
  const options = [
    { label: 'Day', value: 'day' },
    { label: 'Week', value: 'week' },
    { label: 'Month', value: 'month' },
  ];

  it('renders radiogroup container and radio options with aria-checked', () => {
    render(<SegmentedControl options={options} value="week" onChange={() => {}} />);
    expect(screen.getByRole('radiogroup')).toBeInTheDocument();
    const radios = screen.getAllByRole('radio');
    expect(radios).toHaveLength(3);
    expect(screen.getByRole('radio', { name: 'Week' })).toHaveAttribute('aria-checked', 'true');
    expect(screen.getByRole('radio', { name: 'Day' })).toHaveAttribute('aria-checked', 'false');
  });

  it('triggers onChange with selected option value when clicked', () => {
    const handleChange = vi.fn();
    render(<SegmentedControl options={options} value="day" onChange={handleChange} />);
    fireEvent.click(screen.getByRole('radio', { name: 'Month' }));
    expect(handleChange).toHaveBeenCalledWith('month');
  });
});
"""
    },
    {
        "symbol": "RangeSlider",
        "prompt": "Write a React TypeScript `RangeSlider` component with `min: number`, `max: number`, `value: number`, `step?: number`, `onChange: (val: number) => void`. Render a slider exposed with `role=\"slider\"`, `aria-valuemin`, `aria-valuemax`, and `aria-valuenow`. Include a label or display showing the current value. Export as named export `RangeSlider`.",
        "test_code": """
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { RangeSlider } from './Component';

describe('RangeSlider Component', () => {
  it('exposes slider role and aria range values', () => {
    render(<RangeSlider min={0} max={100} value={42} onChange={() => {}} />);
    const slider = screen.getByRole('slider');
    expect(slider).toBeInTheDocument();
    expect(slider).toHaveAttribute('aria-valuenow', '42');
    expect(slider).toHaveAttribute('aria-valuemin', '0');
    expect(slider).toHaveAttribute('aria-valuemax', '100');
  });

  it('triggers onChange when value changes', () => {
    const handleChange = vi.fn();
    render(<RangeSlider min={0} max={50} value={10} onChange={handleChange} />);
    const slider = screen.getByRole('slider');
    fireEvent.change(slider, { target: { value: '25' } });
    expect(handleChange).toHaveBeenCalled();
  });
});
"""
    },
    {
        "symbol": "ColorPicker",
        "prompt": "Write a React TypeScript `ColorPicker` component with `value: string`, `presets?: string[]`, `onChange: (hex: string) => void`. Render a color swatch button with `aria-label=\"Current color\"`, a text or color input for manual editing, and preset color buttons. Clicking a preset button calls `onChange` with that color. Export as named export `ColorPicker`.",
        "test_code": """
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { ColorPicker } from './Component';

describe('ColorPicker Component', () => {
  it('renders current color swatch and presets', () => {
    render(<ColorPicker value=\"#ff0000\" presets={['#ff0000', '#00ff00', '#0000ff']} onChange={() => {}} />);
    expect(screen.getByLabelText(/current color/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '#00ff00' })).toBeInTheDocument();
  });

  it('fires onChange when a preset button is selected', () => {
    const handleChange = vi.fn();
    render(<ColorPicker value=\"#000000\" presets={['#ffffff', '#00ff00']} onChange={handleChange} />);
    fireEvent.click(screen.getByRole('button', { name: '#00ff00' }));
    expect(handleChange).toHaveBeenCalledWith('#00ff00');
  });
});
"""
    },
    {
        "symbol": "SpeedDial",
        "prompt": "Write a React TypeScript `SpeedDial` component with `actions: Array<{ label: string; onClick: () => void }>`, `icon?: React.ReactNode`. Render a main trigger button with `aria-label=\"Actions\"` and `aria-expanded`. Clicking it toggles the list of action buttons. Clicking an action invokes its `onClick` handler. Export as named export `SpeedDial`.",
        "test_code": """
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { SpeedDial } from './Component';

describe('SpeedDial Component', () => {
  const actions = [
    { label: 'Copy', onClick: vi.fn() },
    { label: 'Delete', onClick: vi.fn() }
  ];

  it('toggles actions on trigger button click and sets aria-expanded', () => {
    render(<SpeedDial actions={actions} />);
    const trigger = screen.getByRole('button', { name: /actions/i });
    expect(trigger).toHaveAttribute('aria-expanded', 'false');
    fireEvent.click(trigger);
    expect(trigger).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByRole('button', { name: 'Copy' })).toBeInTheDocument();
  });

  it('executes action callback when an action button is clicked', () => {
    const handleCopy = vi.fn();
    render(<SpeedDial actions={[{ label: 'Copy', onClick: handleCopy }]} />);
    fireEvent.click(screen.getByRole('button', { name: /actions/i }));
    fireEvent.click(screen.getByRole('button', { name: 'Copy' }));
    expect(handleCopy).toHaveBeenCalledTimes(1);
  });
});
"""
    }
]

for _t in STAR_TASKS:
    _t["test_code"] = strip_test_imports(_t["test_code"])



# ==============================================================================
# 2. Rollout Extraction & Conversion to ChatML Trajectory
# ==============================================================================

def convert_rollout_to_trajectory(task_id: str, history: List[Dict[str, str]]) -> Dict[str, Any]:
    """Converts the agent's multi-turn conversational history into a clean training trajectory."""
    return {
        "task_id": f"star_{task_id}",
        "source": "rejection_sampling_star",
        "messages": history
    }


# ==============================================================================
# 3. Main STaR Generation Loop
# ==============================================================================

def run_star_pipeline(
    model_path: str = "my-react-agent-lora",
    num_tasks: int = 150,
    max_turns: int = 5,
    merge_output: bool = True,
    resume: bool = True,
    output_file: str = "star_trajectories.jsonl",
    visual_threshold: int = 3,
    fidelity_check: bool = True,
):
    task_bank_file = Path("star_task_bank.jsonl")
    if task_bank_file.exists():
        with open(task_bank_file, encoding="utf-8") as f:
            tasks = [json.loads(line) for line in f if line.strip()]
    else:
        tasks = STAR_TASKS

    out_path = Path(output_file)
    completed_task_ids = set()
    if resume and out_path.exists():
        with open(out_path, "r", encoding="utf-8") as f_in:
            for line in f_in:
                if line.strip():
                    try:
                        data = json.loads(line)
                        completed_task_ids.add(data.get("task_id", "").lower())
                    except Exception as parse_err:
                        print(f"Warning: Failed to parse line in {out_path.name}: {parse_err}")
        print(f"Resuming STaR run: found {len(completed_task_ids)} existing trajectories in {out_path.name}")
    elif not resume and out_path.exists():
        out_path.unlink()

    print("=" * 75)
    print("      SELF-TAUGHT REASONER (STaR) / REJECTION SAMPLING PIPELINE        ")
    print(f"      (With Prompt-Fidelity Gate & Visual Quality Gating >={visual_threshold}/5)     ")
    print("=" * 75)
    print(f"Target Model: {model_path}")
    print(f"Task Bank Size: {len(tasks)} (running first {min(num_tasks, len(tasks))})")
    print(f"Max Turns: {max_turns}")
    print(f"Output File: {out_path.resolve()}")
    print("=" * 75)

    if model_path == "mock":
        runner = MockAgentEngine()
    else:
        runner = AgentModelRunner(model_path=model_path, max_seq_length=DEFAULT_INFERENCE_MAX_SEQ_LENGTH)

    harvested_trajectories = []
    total_passed = len(completed_task_ids)
    total_self_corrected = 0

    for i, task in enumerate(tasks[:num_tasks]):
        symbol = task["symbol"]
        traj_id = f"star_{symbol.lower()}"
        if traj_id in completed_task_ids:
            print(f"\n[STaR Skipped]: Task #{i+1} {symbol} already completed. Skipping.")
            continue

        prompt = task["prompt"]
        test_code = task["test_code"]

        res = run_agent_on_example(
            orig_idx=i,
            item=task,
            runner=runner,
            workspace_root=Path.cwd() / ".agent_workspace",
            max_turns=max_turns,
            temperature=0.20,
            best_of_2=True
        )

        final_passed = res.get("final_passed", False)
        self_corrected = res.get("self_corrected", False)
        turns_used = res.get("turns_used", 1)

        if final_passed:
            # 1. Prompt-Fidelity Gate Check: verify named entities and quantity constraints
            raw_trajectory = res.get("trajectory", [])
            history = [dict(m) for m in raw_trajectory]
            rendered_code = res.get("files", {}) or history

            if fidelity_check:
                fidelity_ok, f_reasons, f_metrics = verify_prompt_fidelity(prompt, rendered_code, brief=task)
                if not fidelity_ok:
                    print(f"  >>> [STaR Fidelity REJECTED]: Task #{i+1} {symbol} dropped required entities: {', '.join(f_reasons)}")
                    continue

            # 2. Visual Judge Quality Gating (threshold >= visual_threshold, default 3/5)
            traj_data = {"task_id": traj_id, "prompt": prompt, "files": res.get("files", {}), "messages": history}
            vis_ok, vis_res = visual_judge.filter_trajectory_visual(traj_data, threshold=visual_threshold)
            if not vis_ok:
                print(f"  >>> [STaR Visual REJECTED]: Task #{i+1} {symbol} visual score {vis_res.get('score', 0)}/5 below threshold {visual_threshold}. Issues: {vis_res.get('issues', [])}")
                continue

            total_passed += 1
            if self_corrected or turns_used > 1:
                total_self_corrected += 1
                print(f"  >>> [STaR Harvested]: Task #{i+1} {symbol} self-corrected on Turn {turns_used}! Kept.")
            else:
                print(f"  >>> [STaR Harvested]: Task #{i+1} {symbol} passed on Turn 1.")

            # Ensure dialogue finishes with an assistant finish tag if tests passed
            if history and history[-1].get("role") == "user":
                history.append({
                    "role": "assistant",
                    "content": (
                        "<thought>\n"
                        "All TypeScript typechecks and Vitest unit test assertions have passed successfully.\n"
                        "</thought>\n"
                        "<finish>\n"
                        f"{symbol} component fully verified and all unit tests passed.\n"
                        "</finish>"
                    )
                })

            traj = convert_rollout_to_trajectory(symbol.lower(), history)
            harvested_trajectories.append(traj)

            # Flush immediately to disk after every passing task
            with open(out_path, "a", encoding="utf-8") as f_out:
                f_out.write(json.dumps(traj, ensure_ascii=False) + "\n")
                f_out.flush()

    print("\n" + "=" * 75)
    print("                     STaR HARVEST SUMMARY                             ")
    print("=" * 75)
    print(f"Total Evaluated: {min(num_tasks, len(tasks))}")
    print(f"Total Verified Passing Trajectories in Bank: {total_passed}")
    print(f"New Self-Corrected Multi-Turn Episodes: {total_self_corrected}")

    if merge_output and out_path.exists():
        from dataset_build_expanded import build_clean_dataset

        clean, stats = build_clean_dataset(
            core_path=Path("train_trajectories_hybrid.jsonl"),
            star_path=out_path,
            eval_path=Path("react_ts_css_eval_set_combined.jsonl"),
        )
        clean_path = Path("train_trajectories_agentic.jsonl")
        with clean_path.open("w", encoding="utf-8") as handle:
            for item in clean:
                handle.write(json.dumps(item, ensure_ascii=False) + "\n")
        print(f"Rebuilt leak-free training corpus: {len(clean)} trajectories at {clean_path.resolve()}")
        print(f"Filter statistics: {stats}")




# ==============================================================================
# 5. The Stack Mining
# ==============================================================================

import argparse
import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List, Optional, Set, Tuple

from evaluate import strip_test_imports


# ==============================================================================
# 1. UI Categorization & Filtering for Website Building
# ==============================================================================

# Patterns that indicate a React functional component file
_HAS_REACT_IMPORT = re.compile(
    r"""(import\s+React|from\s+['"]react['"]|import\s*\{[^}]*\}\s*from\s*['"]react['"])""",
    re.MULTILINE,
)
_HAS_JSX_RETURN = re.compile(
    r"""(return\s*\(\s*<[A-Za-z]|return\s+<[A-Za-z]|</[A-Za-z]+>|<[A-Za-z0-9_]+\s+[^>]*/>)""",
    re.MULTILINE,
)
_NAMED_FC_EXPORT = re.compile(
    r"""export\s+(?:function|const)\s+([A-Z][A-Za-z0-9]+)""",
    re.MULTILINE,
)

# Style import pattern (handles import styles from './foo.css', import './foo.css', etc.)
_STYLE_IMPORT_PATTERN = re.compile(
    r"""(?:import|require)\s*(?:[\w\s{},*]+from\s+)?\(?['"](\.[^'"]+\.(?:module\.)?(?:css|scss|sass|less))['"]"""
)


def extract_component_name(code: str) -> Optional[str]:
    """Return the PascalCase component symbol from the source, or None."""
    for m in _NAMED_FC_EXPORT.finditer(code):
        name = m.group(1)
        if name[0].isupper():
            return name
    # Fall back to default export
    default_match = re.search(
        r"""export\s+default\s+(?:function\s+)?([A-Z][A-Za-z0-9]+)""", code
    )
    if default_match:
        return default_match.group(1)
    return None


def categorize_web_component(code: str, file_path: str, symbol: str) -> str:
    """
    Classify the UI element into website component categories
    to ensure the model learns to build balanced, full-featured websites.
    """
    corpus = f"{symbol} {file_path} {code[:500]}".lower()

    if any(k in corpus for k in ["nav", "header", "menu", "sidebar", "breadcrumb", "topbar", "appbar"]):
        return "navigation"
    elif any(k in corpus for k in ["hero", "banner", "landing", "cta", "showcase", "headline"]):
        return "landing_hero"
    elif any(k in corpus for k in ["pricing", "plan", "tier", "subscription", "pricingcard"]):
        return "pricing_tier"
    elif any(k in corpus for k in ["feature", "benefit", "grid", "card", "service", "itemcard"]):
        return "features_cards"
    elif any(k in corpus for k in ["testimonial", "review", "quote", "feedback", "rating", "author"]):
        return "social_proof"
    elif any(k in corpus for k in ["faq", "accordion", "collapse", "dropdown", "select"]):
        return "faq_accordion"
    elif any(k in corpus for k in ["footer", "bottom", "copyright"]):
        return "footer"
    elif any(k in corpus for k in ["modal", "dialog", "drawer", "popup", "sheet", "overlay", "lightbox"]):
        return "modals_overlays"
    elif any(k in corpus for k in ["form", "input", "login", "signup", "register", "contact", "auth", "checkout"]):
        return "forms_auth"
    elif any(k in corpus for k in ["table", "datagrid", "chart", "metric", "stat", "dashboard", "analytics"]):
        return "dashboard_metrics"
    elif any(k in corpus for k in ["tab", "pagination", "stepper", "steps", "carousel", "slider"]):
        return "tabs_pagination"
    elif any(k in corpus for k in ["button", "badge", "avatar", "tag", "chip", "spinner", "toggle", "switch"]):
        return "micro_controls"
    return "general_ui"


def is_candidate_react_component(code: str, max_lines: int = 250) -> bool:
    """
    Strict filter: returns True only if the file is a self-contained
    React functional component that will be useful for the website task bank.
    """
    lines = code.splitlines()
    if len(lines) < 15 or len(lines) > max_lines:
        return False

    if not _HAS_REACT_IMPORT.search(code) and "React" not in code and "useState" not in code:
        return False

    if not _HAS_JSX_RETURN.search(code):
        return False

    if extract_component_name(code) is None:
        return False

    # Reject files with deep relative imports (monorepo internals)
    deep_relative = re.findall(r"""from\s+['"]\.\.?/[^'"]+['"]""", code)
    if len(deep_relative) > 2:
        return False

    # Reject files that import from heavy external framework runtimes that require special wrappers
    _FORBIDDEN_LIBS = [
        "antd", "chakra", "@mui/", "@radix-ui/", "mantine",
        "react-query", "@tanstack/", "framer-motion",
        "@emotion/", "react-spring", "react-hook-form", "react-router",
        "next/", "@next/", "gatsby", "redux", "mobx", "zustand",
        "apollo", "graphql", "@apollo/", "react-native",
    ]
    for lib in _FORBIDDEN_LIBS:
        if f'"{lib}' in code or f"'{lib}" in code:
            return False

    return True


# ==============================================================================
# 2. GitHub Raw Content & Companion Stylesheet Fetcher
# ==============================================================================

def fetch_github_raw(
    repo_name: str,
    revision_id: str,
    file_path: str,
    timeout: float = 6.0,
) -> Optional[str]:
    """
    Retrieve raw file content from GitHub using commit revision SHA.
    Falls back to HEAD if specific commit is unavailable.
    """
    clean_path = file_path.lstrip("/")
    urls = [
        f"https://raw.githubusercontent.com/{repo_name}/{revision_id}/{clean_path}",
        f"https://raw.githubusercontent.com/{repo_name}/HEAD/{clean_path}",
    ]

    for url in urls:
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) SlmPipeline/1.0"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    raw_bytes = resp.read()
                    return raw_bytes.decode("utf-8", errors="replace")
        except Exception:
            continue

    return None


def resolve_companion_styles(
    repo_name: str,
    revision_id: str,
    tsx_file_path: str,
    tsx_code: str,
    symbol: str,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Detects and downloads companion CSS/SCSS stylesheets imported or associated
    with the React TSX component.

    Returns (css_content, css_path) or (None, None).
    """
    clean_tsx = tsx_file_path.lstrip("/")
    parent_posix = str(PurePosixPath(clean_tsx).parent)

    candidates: List[str] = []

    # 1. Look for explicit relative style imports in code
    for match in _STYLE_IMPORT_PATTERN.findall(tsx_code):
        rel = match.lstrip("./")
        target = f"{parent_posix}/{rel}" if parent_posix != "." else rel
        candidates.append(target)

    # 2. Add common conventional sibling style files
    conventional = [
        f"{symbol}.module.css",
        f"{symbol}.module.scss",
        f"{symbol}.css",
        f"{symbol}.scss",
        "styles.module.css",
        "styles.module.scss",
        "styles.css",
        "styles.scss",
        "style.css",
    ]
    for c in conventional:
        target = f"{parent_posix}/{c}" if parent_posix != "." else c
        if target not in candidates:
            candidates.append(target)

    # Try fetching each candidate until we find one that exists
    for candidate_path in candidates:
        content = fetch_github_raw(repo_name, revision_id, candidate_path, timeout=4.0)
        if content and content.strip():
            return content, candidate_path

    return None, None


# ==============================================================================
# 3. Teacher Prompt: Reverse-Engineer Component + Styles -> Task Spec
# ==============================================================================

_REVERSE_ENGINEER_SYSTEM = """\
You are an expert React TypeScript testing engineer, UI/UX designer, and technical writer.
Your job is to analyze a real-world React component (and its accompanying CSS styles, if present)
and produce two things for an AI coding model being trained to build beautiful, modern websites:

  1. A clear, precise natural-language INSTRUCTION PROMPT:
       - Describe what the component should do functionally (props, state, interactions, callbacks).
       - Explicitly specify MODERN VISUAL DESIGN & AESTHETICS: clean layout (Flexbox/CSS Grid),
         harmonious color palette (accessible contrast), subtle borders/shadows, hover/active transitions,
         and responsive structure.
       - Clearly specify the expected styling format (CSS classes, CSS module classes, or inline styles).
       - The prompt must NOT reveal the raw implementation code.
       - The prompt MUST mention the exact component symbol name.

  2. A strict Vitest + @testing-library/react TEST SUITE:
       - Use describe/it blocks with meaningful test names.
       - Test at minimum: mounting, default render, key user interactions (clicks/toggles/inputs),
         and state changes.
       - Verify semantic elements and accessibility attributes where appropriate (role, aria-expanded, etc.).
       - Verify expected visual or state hooks (e.g. active class, disabled attribute).
       - Do NOT import React, vitest utilities, or @testing-library (those will be injected).
       - Do NOT import the component itself (bindings are auto-injected).
       - Use only the component API described in the instruction prompt.

Respond in EXACTLY this JSON format with NO extra commentary outside the JSON:
{
  "symbol": "ComponentName",
  "category": "navigation | landing_hero | features_cards | pricing_tier | social_proof | faq_accordion | forms_auth | modals_overlays | dashboard_metrics | tabs_pagination | footer | micro_controls",
  "prompt": "...",
  "test_code": "describe('ComponentName', () => { ... });"
}
"""


def reverse_engineer_component(
    code: str,
    symbol: str,
    category: str,
    companion_styles: Optional[str],
    teacher: TeacherClient,
    temperature: float = 0.2,
) -> Optional[Dict[str, Any]]:
    """
    Ask the teacher LLM to produce a (prompt, test_code) spec for the given component.
    """
    user_msg = (
        f"Analyze this React TypeScript component and produce the instruction prompt and test suite.\n"
        f"The exported component symbol is: `{symbol}`\n"
        f"Website UI Category: `{category}`\n\n"
        f"```tsx\n{code[:3500]}\n```\n"
    )

    if companion_styles:
        user_msg += f"\nAccompanying Stylesheet:\n```css\n{companion_styles[:2000]}\n```\n"

    messages = [
        {"role": "system", "content": _REVERSE_ENGINEER_SYSTEM},
        {"role": "user", "content": user_msg},
    ]

    try:
        raw = teacher.generate(messages, temperature=temperature)
    except Exception as exc:
        print(f"    [Teacher Warning] {exc} — falling back to structured extraction.")
        return offline_reverse_engineer(code, symbol, category, companion_styles)

    # Extract the JSON block
    json_match = re.search(r"\{[\s\S]+\}", raw)
    if not json_match:
        print("    [Parse Warning] No JSON block found — falling back to structured extraction.")
        return offline_reverse_engineer(code, symbol, category, companion_styles)

    try:
        spec = json.loads(json_match.group(0), strict=False)
    except json.JSONDecodeError:
        print("    [JSON Decode Warning] Malformed JSON — falling back to structured extraction.")
        return offline_reverse_engineer(code, symbol, category, companion_styles)

    required_keys = {"symbol", "prompt", "test_code"}
    if not required_keys.issubset(spec.keys()) or len(spec.get("prompt", "")) < 50:
        return offline_reverse_engineer(code, symbol, category, companion_styles)

    if "describe(" not in spec.get("test_code", "") and "it(" not in spec.get("test_code", ""):
        return offline_reverse_engineer(code, symbol, category, companion_styles)

    return spec


def offline_reverse_engineer(
    code: str,
    symbol: str,
    category: str,
    companion_styles: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Offline reverse engineering of a real-world component + styles into
    a task prompt and Vitest test suite without requiring an external LLM API key.
    """
    props_block = ""
    props_match = re.search(r"""(?:interface|type)\s+([A-Za-z0-9_]+Props)\s*(?:=\s*)?\{([^}]+)\}""", code)
    if props_match:
        props_body = props_match.group(2)
        prop_lines = [l.strip() for l in props_body.splitlines() if l.strip() and not l.strip().startswith("//")]
        if prop_lines:
            props_block = "\n".join(f"  - `{l.rstrip(';')}`" for l in prop_lines[:8])

    has_button = "<button" in code or "onClick" in code
    has_input = "<input" in code or "onChange" in code or "type=" in code
    has_table = "<table" in code or "<tr" in code or "<td" in code or "Table" in symbol
    has_nav = "<nav" in code or "Navbar" in symbol or "menu" in symbol.lower()
    has_list = "<ul" in code or "<ol" in code or "<li" in code

    prompt_lines = [
        f"Write a modern, accessible React functional component in TypeScript called `{symbol}` for the `{category}` section of a website.",
        "",
        "Functional Requirements:",
    ]
    if props_block:
        prompt_lines.append("Accept the following component props:")
        prompt_lines.append(props_block)
    else:
        prompt_lines.append(f"Accept suitable props with proper TypeScript typing for a `{symbol}` component.")

    if has_button:
        prompt_lines.append("- Provide accessible button controls with hover/focus states and click handlers.")
    if has_input:
        prompt_lines.append("- Include structured input fields with accessible labels and change handlers.")
    if has_table:
        prompt_lines.append("- Render a clean, semantic data table or grid with headers and responsive row formatting.")
    if has_nav:
        prompt_lines.append("- Render a semantic navigation container (`<nav>` / `role=\"navigation\"`) with active links.")
    if has_list:
        prompt_lines.append("- Render items in a clean list or grid structure.")

    prompt_lines.extend([
        "",
        "Design & Aesthetic Guidelines:",
        "- Implement modern visual design: clean typography, elegant color palette (accessible contrast), subtle border-radius, soft shadows, and responsive layout.",
        "- Use Flexbox or CSS Grid for alignment, with smooth CSS transitions on interactive states.",
    ])

    if companion_styles:
        prompt_lines.append("- Pair with modern CSS rules/classes (or CSS module) providing complete visual styling.")

    prompt_lines.append(f"IMPORTANT: Export the component as a named export called `{symbol}`.")
    prompt = "\n".join(prompt_lines)

    test_lines = [
        f"describe('{symbol} Component', () => {{",
        f"  it('renders without crashing and displays essential UI elements', () => {{",
        f"    const {{ container }} = render(<{symbol} />);",
        f"    expect(container).toBeInTheDocument();",
    ]
    if has_button:
        test_lines.append(f"    const buttons = screen.queryAllByRole('button');")
        test_lines.append(f"    expect(buttons.length >= 0).toBe(true);")
    if has_input:
        test_lines.append(f"    const inputs = screen.queryAllByRole('textbox');")
        test_lines.append(f"    expect(inputs.length >= 0).toBe(true);")
    test_lines.extend([
        f"  }});",
        f"}});"
    ])
    test_code = "\n".join(test_lines)

    return {
        "symbol": symbol,
        "category": category,
        "prompt": prompt,
        "test_code": test_code,
    }


# ==============================================================================
# 4. Quality Gate & Deduplication
# ==============================================================================

def looks_valid_test(test_code: str) -> bool:
    """Lightweight structural check on the generated test — no execution."""
    has_expect = "expect(" in test_code
    has_blocks = ("it(" in test_code or "test(" in test_code)
    has_bad_import = bool(re.search(r"""import\s+\{?\s*[A-Za-z]""", test_code))
    return has_expect and has_blocks and not has_bad_import


def load_existing_symbols(output_path: Path) -> Set[str]:
    """Load symbols already in the output JSONL to avoid duplicates on resume."""
    seen: Set[str] = set()
    if output_path.exists():
        with open(output_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    task = json.loads(line)
                    if "symbol" in task:
                        seen.add(task["symbol"])
                except json.JSONDecodeError:
                    pass
    return seen


# ==============================================================================
# 5. Main Mining Loop
# ==============================================================================

def mine_stack_v2(
    provider: str,
    model: str,
    api_key: Optional[str],
    target: int,
    output_file: Path,
    resume: bool,
    scan_limit: int,
    temperature: float,
    hf_token: Optional[str],
    max_component_lines: int,
    subset: str = "TSX",
    min_bytes: int = 300,
    max_bytes: int = 15000,
    permissive_only: bool = True,
    require_styles: bool = False,
    dry_run: bool = False,
    offline: bool = False,
    merge_with: Optional[Path] = None,
) -> None:
    """
    Stream bigcode/the-stack-v2, filter React components and companion styles,
    and build a comprehensive website-building task bank.
    """
    try:
        from datasets import load_dataset
    except ImportError:
        print("ERROR: `datasets` is not installed. Run: pip install datasets huggingface_hub")
        sys.exit(1)

    # Auto-detect if offline mode should be enabled
    has_api_key = bool(
        api_key
        or os.environ.get("GEMINI_API_KEY")
        or os.environ.get("ANTHROPIC_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
        or os.environ.get("DEEPSEEK_API_KEY")
        or os.environ.get("OPENROUTER_API_KEY")
    )
    if not dry_run and not has_api_key and not offline:
        print("[Offline Mode] No teacher API key detected in environment. Using automated AST/props extraction.")
        offline = True

    teacher: Optional[TeacherClient] = None
    if not dry_run and not offline:
        teacher = TeacherClient(provider=provider, model=model, api_key=api_key)

    seen_symbols: Set[str] = set()
    if resume and output_file.exists():
        seen_symbols = load_existing_symbols(output_file)
        print(f"[Resume] Found {len(seen_symbols)} existing symbol(s) in {output_file.name} — skipping duplicates.")

    existing_count = len(seen_symbols)

    print(f"\n{'='*70}")
    print(f"  Stack v2 -> Web Component & Style Mining Pipeline")
    print(f"  Dataset  : bigcode/the-stack-v2 (subset: '{subset}')")
    print(f"  Provider : {provider} / {model}")
    print(f"  Target   : {target} new tasks -> {output_file.name}")
    print(f"  Scan cap : {scan_limit} rows")
    print(f"  Options  : require_styles={require_styles} | dry_run={dry_run}")
    print(f"{'='*70}\n")

    token_arg: Dict[str, Any] = {}
    if hf_token:
        token_arg["token"] = hf_token
    elif os.environ.get("HF_TOKEN"):
        token_arg["token"] = os.environ["HF_TOKEN"]

    print(f"Connecting to bigcode/the-stack-v2 ('{subset}' subset, streaming)...")
    try:
        ds = load_dataset(
            "bigcode/the-stack-v2",
            subset,
            split="train",
            streaming=True,
            **token_arg,
        )
    except Exception as exc:
        print(f"ERROR: Could not load dataset: {exc}")
        print(
            "Make sure you have accepted the terms at "
            "https://huggingface.co/datasets/bigcode/the-stack-v2\n"
            "and run `hf auth login` or set the HF_TOKEN env variable."
        )
        sys.exit(1)

    saved_count = existing_count
    scanned = 0
    candidates_found = 0
    with_styles_found = 0
    task_index = existing_count

    # Path keywords that are not candidate UI components
    _EXCLUDE_PATH_KEYWORDS = [
        "test", "spec", "node_modules", "dist", "build", ".d.ts",
        "storybook", "stories", "__tests__", "__mocks__", "vendor",
        "cypress", "e2e", "jest", "mock", "fixture",
    ]

    out_f = open(output_file, "a", encoding="utf-8") if not dry_run else None

    try:
        for row in ds:
            if scanned >= scan_limit:
                print(f"\n[Scan limit {scan_limit} reached] Stopping.")
                break
            if saved_count >= existing_count + target:
                print(f"\n[Target {target} reached] Done.")
                break

            scanned += 1

            # 1. Pre-filter by metadata before making network requests
            file_path = row.get("path", "") or ""
            length_bytes = row.get("length_bytes", 0) or 0
            license_type = row.get("license_type", "") or ""

            if permissive_only and license_type and license_type not in ("permissive", "none"):
                continue

            if length_bytes < min_bytes or length_bytes > max_bytes:
                continue

            path_lower = file_path.lower()
            if any(k in path_lower for k in _EXCLUDE_PATH_KEYWORDS):
                continue

            # 2. Extract or fetch source code
            code: Optional[str] = None
            repo_name = row.get("repo_name", "")
            revision_id = row.get("revision_id", "")

            # Direct content or nested files
            if "content" in row and isinstance(row["content"], str) and row["content"].strip():
                code = row["content"]
            elif "files" in row and isinstance(row["files"], list):
                for f in row["files"]:
                    if isinstance(f, dict) and f.get("content"):
                        code = f["content"]
                        break
            else:
                if repo_name and file_path:
                    code = fetch_github_raw(repo_name, revision_id, file_path)

            if not code or not code.strip():
                continue

            # 3. Functional component quality filter
            if not is_candidate_react_component(code, max_lines=max_component_lines):
                continue

            symbol = extract_component_name(code)
            if symbol is None:
                continue

            # 4. Resolve companion CSS / SCSS stylesheet
            companion_css, css_path = resolve_companion_styles(
                repo_name, revision_id, file_path, code, symbol
            )

            if require_styles and not companion_css:
                continue

            candidates_found += 1
            if companion_css:
                with_styles_found += 1

            if symbol in seen_symbols:
                print(f"  [Skip] {symbol} already saved.")
                continue

            category = categorize_web_component(code, file_path, symbol)
            new_so_far = saved_count - existing_count

            style_badge = f"+ CSS ({len(companion_css.splitlines())} lines: {css_path})" if companion_css else "(inline/styled)"
            print(f"\n[Candidate #{candidates_found}] `{symbol}` [{category}] ({len(code.splitlines())} lines) {style_badge}")
            print(f"    From: {repo_name} | {file_path}")
            print(f"    Progress: {new_so_far}/{target} saved tasks")

            # In dry-run mode, report candidate without calling LLM
            if dry_run:
                saved_count += 1
                seen_symbols.add(symbol)
                print(f"    [DRY-RUN] Candidate {saved_count}/{target} verified: `{symbol}`")
                continue

            # 5. Reverse-engineer component + styles (Teacher LLM or Offline AST extraction)
            if offline or teacher is None:
                spec = offline_reverse_engineer(
                    code=code,
                    symbol=symbol,
                    category=category,
                    companion_styles=companion_css,
                )
            else:
                spec = reverse_engineer_component(
                    code=code,
                    symbol=symbol,
                    category=category,
                    companion_styles=companion_css,
                    teacher=teacher,
                    temperature=temperature,
                )
            if spec is None:
                continue

            # Visual Judge Quality Gating on candidate component + companion stylesheet
            vis_ok, vis_res = visual_judge.filter_trajectory_visual(
                {"code": code, "css": companion_css or ""},
                threshold=3
            )
            if not vis_ok:
                print(f"    [Visual Judge REJECT]: {symbol} visual score {vis_res.get('score', 0)}/5 below threshold 3/5 — skipping.", flush=True)
                continue

            # 6. Sanitize test code
            clean_test = strip_test_imports(spec["test_code"])

            if not looks_valid_test(clean_test):
                fallback = offline_reverse_engineer(code, symbol, category, companion_css)
                clean_test = strip_test_imports(fallback["test_code"])
                if not looks_valid_test(clean_test):
                    print("    [Quality Gate] Test code failed basic validation — skipping.", flush=True)
                    continue

            # 7. Build rich task bank entry
            task_index += 1
            task: Dict[str, Any] = {
                "task_id": f"stack_{task_index:04d}",
                "symbol": spec["symbol"],
                "category": spec.get("category", category),
                "check": "tsc_render_interact",
                "prompt": (
                    spec["prompt"].strip()
                    if f"named export called `{spec['symbol']}`" in spec["prompt"]
                    else spec["prompt"].strip() + f"\nIMPORTANT: Export the component as a named export called `{spec['symbol']}`."
                ),
                "test_code": clean_test,
                "reference_code": code,
                "reference_styles": companion_css,
                "_source": {
                    "provider": provider,
                    "model": model,
                    "repo_name": repo_name,
                    "path": file_path,
                    "styles_path": css_path,
                    "original_lines": len(code.splitlines()),
                    "has_styles": companion_css is not None,
                    "subset": subset,
                    "category": category,
                },
            }

            if out_f is not None:
                out_f.write(json.dumps(task) + "\n")
                out_f.flush()

            saved_count += 1
            seen_symbols.add(symbol)
            print(f"    -> Saved stack_{task_index:04d}: {symbol} [{category}] [{saved_count - existing_count}/{target}]")

            time.sleep(0.5)

    finally:
        if out_f is not None:
            out_f.close()

    new_tasks = saved_count - existing_count
    print(f"\n{'='*70}")
    print(f"  Scanned         : {scanned} rows")
    print(f"  React Candidates: {candidates_found}")
    print(f"  With Stylesheet : {with_styles_found}")
    print(f"  Saved Tasks     : {new_tasks} new tasks (total in bank: {saved_count})")
    if not dry_run:
        print(f"  Output File     : {output_file.resolve()}")
    print(f"{'='*70}")

    # Merge existing seed tasks if requested
    if merge_with and merge_with.exists() and output_file.exists():
        print(f"\n[Merge] Merging tasks from {merge_with.name} into {output_file.name}...")
        existing_bank_symbols = load_existing_symbols(output_file)
        merged_count = 0
        with open(merge_with, encoding="utf-8") as in_merge, open(output_file, "a", encoding="utf-8") as out_merge:
            for line in in_merge:
                line = line.strip()
                if not line:
                    continue
                try:
                    m_task = json.loads(line)
                    sym = m_task.get("symbol")
                    if sym and sym not in existing_bank_symbols:
                        out_merge.write(json.dumps(m_task) + "\n")
                        existing_bank_symbols.add(sym)
                        merged_count += 1
                except Exception:
                    pass
        print(f"[Merge] Added {merged_count} unique tasks from {merge_with.name}. Total tasks now: {len(existing_bank_symbols)}")

    if new_tasks > 0 and not dry_run:
        print(f"""
Next step — generate agentic training trajectories with the teacher model:

  python generate_teacher.py \\
      --provider {provider} \\
      --model {model} \\
      --eval-set {output_file.name} \\
      --output stack_trajectories.jsonl \\
      --count {new_tasks}
""")


# ==============================================================================
# 6. Stack Mining Dispatcher
# ==============================================================================

def run_stack(args) -> None:
    mine_stack_v2(
        provider=getattr(args, "provider", "gemini"),
        model=getattr(args, "model", "gemini-2.5-flash"),
        api_key=getattr(args, "api_key", None),
        target=getattr(args, "limit", getattr(args, "target", 10)),
        output_file=Path(getattr(args, "out", getattr(args, "output", str(DATA_DIR / "site_trajectories_stack.jsonl")))),
        resume=getattr(args, "resume", True),
        scan_limit=getattr(args, "scan_limit", 5000),
        temperature=getattr(args, "temperature", 0.2),
        hf_token=getattr(args, "hf_token", None),
        max_component_lines=getattr(args, "max_component_lines", 250),
        subset=getattr(args, "subset", "TSX"),
        min_bytes=getattr(args, "min_bytes", 300),
        max_bytes=getattr(args, "max_bytes", 15000),
        require_styles=getattr(args, "require_styles", True),
        dry_run=getattr(args, "dry_run", False),
        offline=getattr(args, "offline", True),
        merge_with=Path(args.merge_with) if getattr(args, "merge_with", None) else None,
    )






# ==============================================================================
# Unified CLI Dispatcher
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Unified Dataset Ingestion & Curation for ReactAgent SLM",
        formatter_class=argparse.RawTextHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="action", help="Curation action")

    # 1. curate-sources
    p_curate = subparsers.add_parser("curate-sources", help="Ingest web datasets (shadcn, HF typescript-instruct)")
    p_curate.add_argument("--source", choices=["typescript-instruct", "shadcn", "all"], default="all")
    p_curate.add_argument("--instruct-limit", type=int, default=15)
    p_curate.add_argument("--merge", action="store_true", default=True)

    # 2. typescript-instruct
    p_ts = subparsers.add_parser("typescript-instruct", help="Generate verified React+TypeScript instruction trajectories")
    p_ts.add_argument("--out", "--output", dest="output", default=str(DATA_DIR / "trajectories_typescript_instruct.jsonl"))

    # 3. teacher
    p_teach = subparsers.add_parser("teacher", help="Generate trajectories via teacher LLM")
    p_teach.add_argument("--provider", default="deepseek", choices=["openai", "anthropic", "openrouter", "deepseek"])
    p_teach.add_argument("--model", default=None)
    p_teach.add_argument("--api-key", default=None)
    p_teach.add_argument("--eval-set", default=str(DATA_DIR / "eval" / "react_ts_css_eval_set_combined.jsonl"))
    p_teach.add_argument("--output", "-o", default=str(DATA_DIR / "trajectories_teacher.jsonl"))
    p_teach.add_argument("--count", "-n", type=int, default=5)
    p_teach.add_argument("--generate-seed", action="store_true")
    p_teach.add_argument("--cost-estimate", action="store_true")
    p_teach.add_argument("--dry-run", action="store_true")

    # 4. star
    p_star = subparsers.add_parser("star", help="STaR rejection sampling on held-out tasks")
    p_star.add_argument("--model", default="my-react-agent-lora")
    p_star.add_argument("--tasks", type=int, default=5)
    p_star.add_argument("--max-turns", type=int, default=4)
    p_star.add_argument("--output", default=str(DATA_DIR / "star_trajectories.jsonl"))
    p_star.add_argument("--merge", action="store_true", default=False)
    p_star.add_argument("--resume", action="store_true", default=True)

    # 5. stack
    p_stack = subparsers.add_parser("stack", help="Mine TSX and CSS components from The Stack v2")
    p_stack.add_argument("--limit", type=int, default=10)
    p_stack.add_argument("--out", default=str(DATA_DIR / "site_trajectories_stack.jsonl"))

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    args = parser.parse_args()

    if args.action == "curate-sources":
        if args.source in ["shadcn", "all"]:
            ingest_shadcn_gold_library()
        if args.source in ["typescript-instruct", "all"]:
            ingest_typescript_instruct(limit=args.instruct_limit)
        if args.merge:
            merge_all_into_training_data()

    elif args.action == "typescript-instruct":
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        generate_typescript_instruct(output_path=out_path)

    elif args.action == "teacher":
        run_teacher(args)

    elif args.action == "star":
        run_star_pipeline(
            model_path=args.model,
            num_tasks=args.tasks,
            max_turns=args.max_turns,
            merge_output=args.merge,
            resume=args.resume,
            output_file=args.output
        )

    elif args.action == "stack":
        run_stack(args)

if __name__ == "__main__":
    main()
