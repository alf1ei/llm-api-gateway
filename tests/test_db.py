def test_usage_table_initializes_and_returns_rows(monkeypatch, tmp_path):
    from app.config import get_settings
    from app.db import init_db, log_usage, recent_usage
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'usage.db'}")
    get_settings.cache_clear()
    init_db()
    log_usage("demo", "m1", 200, {"prompt_tokens": 2, "completion_tokens": 3,
                                   "total_tokens": 5}, 42)
    rows = recent_usage()
    assert rows[0]["total_tokens"] == 5
    get_settings.cache_clear()
