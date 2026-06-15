"""Security/regression tests for the FastAPI web layer.

Covers the path-traversal hardening on project endpoints, the SiteAnalyzer
session-close path, and that the app builds and basic endpoints respond.
"""

import pytest
from fastapi import HTTPException

from src.config import config
from src.web.fastapi_app import _safe_project_dir, _safe_subpath, create_app
from src.discovery import SiteAnalyzer


@pytest.mark.parametrize("bad", ["", ".", "..", "../x", "a/b", "a\\b", "/etc/passwd", "..\\..\\x"])
def test_safe_project_dir_rejects_traversal(bad):
    with pytest.raises(HTTPException):
        _safe_project_dir(bad)


def test_safe_project_dir_accepts_plain_name():
    p = _safe_project_dir("aHR0cHM6Ly9leGFtcGxlLmNvbQ==")
    assert config.PROJECT_DIR.resolve() in p.parents


@pytest.mark.parametrize("bad", ["../../etc", "..", "../sibling", "a/../../escape"])
def test_safe_subpath_rejects_traversal(bad):
    base = (config.PROJECT_DIR.resolve() / "proj")
    with pytest.raises(HTTPException):
        _safe_subpath(base, bad)


def test_safe_subpath_allows_inside():
    base = (config.PROJECT_DIR.resolve() / "proj")
    assert _safe_subpath(base, "sub/dir") == (base / "sub" / "dir").resolve()
    assert _safe_subpath(base, "") == base


def test_site_analyzer_close_is_safe():
    analyzer = SiteAnalyzer(timeout=5)
    # Sessions exist before close and close() must not raise.
    assert analyzer.detector.session is not None
    analyzer.close()
    analyzer.close()  # idempotent


def test_app_builds_and_health_ok():
    try:
        from fastapi.testclient import TestClient
    except Exception:
        pytest.skip("fastapi TestClient unavailable")
    client = TestClient(create_app())
    assert client.get("/health").status_code == 200
    assert client.get("/api/projects").status_code == 200
