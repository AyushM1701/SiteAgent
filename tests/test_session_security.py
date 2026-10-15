"""
tests/test_session_security.py - Regression tests for session_id path traversal defense.
"""

import sys
from pathlib import Path
from unittest.mock import patch

# Add workspace root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from server.sessions import session_manager, Session, _SESSION_ID_RE
from server.app import app


def test_session_id_traversal_returns_none_without_touching_fs():
    """Verify traversal payloads return None from get_session without filesystem interaction."""
    traversal_payloads = [
        r"..\..\..\Windows\win.ini",
        "../../etc/passwd",
        "foo/bar",
        r"foo\bar",
        "..",
        "../",
        r"..\..",
        "1789148917_174154/../../etc/passwd",
        r"1789148917_174154\..\win.ini",
        "",
        "   ",
        "invalid_id",
        None,
        12345,
    ]

    with patch("pathlib.Path.exists") as mock_exists, patch("builtins.open") as mock_open:
        for payload in traversal_payloads:
            result = session_manager.get_session(payload)
            assert result is None, f"Expected None for payload {payload!r}, got {result!r}"

        # Ensure filesystem was never touched for any of these payloads
        assert mock_exists.call_count == 0, f"Path.exists was called {mock_exists.call_count} times on traversal payloads!"
        assert mock_open.call_count == 0, f"open was called {mock_open.call_count} times on traversal payloads!"

    print("PASS: test_session_id_traversal_returns_none_without_touching_fs")


def test_session_init_rejects_invalid_id():
    """Verify Session constructor rejects traversal or non-matching session IDs."""
    invalid_ids = [
        r"..\..\..\Windows\win.ini",
        "../../etc/passwd",
        "foo/bar",
        "not_a_valid_session_id",
        "",
    ]
    for invalid_id in invalid_ids:
        try:
            Session(session_id=invalid_id)
            assert False, f"Expected ValueError for invalid session_id: {invalid_id!r}"
        except ValueError:
            pass

    print("PASS: test_session_init_rejects_invalid_id")


def test_session_id_regex_valid_format():
    """Verify _SESSION_ID_RE matches generated IDs and rejects malformed ones."""
    assert _SESSION_ID_RE.match("1789148917_174154")
    assert _SESSION_ID_RE.match("1726200000_abcdef")
    assert not _SESSION_ID_RE.match("1789148917_174154/extra")
    assert not _SESSION_ID_RE.match("../1789148917_174154")
    assert not _SESSION_ID_RE.match("1789148917_17415")   # only 5 hex chars
    assert not _SESSION_ID_RE.match("1789148917_1741549") # 7 hex chars
    print("PASS: test_session_id_regex_valid_format")


def test_flask_endpoint_traversal_returns_404():
    """Verify Flask routes return 404 when hit with path traversal payloads."""
    client = app.test_client()
    routes_to_test = [
        "/api/sessions/..%5C..%5C..%5CWindows%5Cwin32.json",
        "/api/sessions/..%2F..%2F..%2Fetc%2Fpasswd",
        "/api/sessions/foo%2Fbar",
        "/api/sessions/foo%5Cbar",
        "/api/sessions/..%5C..%5C..%5CWindows%5Cwin.ini/diff/1",
        "/preview/..%5C..%5C..%5CWindows%5Cwin.ini",
    ]
    for route in routes_to_test:
        resp = client.get(route)
        assert resp.status_code == 404, f"Route {route} returned status {resp.status_code}, expected 404"

    print("PASS: test_flask_endpoint_traversal_returns_404")


if __name__ == "__main__":
    test_session_id_traversal_returns_none_without_touching_fs()
    test_session_init_rejects_invalid_id()
    test_session_id_regex_valid_format()
    test_flask_endpoint_traversal_returns_404()
    print("\nALL REGRESSION TESTS PASSED.")
