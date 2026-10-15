"""
Regression tests for the three bug fixes:
  A. JSON-envelope parser backtick-template-literal extraction
  B. Pre-write JSON envelope leak detection helper
  C. Dead-tab-state lint

Run with: python -m pytest tests/test_json_envelope_parser.py -v
"""
import sys
import re
from pathlib import Path
from typing import List, Tuple

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.agent_protocol import _try_parse_json_tool_call, WriteSiteAction


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _detect_json_envelope_leak(content: str) -> bool:
    """Mirrors the helper defined inline inside run_site_agent_on_example."""
    JSON_ENVELOPE_MARKERS = (
        '''"function": "write_site"''',
        '''"function": "write_component"''',
        '''"arguments":''',
    )
    BACKTICK_PATH_RE = re.compile(r'"src/components/[^"]+"\s*:`')
    if any(m in content for m in JSON_ENVELOPE_MARKERS):
        return True
    if BACKTICK_PATH_RE.search(content):
        return True
    return False


# ─────────────────────────────────────────────────────────────────────────────
# Group C-1: Pre-write leak detection
# ─────────────────────────────────────────────────────────────────────────────

class TestDetectJsonEnvelopeLeak:
    def test_clean_tsx_passes(self):
        code = "import React from 'react';\nexport default function Hero() { return <section/>; }"
        assert _detect_json_envelope_leak(code) is False

    def test_write_site_marker_detected(self):
        code = '''{"function": "write_site", "arguments": {"files": {}}}'''
        assert _detect_json_envelope_leak(code) is True

    def test_write_component_marker_detected(self):
        code = '''{"function": "write_component", "arguments": {}}'''
        assert _detect_json_envelope_leak(code) is True

    def test_arguments_key_detected(self):
        code = '''"arguments": {"files": {"src/components/Foo.tsx": "..."}}''' 
        assert _detect_json_envelope_leak(code) is True

    def test_backtick_path_marker_detected(self):
        code = '''"src/components/Features.tsx":`import React from "react";`'''
        assert _detect_json_envelope_leak(code) is True

    def test_clean_css_passes(self):
        code = ".hero { background: var(--bg-color); padding: 64px 24px; }"
        assert _detect_json_envelope_leak(code) is False


# ─────────────────────────────────────────────────────────────────────────────
# Group C-2: Parser — backtick template-literal payload
# ─────────────────────────────────────────────────────────────────────────────

_BACKTICK_PAYLOAD = """
{
  "tool_calls": [
    {
      "function": "write_site",
      "arguments": {
        "files": {
          "src/components/Features.tsx": `import React from 'react';
import './Features.css';
const Features = () => <section id="features"><h2>Features</h2></section>;
export default Features;`,
          "src/components/Features.css": `.features {
  padding: 64px 24px;
  background: var(--color-obsidian);
}`
        }
      }
    }
  ]
}
"""


class TestBacktickParserExtraction:
    def test_extracts_tsx_from_backtick_payload(self):
        turn = _try_parse_json_tool_call(_BACKTICK_PAYLOAD)
        assert turn is not None, "Parser should extract files from backtick payload"
        assert isinstance(turn.action, WriteSiteAction)
        paths = [p for p, _ in turn.action.files]
        assert "src/components/Features.tsx" in paths

    def test_extracts_css_from_backtick_payload(self):
        turn = _try_parse_json_tool_call(_BACKTICK_PAYLOAD)
        assert turn is not None
        paths = [p for p, _ in turn.action.files]
        assert "src/components/Features.css" in paths

    def test_extracted_tsx_is_clean_code(self):
        turn = _try_parse_json_tool_call(_BACKTICK_PAYLOAD)
        assert turn is not None
        tsx_content = next(c for p, c in turn.action.files if p.endswith(".tsx"))
        assert "import React" in tsx_content
        assert '"function"' not in tsx_content
        assert '"arguments"' not in tsx_content

    def test_extracted_css_is_clean_code(self):
        turn = _try_parse_json_tool_call(_BACKTICK_PAYLOAD)
        assert turn is not None
        css_content = next(c for p, c in turn.action.files if p.endswith(".css"))
        assert ".features" in css_content
        assert '"function"' not in css_content

    def test_multiple_files_in_one_envelope(self):
        import textwrap
        # Build with format to avoid backtick issue in Python string
        hdr_tsx = "import React from 'react'; export default function Header() { return <nav/>; }"
        hdr_css = ".header { position: sticky; top: 0; }"
        hero_tsx = "import React from 'react'; export default function Hero() { return <section/>; }"
        hero_css = ".hero { min-height: 80vh; }"
        payload = (
            '''{"function": "write_site", "arguments": {"files": {''' + "\n"
            + f'  "src/components/Header.tsx": `{hdr_tsx}`,' + "\n"
            + f'  "src/components/Header.css": `{hdr_css}`,' + "\n"
            + f'  "src/components/Hero.tsx": `{hero_tsx}`,' + "\n"
            + f'  "src/components/Hero.css": `{hero_css}`' + "\n"
            + "}}}}"
        )
        turn = _try_parse_json_tool_call(payload)
        assert turn is not None
        assert len(turn.action.files) == 4

    def test_plain_text_not_misidentified(self):
        plain = "Here is my thought about the Header section. I will build it now."
        turn = _try_parse_json_tool_call(plain)
        assert turn is None


