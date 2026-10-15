from agent.repair_budget import focus_repair_errors, repair_timeout_seconds


def test_compiler_fix_is_focused_on_one_file_before_visual_repairs():
    errors=['[Rendering Contract Error] src/Hero.css contrast',
            '[TypeScript Error] src/Navbar.tsx(4): listener',
            '[TypeScript Error] src/Shop.tsx(5): listener',
            '[TypeScript Error] src/Navbar.tsx(6): cleanup']
    assert focus_repair_errors(errors)==[errors[1],errors[3]]


def test_local_repair_can_finish_at_observed_ten_tokens_per_second():
    timeout=repair_timeout_seconds(1800,{'tokens_per_second':10})
    assert timeout>180
    assert repair_timeout_seconds(4096,{'tokens_per_second':1})==600
    assert repair_timeout_seconds(1800,override='45')==45
