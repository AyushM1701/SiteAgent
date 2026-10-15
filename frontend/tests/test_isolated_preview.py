"""Regression coverage for the sandboxed production preview lifecycle."""
import io
from unittest.mock import MagicMock, patch
from server.preview_manager import PreviewManager


def test_preview_builds_production_assets_before_launch(tmp_path):
    (tmp_path / 'index.html').write_text('<div id="root"></div>')
    (tmp_path / 'src').mkdir()
    (tmp_path / 'src' / 'main.tsx').write_text('console.log("first")')
    proc = MagicMock()
    proc.poll.return_value = None
    proc.stderr = io.BytesIO()
    manager = PreviewManager()
    with patch('server.preview_manager._link_node_modules'), patch('server.preview_manager.time.sleep'), \
         patch.object(manager, '_is_port_available', return_value=True), \
         patch.object(manager, '_check_project_health', return_value=True), \
         patch('server.preview_manager.subprocess.run') as build, \
         patch('server.preview_manager.subprocess.Popen', return_value=proc) as launch:
        build.return_value.returncode = 0
        assert manager.start('demo', tmp_path) == 'http://127.0.0.1:5173'
        assert build.called, 'Sandbox preview must compile assets before serving them'
        assert 'build' in build.call_args.args[0]
        assert '--serve' in launch.call_args.args[0]
        assert '127.0.0.1' not in launch.call_args.args[0]  # server binds loopback internally
        build.reset_mock()
        manager.start('demo', tmp_path)
        assert not build.called, 'Unchanged previews should reuse the production build'
        (tmp_path / 'src' / 'main.tsx').write_text('console.log("edited")')
        with patch('server.preview_manager._stop_process_tree'):
            manager.start('demo', tmp_path)
        assert build.called, 'Saved source changes must rebuild the embedded preview'


def test_failed_build_does_not_launch_a_stale_preview(tmp_path):
    (tmp_path / 'index.html').write_text('preview')
    manager = PreviewManager()
    with patch('server.preview_manager._link_node_modules'), \
         patch('server.preview_manager.subprocess.run') as build, \
         patch('server.preview_manager.subprocess.Popen') as launch:
        build.return_value.returncode = 1
        build.return_value.stderr = 'invalid import'
        build.return_value.stdout = ''
        try:
            manager.start('broken', tmp_path)
        except RuntimeError as error:
            assert 'invalid import' in str(error)
        else:
            assert False, 'Build failure must be reported instead of launching stale assets'
        launch.assert_not_called()
