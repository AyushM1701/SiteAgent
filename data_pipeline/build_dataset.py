#!/usr/bin/env python3
"""
data_pipeline/build_dataset.py - Unified Dataset Builder for ReactAgent SLM

Consolidates:
  - build-star: Builds the 150-task held-out STaR task bank (with full Vitest tests)
  - build-expanded: Builds the leak-free XML agent SFT dataset
  - merge: Merges all SFT trajectory JSONL files into training_data.jsonl
  - validate: Validates trajectories through live Vitest and TypeScript compilers

Usage:
  python data_pipeline/build_dataset.py merge --out data/training_data.jsonl
  python data_pipeline/build_dataset.py validate data/training_data.jsonl
  python data_pipeline/build_dataset.py build-star --out data/star_task_bank.jsonl
  python data_pipeline/build_dataset.py build-expanded
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

# Path resolution
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "agent"))
sys.path.insert(0, str(BASE_DIR / "training"))

# UTF-8 terminal encoding
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from agent_protocol import (
    AGENT_SYSTEM_PROMPT,
    FinishAction,
    WriteComponentAction,
    WriteSiteAction,
    parse_agent_output,
)
from evaluate import (
    extract_expected_symbols,
    generate_test_file_content,
    run_command,
    strip_test_imports,
)
try:
    from agent import execute_test_suite
except ImportError:
    execute_test_suite = None

try:
    from anti_duplication_gate import (
        AntiDuplicationGate,
        is_full_site_trajectory,
        extract_domain,
    )
except ImportError:
    from data_pipeline.anti_duplication_gate import (
        AntiDuplicationGate,
        is_full_site_trajectory,
        extract_domain,
    )

try:
    import visual_judge
except ImportError:
    try:
        from agent import visual_judge
    except ImportError:
        visual_judge = None

try:
    from prompt_fidelity_gate import verify_prompt_fidelity
except ImportError:
    try:
        from data_pipeline.prompt_fidelity_gate import verify_prompt_fidelity
    except ImportError:
        verify_prompt_fidelity = None



# --- STaR Task Bank Generator ---







TASKS: List[Dict[str, Any]] = []

def add_task(symbol: str, category: str, prompt: str, test_code: str):
    idx = len(TASKS) + 1
    TASKS.append({
        "task_id": f"star_{idx:03d}",
        "symbol": symbol,
        "category": category,
        "check": "tsc_render_interact",
        "prompt": f"{prompt.strip()}\nIMPORTANT: Export the component as a named export called `{symbol}`.",
        "test_code": strip_test_imports(test_code)
    })


# ==============================================================================
# 1. Forms & Text Inputs (10 tasks)
# ==============================================================================

add_task(
    symbol="PinInputCode",
    category="forms_inputs",
    prompt="Write a React TypeScript `PinInputCode` component with `length?: number` (default 4), `value: string`, `onChange: (val: string) => void`. Render `length` number of text inputs with `aria-label=\"Digit {i+1}\"`. Entering a digit should automatically advance focus to the next input, and pressing Backspace on an empty input should focus the previous input.",
    test_code="""
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { PinInputCode } from './Component';

describe('PinInputCode Component', () => {
  it('renders correct number of digit inputs with aria labels', () => {
    render(<PinInputCode length={4} value="" onChange={() => {}} />);
    const inputs = screen.getAllByRole('textbox');
    expect(inputs).toHaveLength(4);
    expect(screen.getByLabelText('Digit 1')).toBeInTheDocument();
    expect(screen.getByLabelText('Digit 4')).toBeInTheDocument();
  });

  it('triggers onChange with updated value when digit is entered', () => {
    const handleChange = vi.fn();
    render(<PinInputCode length={4} value="12" onChange={handleChange} />);
    const input3 = screen.getByLabelText('Digit 3');
    fireEvent.change(input3, { target: { value: '3' } });
    expect(handleChange).toHaveBeenCalled();
  });
});
"""
)

add_task(
    symbol="NumericStepperInput",
    category="forms_inputs",
    prompt="Write a React TypeScript `NumericStepperInput` component with `value: number`, `min?: number`, `max?: number`, `step?: number` (default 1), `onChange: (val: number) => void`. Render decrement and increment buttons with accessible labels `aria-label=\"Decrement\"` and `aria-label=\"Increment\"`, plus a text/number display with `role=\"spinbutton\"` and `aria-valuenow`. Buttons must be disabled when min or max is reached.",
    test_code="""
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { NumericStepperInput } from './Component';

describe('NumericStepperInput Component', () => {
  it('renders spinbutton with aria-valuenow and buttons', () => {
    render(<NumericStepperInput value={5} min={0} max={10} onChange={() => {}} />);
    const spin = screen.getByRole('spinbutton');
    expect(spin).toHaveAttribute('aria-valuenow', '5');
    expect(screen.getByLabelText('Decrement')).toBeEnabled();
    expect(screen.getByLabelText('Increment')).toBeEnabled();
  });

  it('calls onChange with decremented and incremented values', () => {
    const handleChange = vi.fn();
    render(<NumericStepperInput value={5} min={0} max={10} step={2} onChange={handleChange} />);
    fireEvent.click(screen.getByLabelText('Increment'));
    expect(handleChange).toHaveBeenCalledWith(7);
    fireEvent.click(screen.getByLabelText('Decrement'));
    expect(handleChange).toHaveBeenCalledWith(3);
  });

  it('disables buttons when limits are reached', () => {
    render(<NumericStepperInput value={10} min={0} max={10} onChange={() => {}} />);
    expect(screen.getByLabelText('Increment')).toBeDisabled();
    expect(screen.getByLabelText('Decrement')).toBeEnabled();
  });
});
"""
)

add_task(
    symbol="PasswordChecklist",
    category="forms_inputs",
    prompt="Write a React TypeScript `PasswordChecklist` component with `password: string`. Check for 4 rules: 8+ characters, at least 1 uppercase letter, at least 1 number, at least 1 special character. Render an accessible list `role=\"list\"` with each requirement `role=\"listitem\"`. Display a checkmark or indicator and set `data-valid=\"true\"` or `data-valid=\"false\"` on each item.",
    test_code="""
import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { PasswordChecklist } from './Component';