# ─────────────────────────────────────────────────────────────────────────────
# Group B: Dead-tab-state lint
# ─────────────────────────────────────────────────────────────────────────────

from agent.style_ingest import check_dead_tab_state_lint

_DEAD_TAB_TSX = """
import React, { useState } from 'react';
const Pricing = () => {
  const [activeTab, setActiveTab] = useState('starter');
  return (
    <section id="pricing">
      <button className={`tab ${activeTab === 'starter' ? 'tab--active' : ''}`} onClick={() => setActiveTab('starter')}>Starter</button>
      <button className={`tab ${activeTab === 'pro' ? 'tab--active' : ''}`} onClick={() => setActiveTab('pro')}>Pro</button>
      <div>
        {['starter', 'pro'].map((tier) => (
          <div key={tier}><h3>{tier}</h3></div>
        ))}
      </div>
    </section>
  );
};
export default Pricing;
"""

_WORKING_TAB_TSX = """
import React, { useState } from 'react';
const Pricing = () => {
  const [activeTab, setActiveTab] = useState('starter');
  const TIERS = [{id: 'starter', name: 'Starter'}, {id: 'pro', name: 'Pro'}];
  return (
    <section id="pricing">
      <button className={`tab ${activeTab === 'starter' ? 'tab--active' : ''}`} onClick={() => setActiveTab('starter')}>Starter</button>
      <button className={`tab ${activeTab === 'pro' ? 'tab--active' : ''}`} onClick={() => setActiveTab('pro')}>Pro</button>
      <div>
        {TIERS.filter(t => t.id === activeTab).map((tier) => (
          <div key={tier.id}><h3>{tier.name}</h3></div>
        ))}
      </div>
    </section>
  );
};
export default Pricing;
"""

_TERNARY_TAB_TSX = """
import React, { useState } from 'react';
const Contact = () => {
  const [activeTab, setActiveTab] = useState('email');
  return (
    <section>
      <button className={`tab ${activeTab === 'email' ? 'is-active' : ''}`} onClick={() => setActiveTab('email')}>Email</button>
      <button className={`tab ${activeTab === 'phone' ? 'is-active' : ''}`} onClick={() => setActiveTab('phone')}>Phone</button>
      <div>
        {activeTab === 'email' ? (
          <p>Email: support@example.com</p>
        ) : (
          <p>Phone: +1 888 555 1234</p>
        )}
      </div>
    </section>
  );
};
export default Contact;
"""


class TestDeadTabStateLint:
    def test_detects_dead_tab_state_pattern(self):
        viols = check_dead_tab_state_lint(_DEAD_TAB_TSX, file_path="Pricing.tsx")
        assert len(viols) > 0, "Should detect dead tab state"
        assert "DEAD TAB STATE" in viols[0]
        assert "activeTab" in viols[0]

    def test_filter_pattern_passes(self):
        viols = check_dead_tab_state_lint(_WORKING_TAB_TSX, file_path="Pricing.tsx")
        assert len(viols) == 0, f"Filter pattern should pass. Got: {viols}"

    def test_ternary_conditional_render_passes(self):
        viols = check_dead_tab_state_lint(_TERNARY_TAB_TSX, file_path="Contact.tsx")
        assert len(viols) == 0, f"Ternary render should pass. Got: {viols}"

    def test_no_false_positive_on_non_tab_state(self):
        tsx = """
import React, { useState } from 'react';
const Comp = () => {
  const [isOpen, setIsOpen] = useState(False);
  return <div className={isOpen ? 'open' : ''} onClick={() => setIsOpen(!isOpen)} />;
};
"""
        viols = check_dead_tab_state_lint(tsx)
        assert len(viols) == 0
