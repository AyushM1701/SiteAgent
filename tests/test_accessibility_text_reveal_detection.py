from agent.project_validator import run_accessibility_check


def test_plain_transition_class_does_not_trigger_text_reveal_error(tmp_path):
    component = tmp_path / "Hero.tsx"
    component.write_text(
        'export default function Hero() { return <section><h1 className="transition-colors">Hi</h1></section>; }',
        encoding="utf-8",
    )
    passed, errors, _ = run_accessibility_check(tmp_path)
    assert passed, errors


def test_unlabeled_split_text_still_triggers_text_reveal_error(tmp_path):
    component = tmp_path / "Hero.tsx"
    component.write_text(
        'export default function Hero() { return <section><h1>{splitText("Hi")}</h1></section>; }',
        encoding="utf-8",
    )
    passed, errors, _ = run_accessibility_check(tmp_path)
    assert not passed
    assert any("text-reveal" in error for error in errors)
