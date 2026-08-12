import os
import sys


def _ensure_backend_on_path():
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)


def test_db_ssl_mode_included_in_connect_args(monkeypatch):
    _ensure_backend_on_path()
    monkeypatch.setenv("DB_SSL_MODE", "require")
    sys.modules.pop("database", None)
    import database
    assert database._build_postgres_connect_args() == {"sslmode": "require"}
    sys.modules.pop("database", None)


def test_db_ssl_mode_omitted_when_unset(monkeypatch):
    _ensure_backend_on_path()
    monkeypatch.delenv("DB_SSL_MODE", raising=False)
    sys.modules.pop("database", None)
    import database
    assert database._build_postgres_connect_args() == {}
    sys.modules.pop("database", None)
