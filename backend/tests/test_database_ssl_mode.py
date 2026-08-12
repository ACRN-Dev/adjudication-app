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


def test_postgres_url_built_from_discrete_vars(monkeypatch):
    _ensure_backend_on_path()
    monkeypatch.setenv("DB_NAME", "some_db")
    monkeypatch.setenv("DB_USER", "some_user")
    monkeypatch.setenv("DB_PASSWORD", "some_pass")
    monkeypatch.setenv("DB_HOST", "some_host")
    monkeypatch.setenv("DB_PORT", "5433")
    sys.modules.pop("database", None)
    import database
    assert database._build_postgres_url() == "postgresql://some_user:some_pass@some_host:5433/some_db"
    sys.modules.pop("database", None)


def test_postgres_url_encodes_special_characters(monkeypatch):
    _ensure_backend_on_path()
    monkeypatch.setenv("DB_USER", "user@corp")
    monkeypatch.setenv("DB_PASSWORD", "p@ss:w/ord")
    monkeypatch.setenv("DB_HOST", "some_host")
    monkeypatch.setenv("DB_NAME", "some_db")
    monkeypatch.delenv("DB_PORT", raising=False)
    sys.modules.pop("database", None)
    import database
    assert database._build_postgres_url() == "postgresql://user%40corp:p%40ss%3Aw%2Ford@some_host:5432/some_db"
    sys.modules.pop("database", None)