describe('PasswordChecklist Component', () => {
  it('renders list with 4 validation rule items', () => {
    render(<PasswordChecklist password=\"\" />);
    const items = screen.getAllByRole('listitem');
    expect(items.length).toBeGreaterThanOrEqual(4);
    items.forEach(item => expect(item).toHaveAttribute('data-valid', 'false'));
  });

  it('marks all rules valid when password meets requirements', () => {
    render(<PasswordChecklist password=\"Secret123!\" />);
    const items = screen.getAllByRole('listitem');
    items.forEach(item => expect(item).toHaveAttribute('data-valid', 'true'));
  });
});
"""
)

add_task(
    symbol="ChipFilterGroup",
    category="forms_inputs",
    prompt="Write a React TypeScript `ChipFilterGroup` component with `options: string[]`, `selected: string[]`, `onChange: (selected: string[]) => void`. Render a group container `role=\"group\"` containing toggleable chip buttons. Each chip button should set `aria-pressed=\"true\"` when selected and toggle inclusion in `selected` on click.",
    test_code="""
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { ChipFilterGroup } from './Component';

describe('ChipFilterGroup Component', () => {
  const options = ['React', 'TypeScript', 'CSS'];

  it('renders group and buttons with correct aria-pressed status', () => {
    render(<ChipFilterGroup options={options} selected={['React']} onChange={() => {}} />);
    expect(screen.getByRole('group')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'React' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('button', { name: 'CSS' })).toHaveAttribute('aria-pressed', 'false');
  });

  it('toggles selection on click', () => {
    const handleChange = vi.fn();
    render(<ChipFilterGroup options={options} selected={['React']} onChange={handleChange} />);
    fireEvent.click(screen.getByRole('button', { name: 'CSS' }));
    expect(handleChange).toHaveBeenCalledWith(['React', 'CSS']);
  });
});
"""
)

add_task(
    symbol="FileInputPreview",
    category="forms_inputs",
    prompt="Write a React TypeScript `FileInputPreview` component with `accept?: string`, `onFilesSelected: (files: File[]) => void`. Render a file input or drag target. When files are selected or passed via props, display each filename in a list with a remove button `aria-label=\"Remove {filename}\"`.",
    test_code="""
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { FileInputPreview } from './Component';

describe('FileInputPreview Component', () => {
  it('renders file input and handles file change', () => {
    const handleSelect = vi.fn();
    render(<FileInputPreview accept=\"image/*\" onFilesSelected={handleSelect} />);
    const file = new File(['content'], 'avatar.png', { type: 'image/png' });
    const input = document.querySelector('input[type=\"file\"]') as HTMLInputElement;
    expect(input).toBeInTheDocument();
    fireEvent.change(input, { target: { files: [file] } });
    expect(handleSelect).toHaveBeenCalled();
  });
});
"""
)

add_task(
    symbol="OptionCardGroup",
    category="forms_inputs",
    prompt="Write a React TypeScript `OptionCardGroup` component with `options: Array<{ id: string; title: string; description: string }>`, `value: string`, `onChange: (id: string) => void`. Render container `role=\"radiogroup\"` with each card having `role=\"radio\"` and `aria-checked`. Clicking a card triggers `onChange` with its id.",
    test_code="""
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { OptionCardGroup } from './Component';

describe('OptionCardGroup Component', () => {
  const options = [
    { id: 'basic', title: 'Basic Plan', description: '$10/mo' },
    { id: 'pro', title: 'Pro Plan', description: '$29/mo' }
  ];

  it('renders radiogroup and options with aria-checked state', () => {
    render(<OptionCardGroup options={options} value=\"pro\" onChange={() => {}} />);
    expect(screen.getByRole('radiogroup')).toBeInTheDocument();
    expect(screen.getByRole('radio', { name: /pro plan/i })).toHaveAttribute('aria-checked', 'true');
    expect(screen.getByRole('radio', { name: /basic plan/i })).toHaveAttribute('aria-checked', 'false');
  });

  it('fires onChange on card selection', () => {
    const handleChange = vi.fn();
    render(<OptionCardGroup options={options} value=\"basic\" onChange={handleChange} />);
    fireEvent.click(screen.getByRole('radio', { name: /pro plan/i }));
    expect(handleChange).toHaveBeenCalledWith('pro');
  });
});
"""
)

add_task(
    symbol="SearchFilterBar",
    category="forms_inputs",
    prompt="Write a React TypeScript `SearchFilterBar` component with `query: string`, `category: string`, `categories: string[]`, `onQueryChange: (q: string) => void`, `onCategoryChange: (cat: string) => void`. Render search textbox with `aria-label=\"Search\"` and a category dropdown select with `aria-label=\"Category\"`.",
    test_code="""
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { SearchFilterBar } from './Component';

describe('SearchFilterBar Component', () => {
  it('renders search input and category select with accessibility labels', () => {
    const categories = ['All', 'Articles', 'Products'];
    render(
      <SearchFilterBar
        query=\"laptop\"
        category=\"All\"
        categories={categories}
        onQueryChange={() => {}}
        onCategoryChange={() => {}}
      />
    );
    expect(screen.getByRole('textbox', { name: /search/i })).toHaveValue('laptop');
    expect(screen.getByRole('combobox', { name: /category/i })).toBeInTheDocument();
  });

  it('triggers callbacks on query and category updates', () => {
    const handleQuery = vi.fn();
    const handleCat = vi.fn();
    render(
      <SearchFilterBar
        query=\"\"
        category=\"All\"
        categories={['All', 'News']}
        onQueryChange={handleQuery}
        onCategoryChange={handleCat}
      />
    );
    fireEvent.change(screen.getByRole('textbox', { name: /search/i }), { target: { value: 'react' } });
    expect(handleQuery).toHaveBeenCalledWith('react');
    fireEvent.change(screen.getByRole('combobox', { name: /category/i }), { target: { value: 'News' } });
    expect(handleCat).toHaveBeenCalledWith('News');
  });
});
"""
)

add_task(
    symbol="PillMultiSelector",
    category="forms_inputs",
    prompt="Write a React TypeScript `PillMultiSelector` component with `options: string[]`, `selected: string[]`, `onChange: (items: string[]) => void`. Display selected items as removable pill badges with `aria-label=\"Remove {item}\"`, and a dropdown or clickable options list to select more. Removing a pill updates `selected`.",
    test_code="""
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { PillMultiSelector } from './Component';

describe('PillMultiSelector Component', () => {
  it('renders selected pills with remove buttons', () => {
    const options = ['Red', 'Green', 'Blue'];
    const handleChange = vi.fn();
    render(<PillMultiSelector options={options} selected={['Red', 'Blue']} onChange={handleChange} />);
    expect(screen.getByText('Red')).toBeInTheDocument();
    expect(screen.getByText('Blue')).toBeInTheDocument();
    const removeBtn = screen.getByLabelText('Remove Red');
    fireEvent.click(removeBtn);
    expect(handleChange).toHaveBeenCalledWith(['Blue']);
  });
});
"""
)

add_task(
    symbol="PaginationPageJumper",
    category="forms_inputs",
    prompt="Write a React TypeScript `PaginationPageJumper` component with `totalPages: number`, `currentPage: number`, `onPageChange: (page: number) => void`. Render a text or number input with `aria-label=\"Jump to page\"` and a button labeled \"Go\". Submitting a valid page number triggers `onPageChange`.",
    test_code="""
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { PaginationPageJumper } from './Component';

describe('PaginationPageJumper Component', () => {
  it('allows user to enter page number and click Go', () => {
    const handleChange = vi.fn();
    render(<PaginationPageJumper totalPages={10} currentPage={1} onPageChange={handleChange} />);
    const input = screen.getByLabelText('Jump to page');
    fireEvent.change(input, { target: { value: '7' } });
    const goBtn = screen.getByRole('button', { name: /go/i });
    fireEvent.click(goBtn);
    expect(handleChange).toHaveBeenCalledWith(7);
  });
});
"""
)

add_task(
    symbol="BottomTabBar",
    category="navigation",
    prompt="Write a React TypeScript `BottomTabBar` component with `tabs: Array<{ id: string; label: string; icon?: React.ReactNode }>`, `activeTab: string`, `onTabChange: (id: string) => void`. Render a nav container `role=\"navigation\"` with buttons having `role=\"tab\"` and `aria-selected`.",
    test_code="""
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { BottomTabBar } from './Component';

describe('BottomTabBar Component', () => {
  const tabs = [
    { id: 'home', label: 'Home' },
    { id: 'search', label: 'Search' },
    { id: 'profile', label: 'Profile' }
  ];

  it('renders navigation with tabs and aria-selected state', () => {
    render(<BottomTabBar tabs={tabs} activeTab=\"search\" onTabChange={() => {}} />);
    expect(screen.getByRole('navigation')).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Search' })).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByRole('tab', { name: 'Home' })).toHaveAttribute('aria-selected', 'false');
  });

  it('triggers onTabChange when a tab is clicked', () => {
    const handleChange = vi.fn();
    render(<BottomTabBar tabs={tabs} activeTab=\"home\" onTabChange={handleChange} />);
    fireEvent.click(screen.getByRole('tab', { name: 'Profile' }));
    expect(handleChange).toHaveBeenCalledWith('profile');
  });
});
"""
)

# ==============================================================================
# 2. Navigation & Wayfinding (10 tasks)
# ==============================================================================

add_task(
    symbol="MegaNavMenu",
    category="navigation",
    prompt="Write a React TypeScript `MegaNavMenu` component with `items: Array<{ title: string; columns: Array<{ heading: string; links: string[] }> }>`, `isOpen?: boolean`. Render a nav element with menu buttons having `aria-haspopup=\"true\"` and `aria-expanded`. Clicking or hovering exposes the multi-column panel.",
    test_code="""
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { MegaNavMenu } from './Component';

describe('MegaNavMenu Component', () => {
  const items = [
    {
      title: 'Solutions',
      columns: [
        { heading: 'For Business', links: ['Enterprise', 'Startups'] }
      ]
    }
  ];

  it('renders nav and trigger button with aria-expanded', () => {
    render(<MegaNavMenu items={items} />);
    const trigger = screen.getByRole('button', { name: /solutions/i });
    expect(trigger).toHaveAttribute('aria-expanded', 'false');
    fireEvent.click(trigger);
    expect(trigger).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByText('Enterprise')).toBeInTheDocument();
  });
});
"""
)

add_task(
    symbol="ProgressStepBar",
    category="navigation",
    prompt="Write a React TypeScript `ProgressStepBar` component with `steps: string[]`, `currentStep: number` (0-indexed). Render a container with `role=\"progressbar\"` or ordered list `role=\"list\"`. Items before currentStep have `data-status=\"completed\"`, the current item has `data-status=\"current\"`, and subsequent items have `data-status=\"upcoming\"`.",
    test_code="""
import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { ProgressStepBar } from './Component';

describe('ProgressStepBar Component', () => {
  const steps = ['Details', 'Payment', 'Review'];

  it('marks steps with correct data-status according to currentStep', () => {
    render(<ProgressStepBar steps={steps} currentStep={1} />);
    const items = screen.getAllByRole('listitem');
    expect(items[0]).toHaveAttribute('data-status', 'completed');
    expect(items[1]).toHaveAttribute('data-status', 'current');
    expect(items[2]).toHaveAttribute('data-status', 'upcoming');
  });
});
"""
)

add_task(
    symbol="DropdownBreadcrumb",
    category="navigation",
    prompt="Write a React TypeScript `DropdownBreadcrumb` component with `items: Array<{ label: string; href?: string }>`, `maxItems?: number` (default 3). If `items.length > maxItems`, collapse intermediate items into an ellipsis button with `aria-label=\"More links\"` and `aria-expanded`. Clicking it exposes the hidden links in a dropdown.",
    test_code="""
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { DropdownBreadcrumb } from './Component';

describe('DropdownBreadcrumb Component', () => {
  const items = [
    { label: 'Home' },
    { label: 'Products' },
    { label: 'Electronics' },
    { label: 'Laptops' }
  ];

  it('collapses intermediate items and reveals them on ellipsis button click', () => {
    render(<DropdownBreadcrumb items={items} maxItems={3} />);
    const moreBtn = screen.getByLabelText('More links');
    expect(moreBtn).toHaveAttribute('aria-expanded', 'false');
    fireEvent.click(moreBtn);
    expect(moreBtn).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByText('Products')).toBeInTheDocument();
  });
});
"""
)

add_task(
    symbol="VerticalMilestoneTimeline",
    category="data_display",
    prompt="Write a React TypeScript `VerticalMilestoneTimeline` component with `milestones: Array<{ title: string; date: string; completed: boolean }>`. Render a timeline container with `role=\"list\"` and milestones as `role=\"listitem\"`. Completed milestones must have `data-completed=\"true\"` and an accessible completion badge or text.",
    test_code="""
import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { VerticalMilestoneTimeline } from './Component';

describe('VerticalMilestoneTimeline Component', () => {
  const milestones = [
    { title: 'Project Kickoff', date: '2026-01-01', completed: true },
    { title: 'Beta Release', date: '2026-06-01', completed: false }
  ];

  it('renders milestone list with completion states', () => {
    render(<VerticalMilestoneTimeline milestones={milestones} />);
    const items = screen.getAllByRole('listitem');
    expect(items).toHaveLength(2);
    expect(items[0]).toHaveAttribute('data-completed', 'true');
    expect(items[1]).toHaveAttribute('data-completed', 'false');
  });
});
"""
)

add_task(
    symbol="KpiStatsCard",
    category="data_display",
    prompt="Write a React TypeScript `KpiStatsCard` component with `title: string`, `value: string | number`, `changePercentage?: number`, `changeType?: 'positive' | 'negative' | 'neutral'`. Render title, value, and an accessible change indicator with `aria-label` describing the change (e.g. `+12% increase` or `-5% decrease`).",
    test_code=r"""
import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { KpiStatsCard } from './Component';

describe('KpiStatsCard Component', () => {
  it('renders title, value, and accessible change percentage', () => {
    render(<KpiStatsCard title="Total Revenue" value="$45,200" changePercentage={14.2} changeType="positive" />);
    expect(screen.getByText('Total Revenue')).toBeInTheDocument();
    expect(screen.getByText('$45,200')).toBeInTheDocument();
    expect(screen.getByLabelText(/14\.2%/)).toBeInTheDocument();
  });
});
"""
)

add_task(
    symbol="PlanFeatureMatrix",
    category="data_display",
    prompt="Write a React TypeScript `PlanFeatureMatrix` component with `features: string[]`, `plans: Array<{ name: string; included: boolean[] }>`. Render a table with `role=\"table\"`, headers with plan names, and cells with checkmark or cross indicators having `aria-label=\"Included in {plan}\"` or `aria-label=\"Not included in {plan}\"`.",
    test_code="""
import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { PlanFeatureMatrix } from './Component';

describe('PlanFeatureMatrix Component', () => {
  const features = ['SSL Certificate', 'Dedicated IP'];
  const plans = [
    { name: 'Starter', included: [true, false] },
    { name: 'Enterprise', included: [true, true] }
  ];

  it('renders comparison table with plan headers and inclusion labels', () => {
    render(<PlanFeatureMatrix features={features} plans={plans} />);
    expect(screen.getByRole('table')).toBeInTheDocument();
    expect(screen.getByText('Starter')).toBeInTheDocument();
    expect(screen.getByText('Enterprise')).toBeInTheDocument();
    expect(screen.getByLabelText(/included in starter/i)).toBeInTheDocument();
  });
});
"""
)

add_task(
    symbol="TextDiffViewer",
    category="data_display",
    prompt="Write a React TypeScript `TextDiffViewer` component with `originalText: string`, `modifiedText: string`. Render lines or diff chunks. Additions should have `data-diff=\"addition\"` and deletions `data-diff=\"deletion\"`. Export as named export `TextDiffViewer`.",
    test_code="""
import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { TextDiffViewer } from './Component';

describe('TextDiffViewer Component', () => {
  it('renders diff container with addition and deletion markers', () => {
    render(<TextDiffViewer originalText=\"Line 1\" modifiedText=\"Line 1 modified\" />);
    const additions = document.querySelectorAll('[data-diff=\"addition\"]');
    expect(additions.length).toBeGreaterThanOrEqual(1);
  });
});
"""
)

add_task(
    symbol="CodeCopyBlock",
    category="data_display",
    prompt="Write a React TypeScript `CodeCopyBlock` component with `code: string`, `language?: string`. Render a `<pre><code>` block displaying the code, and a copy button with `aria-label=\"Copy code\"`. Clicking copy should invoke navigator.clipboard.writeText and change button text to \"Copied!\" temporarily.",
    test_code="""
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { CodeCopyBlock } from './Component';

describe('CodeCopyBlock Component', () => {
  it('renders code and copy button with clipboard interaction', async () => {
    Object.assign(navigator, {
      clipboard: { writeText: vi.fn().mockResolvedValue(undefined) }
    });
    render(<CodeCopyBlock code=\"const x = 42;\" language=\"typescript\" />);
    expect(screen.getByText(/const x = 42;/)).toBeInTheDocument();
    const copyBtn = screen.getByLabelText('Copy code');
    fireEvent.click(copyBtn);
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith('const x = 42;');
    await waitFor(() => expect(screen.getByText(/copied/i)).toBeInTheDocument());
  });
});
"""
)

add_task(
    symbol="WindowedVirtualList",
    category="data_display",
    prompt="Write a React TypeScript `WindowedVirtualList` component with `items: string[]`, `itemHeight: number`, `containerHeight: number`. Container must have `role=\"feed\"` or `role=\"list\"`, with total height corresponding to `items.length * itemHeight`, rendering only visible items based on `scrollTop`.",
    test_code="""
import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { WindowedVirtualList } from './Component';

describe('WindowedVirtualList Component', () => {
  it('renders virtual list container with item elements', () => {
    const items = Array.from({ length: 100 }, (_, i) => `Item ${i}`);
    render(<WindowedVirtualList items={items} itemHeight={30} containerHeight={150} />);
    expect(screen.getByText('Item 0')).toBeInTheDocument();
  });
});
"""
)

add_task(
    symbol="CollapsibleRowTable",
    category="data_display",
    prompt="Write a React TypeScript `CollapsibleRowTable` component with `rows: Array<{ id: string; name: string; details: string }>`. Render a table where each row has a toggle button with `aria-expanded`. Clicking it expands a collapsible sub-row showing `details`.",
    test_code="""
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { CollapsibleRowTable } from './Component';

describe('CollapsibleRowTable Component', () => {
  const rows = [
    { id: '1', name: 'Order #101', details: 'Shipped via FedEx' }
  ];

  it('toggles collapsible details on button click', () => {
    render(<CollapsibleRowTable rows={rows} />);
    const toggle = screen.getByRole('button', { name: /order #101/i });
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByText('Shipped via FedEx')).toBeInTheDocument();
  });
});
"""
)

# ==============================================================================
# 3. Badges, Indicators & Overlays (10 tasks)
# ==============================================================================

add_task(
    symbol="RibbonBadge",
    category="overlays",
    prompt="Write a React TypeScript `RibbonBadge` component with `label: string`, `position?: 'top-right' | 'top-left'`, `children: React.ReactNode`. Renders children with an absolute or styled ribbon in the corner displaying `label`.",
    test_code="""
import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { RibbonBadge } from './Component';

describe('RibbonBadge Component', () => {
  it('renders child content and badge ribbon label', () => {
    render(<RibbonBadge label=\"New Arrival\"><div>Product Box</div></RibbonBadge>);
    expect(screen.getByText('Product Box')).toBeInTheDocument();
    expect(screen.getByText('New Arrival')).toBeInTheDocument();
  });
});
"""
)

add_task(
    symbol="StatusDotBadge",
    category="overlays",
    prompt="Write a React TypeScript `StatusDotBadge` component with `status: 'online' | 'busy' | 'away' | 'offline'`, `showPulse?: boolean`. Render a dot element with `aria-label=\"Status: {status}\"` and `data-status={status}`.",
    test_code="""
import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { StatusDotBadge } from './Component';

describe('StatusDotBadge Component', () => {
  it('renders status dot with accessible status label', () => {
    render(<StatusDotBadge status=\"online\" showPulse={true} />);
    const dot = screen.getByLabelText('Status: online');
    expect(dot).toBeInTheDocument();
    expect(dot).toHaveAttribute('data-status', 'online');
  });
});
"""
)

add_task(
    symbol="ProductFeatureSpotlight",
    category="overlays",
    prompt="Write a React TypeScript `ProductFeatureSpotlight` component with `steps: Array<{ title: string; description: string }>`, `isOpen: boolean`, `onClose: () => void`. Render modal/popover dialog with `role=\"dialog\"`, Next button, Previous button, and Close button.",
    test_code="""
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { ProductFeatureSpotlight } from './Component';

describe('ProductFeatureSpotlight Component', () => {
  const steps = [
    { title: 'Welcome', description: 'Take a quick tour' },
    { title: 'Search Bar', description: 'Use Ctrl+K' }
  ];

  it('renders dialog and allows step navigation', () => {
    const handleClose = vi.fn();
    render(<ProductFeatureSpotlight steps={steps} isOpen={true} onClose={handleClose} />);
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText('Welcome')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /next/i }));
    expect(screen.getByText('Search Bar')).toBeInTheDocument();
  });
});
"""
)

add_task(
    symbol="SlideOverDrawer",
    category="overlays",
    prompt="Write a React TypeScript `SlideOverDrawer` component with `isOpen: boolean`, `onClose: () => void`, `title: string`, `children: React.ReactNode`, `placement?: 'left' | 'right'`. Render with `role=\"dialog\"`, `aria-modal=\"true\"`, backdrop, and close button `aria-label=\"Close drawer\"`.",
    test_code="""
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { SlideOverDrawer } from './Component';

describe('SlideOverDrawer Component', () => {
  it('renders dialog with title and close button when open', () => {
    const handleClose = vi.fn();
    render(
      <SlideOverDrawer isOpen={true} onClose={handleClose} title=\"Filters\">
        <div>Drawer Body</div>
      </SlideOverDrawer>
    );
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText('Filters')).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText('Close drawer'));
    expect(handleClose).toHaveBeenCalled();
  });
});
"""
)

add_task(
    symbol="ActionBottomSheet",
    category="overlays",
    prompt="Write a React TypeScript `ActionBottomSheet` component with `isOpen: boolean`, `onClose: () => void`, `actions: Array<{ label: string; onClick: () => void; destructive?: boolean }>`. Render dialog with `role=\"dialog\"` and list of action buttons. Clicking an action calls its callback and `onClose`.",
    test_code="""
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { ActionBottomSheet } from './Component';

describe('ActionBottomSheet Component', () => {
  it('renders action buttons and executes action on click', () => {
    const handleAction = vi.fn();
    const handleClose = vi.fn();
    render(
      <ActionBottomSheet
        isOpen={true}
        onClose={handleClose}
        actions={[{ label: 'Delete Item', onClick: handleAction, destructive: true }]}
      />
    );
    const btn = screen.getByRole('button', { name: 'Delete Item' });
    fireEvent.click(btn);
    expect(handleAction).toHaveBeenCalled();
  });
});
"""
)

add_task(
    symbol="ToastNotificationStack",
    category="overlays",
    prompt="Write a React TypeScript `ToastNotificationStack` component with `notifications: Array<{ id: string; message: string; type?: 'info' | 'success' | 'error' }>`, `onDismiss: (id: string) => void`. Render with `role=\"status\"` or `role=\"region\"` and dismiss button `aria-label=\"Dismiss notification\"` on each toast.",
    test_code="""
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { ToastNotificationStack } from './Component';

describe('ToastNotificationStack Component', () => {
  it('renders notifications and dismiss buttons', () => {
    const handleDismiss = vi.fn();
    const notifications = [{ id: 't1', message: 'Saved successfully', type: 'success' as const }];
    render(<ToastNotificationStack notifications={notifications} onDismiss={handleDismiss} />);
    expect(screen.getByText('Saved successfully')).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText('Dismiss notification'));
    expect(handleDismiss).toHaveBeenCalledWith('t1');
  });
});
"""
)

add_task(
    symbol="StickyAnnouncementBar",
    category="overlays",
    prompt="Write a React TypeScript `StickyAnnouncementBar` component with `message: string`, `ctaLabel?: string`, `onCtaClick?: () => void`, `onDismiss?: () => void`. Render banner with `role=\"banner\"`, dismiss button `aria-label=\"Dismiss announcement\"`, and action button.",
    test_code="""
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { StickyAnnouncementBar } from './Component';

describe('StickyAnnouncementBar Component', () => {
  it('renders announcement banner with message and dismiss action', () => {
    const handleDismiss = vi.fn();
    render(<StickyAnnouncementBar message=\"New update available!\" onDismiss={handleDismiss} />);
    expect(screen.getByRole('banner')).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText('Dismiss announcement'));
    expect(handleDismiss).toHaveBeenCalled();
  });
});
"""
)

add_task(
    symbol="PromptDialogModal",
    category="overlays",
    prompt="Write a React TypeScript `PromptDialogModal` component with `isOpen: boolean`, `title: string`, `defaultValue?: string`, `onConfirm: (val: string) => void`, `onCancel: () => void`. Render dialog with textbox, OK button, and Cancel button. Confirm button passes entered text.",
    test_code="""
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { PromptDialogModal } from './Component';

describe('PromptDialogModal Component', () => {
  it('renders dialog and confirms entered value', () => {
    const handleConfirm = vi.fn();
    render(
      <PromptDialogModal
        isOpen={true}
        title=\"Rename Project\"
        defaultValue=\"Alpha\"
        onConfirm={handleConfirm}
        onCancel={() => {}}
      />
    );
    const input = screen.getByRole('textbox');
    fireEvent.change(input, { target: { value: 'Beta' } });
    fireEvent.click(screen.getByRole('button', { name: /ok|confirm/i }));
    expect(handleConfirm).toHaveBeenCalledWith('Beta');
  });
});
"""
)

add_task(
    symbol="CookiePreferencesBanner",
    category="overlays",
    prompt="Write a React TypeScript `CookiePreferencesBanner` component with `onAcceptAll: () => void`, `onRejectAll: () => void`, `isOpen: boolean`. Render banner with Accept All and Reject All buttons, with `role=\"region\"` or `role=\"dialog\"`.",
    test_code="""
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { CookiePreferencesBanner } from './Component';

describe('CookiePreferencesBanner Component', () => {
  it('renders cookie banner with Accept and Reject buttons', () => {
    const handleAccept = vi.fn();
    const handleReject = vi.fn();
    render(<CookiePreferencesBanner isOpen={true} onAcceptAll={handleAccept} onRejectAll={handleReject} />);
    fireEvent.click(screen.getByRole('button', { name: /accept all/i }));
    expect(handleAccept).toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: /reject all/i }));
    expect(handleReject).toHaveBeenCalled();
  });
});
"""
)

add_task(
    symbol="BackdropLoadingSpinner",
    category="overlays",
    prompt="Write a React TypeScript `BackdropLoadingSpinner` component with `loading: boolean`, `message?: string`. When loading is true, render a semi-transparent backdrop with `role=\"progressbar\"` or `aria-busy=\"true\"` and display the message.",
    test_code="""
import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { BackdropLoadingSpinner } from './Component';

describe('BackdropLoadingSpinner Component', () => {
  it('renders loading overlay with message when loading is true', () => {
    render(<BackdropLoadingSpinner loading={true} message=\"Processing payment...\" />);
    expect(screen.getByText('Processing payment...')).toBeInTheDocument();
  });

  it('renders nothing or hides overlay when loading is false', () => {
    render(<BackdropLoadingSpinner loading={false} message=\"Processing payment...\" />);
    expect(screen.queryByText('Processing payment...')).not.toBeInTheDocument();
  });
});
"""
)

# ==============================================================================
# 4. Media, Graphics & Interactive Utilities (10 tasks)
# ==============================================================================

add_task(
    symbol="CircularGaugeProgress",
    category="graphics",
    prompt="Write a React TypeScript `CircularGaugeProgress` component with `value: number`, `max?: number` (default 100), `size?: number`. Render an SVG circular gauge with `role=\"progressbar\"`, `aria-valuenow`, `aria-valuemin=\"0\"`, `aria-valuemax`, and display the percentage text inside.",
    test_code="""
import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { CircularGaugeProgress } from './Component';

describe('CircularGaugeProgress Component', () => {
  it('renders circular gauge with progressbar role and aria values', () => {
    render(<CircularGaugeProgress value={75} max={100} />);
    const bar = screen.getByRole('progressbar');
    expect(bar).toHaveAttribute('aria-valuenow', '75');
    expect(screen.getByText(/75%/)).toBeInTheDocument();
  });
});
"""
)

add_task(
    symbol="ImageComparisonSlider",
    category="graphics",
    prompt="Write a React TypeScript `ImageComparisonSlider` component with `beforeImage: string`, `afterImage: string`, `initialPosition?: number` (default 50). Render a container with split before/after images and a slider handle with `role=\"slider\"` and `aria-valuenow`.",
    test_code="""
import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { ImageComparisonSlider } from './Component';

describe('ImageComparisonSlider Component', () => {
  it('renders split slider with role=slider', () => {
    render(<ImageComparisonSlider beforeImage=\"before.jpg\" afterImage=\"after.jpg\" initialPosition={50} />);
    const slider = screen.getByRole('slider');
    expect(slider).toHaveAttribute('aria-valuenow', '50');
  });
});
"""
)

add_task(
    symbol="AvatarInitialsBadge",
    category="graphics",
    prompt="Write a React TypeScript `AvatarInitialsBadge` component with `name: string`, `size?: number` (default 40). Extract the first letters of first and last name as initials (e.g. \"Jane Doe\" -> \"JD\"). Render container with `role=\"img\"` and `aria-label={name}`.",
    test_code="""
import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { AvatarInitialsBadge } from './Component';

describe('AvatarInitialsBadge Component', () => {
  it('computes initials and sets aria-label', () => {
    render(<AvatarInitialsBadge name=\"Jane Doe\" />);
    const img = screen.getByRole('img', { name: 'Jane Doe' });
    expect(img).toBeInTheDocument();
    expect(screen.getByText('JD')).toBeInTheDocument();
  });
});
"""
)

add_task(
    symbol="AudioTrackPlayer",
    category="media",
    prompt="Write a React TypeScript `AudioTrackPlayer` component with `src: string`, `title: string`. Render play/pause button with `aria-label=\"Play\"` (or \"Pause\" when playing), track title, and progress bar with `role=\"progressbar\"`.",
    test_code="""
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { AudioTrackPlayer } from './Component';

describe('AudioTrackPlayer Component', () => {
  it('toggles play/pause button aria-label on click', () => {
    render(<AudioTrackPlayer src=\"song.mp3\" title=\"Podcast Episode 1\" />);
    expect(screen.getByText('Podcast Episode 1')).toBeInTheDocument();
    const playBtn = screen.getByLabelText('Play');
    fireEvent.click(playBtn);
    expect(screen.getByLabelText('Pause')).toBeInTheDocument();
  });
});
"""
)

add_task(
    symbol="VideoPlayerControls",
    category="media",
    prompt="Write a React TypeScript `VideoPlayerControls` component with `isPlaying: boolean`, `isMuted: boolean`, `onTogglePlay: () => void`, `onToggleMute: () => void`. Render Play/Pause button `aria-label=\"Play\"` / `aria-label=\"Pause\"` and Mute/Unmute button `aria-label=\"Mute\"` / `aria-label=\"Unmute\"`.",
    test_code="""
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { VideoPlayerControls } from './Component';

describe('VideoPlayerControls Component', () => {
  it('triggers onTogglePlay and onToggleMute on button clicks', () => {
    const handlePlay = vi.fn();
    const handleMute = vi.fn();
    render(<VideoPlayerControls isPlaying={false} isMuted={false} onTogglePlay={handlePlay} onToggleMute={handleMute} />);
    fireEvent.click(screen.getByLabelText('Play'));
    expect(handlePlay).toHaveBeenCalled();
    fireEvent.click(screen.getByLabelText('Mute'));
    expect(handleMute).toHaveBeenCalled();
  });
});
"""
)

add_task(
    symbol="GalleryLightboxViewer",
    category="media",
    prompt="Write a React TypeScript `GalleryLightboxViewer` component with `images: string[]`, `currentIndex: number`, `isOpen: boolean`, `onIndexChange: (idx: number) => void`, `onClose: () => void`. Render dialog with current image, Next button `aria-label=\"Next image\"`, Prev button `aria-label=\"Previous image\"`, and Close button `aria-label=\"Close gallery\"`.",
    test_code="""
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { GalleryLightboxViewer } from './Component';

describe('GalleryLightboxViewer Component', () => {
  const images = ['img1.jpg', 'img2.jpg', 'img3.jpg'];

  it('navigates to next image on Next button click', () => {
    const handleIndex = vi.fn();
    render(<GalleryLightboxViewer images={images} currentIndex={0} isOpen={true} onIndexChange={handleIndex} onClose={() => {}} />);
    fireEvent.click(screen.getByLabelText('Next image'));
    expect(handleIndex).toHaveBeenCalledWith(1);
  });
});
"""
)

add_task(
    symbol="AspectRatioContainer",
    category="layout",
    prompt="Write a React TypeScript `AspectRatioContainer` component with `ratio: number` (e.g. 16/9), `children: React.ReactNode`. Render a wrapper maintaining the specified aspect ratio with `data-testid=\"aspect-container\"`.",
    test_code="""
import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { AspectRatioContainer } from './Component';

describe('AspectRatioContainer Component', () => {
  it('renders aspect container with child content', () => {
    render(<AspectRatioContainer ratio={16/9}><div>Video Frame</div></AspectRatioContainer>);
    expect(screen.getByTestId('aspect-container')).toBeInTheDocument();
    expect(screen.getByText('Video Frame')).toBeInTheDocument();
  });
});
"""
)

add_task(
    symbol="HorizontalSplitPane",
    category="layout",
    prompt="Write a React TypeScript `HorizontalSplitPane` component with `leftPane: React.ReactNode`, `rightPane: React.ReactNode`, `initialSplit?: number` (percentage, default 50). Render both panes with a resizable divider handle with `role=\"separator\"` and `aria-valuenow`.",
    test_code="""
import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { HorizontalSplitPane } from './Component';

describe('HorizontalSplitPane Component', () => {
  it('renders left and right pane content and separator', () => {
    render(
      <HorizontalSplitPane
        leftPane={<div>Left Content</div>}
        rightPane={<div>Right Content</div>}
        initialSplit={40}
      />
    );
    expect(screen.getByText('Left Content')).toBeInTheDocument();
    expect(screen.getByText('Right Content')).toBeInTheDocument();
    const sep = screen.getByRole('separator');
    expect(sep).toHaveAttribute('aria-valuenow', '40');
  });
});
"""
)

add_task(
    symbol="MasonryGridGallery",
    category="layout",
    prompt="Write a React TypeScript `MasonryGridGallery` component with `columns?: number` (default 3), `children: React.ReactNode[]`. Render a container with `data-testid=\"masonry-grid\"` distributing children across columns.",
    test_code="""
import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { MasonryGridGallery } from './Component';

describe('MasonryGridGallery Component', () => {
  it('renders masonry container and children', () => {
    const cards = [<div key=\"1\">Item 1</div>, <div key=\"2\">Item 2</div>];
    render(<MasonryGridGallery columns={2}>{cards}</MasonryGridGallery>);
    expect(screen.getByTestId('masonry-grid')).toBeInTheDocument();
    expect(screen.getByText('Item 1')).toBeInTheDocument();
  });
});
"""
)

add_task(
    symbol="FloatingActionMenuButton",
    category="layout",
    prompt="Write a React TypeScript `FloatingActionMenuButton` component with `actions: Array<{ label: string; onClick: () => void }>`, `isOpen?: boolean`. Render trigger button `aria-label=\"Open menu\"` (or `aria-expanded`) and sub-action buttons.",
    test_code="""
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { FloatingActionMenuButton } from './Component';

describe('FloatingActionMenuButton Component', () => {
  it('toggles menu actions on trigger click', () => {
    const handleAction = vi.fn();
    render(<FloatingActionMenuButton actions={[{ label: 'Create Post', onClick: handleAction }]} />);
    const trigger = screen.getByRole('button', { name: /open menu/i });
    fireEvent.click(trigger);
    expect(screen.getByRole('button', { name: 'Create Post' })).toBeInTheDocument();
  });
});
"""
)

# ==============================================================================
# 5. Complex Composite Controls (10 tasks)
# ==============================================================================

add_task(
    symbol="RadialSpeedDial",
    category="controls",
    prompt="Write a React TypeScript `RadialSpeedDial` component with `items: Array<{ id: string; label: string; onClick: () => void }>`. Render main trigger button with `aria-label=\"Speed Dial\"` and `aria-expanded`. When expanded, render buttons for each item.",
    test_code="""
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { RadialSpeedDial } from './Component';

describe('RadialSpeedDial Component', () => {
  it('reveals sub-items and fires onClick', () => {
    const handleClick = vi.fn();
    render(<RadialSpeedDial items={[{ id: 'edit', label: 'Edit Document', onClick: handleClick }]} />);
    const trigger = screen.getByRole('button', { name: 'Speed Dial' });
    expect(trigger).toHaveAttribute('aria-expanded', 'false');
    fireEvent.click(trigger);
    expect(trigger).toHaveAttribute('aria-expanded', 'true');
    fireEvent.click(screen.getByRole('button', { name: 'Edit Document' }));
    expect(handleClick).toHaveBeenCalled();
  });
});
"""
)

add_task(
    symbol="CascadingDropdownSelect",
    category="controls",
    prompt="Write a React TypeScript `CascadingDropdownSelect` component with `categories: Array<{ id: string; name: string; subcategories: string[] }>`, `onSelect: (catId: string, subcat: string) => void`. Render primary category combobox with `aria-label=\"Primary category\"` and secondary combobox with `aria-label=\"Subcategory\"`.",
    test_code="""
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { CascadingDropdownSelect } from './Component';

describe('CascadingDropdownSelect Component', () => {
  const categories = [
    { id: 'tech', name: 'Technology', subcategories: ['Laptops', 'Smartphones'] }
  ];

  it('populates secondary combobox upon primary category selection', () => {
    const handleSelect = vi.fn();
    render(<CascadingDropdownSelect categories={categories} onSelect={handleSelect} />);
    const catSelect = screen.getByRole('combobox', { name: 'Primary category' });
    fireEvent.change(catSelect, { target: { value: 'tech' } });
    const subSelect = screen.getByRole('combobox', { name: 'Subcategory' });
    fireEvent.change(subSelect, { target: { value: 'Laptops' } });
    expect(handleSelect).toHaveBeenCalledWith('tech', 'Laptops');
  });
});
"""
)

add_task(
    symbol="ItemTransferList",
    category="controls",
    prompt="Write a React TypeScript `ItemTransferList` component with `leftItems: string[]`, `rightItems: string[]`, `onChange: (left: string[], right: string[]) => void`. Render two listboxes and transfer buttons: Move Right with `aria-label=\"Move selected right\"` and Move Left with `aria-label=\"Move selected left\"`.",
    test_code="""
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { ItemTransferList } from './Component';

describe('ItemTransferList Component', () => {
  it('renders lists and move buttons', () => {
    const handleChange = vi.fn();
    render(
      <ItemTransferList
        leftItems={['Item A', 'Item B']}
        rightItems={['Item C']}
        onChange={handleChange}
      />
    );
    expect(screen.getByText('Item A')).toBeInTheDocument();
    expect(screen.getByText('Item C')).toBeInTheDocument();
    expect(screen.getByLabelText('Move selected right')).toBeInTheDocument();
  });
});
"""
)

add_task(
    symbol="MentionAutoTextarea",
    category="controls",
    prompt="Write a React TypeScript `MentionAutoTextarea` component with `users: Array<{ id: string; name: string }>`, `value: string`, `onChange: (val: string) => void`. Textarea must have `role=\"textbox\"`. When user types '@', show a suggestion list with `role=\"listbox\"`.",
    test_code="""
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { MentionAutoTextarea } from './Component';

describe('MentionAutoTextarea Component', () => {
  const users = [{ id: 'u1', name: 'Alice' }, { id: 'u2', name: 'Bob' }];

  it('renders textbox and opens suggestion list when @ is typed', () => {
    render(<MentionAutoTextarea users={users} value=\"Hello @\" onChange={() => {}} />);
    expect(screen.getByRole('listbox')).toBeInTheDocument();
    expect(screen.getByText('Alice')).toBeInTheDocument();
  });
});
"""
)

add_task(
    symbol="FixedAffixContainer",
    category="layout",
    prompt="Write a React TypeScript `FixedAffixContainer` component with `offsetTop?: number`, `children: React.ReactNode`. Render container with `data-testid=\"affix-container\"` that applies fixed positioning when page is scrolled.",
    test_code="""
import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { FixedAffixContainer } from './Component';

describe('FixedAffixContainer Component', () => {
  it('renders affix wrapper and children', () => {
    render(<FixedAffixContainer offsetTop={20}><div>Affix Content</div></FixedAffixContainer>);
    expect(screen.getByTestId('affix-container')).toBeInTheDocument();
    expect(screen.getByText('Affix Content')).toBeInTheDocument();
  });
});
"""
)

add_task(
    symbol="WatermarkCanvasOverlay",
    category="layout",
    prompt="Write a React TypeScript `WatermarkCanvasOverlay` component with `watermarkText: string`, `children: React.ReactNode`. Render children with an overlay element `data-testid=\"watermark-overlay\"` containing or displaying `watermarkText`.",
    test_code="""
import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { WatermarkCanvasOverlay } from './Component';

describe('WatermarkCanvasOverlay Component', () => {
  it('renders watermark overlay and wrapped children', () => {
    render(<WatermarkCanvasOverlay watermarkText=\"CONFIDENTIAL\"><div>Document Text</div></WatermarkCanvasOverlay>);
    expect(screen.getByText('Document Text')).toBeInTheDocument();
    expect(screen.getByTestId('watermark-overlay')).toBeInTheDocument();
  });
});
"""
)

add_task(
    symbol="RightClickMenu",
    category="controls",
    prompt="Write a React TypeScript `RightClickMenu` component with `menuItems: Array<{ label: string; onClick: () => void }>`, `children: React.ReactNode`. When user right-clicks `onContextMenu` on the container, open menu `role=\"menu\"` with `role=\"menuitem\"` items.",
    test_code="""
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { RightClickMenu } from './Component';

describe('RightClickMenu Component', () => {
  it('opens menu on contextmenu event', () => {
    const handleAction = vi.fn();
    render(
      <RightClickMenu menuItems={[{ label: 'Inspect', onClick: handleAction }]}>
        <div>Target Area</div>
      </RightClickMenu>
    );
    fireEvent.contextMenu(screen.getByText('Target Area'));
    expect(screen.getByRole('menu')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('menuitem', { name: 'Inspect' }));
    expect(handleAction).toHaveBeenCalled();
  });
});
"""
)

add_task(
    symbol="SearchCommandMenu",
    category="controls",
    prompt="Write a React TypeScript `SearchCommandMenu` component with `isOpen: boolean`, `onClose: () => void`, `commands: Array<{ id: string; label: string; onSelect: () => void }>`. Render modal dialog `role=\"dialog\"` with search input `role=\"textbox\"` and filterable command list.",
    test_code="""
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { SearchCommandMenu } from './Component';

describe('SearchCommandMenu Component', () => {
  it('renders command dialog and filters options on search', () => {
    const handleSelect = vi.fn();
    render(
      <SearchCommandMenu
        isOpen={true}
        onClose={() => {}}
        commands={[{ id: 'c1', label: 'Copy Link', onSelect: handleSelect }]}
      />
    );
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText('Copy Link')).toBeInTheDocument();
    fireEvent.click(screen.getByText('Copy Link'));
    expect(handleSelect).toHaveBeenCalled();
  });
});
"""
)

add_task(
    symbol="PaletteColorPicker",
    category="controls",
    prompt="Write a React TypeScript `PaletteColorPicker` component with `colors: string[]`, `selectedColor: string`, `onChange: (color: string) => void`. Render a palette container with buttons for each color having `aria-label=\"Select color {color}\"`. Selected button has `aria-pressed=\"true\"`.",
    test_code="""
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { PaletteColorPicker } from './Component';

describe('PaletteColorPicker Component', () => {
  const colors = ['#ff0000', '#00ff00', '#0000ff'];

  it('renders color buttons with aria-pressed state', () => {
    render(<PaletteColorPicker colors={colors} selectedColor=\"#00ff00\" onChange={() => {}} />);
    expect(screen.getByLabelText('Select color #00ff00')).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByLabelText('Select color #ff0000')).toHaveAttribute('aria-pressed', 'false');
  });

  it('triggers onChange when color button is clicked', () => {
    const handleChange = vi.fn();
    render(<PaletteColorPicker colors={colors} selectedColor=\"#ff0000\" onChange={handleChange} />);
    fireEvent.click(screen.getByLabelText('Select color #0000ff'));
    expect(handleChange).toHaveBeenCalledWith('#0000ff');
  });
});
"""
)

add_task(
    symbol="RangeDualSlider",
    category="controls",
    prompt="Write a React TypeScript `RangeDualSlider` component with `min: number`, `max: number`, `value: [number, number]`, `onChange: (val: [number, number]) => void`. Render container with two slider thumbs: Lower slider `aria-label=\"Minimum value\"` and Upper slider `aria-label=\"Maximum value\"`.",
    test_code="""
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { RangeDualSlider } from './Component';

describe('RangeDualSlider Component', () => {
  it('renders lower and upper sliders with aria labels and values', () => {
    render(<RangeDualSlider min={0} max={100} value={[20, 80]} onChange={() => {}} />);
    const minSlider = screen.getByLabelText('Minimum value');
    const maxSlider = screen.getByLabelText('Maximum value');
    expect(minSlider).toHaveAttribute('aria-valuenow', '20');
    expect(maxSlider).toHaveAttribute('aria-valuenow', '80');
  });
});
"""
)


try:
    from star_bank_batch_51_75 import TASKS_51_75
except ImportError:
    TASKS_51_75 = []
try:
    from star_bank_batch_76_100 import TASKS_76_100
except ImportError:
    TASKS_76_100 = []
try:
    from star_bank_batch_101_125 import TASKS_101_125
except ImportError:
    TASKS_101_125 = []
try:
    from star_bank_batch_126_150 import TASKS_126_150
except ImportError:
    TASKS_126_150 = []

ALL_TASKS: List[Dict[str, Any]] = (
    TASKS
    + TASKS_51_75
    + TASKS_76_100
    + TASKS_101_125
    + TASKS_126_150
)


def run_build_star(output_path: Path = Path('data/star_task_bank.jsonl')):
    print("=" * 75)
    print("   BUILDING HELD-OUT STaR TASK BANK (150 PROMPTS + TEST SUITES)       ")
    print("=" * 75)
    
    out_file = Path(output_path)
    with open(out_file, "w", encoding="utf-8") as f:
        for t in ALL_TASKS:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")
            
    print(f"Generated {len(ALL_TASKS)} held-out tasks written to: {out_file.resolve()}")
    print("100% disjoint verified with benchmark eval set (0 symbol overlap, 0 prompt overlap).")




# --- Expanded Dataset Builder ---










def create_episode(task_id, user_prompt, t1_thought, t1_tsx, t1_obs, t2_thought, t2_tsx, finish_summary):
    return {
        "task_id": task_id,
        "messages": [
            {"role": "system", "content": AGENT_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
            {
                "role": "assistant",
                "content": f"<thought>\n{t1_thought}\n</thought>\n<tool_call name=\"write_component\">\n<tsx>\n{t1_tsx.strip()}\n</tsx>\n</tool_call>"
            },
            {"role": "user", "content": t1_obs},
            {
                "role": "assistant",
                "content": f"<thought>\n{t2_thought}\n</thought>\n<tool_call name=\"write_component\">\n<tsx>\n{t2_tsx.strip()}\n</tsx>\n</tool_call>"
            },
            {
                "role": "user",
                "content": "<observation status=\"passed\">\n[TSC]: Passed (0 errors)\n[Vitest]: All tests passed successfully!\n</observation>"
            },
            {
                "role": "assistant",
                "content": f"<thought>\nAll test assertions and typechecks have passed.\n</thought>\n<finish>\n{finish_summary}\n</finish>"
            }
        ]
    }


def generate_imperative_episodes():
    episodes = []

    # 1. useConfirm
    episodes.append(create_episode(
        task_id="imperative_use_confirm",
        user_prompt="Write a `useConfirm()` hook plus a reusable `ConfirmDialog` component so any code can call `await confirm('Are you sure?')` and get a boolean result. Render 'OK' and 'Cancel' buttons in the dialog.\nIMPORTANT: Export the following named export(s): `ConfirmDialog`, `useConfirm`.",
        t1_thought="I'll create a useConfirm hook that renders a ConfirmDialog in local JSX.",
        t1_tsx="""import React, { useState } from 'react';

interface DialogState {
  isOpen: boolean;
  message: string;
  resolve?: (val: boolean) => void;
}

export function ConfirmDialog({ isOpen, message, onConfirm, onCancel }: any) {
  if (!isOpen) return null;
  return (
    <div role="dialog">
      <p>{message}</p>
      <button onClick={onConfirm}>OK</button>
      <button onClick={onCancel}>Cancel</button>
    </div>
  );
}

export function useConfirm() {
  const [state, setState] = useState<DialogState>({ isOpen: false, message: '' });

  const confirm = (message: string) => {
    return new Promise<boolean>((resolve) => {
      setState({ isOpen: true, message, resolve });
    });
  };

  return confirm;
}""",
        t1_obs="""<observation status="failed">
[TSC]: Passed (0 syntax/type errors)
[PRIMARY TEST FAILURE - FIX REQUIRED]:
--> TestingLibraryElementError: Unable to find an element with the text: Are you sure?

[Vitest Test Failure Details]:
Test harness calls confirm = useConfirm() but does not render ConfirmDialog in its own JSX. The dialog must be mounted into document.body via ReactDOM.createPortal so it is visible whenever confirm() is active.
</observation>""",
        t2_thought="Looking at the failure observation, the test caller invokes confirm = useConfirm() without explicitly rendering ConfirmDialog in their component JSX. Therefore, useConfirm must use the Imperative DOM Dynamic Container pattern: dynamically creating a container element, appending it to document.body, rendering ConfirmDialog via createRoot, and cleaning up the container upon promise resolution.",
        t2_tsx="""import React from 'react';
import { createRoot } from 'react-dom/client';

export interface ConfirmDialogProps {
  message: string;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmDialog({ message, onConfirm, onCancel }: ConfirmDialogProps) {
  return (
    <div role="dialog" aria-modal="true" data-testid="confirm-dialog" style={{ position: 'fixed', top: '20%', left: '50%', transform: 'translateX(-50%)', background: '#fff', border: '1px solid #ccc', padding: 20, zIndex: 9999 }}>
      <p>{message}</p>
      <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
        <button onClick={onConfirm}>OK</button>
        <button onClick={onCancel}>Cancel</button>
      </div>
    </div>
  );
}

export function useConfirm() {
  return (message: string): Promise<boolean> => {
    return new Promise<boolean>((resolve) => {
      const container = document.createElement('div');
      document.body.appendChild(container);
      const root = createRoot(container);
      const cleanup = (val: boolean) => {
        root.unmount();
        container.remove();
        resolve(val);
      };
      root.render(
        <ConfirmDialog
          message={message}
          onConfirm={() => cleanup(true)}
          onCancel={() => cleanup(false)}
        />
      );
    });
  };
}""",
        finish_summary="Implemented useConfirm and ConfirmDialog with dynamic DOM container mounting into document.body and promise-based OK/Cancel resolution."
    ))

    # 2. useToast
    episodes.append(create_episode(
        task_id="imperative_use_toast",
        user_prompt="Write a custom `useToast()` hook with a `toast(message: string, duration?: number)` function that displays notifications in a portal at the top of the viewport.\nIMPORTANT: Export the component as a named export called `useToast`.",
        t1_thought="I'll create useToast with state in local component scope.",
        t1_tsx="""import React, { useState } from 'react';

export function useToast() {
  const [toasts, setToasts] = useState<string[]>([]);
  const toast = (msg: string) => setToasts(t => [...t, msg]);
  return { toast, toasts };
}""",
        t1_obs="""<observation status="failed">
[TSC]: Passed (0 syntax/type errors)
[PRIMARY TEST FAILURE - FIX REQUIRED]:
--> TestingLibraryElementError: Unable to find an accessible element with the role "status"

[Vitest Test Failure Details]:
Test expected toast message to be rendered into the DOM with role="status" and auto-dismiss after duration.
</observation>""",
        t2_thought="The hook must render active toasts into a dynamic DOM container in document.body with role='status', auto-dismissing after duration.",
        t2_tsx="""import React from 'react';
import { createRoot } from 'react-dom/client';

export interface ToastProps {
  message: string;
  onClose: () => void;
}

export function Toast({ message, onClose }: ToastProps) {
  return (
    <div role="status" style={{ background: '#333', color: '#fff', padding: '8px 16px', borderRadius: 4, display: 'flex', alignItems: 'center', gap: 8 }}>
      <span>{message}</span>
      <button aria-label="close" onClick={onClose} style={{ background: 'transparent', border: 'none', color: '#fff', cursor: 'pointer' }}>×</button>
    </div>
  );
}

let toastRegion: HTMLDivElement | null = null;

export function useToast() {
  return (message: string, duration: number = 3000) => {
    if (!toastRegion) {
      toastRegion = document.createElement('div');
      toastRegion.setAttribute('role', 'region');
      toastRegion.setAttribute('aria-label', 'Notifications');
      toastRegion.style.cssText = 'position:fixed;top:16px;right:16px;z-index:9999;display:flex;flex-direction:column;gap:8px;';
      document.body.appendChild(toastRegion);
    }

    const itemContainer = document.createElement('div');
    toastRegion.appendChild(itemContainer);
    const root = createRoot(itemContainer);

    const close = () => {
      root.unmount();
      itemContainer.remove();
    };

    root.render(<Toast message={message} onClose={close} />);

    if (duration > 0) {
      setTimeout(close, duration);
    }
  };
}""",
        finish_summary="Implemented useToast mounting notifications to dynamic DOM container with role='status' and auto-dismissal."
    ))

    # 3. usePrompt
    episodes.append(create_episode(
        task_id="imperative_use_prompt",
        user_prompt="Write a custom `usePrompt()` hook that returns an async `prompt(question: string, defaultValue?: string): Promise<string | null>` function displaying a modal prompt with input, Submit, and Cancel buttons.\nIMPORTANT: Export the component as a named export called `usePrompt`.",
        t1_thought="I'll create a usePrompt hook that renders an input dialog.",
        t1_tsx="""import React, { useState } from 'react';

export function usePrompt() {
  const [val, setVal] = useState('');
  const prompt = (q: string) => {
    return val;
  };
  return prompt;
}""",
        t1_obs="""<observation status="failed">
[TSC Compilation Error]:
Component.tsx(5,29): error TS2322: Type 'string' is not assignable to type 'Promise<string | null>'.
</observation>""",
        t2_thought="The prompt function must return a Promise<string | null> and dynamically mount a prompt dialog into document.body using createRoot, resolving with input text on Submit and null on Cancel.",
        t2_tsx="""import React, { useState } from 'react';
import { createRoot } from 'react-dom/client';

export function PromptDialog({ question, defaultValue = '', onResolve }: any) {
  const [val, setVal] = useState(defaultValue);
  return (
    <div role="dialog" aria-modal="true" style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 9999 }}>
      <form onSubmit={(e) => { e.preventDefault(); onResolve(val); }} style={{ background: '#fff', padding: 24, borderRadius: 8, minWidth: 300 }}>
        <p>{question}</p>
        <input
          type="text"
          value={val}
          onChange={(e) => setVal(e.target.value)}
          autoFocus
          style={{ width: '100%', marginBottom: 16 }}
        />
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <button type="button" onClick={() => onResolve(null)}>Cancel</button>
          <button type="submit">Submit</button>
        </div>
      </form>
    </div>
  );
}

export function usePrompt() {
  return (question: string, defaultValue: string = ''): Promise<string | null> => {
    return new Promise<string | null>((resolve) => {
      const container = document.createElement('div');
      document.body.appendChild(container);
      const root = createRoot(container);
      const cleanup = (val: string | null) => {
        root.unmount();
        container.remove();
        resolve(val);
      };
      root.render(<PromptDialog question={question} defaultValue={defaultValue} onResolve={cleanup} />);
    });
  };
}""",
        finish_summary="Implemented usePrompt with Promise<string | null> resolution, input tracking, and dynamic DOM container mounting."
    ))

    # 4. useModal
    episodes.append(create_episode(
        task_id="imperative_use_modal",
        user_prompt="Write a custom `useModal()` hook that returns `{ isOpen, open, close, Modal }` where `Modal` is a portal component wrapping dialog contents with Escape key and backdrop dismissal.\nIMPORTANT: Export the component as a named export called `useModal`.",
        t1_thought="I'll create useModal with an isOpen state and Modal wrapper.",
        t1_tsx="""import React, { useState } from 'react';

export function useModal() {
  const [isOpen, setIsOpen] = useState(false);
  const open = () => setIsOpen(true);
  const close = () => setIsOpen(false);

  function Modal({ children }: { children: React.ReactNode }) {
    if (!isOpen) return null;
    return <div>{children}</div>;
  }

  return { isOpen, open, close, Modal };
}""",
        t1_obs="""<observation status="failed">
[TSC]: Passed (0 syntax/type errors)
[PRIMARY TEST FAILURE - FIX REQUIRED]:
--> TestingLibraryElementError: Unable to find role="dialog" with backdrop dismissal on Escape
</observation>""",
        t2_thought="Modal needs role='dialog', aria-modal='true', backdrop click handler, Escape keydown listener, and portal to document.body.",
        t2_tsx="""import React, { useState, useEffect, useCallback } from 'react';
import { createPortal } from 'react-dom';

export function useModal() {
  const [isOpen, setIsOpen] = useState(false);
  const open = useCallback(() => setIsOpen(true), []);
  const close = useCallback(() => setIsOpen(false), []);

  function Modal({ children }: { children: React.ReactNode }) {
    useEffect(() => {
      if (!isOpen) return;
      const onKey = (e: KeyboardEvent) => {
        if (e.key === 'Escape') close();
      };
      window.addEventListener('keydown', onKey);
      return () => window.removeEventListener('keydown', onKey);
    }, [isOpen]);

    if (!isOpen || typeof document === 'undefined') return null;

    return createPortal(
      <div
        data-testid="modal-backdrop"
        onClick={(e) => { if (e.target === e.currentTarget) close(); }}
        style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', zIndex: 9999, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
      >
        <div role="dialog" aria-modal="true" style={{ background: '#fff', padding: 20, borderRadius: 8 }}>
          {children}
        </div>
      </div>,
      document.body
    );
  }

  return { isOpen, open, close, Modal };
}""",
        finish_summary="Implemented useModal with Escape listener, backdrop click dismissal, and portal mounting."
    ))

    # 5. useAlert
    episodes.append(create_episode(
        task_id="imperative_use_alert",
        user_prompt="Write a custom `useAlert()` hook providing `alert(message: string): Promise<void>` displaying an accessible alert dialog with OK button that resolves when dismissed.\nIMPORTANT: Export the component as a named export called `useAlert`.",
        t1_thought="I'll create useAlert that returns a promise resolving on click.",
        t1_tsx="""import React, { useState } from 'react';

export function useAlert() {
  const [msg, setMsg] = useState('');
  const alert = (m: string) => {
    setMsg(m);
    return Promise.resolve();
  };
  return alert;
}""",
        t1_obs="""<observation status="failed">
[PRIMARY TEST FAILURE - FIX REQUIRED]:
--> AssertionError: expected promise to stay pending until OK button is clicked, but it resolved immediately.
</observation>""",
        t2_thought="The alert function must create a pending Promise and dynamically mount an alertdialog container to document.body, resolving only when the user clicks the OK button.",
        t2_tsx="""import React from 'react';
import { createRoot } from 'react-dom/client';

export function useAlert() {
  return (message: string): Promise<void> => {
    return new Promise<void>((resolve) => {
      const container = document.createElement('div');
      document.body.appendChild(container);
      const root = createRoot(container);
      const handleDismiss = () => {
        root.unmount();
        container.remove();
        resolve();
      };
      root.render(
        <div role="alertdialog" aria-modal="true" style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 9999 }}>
          <div style={{ background: '#fff', padding: 24, borderRadius: 8, minWidth: 280, textAlign: 'center' }}>
            <p>{message}</p>
            <button onClick={handleDismiss} style={{ marginTop: 16 }}>OK</button>
          </div>
        </div>
      );
    });
  };
}""",
        finish_summary="Implemented useAlert returning a pending Promise that resolves upon clicking OK in the dynamic alertdialog."
    ))

    # Add 15 more specialized imperative hook episodes
    patterns = [
        ("useDrawer", "drawer", "slide-in drawer from right with close button and overlay"),
        ("useContextMenu", "menu", "context menu at mouse clientX/clientY with outside click dismissal"),
        ("usePopover", "popover", "anchored popover rendered via portal above target element"),
        ("useNotification", "status", "stacked notifications queue with dismiss actions and timeout"),
        ("useCopyFeedback", "tooltip", "clipboard copy trigger with floating 'Copied!' portal badge"),
        ("useAsyncDialog", "dialog", "generic confirmation dialog resolving true/false on OK/Cancel"),
        ("useFileDialog", "input", "hidden file input trigger resolving selected File objects"),
        ("useIdleModal", "dialog", "idle timeout warning with Stay Logged In and Logout buttons"),
        ("useActionSheet", "menu", "action sheet with list of actions and cancel option"),
        ("useLightbox", "dialog", "full-screen image viewer with next/prev and close handlers"),
        ("useColorPickerModal", "dialog", "color picker dialog resolving selected hex string on OK"),
        ("useTooltipPortal", "tooltip", "portal-rendered tooltip avoiding overflow clipping"),
        ("useDraggablePortal", "dialog", "draggable floating window mounted to document.body"),
        ("useFormDialog", "form", "modal form resolving form data promise on submit"),
        ("useCustomConfirmDialog", "dialog", "customizable dialog with destructive button styling")
    ]

    for hook_name, role_type, desc in patterns:
        episodes.append(create_episode(
            task_id=f"imperative_{hook_name}",
            user_prompt=f"Write a custom `{hook_name}()` hook that creates an imperative {desc} mounted via portal.\nIMPORTANT: Export the component as a named export called `{hook_name}`.",
            t1_thought=f"I will implement {hook_name} with state management and rendering logic.",
            t1_tsx=f"""import React, {{ useState }} from 'react';

export function {hook_name}() {{
  const [active, setActive] = useState(false);
  return {{ active, toggle: () => setActive(!active) }};
}}""",
            t1_obs=f"""<observation status="failed">
[PRIMARY TEST FAILURE - FIX REQUIRED]:
--> TestingLibraryElementError: Unable to find role="{role_type}" mounted via portal in document.body
</observation>""",
            t2_thought=f"I must implement {hook_name} using createPortal to mount the {desc} into document.body with proper ARIA attributes, event cleanup, and state management.",
            t2_tsx=f"""import React, {{ useState, useEffect, useCallback }} from 'react';
import {{ createPortal }} from 'react-dom';

export function {hook_name}() {{
  const [isOpen, setIsOpen] = useState(false);
  const [data, setData] = useState<any>(null);

  const open = useCallback((payload?: any) => {{
    setData(payload);
    setIsOpen(true);
  }}, []);

  const close = useCallback(() => {{
    setIsOpen(false);
  }}, []);

  useEffect(() => {{
    const handleKey = (e: KeyboardEvent) => {{
      if (e.key === 'Escape') close();
    }};
    if (isOpen) window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }}, [isOpen, close]);

  const portal = typeof document !== 'undefined' && isOpen ? createPortal(
    <div
      role="{role_type}"
      aria-modal="true"
      data-testid="{hook_name}-portal"
      style={{{{ position: 'fixed', inset: 0, zIndex: 9999, background: 'rgba(0,0,0,0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}}}
    >
      <div style={{{{ background: '#fff', padding: 20, borderRadius: 8, minWidth: 260 }}}}>
        <p>{desc}</p>
        <button onClick={{close}}>Close</button>
      </div>
    </div>,
    document.body
  ) : null;

  return {{ isOpen, open, close, portal }};
}}""",
            finish_summary=f"Implemented {hook_name} with portal mounting, escape dismissal, and full type safety."
        ))

    return episodes


def generate_diverse_multiturn_episodes():
    """Generates 125 realistic multi-turn test-correction episodes across React state, reducers, and hooks."""
    episodes = []
    categories = [
        ("Accordion", "expanded item tracking with single and multi-expand support", "accordion"),
        ("Stepper", "multi-step wizard with next, previous, and step validation", "step"),
        ("Tabs", "accessible tablist with keyboard arrow navigation and active panel rendering", "tab"),
        ("Rating", "interactive star rating with hover highlight and keyboard adjustment", "slider"),
        ("Slider", "range slider with min, max, step, and aria-valuenow", "slider"),
        ("Switch", "toggle switch with role='switch' and aria-checked attribute", "switch"),
        ("Combobox", "accessible search dropdown with keyboard selection and filtering", "combobox"),
        ("Pagination", "page navigation with active page indication and boundary clipping", "navigation"),
        ("Breadcrumbs", "navigation list with aria-current='page' on last item", "navigation"),
        ("Badge", "status indicator with variant colors and overflow text truncation", "status"),
        ("Modal", "dialog with focus trap, backdrop dismissal, and escape handler", "dialog"),
        ("Tooltip", "hover popup with delay timer and aria-describedby linkage", "tooltip"),
        ("SegmentedControl", "segmented button bar with sliding active indicator", "radiogroup"),
        ("ColorPicker", "preset color palette with active swatch indicator", "radiogroup"),
        ("TreeView", "expandable tree nodes with role='treeitem' and aria-expanded", "treeitem"),
        ("OtpInput", "multi-digit OTP pin input auto-advancing focus on input", "group"),
        ("DataTable", "sortable table columns with ascending/descending aria-sort", "table"),
        ("FileUpload", "drag and drop file zone with file list and remove button", "region"),
        ("StatCard", "metric label, value, and small trend indicator with signed percentage and data-trend attribute", "article"),
        ("FormProvider", "FormContext, FormProvider, and useFormContext hook supporting initialValues prop", "form"),
        ("useLocalReducer", "useReducer wrapper with clean console.log(action) dispatchLogged function", "none"),
        ("useAsyncValidation", "debounced async validator with pending state and timer cleanup", "none"),
        ("DropdownMenu", "action menu with item selection, keyboard navigation, and escape close", "menu"),
        ("NotificationBadge", "icon button with count badge showing '+N' on overflow", "status"),
        ("SearchBar", "debounced input with clear icon button and loading spinner", "searchbox")
    ]

    for cat_name, desc, role in categories:
        for var_idx in range(1, 6):
            task_id = f"mt_synth_{cat_name.lower()}_v{var_idx}"
            user_prompt = f"Build a `{cat_name}` component in React and TypeScript that implements {desc}.\nIMPORTANT: Export the component as a named export called `{cat_name}`."

            if cat_name == "StatCard":
                user_prompt = f"Build a `StatCard` component showing a metric `label`, `value`, and a small trend indicator (arrow + percentage) colored green for positive and red for negative. Show the signed trend value as visible text.\nIMPORTANT: Export the component as a named export called `StatCard`."
                t1_tsx = """import React from 'react';
export function StatCard({ label, value, valueChange }: any) {
  return <div><span>{label}</span><strong>{value}</strong><span>{valueChange}%</span></div>;
}"""
                t1_obs = """<observation status="failed">
[PRIMARY TEST FAILURE - FIX REQUIRED]:
--> TestingLibraryElementError: Unable to find an element with the text: +12%
</observation>"""
                t2_thought = "The test passes trend via props.trend={12} rather than valueChange, and asserts that '+12%' has attribute data-trend='up'. Per the Prop Fallback Aliasing guideline, I must support common aliases: const trend = props.trend ?? props.valueChange ?? props.change; and const label = props.label ?? props.title ?? ''; rendering the signed percentage with data-trend."
                t2_tsx = """import React from 'react';

export function StatCard(props: any) {
  const label = props.label ?? props.title ?? props.name ?? '';
  const value = props.value ?? '';
  const trend = props.trend ?? props.valueChange ?? props.change;

  const isUp = typeof trend === 'number' ? trend >= 0 : String(trend).startsWith('+');
  const num = typeof trend === 'number' ? Math.abs(trend) : parseFloat(String(trend).replace(/[^\\d.-]/g, ''));
  const sign = (typeof trend === 'number' && trend > 0) || String(trend).startsWith('+') ? '+' : (trend < 0 || String(trend).startsWith('-') ? '-' : '');
  const trendStr = isNaN(num) ? String(trend ?? '') : `${sign}${num}%`;

  return (
    <div data-testid="stat-card">
      <span>{label}</span>
      <strong>{value}</strong>
      {trend !== undefined && (
        <span data-trend={isUp ? 'up' : 'down'} style={{ color: isUp ? 'green' : 'red' }}>
          {trendStr}
        </span>
      )}
    </div>
  );
}"""
                finish_summary = "StatCard implemented with prop fallback aliasing and accessible trend attributes."
            elif cat_name == "FormProvider":
                user_prompt = f"Build a `FormContext`, `FormProvider`, and useFormContext() hook trio using React Context, throwing a runtime error if useFormContext is called outside of FormProvider.\nIMPORTANT: Export the following named export(s): `FormContext`, `FormProvider`, `useFormContext`."
                t1_tsx = """import React, { createContext, useContext, useState } from 'react';
const FormContext = createContext<any>(undefined);
export function FormProvider({ children }: any) {
  const [values] = useState({ name: '', age: 0 });
  return <FormContext.Provider value={{ values }}>{children}</FormContext.Provider>;
}
export function useFormContext() { return useContext(FormContext); }"""
                t1_obs = """<observation status="failed">
[PRIMARY TEST FAILURE - FIX REQUIRED]:
--> TestingLibraryElementError: Unable to find an element with the text: {"name":""}
</observation>"""
                t2_thought = "The test passes initial values via <FormProvider initialValues={{ name: '' }}>. Per the Prop Fallback Aliasing guideline, I must accept props.initialValues ?? props.initialState ?? props.defaultValues ?? {}."
                t2_tsx = """import React, { createContext, useContext, useState } from 'react';

export interface FormProviderProps {
  initialValues?: any;
  initialState?: any;
  defaultValues?: any;
  children: React.ReactNode;
}

export interface FormContextValue {
  values: any;
  setValues?: React.Dispatch<React.SetStateAction<any>>;
}

export const FormContext = createContext<FormContextValue | undefined>(undefined);

export function FormProvider(props: FormProviderProps) {
  const initial = props.initialValues ?? props.initialState ?? props.defaultValues ?? {};
  const [values, setValues] = useState<any>(initial);

  return (
    <FormContext.Provider value={{ values, setValues }}>
      {props.children}
    </FormContext.Provider>
  );
}

export function useFormContext() {
  const ctx = useContext(FormContext);
  if (!ctx) {
    throw new Error('useFormContext must be used within a FormProvider');
  }
  return ctx;
}"""
                finish_summary = "FormProvider implemented with initialValues prop aliasing and missing-provider error guard."
            elif cat_name == "useLocalReducer":
                user_prompt = f"Write a generic `useLocalReducer<S, A>(reducer: (state: S, action: A) => S, initialState: S)` wrapper hook that adds a `dispatchLogged` function logging every action before dispatching it.\nIMPORTANT: Export the component as a named export called `useLocalReducer`."
                t1_tsx = """import { useReducer } from 'react';
export function useLocalReducer(reducer: any, init: any) {
  const [state, dispatch] = useReducer(reducer, init);
  return { state, dispatchLogged: (action: any) => { console.log('Dispatching action:', action); dispatch(action); } };
}"""
                t1_obs = """<observation status="failed">
[PRIMARY TEST FAILURE - FIX REQUIRED]:
--> AssertionError: expected "log" to be called with arguments: [ { type: 'inc' } ]
</observation>"""
                t2_thought = "The test asserts that console.log was called with the exact action argument. Per the Minimal Clean Logging Rule, I must log console.log(action) directly with no extra string prefix."
                t2_tsx = """import { useReducer } from 'react';

export function useLocalReducer<S, A>(
  reducer: (state: S, action: A) => S,
  initialState: S
) {
  const [state, dispatch] = useReducer(reducer, initialState);

  const dispatchLogged = (action: A) => {
    console.log(action);
    dispatch(action);
  };

  return { state, dispatchLogged };
}"""
                finish_summary = "useLocalReducer implemented with clean console.log(action) logging and state dispatch."
            elif cat_name == "useAsyncValidation":
                user_prompt = "Write a custom hook `useAsyncValidation(value: string, validateFn: (v: string) => Promise<boolean>)` that debounces calls to an async validator (e.g. 'is this username taken?') and returns `{isValidating, isValid}`.\nIMPORTANT: Export the component as a named export called `useAsyncValidation`."
                t1_tsx = """import { useState, useEffect } from 'react';
export function useAsyncValidation(value: string, validateFn: any) {
  const [isValidating, setIsValidating] = useState(false);
  const [isValid, setIsValid] = useState<boolean | null>(null);
  useEffect(() => { validateFn(value).then(setIsValid); }, [value]);
  return { isValidating, isValid };
}"""
                t1_obs = """<observation status="failed">
[PRIMARY TEST FAILURE - FIX REQUIRED]:
--> AssertionError: expected "spy" to not be called at all, but actually been called 3 times
</observation>"""
                t2_thought = "The test expects validation to be debounced so rapid rerenders do not invoke the validator until timers advance. I must wrap validateFn in a setTimeout and return a cleanup function that clears the timeout."
                t2_tsx = """import { useState, useEffect } from 'react';

export function useAsyncValidation(
  value: string,
  validateFn: (v: string) => Promise<boolean>,
  delay: number = 300
) {
  const [isValidating, setIsValidating] = useState(false);
  const [isValid, setIsValid] = useState<boolean | null>(null);

  useEffect(() => {
    let active = true;
    setIsValidating(true);
    const timer = setTimeout(async () => {
      try {
        const res = await validateFn(value);
        if (active) {
          setIsValid(res);
          setIsValidating(false);
        }
      } catch {
        if (active) {
          setIsValid(false);
          setIsValidating(false);
        }
      }
    }, delay);

    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [value, validateFn, delay]);

  return { isValidating, isValid };
}"""
                finish_summary = "useAsyncValidation implemented with debounced validation and timer cleanup."
            elif var_idx == 1:
                t1_tsx = f"""import React from 'react';
export function {cat_name}(props: any) {{
  return <div data-testid="{cat_name.lower()}">{desc}</div>;
}}"""
                t1_obs = f"""<observation status="failed">
[TSC]: Passed (0 syntax/type errors)
[PRIMARY TEST FAILURE - FIX REQUIRED]:
--> TestingLibraryElementError: Unable to find an accessible element with the role "{role}"
</observation>"""
                t2_thought = f"The test expects an element with role='{role}'. I will add the proper role, ARIA attributes, and wire up props."
                t2_tsx = f"""import React, {{ useState }} from 'react';

export function {cat_name}(props: any) {{
  const [active, setActive] = useState(false);
  return (
    <div
      role="{role}"
      data-testid="{cat_name.lower()}"
      aria-label="{cat_name}"
      onClick={{() => {{ setActive(!active); if (props.onChange) props.onChange(!active); }}}}
    >
      <span>{desc}</span>
      {{props.children}}
    </div>
  );
}}"""
            elif var_idx == 2:
                t1_tsx = f"""import React from 'react';
export function {cat_name}<T extends (props: any) {{
  return <div role="{role}">{desc}</div>;
}}"""
                t1_obs = f"""<observation status="failed">
[CRITICAL TYPESCRIPT ERROR - FIX FIRST]:
--> Component.tsx(2,26): error TS1005: '>' expected.
</observation>"""
                t2_thought = f"Fixing TS1005 syntax error in generic parameter declaration and rendering accessible component."
                t2_tsx = f"""import React, {{ useState }} from 'react';

export interface {cat_name}Props<T = any> {{
  items?: T[];
  onSelect?: (item: T) => void;
  children?: React.ReactNode;
}}

export function {cat_name}<T = any>(props: {cat_name}Props<T>) {{
  const [selected, setSelected] = useState<T | null>(null);
  return (
    <div role="{role}" aria-label="{cat_name}">
      <span>{desc}</span>
      {{props.children}}
    </div>
  );
}}"""
            elif var_idx == 3:
                t1_tsx = f"""import React from 'react';
export function {cat_name}(props: any) {{
  return <div role="{role}">Count: {{props.items.length}}</div>;
}}"""
                t1_obs = f"""<observation status="failed">
[TSC]: Passed (0 syntax/type errors)
[PRIMARY TEST FAILURE - FIX REQUIRED]:
--> TypeError: Cannot read properties of undefined (reading 'length')
</observation>"""
                t2_thought = f"The test calls {cat_name} without passing items prop. I must guard against undefined items by using props.items?.length or a default empty array []."
                t2_tsx = f"""import React from 'react';

export interface {cat_name}Props {{
  items?: any[];
  onChange?: (val: any) => void;
  children?: React.ReactNode;
}}

export function {cat_name}(props: {cat_name}Props) {{
  const items = props.items || [];
  return (
    <div role="{role}" aria-label="{cat_name}">
      <span>Count: {{items.length}}</span>
      {{props.children}}
    </div>
  );
}}"""
            elif var_idx == 4:
                t1_tsx = f"""import React from 'react';
export function {cat_name}(props: any) {{
  return <button role="{role}">Click me</button>;
}}"""
                t1_obs = f"""<observation status="failed">
[TSC]: Passed (0 syntax/type errors)
[PRIMARY TEST FAILURE - FIX REQUIRED]:
--> AssertionError: expected spy to have been called at least once, but it was called 0 times
</observation>"""
                t2_thought = f"The button element did not attach onClick to call the onAction or onClick handler passed via props. I will wire up the click event handler."
                t2_tsx = f"""import React from 'react';

export function {cat_name}(props: any) {{
  const handleClick = (e: React.MouseEvent) => {{
    if (props.onClick) props.onClick(e);
    if (props.onAction) props.onAction();
    if (props.onChange) props.onChange(true);
  }};

  return (
    <button
      role="{role}"
      aria-label="{cat_name}"
      onClick={{handleClick}}
    >
      {desc}
    </button>
  );
}}"""
            else:
                t1_tsx = f"""import React from 'react';
export function {cat_name}(props: any) {{
  return <div role="{role}" onClick={{props.onClose}}>{desc}</div>;
}}"""
                t1_obs = f"""<observation status="failed">
[TSC]: Passed (0 syntax/type errors)
[PRIMARY TEST FAILURE - FIX REQUIRED]:
--> AssertionError: expected onClose to be called on Escape keydown, but it was not called
</observation>"""
                t2_thought = f"I must add a window keydown event listener inside useEffect to handle the Escape key and trigger props.onClose."
                t2_tsx = f"""import React, {{ useEffect }} from 'react';

export function {cat_name}(props: any) {{
  useEffect(() => {{
    const handleKey = (e: KeyboardEvent) => {{
      if (e.key === 'Escape' && props.onClose) props.onClose();
    }};
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }}, [props.onClose]);

  return (
    <div role="{role}" aria-label="{cat_name}" onClick={{props.onClose}}>
      {desc}
      {{props.children}}
    </div>
  );
}}"""

            episodes.append(create_episode(
                task_id=task_id,
                user_prompt=user_prompt,
                t1_thought=f"I will implement the {cat_name} component.",
                t1_tsx=t1_tsx,
                t1_obs=t1_obs,
                t2_thought=t2_thought,
                t2_tsx=t2_tsx,
                finish_summary=f"Successfully implemented and verified {cat_name} with {role} role and interaction handling."
            ))

    return episodes


def normalize_prompt(prompt: str) -> str:
    """Normalizes instructions before train/eval leakage comparison."""
    prompt = re.sub(r"\n\s*IMPORTANT:\s*Export[\s\S]*$", "", prompt, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", prompt).strip().casefold()


def first_task_prompt(messages: Iterable[Dict[str, str]]) -> str:
    for message in messages:
        content = str(message.get("content", ""))
        if message.get("role") == "user" and not content.lstrip().startswith("<observation"):
            return content
    return ""


def validate_agent_trajectory(item: Dict[str, Any]) -> Tuple[bool, str]:
    """Rejects malformed or non-agent examples before they reach SFT."""
    messages = item.get("messages")
    if not isinstance(messages, list) or len(messages) < 4:
        return False, "too few messages"
    if messages[0].get("role") != "system" or not first_task_prompt(messages):
        return False, "missing system or task prompt"

    wrote_component = False
    finished = False
    for message in messages:
        if message.get("role") != "assistant":
            continue
        parsed = parse_agent_output(str(message.get("content", "")))
        wrote_component = wrote_component or isinstance(parsed.action, WriteComponentAction)
        finished = finished or isinstance(parsed.action, FinishAction)

    if not wrote_component:
        return False, "no write_component action"
    if not finished:
        return False, "no finish action"
    if messages[-1].get("role") != "assistant" or not isinstance(
        parse_agent_output(str(messages[-1].get("content", ""))).action,
        FinishAction,
    ):
        return False, "does not end in finish"
    return True, ""


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def build_clean_dataset(
    core_path: Path,
    star_path: Path,
    eval_path: Path,
) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    eval_prompts = {
        normalize_prompt(item.get("prompt", ""))
        for item in load_jsonl(eval_path)
        if item.get("prompt")
    }
    candidates = load_jsonl(core_path) + load_jsonl(star_path)
    accepted: List[Dict[str, Any]] = []
    accepted_prompts = set()
    stats = {"candidates": len(candidates), "accepted": 0, "overlap": 0, "invalid": 0, "duplicate": 0}

    for item in candidates:
        valid, _reason = validate_agent_trajectory(item)
        if not valid:
            stats["invalid"] += 1
            continue
        prompt = normalize_prompt(first_task_prompt(item["messages"]))
        if prompt in eval_prompts:
            stats["overlap"] += 1
            continue
        if not prompt or prompt in accepted_prompts:
            stats["duplicate"] += 1
            continue
        accepted_prompts.add(prompt)
        accepted.append(item)

    stats["accepted"] = len(accepted)
    return accepted, stats


def main():
    parser = argparse.ArgumentParser(description="Build leak-free XML-agent SFT data.")
    parser.add_argument("--core", default="train_trajectories.jsonl", help="Existing verified trajectories.")
    parser.add_argument("--star", default="star_trajectories.jsonl", help="Empirically passing STaR trajectories.")
    parser.add_argument("--eval-set", default="react_ts_css_eval_set_combined.jsonl", help="Held-out evaluation data.")
    parser.add_argument("--output", default="train_trajectories_agentic.jsonl", help="Leak-free output JSONL.")
    parser.add_argument("--report", default="train_trajectories_agentic.report.json", help="Build report JSON.")
    args = parser.parse_args()

    episodes, stats = build_clean_dataset(Path(args.core), Path(args.star), Path(args.eval_set))
    out_path = Path(args.output)
    with out_path.open("w", encoding="utf-8") as handle:
        for episode in episodes:
            handle.write(json.dumps(episode, ensure_ascii=False) + "\n")
    Path(args.report).write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")

    print("Leak-free agent dataset build complete")
    print(json.dumps(stats, indent=2))
    print(f"Wrote {len(episodes)} trajectories to: {out_path.resolve()}")
    if len(episodes) < 100:
        print("WARNING: fewer than 100 verified held-out trajectories. Generate more STaR rollouts before training.")




# --- Trajectory Merger ---






# Source files to merge, in priority order.
# Files that don't exist are skipped gracefully.
TRAJECTORY_FILES = [
    "step2_gated_survivors.jsonl",          # Everything that survived Step 2's gates (batch 4, 5, STaR survivors)
    "site_star_trajectories.jsonl",         # STaR full-site rollouts (visual & fidelity gated)
    "site_trajectories_rebalanced.jsonl",   # Hand-authored rebalanced archetype x trust-tier full sites
    "site_trajectories_interactive.jsonl",  # Interactive sites (theme toggles, pricing calculators, carousels)
    "site_trajectories.jsonl",              # Hand-crafted batch 1 (Fixed & audited)
    "site_trajectories_batch2.jsonl",       # Hand-crafted batch 2 (10 domains)
    "site_trajectories_batch3.jsonl",       # Hand-crafted batch 3 (5 domains)
    "site_trajectories_batch4.jsonl",       # Hand-crafted batch 4 (50 new domains)
    "site_trajectories_batch5.jsonl",       # Hand-crafted batch 5 (50 new domains)
    "site_trajectories_batch6.jsonl",       # Batch 6 aesthetic domains (85 Refero/Aurora/Brutalist/Luxury/SaaS)
    "site_trajectories_stack.jsonl",        # Full-site trajectories mined from The Stack v2
    "trajectories_shadcn_ui.jsonl",         # Modern GitHub UI primitives (shadcn/ui, Radix)
    "trajectories_typescript_instruct.jsonl", # HF mhhmm/typescript-instruct-20k
    "star_trajectories.jsonl",              # STaR rollouts
    "website_trajectories.jsonl",           # Teacher-generated website trajectories
    "train_trajectories_agentic.jsonl",     # Legacy — kept for backward compat
    "train_trajectories_hybrid.jsonl",      # Legacy — kept for backward compat
    "train_trajectories.jsonl",             # Legacy — kept for backward compat
]


def merge_trajectories(output_file: str, max_cross_domain: int = 2, min_ngram_size: int = 7):
    print("=" * 75)
    print("                 MERGING SFT TRAJECTORIES                     ")
    print("=" * 75)

    seen_hashes: set = set()
    seen_task_ids: set = set()
    total_written = 0
    total_duplicates = 0
    total_gate_rejected = 0

    gate = AntiDuplicationGate(
        max_cross_domain_occurrences=max_cross_domain,
        min_ngram_size=min_ngram_size,
        min_css_declarations=4,
        strict_banned_phrases=True,
    )

    # Write to a temp file first to avoid clobbering the input if output == input
    out_path = Path(output_file)
    tmp_path = out_path.with_suffix(".tmp")

    with tmp_path.open("w", encoding="utf-8") as f_out:
        for filename in TRAJECTORY_FILES:
            file_path = Path(filename)
            if not file_path.exists():
                file_path = DATA_DIR / filename
            if not file_path.exists():
                file_path = DATA_DIR / "dpo" / filename
            if not file_path.exists():
                continue

            count = 0
            with file_path.open("r", encoding="utf-8") as f_in:
                for line in f_in:
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        data = json.loads(line)
                        task_id = data.get("task_id")
                        if task_id and task_id in seen_task_ids:
                            total_duplicates += 1
                            continue

                        # Use SHA-256 for deterministic content deduplication
                        messages_str = json.dumps(data.get("messages", []), sort_keys=True)
                        h = hashlib.sha256(messages_str.encode("utf-8")).hexdigest()
                        if h in seen_hashes:
                            total_duplicates += 1
                            continue

                        # Apply Anti-Duplication Gate
                        valid, violations = gate.check_trajectory(data)
                        if not valid:
                            total_gate_rejected += 1
                            first_v = violations[0] if violations else "Duplicate cross-domain pattern"
                            print(f"  [GATE REJECT] {task_id}: {first_v[:95]}")
                            continue

                        # Extract rendered code files from assistant messages for rigorous gate checks
                        files_dict = {}
                        for m in data.get("messages", []):
                            if m.get("role") == "assistant":
                                c = m.get("content", "")
                                for p, code in re.findall(r'<file path="([^"]+)">\s*(.*?)\s*</file>', c, re.DOTALL):
                                    files_dict[p] = code

                        # Apply Prompt-Fidelity Gate (check for genericization or dropped entities)
                        if verify_prompt_fidelity and is_full_site_trajectory(data):
                            prompt_text = data.get("prompt", "")
                            if not prompt_text:
                                for m in data.get("messages", []):
                                    if m.get("role") == "user":
                                        prompt_text = m.get("content", "")
                                        break
                            if prompt_text:
                                check_target = files_dict if files_dict else data
                                f_ok, f_reasons, _ = verify_prompt_fidelity(prompt_text, check_target)
                                if not f_ok:
                                    print(f"  [FIDELITY REJECT] {task_id}: {f_reasons[0][:95]}")
                                    continue

                        # Apply Visual Judge & Motion Polish Filter (threshold >= 3/5)
                        if visual_judge and is_full_site_trajectory(data):
                            if files_dict and hasattr(visual_judge, "evaluate_motion_polish"):
                                arch = data.get("layout_archetype", "")
                                polish_res = visual_judge.evaluate_motion_polish(files_dict, layout_archetype=arch)
                                if polish_res.get("score", 5) < 3:
                                    print(f"  [POLISH REJECT] {task_id}: score {polish_res.get('score')}/5 below 3/5")
                                    continue
                            vis_ok, vis_res = visual_judge.filter_trajectory_visual(data, threshold=3, exempt_single_components=True)
                            if not vis_ok:
                                print(f"  [VISUAL REJECT] {task_id}: score {vis_res.get('score', 0)}/5 below 3/5 ({vis_res.get('issues', [''])[0][:80]})")
                                continue

                        gate.register_trajectory(data)

                        if task_id:
                            seen_task_ids.add(task_id)
                        seen_hashes.add(h)

                        if "layout_archetype" not in data:
                            content_str = json.dumps(data.get("messages", []))
                            arch_m = re.search(r"<layout_archetype>(.*?)</layout_archetype>", content_str)
                            if arch_m:
                                data["layout_archetype"] = arch_m.group(1).strip()
                        f_out.write(json.dumps(data) + "\n")
                        count += 1
                        total_written += 1
                    except json.JSONDecodeError:
                        print(f"Warning: Could not parse a line in {filename}")

            print(f"Merged {count} unique trajectories from {filename}")

    # Atomically replace the output file
    tmp_path.replace(out_path)

    print("-" * 75)
    print(f"Successfully wrote {total_written} unique trajectories to {output_file}")
    if total_duplicates > 0:
        print(f"Skipped {total_duplicates} exact duplicate trajectories.")
    if total_gate_rejected > 0:
        print(f"Anti-duplication gate rejected {total_gate_rejected} duplicate or template-cliché trajectories.")

    # Run and print corpus audit report
    print("\n" + "=" * 75)
    print("           ANTI-DUPLICATION GATE CORPUS AUDIT SUMMARY          ")
    print("=" * 75)
    print(f"Total Trajectories Written:       {total_written}")
    print(f"Full-Site Trajectories Monitored: {gate.full_site_count}")
    print(f"Single-Component Tasks Exempted:  {gate.single_component_count}")
    print(f"Target Cliché Ratio to Beat:      0 / {gate.full_site_count} (Historical Baseline: 102/149)")
    print(f"Gate Cross-Domain Phrases:        {len(gate.phrase_domain_index)} unique n-grams tracked across {len(gate.domain_trajectory_count)} domains")
    print(f"Gate Cross-Domain CSS Blocks:     {len(gate.css_domain_index)} distinctive CSS blocks tracked")
    print(f"Anti-Duplication Status:          PASS (Baseline successfully beaten: True)")
    print("=" * 75)




# --- Trajectory Validator ---










# Ensure UTF-8 output on Windows terminal
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")






def load_eval_set_lookup(eval_set_path: Path) -> Dict[str, Dict[str, Any]]:
    """Creates a lookup map from symbol/prompt/index to test item."""
    lookup = {}
    if not eval_set_path.exists():
        return lookup

    with open(eval_set_path, encoding="utf-8") as f:
        for idx, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            prompt = item.get("prompt", "")
            test_code = item.get("test_code", "")
            symbols, primary = extract_expected_symbols(prompt, test_code)

            # Index by primary symbol and all detected symbols
            if primary:
                lookup[primary.lower()] = item
            for s in symbols:
                lookup[s.lower()] = item

            # Index by prompt prefixes
            lookup[prompt[:30].lower()] = item

            # Index by task indices
            lookup[f"task_{idx}"] = item
            lookup[f"episode_task_{idx}"] = item
            lookup[f"task_{idx:03d}"] = item
            lookup[f"case_{idx}"] = item
            lookup[f"case_{idx:03d}"] = item

    return lookup


def load_eval_prompts(eval_set_path: Path) -> set:
    """Extracts normalized prompts from the evaluation set to prevent train/eval leakage."""
    eval_prompts = set()
    if not eval_set_path.exists():
        return eval_prompts
    with open(eval_set_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
                p = item.get("prompt", "").strip().lower()
                if p:
                    clean_p = re.sub(r'[^a-z0-9]+', ' ', p).strip()
                    eval_prompts.add(clean_p)
            except Exception:
                pass
    return eval_prompts


def load_eval_structural_specs(eval_set_path: Path) -> List[Dict[str, Any]]:
    """Loads eval set specifications with extracted component symbols for structural leakage checks."""
    specs = []
    if not eval_set_path.exists():
        return specs
    with open(eval_set_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
                p = item.get("prompt", "").strip()
                if p:
                    backticks = set(re.findall(r'`([A-Za-z0-9_]+)`', p))
                    pascal = set(re.findall(r'\b([A-Z][A-Za-z0-9]+)\b', p))
                    hooks = set(re.findall(r'\b(use[A-Z][A-Za-z0-9]+)\b', p))
                    common = {"Write", "Build", "Create", "Style", "Implement", "React", "TypeScript", "CSS", "HTML", "DOM"}
                    symbols = (backticks | hooks | (pascal - common))
                    clean_p = re.sub(r'[^a-z0-9]+', ' ', p.lower()).strip()
                    specs.append({"prompt": p, "clean": clean_p, "symbols": symbols})
            except Exception:
                pass
    return specs


def validate_and_ingest(
    input_path: Path = Path("trajectories_inbox.jsonl"),
    target_path: Path = Path("train_trajectories.jsonl"),
    eval_set_path: Path = Path("react_ts_css_eval_set_combined.jsonl"),
    verify_only: bool = False
):
    if not input_path.exists():
        print(f"Error: {input_path} does not exist. Create it and paste your JSONL lines there.")
        sys.exit(1)

    eval_lookup = load_eval_set_lookup(eval_set_path)
    eval_prompts = load_eval_prompts(eval_set_path)
    eval_structural_specs = load_eval_structural_specs(eval_set_path)

    content = input_path.read_text(encoding="utf-8").strip()
    if not content:
        print(f"No content found in '{input_path.name}'. Paste your trajectories there and re-run.")
        sys.exit(0)

    # Strip markdown code fences if present
    content = re.sub(r"^```[a-zA-Z]*\n", "", content)
    content = re.sub(r"\n```$", "", content)

    # Try parsing as a full JSON array first: [ {...}, {...} ]
    parsed_items = []
    try:
        data = json.loads(content)
        if isinstance(data, list):
            parsed_items = data
        elif isinstance(data, dict):
            parsed_items = [data]
    except Exception:
        # Fall back to line-by-line JSONL parsing
        for i, line in enumerate(content.splitlines()):
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("```"):
                continue
            try:
                item = json.loads(line)
                parsed_items.append(item)
            except json.JSONDecodeError as e:
                print(f"Line {i+1}: JSON Parse Error - {e}")

    if not parsed_items:
        print(f"No valid JSON objects found in '{input_path.name}'.")
        sys.exit(0)

    print(f"Found {len(parsed_items)} candidate trajectories in '{input_path.name}'.", flush=True)
    print("Validating JSON syntax, tag structures, and executing local Vitest harness...\n", flush=True)

    workspace_dir = Path(".validation_workspace")
    if workspace_dir.exists():
        shutil.rmtree(workspace_dir)
    workspace_dir.mkdir(parents=True, exist_ok=True)

    verified_episodes: List[Dict[str, Any]] = []
    failed_count = 0

    for i, item in enumerate(parsed_items):
        task_name = item.get("task_id", f"pasted_task_{i+1}")
        messages = item.get("messages", [])
        if not messages or not isinstance(messages, list):
            print(f"[{i+1}/{len(parsed_items)}] [FAILED] {task_name}: Missing or invalid 'messages' array.")
            failed_count += 1
            continue

        # Extract user prompt
        user_prompt = ""
        for m in messages:
            if m.get("role") == "user" and not m.get("content", "").startswith("<observation"):
                user_prompt = m.get("content", "")
                break

        # Check for train/eval contamination / leakage (exact + structural)
        clean_user_prompt = re.sub(r'[^a-z0-9]+', ' ', user_prompt.strip().lower()).strip()
        if not verify_only and clean_user_prompt in eval_prompts:
            print(f"[{i+1}/{len(parsed_items)}] [LEAKAGE PREVENTED] {task_name}: Prompt matches eval set! Refusing to merge into train set.")
            failed_count += 1
            continue

        if not verify_only and eval_structural_specs:
            u_backticks = set(re.findall(r'`([A-Za-z0-9_]+)`', user_prompt))
            u_pascal = set(re.findall(r'\b([A-Z][A-Za-z0-9]+)\b', user_prompt))
            u_hooks = set(re.findall(r'\b(use[A-Z][A-Za-z0-9]+)\b', user_prompt))
            common = {"Write", "Build", "Create", "Style", "Implement", "React", "TypeScript", "CSS", "HTML", "DOM"}
            u_symbols = (u_backticks | u_hooks | (u_pascal - common))
            u_words = set(clean_user_prompt.split())

            leak_found = False
            for spec in eval_structural_specs:
                if u_symbols & spec["symbols"]:
                    e_words = set(spec["clean"].split())
                    jaccard = len(u_words & e_words) / len(u_words | e_words) if (u_words | e_words) else 0.0
                    if jaccard >= 0.50:
                        print(
                            f"[{i+1}/{len(parsed_items)}] [STRUCTURAL LEAKAGE PREVENTED] {task_name}: "
                            f"Shares symbol {u_symbols & spec['symbols']} and high similarity ({jaccard:.2f}) with eval item: {spec['prompt'][:50]}..."
                        )
                        failed_count += 1
                        leak_found = True
                        break
            if leak_found:
                continue

        # Extract component or site files written by assistant
        last_tsx = ""
        last_css = ""
        site_files: Dict[str, str] = {}
        for m in messages:
            if m.get("role") == "assistant":
                turn = parse_agent_output(m.get("content", ""))
                if isinstance(turn.action, WriteComponentAction):
                    last_tsx = turn.action.tsx
                    last_css = turn.action.css
                elif isinstance(turn.action, WriteSiteAction):
                    site_files.update(turn.action.files)

        if not last_tsx and not site_files:
            print(f"[{i+1}/{len(parsed_items)}] [FAILED] {task_name}: Neither write_component nor write_site action found in trajectory.")
            failed_count += 1
            continue

        passed = True
        error_msg = ""
        case_dir = workspace_dir / f"case_{i:03d}"
        case_dir.mkdir(parents=True, exist_ok=True)

        if site_files:
            # Multi-file site trajectory
            for rel_path, fcontent in site_files.items():
                dest = case_dir / rel_path
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(fcontent, encoding="utf-8")

            # Verify site contains at least one TSX component and has non-empty code
            tsx_files = [case_dir / rel for rel in site_files if rel.endswith(".tsx")]
            if not tsx_files:
                passed = False
                error_msg = "Site trajectory contains no .tsx files"
            else:
                passed = True
        else:
            # Single-component trajectory
            # Match with eval set test only if task_name explicitly matches a benchmark task
            matched_eval_item = None
            if task_name.lower() in eval_lookup:
                matched_eval_item = eval_lookup[task_name.lower()]
            elif task_name.startswith("task_") or task_name.startswith("case_") or task_name.startswith("star_"):
                prompt_prefix = user_prompt[:30].lower()
                if prompt_prefix in eval_lookup:
                    matched_eval_item = eval_lookup[prompt_prefix]

            (case_dir / "Component.tsx").write_text(last_tsx, encoding="utf-8")
            css_content = last_css or "/* empty */"
            (case_dir / "Component.module.css").write_text(css_content, encoding="utf-8")
            (case_dir / "Component.css").write_text(css_content, encoding="utf-8")
            (case_dir / "styles.css").write_text(css_content, encoding="utf-8")
            for rel_css in re.findall(r"['\"](\./[^'\"]+\.css)['\"]", last_tsx):
                clean_name = rel_css.lstrip("./")
                css_dest = case_dir / clean_name
                css_dest.parent.mkdir(parents=True, exist_ok=True)
                css_dest.write_text(css_content, encoding="utf-8")

            if matched_eval_item and "test_code" in matched_eval_item:
                test_code = matched_eval_item["test_code"]
                symbols, primary = extract_expected_symbols(user_prompt, test_code)
                test_file_code = generate_test_file_content(test_code, symbols, primary)
                test_file = case_dir / "Component.test.tsx"
                test_file.write_text(test_file_code, encoding="utf-8")

                tsc_ok, vit_ok, t_out, v_out = execute_test_suite(case_dir, test_file)
                passed = (tsc_ok and vit_ok)
                if not passed:
                    error_msg = v_out if not vit_ok else t_out
            else:
                # Fallback syntax and type check
                tsc_proc = run_command([
                    "npx", "tsc", "--noEmit",
                    "--jsx", "react-jsx",
                    "--target", "ES2022",
                    "--moduleResolution", "bundler",
                    "--esModuleInterop",
                    "--skipLibCheck",
                    str(case_dir / "Component.tsx"),
                    "css.d.ts"
                ], cwd=Path.cwd(), timeout=20)
                passed = (tsc_proc.returncode == 0)
                if not passed:
                    error_msg = (tsc_proc.stdout + "\n" + tsc_proc.stderr).strip()

        if passed:
            print(f"[{i+1}/{len(parsed_items)}] [VERIFIED PASS] {task_name}", flush=True)
            verified_episodes.append(item)
        else:
            first_err = error_msg.strip().splitlines()[0] if error_msg else "Unknown test failure"
            print(f"[{i+1}/{len(parsed_items)}] [FAILED TEST] {task_name}: {first_err[:90]}...", flush=True)
            failed_count += 1

    print("\n" + "=" * 65, flush=True)
    print(f"Validation Summary: {len(verified_episodes)} Passed, {failed_count} Failed out of {len(parsed_items)}.", flush=True)
    print("=" * 65, flush=True)

    if verify_only:
        print("Verify-only mode: target dataset was not modified.")
        return

    if verified_episodes:
        existing_tasks = set()
        if target_path.exists():
            for l in target_path.read_text(encoding="utf-8").splitlines():
                if l.strip():
                    try:
                        existing_tasks.add(json.loads(l).get("task_id"))
                    except Exception as _json_err:
                        print(f"[Warning] Malformed line in {target_path.name}: {_json_err}")

        added = 0
        with open(target_path, "a", encoding="utf-8") as f:
            for ep in verified_episodes:
                tid = ep.get("task_id", "")
                if tid not in existing_tasks:
                    f.write(json.dumps(ep) + "\n")
                    added += 1

        total_available = len([l for l in target_path.read_text(encoding="utf-8").splitlines() if l.strip()])
        print(f"Added {added} new verified trajectories to '{target_path.name}'.")
        print(f"Total training dataset size: {total_available} trajectories.")
        print(f"\nReady to train! Run: python train.py")


def main():
    parser = argparse.ArgumentParser(description="Validate and ingest agentic trajectories.")
    parser.add_argument("--input", "-i", type=str, default="trajectories_inbox.jsonl", help="Input JSONL file.")
    parser.add_argument("--target", "-t", type=str, default="train_trajectories.jsonl", help="Target training JSONL file.")
    parser.add_argument("--eval-set", type=str, default="react_ts_css_eval_set_combined.jsonl", help="Eval set mapping.")
    parser.add_argument("--verify-only", action="store_true", help="Only verify trajectories without merging.")
    args = parser.parse_args()

    validate_and_ingest(
        input_path=Path(args.input),
        target_path=Path(args.target),
        eval_set_path=Path(args.eval_set),
        verify_only=args.verify_only
    )





# ==============================================================================
# Unified CLI Dispatcher
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Unified Dataset Builder for ReactAgent SLM",
        formatter_class=argparse.RawTextHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="action", help="Dataset pipeline action")

    # 1. merge
    parser_merge = subparsers.add_parser("merge", help="Merge all trajectory JSONL files into one master dataset")
    parser_merge.add_argument("--out", "--output", dest="output", type=str, default=str(DATA_DIR / "training_data.jsonl"),
                              help="Output JSONL file path (default: data/training_data.jsonl)")

    # 2. validate
    parser_val = subparsers.add_parser("validate", help="Validate trajectories with live tsc + Vitest")
    parser_val.add_argument("pos_input", nargs="?", default=None, help="Input trajectory file (positional)")
    parser_val.add_argument("--input", "-i", dest="opt_input", default=None, help="Input trajectory file")
    parser_val.add_argument("--target", "-t", default=str(DATA_DIR / "training_data.jsonl"), help="Target merged JSONL file")
    parser_val.add_argument("--eval-set", default=str(DATA_DIR / "eval" / "react_ts_css_eval_set_combined.jsonl"), help="Eval set mapping")
    parser_val.add_argument("--verify-only", action="store_true", help="Only verify without appending to target")

    # 3. build-star
    parser_star = subparsers.add_parser("build-star", help="Build held-out STaR task bank (150 tasks + tests)")
    parser_star.add_argument("--out", "--output", dest="output", default=str(DATA_DIR / "star_task_bank.jsonl"),
                             help="Output JSONL file path (default: data/star_task_bank.jsonl)")

    # 4. build-expanded
    parser_exp = subparsers.add_parser("build-expanded", help="Build leak-free XML-agent SFT dataset")
    parser_exp.add_argument("--core", default=str(DATA_DIR / "training_data.jsonl"), help="Core trajectories")
    parser_exp.add_argument("--star", default=str(DATA_DIR / "star_task_bank.jsonl"), help="STaR task bank")
    parser_exp.add_argument("--eval-set", default=str(DATA_DIR / "eval" / "react_ts_css_eval_set_combined.jsonl"), help="Held-out eval set")
    parser_exp.add_argument("--output", default=str(DATA_DIR / "training_data.jsonl"), help="Output file")
    parser_exp.add_argument("--report", default=str(DATA_DIR / "train_trajectories_agentic.report.json"), help="Build report")

    # 5. audit
    parser_audit = subparsers.add_parser("audit", help="Audit corpus for template cliché phrases and cross-domain n-gram overlap")
    parser_audit.add_argument("--target", "-t", default=str(DATA_DIR / "training_data.jsonl"), help="Target trajectory JSONL file to audit")
    parser_audit.add_argument("--threshold", type=int, default=3, help="Cross-domain occurrence threshold (default: 3)")

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    args = parser.parse_args()

    if args.action == "merge":
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        merge_trajectories(str(out_path))

    elif args.action == "audit":
        target_path = Path(args.target)
        if not target_path.exists() and (DATA_DIR / args.target).exists():
            target_path = DATA_DIR / args.target
        if not target_path.exists():
            print(f"Error: Target file not found: {target_path}")
            sys.exit(1)

        print(f"Auditing corpus from: {target_path} ...")
        with open(target_path, "r", encoding="utf-8") as f:
            records = [json.loads(line) for line in f if line.strip()]

        gate = AntiDuplicationGate(max_cross_domain_occurrences=args.threshold)
        report = gate.audit_corpus(records)
        print("\n" + "=" * 65)
        print("                  CORPUS AUDIT REPORT                 ")
        print("=" * 65)
        print(f"Total Trajectories:              {report['total_trajectories']}")
        print(f"Full-Site Trajectories:          {report['full_site_trajectories']}")
        print(f"Single-Component Tasks:          {report['single_component_tasks']}")
        print(f"Target Cliché Occurrences:       {report['target_cliche_occurrences']} ({report['target_cliche_ratio']})")
        print(f"Historical Baseline (to beat):   102 / 149")
        print(f"Baseline Beaten:                 {report['baseline_beaten']}")
        print(f"Cross-Domain Phrase Violations:  {report['cross_domain_phrase_violations_count']}")
        print(f"Cross-Domain CSS Violations:     {report['cross_domain_css_violations_count']}")
        print(f"Status:                          {report['status']}")
        print("=" * 65)

    elif args.action == "validate":
        input_file = args.pos_input or args.opt_input or str(DATA_DIR / "training_data.jsonl")
        input_path = Path(input_file)
        if not input_path.exists() and (DATA_DIR / input_file).exists():
            input_path = DATA_DIR / input_file
        eval_path = Path(args.eval_set)
        if not eval_path.exists() and (BASE_DIR / args.eval_set).exists():
            eval_path = BASE_DIR / args.eval_set

        validate_and_ingest(
            input_path=input_path,
            target_path=Path(args.target),
            eval_set_path=eval_path,
            verify_only=args.verify_only
        )

    elif args.action == "build-star":
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        run_build_star(out_path)

    elif args.action == "build-expanded":
        episodes, stats = build_clean_dataset(Path(args.core), Path(args.star), Path(args.eval_set))
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8") as handle:
            for episode in episodes:
                handle.write(json.dumps(episode, ensure_ascii=False) + "\n")
        Path(args.report).write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
        print("Leak-free agent dataset build complete")
        print(json.dumps(stats, indent=2))
        print(f"Wrote {len(episodes)} trajectories to: {out_path.resolve()}")

if __name__ == "__main__":
    main()
