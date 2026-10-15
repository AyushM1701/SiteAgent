from agent.project_validator import run_rendering_contract_check


def test_unmounted_scene_does_not_satisfy_requested_three_d(tmp_path):
    (tmp_path / 'src').mkdir()
    (tmp_path / 'src/main.tsx').write_text("import App from './App';")
    (tmp_path / 'src/App.tsx').write_text('export default function App(){return <main>Flat page</main>}')
    (tmp_path / 'src/Unused.tsx').write_text('export default function Scene(){return <canvas/>}')
    errors = run_rendering_contract_check(tmp_path, 'Create a CSS 3D composition with a flat-view toggle')
    assert any('3D COMPOSITION' in error for error in errors)
    assert any('FLAT VIEW' in error for error in errors)


def test_reachable_styles_report_real_cta_contrast_failure(tmp_path):
    (tmp_path / 'src').mkdir()
    (tmp_path / 'src/main.tsx').write_text("import App from './App';")
    (tmp_path / 'src/App.tsx').write_text("import './App.css';export default function App(){return <button>Shop</button>}")
    (tmp_path / 'src/App.css').write_text('button{color:#a02d25;background:#a02d25}')
    assert any('TEXT CONTRAST' in error for error in run_rendering_contract_check(tmp_path, 'Store'))


def test_inert_cta_is_not_confused_with_a_form_submit_or_real_handler():
    from agent.site_quality import collect_site_rendering_diagnostics
    files={'src/Hero.tsx':'<button>Explore collection</button><form><button>Send</button></form><button onClick={() => setOpen(true)}>View cart</button>'}
    assert sum('INERT BUTTON' in error for error in collect_site_rendering_diagnostics(files)) == 1


def test_large_hero_heading_is_not_a_navigation_wordmark():
    from agent.site_quality import collect_site_rendering_diagnostics
    files={'Main.tsx':'<nav className="nav"><a href="#hero">Brand</a></nav><section id="hero" className="hero"><h1>Editorial title</h1></section>',
           'Main.css':'.hero h1{font-size:68px}'}
    assert not any('NAV TYPOGRAPHY' in error for error in collect_site_rendering_diagnostics(files))
