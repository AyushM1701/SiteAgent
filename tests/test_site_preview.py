import subprocess
import ast
import html
import json
import re
import sys
import urllib.parse
from pathlib import Path
from types import SimpleNamespace
import pytest
from unittest.mock import Mock
from agent.style_ingest import build_site_root_css


@pytest.fixture
def server():
    root = Path(__file__).resolve().parents[1]
    tree = ast.parse((root/'server/app.py').read_text(encoding='utf8'))
    node = next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_scaffold_site_vite_runner')
    ns = dict(Path=Path, Any=object, BASE_DIR=root, re=re, json=json, html=html, sys=sys,
              urllib=urllib, build_site_root_css=build_site_root_css,
              _link_node_modules=Mock(), subprocess=SimpleNamespace(run=Mock()))
    exec(compile(ast.Module(body=[node],type_ignores=[]),'server/app.py','exec'),ns)
    return SimpleNamespace(**ns)


def test_preview_documents_use_one_entry_each(tmp_path, monkeypatch, server):
    monkeypatch.setattr(server.subprocess, 'run', Mock())
    server._scaffold_site_vite_runner(tmp_path, 'NexaFlow', {
        'src/components/Header.tsx': 'export default function Header(){return <header/>}',
        'src/components/Hero.tsx': 'export default function Hero(){return <section/>}',
        'src/components/Footer.tsx': 'export default function Footer(){return <footer/>}',
    }, brief={'font_heading':'Inter','font_body':'Inter'})
    vite = (tmp_path/'index.html').read_text()
    static = (tmp_path/'static-preview.html').read_text()
    assert 'preview.js' not in vite and 'preview.css' not in vite
    assert '/main.tsx' in vite
    assert '/main.tsx' not in static and './preview.js' in static
    assert 'Plus+Jakarta' not in vite and 'family=Inter' in vite
    app = (tmp_path/'App.tsx').read_text(encoding='utf8')
    assert app.index('<Header />') < app.index('<main ')
    assert app.index('</main>') < app.index('<Footer />')
    assert 'Skip to content' in app


def test_failed_bundle_does_not_serve_old_preview(tmp_path, monkeypatch, server):
    monkeypatch.setattr(server.subprocess, 'run', Mock(side_effect=subprocess.CalledProcessError(1,'esbuild')))
    (tmp_path/'static-preview.html').write_text('<script src="old.js"></script>')
    server._scaffold_site_vite_runner(tmp_path, 'NexaFlow', {}, brief={})
    page = (tmp_path/'static-preview.html').read_text()
    assert 'Preview unavailable' in page and '<script' not in page


def test_masthead_and_missing_h1_get_accessible_landmarks(tmp_path, monkeypatch, server):
    monkeypatch.setattr(server.subprocess, 'run', Mock())
    server._scaffold_site_vite_runner(tmp_path, 'Artist Portfolio', {
        'src/components/Masthead.tsx': 'export default function Masthead(){return <header/>}',
        'src/components/Gallery.tsx': 'export default function Gallery(){return <section><h2>Work</h2></section>}',
    }, brief={})
    app = (tmp_path/'App.tsx').read_text(encoding='utf8')
    assert app.index('<Masthead />') < app.index('<main ')
    assert '<h1 className="site-visually-hidden">Artist Portfolio</h1>' in app
    assert 'site-visually-hidden' in (tmp_path/'src/App.css').read_text(encoding='utf8')
