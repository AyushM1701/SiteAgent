import hashlib

import pytest

from agent.edit_actions import EditFileAction, ReplaceHunk, apply_edit
from agent.section_preflight import preflight_section_files


def test_accepts_valid_tsx_and_css():
    files = [("src/components/Hero.tsx", "export default function Hero() { return <main>Hello</main>; }"),
             ("src/components/Hero.css", ".hero { color: red; }\n@media (min-width: 600px) { .hero { color: blue; } }")]
    assert preflight_section_files(files) == []
    assert preflight_section_files([("Hero.css", '.icon { background: url("data:image/svg+xml,<svg></svg>"); }')]) == []


@pytest.mark.parametrize("path,source", [
    ("Hero.tsx", "export default function Hero() { return <main>Broken</main>"),
    ("Hero.css", ".hero { color: red;"),
    ("Hero.css", "<style>.hero { color: red; }</style>"),
    ("Hero.css", "</css>"),
    ("Hero.css", "<div>not styles</div>"),
    ("Hero.css", ".hero { color: red; }\n..."),
    ("Hero.css", "/* TODO: add styles */"),
    ("Hero.css", "/* empty styles */"),
    ("Hero.css", ""),
])
def test_rejects_parser_errors_and_css_envelopes(path, source):
    assert preflight_section_files([(path, source)])


def test_edit_rejects_invalid_css_without_overwriting(tmp_path):
    target = tmp_path / "Hero.css"
    original = ".hero { color: red; }"
    target.write_text(original, encoding="utf-8")
    action = EditFileAction(path="Hero.css", base_sha256=hashlib.sha256(original.encode()).hexdigest(),
                            hunks=[ReplaceHunk(before="red; }", after="red;")])
    with pytest.raises(ValueError, match="parser preflight"):
        apply_edit(tmp_path, action)
    assert target.read_text(encoding="utf-8") == original
