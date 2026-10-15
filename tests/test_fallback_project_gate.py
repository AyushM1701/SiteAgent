from agent.project_validator import find_fallback_components, find_unverified_contact_files, run_contract_check


def test_fallback_project_gate_finds_only_unfinished_sections(tmp_path):
    components = tmp_path / "src/components"
    components.mkdir(parents=True)
    (components / "Header.tsx").write_text(
        '<header data-fallback="true">Pending</header>', encoding="utf-8"
    )
    (components / "Hero.tsx").write_text(
        '<section id="hero">Ready</section>', encoding="utf-8"
    )
    assert find_fallback_components(tmp_path) == ["src/components/Header.tsx"]


def test_contact_gate_requires_email_and_phone_to_come_from_prompt(tmp_path):
    components = tmp_path / "src/components"
    components.mkdir(parents=True)
    (components / "Footer.tsx").write_text(
        '<footer><p>sales@example.org | +1 (800) 555-0199</p></footer>', encoding="utf-8"
    )
    assert find_unverified_contact_files(tmp_path, "Build a product site") == ["src/components/Footer.tsx"]
    assert find_unverified_contact_files(
        tmp_path, "Use sales@example.org and +1 (800) 555-0199 in the footer"
    ) == []


def test_contract_rejects_header_with_no_mobile_navigation(tmp_path):
    components = tmp_path / "src/components"
    components.mkdir(parents=True)
    (components / "Header.tsx").write_text(
        '<header><nav className="hidden md:flex"><a href="#hero">Home</a></nav></header>',
        encoding="utf-8",
    )
    passed, errors, _ = run_contract_check(tmp_path)
    assert not passed
    assert any("desktop navigation is hidden" in error for error in errors)
