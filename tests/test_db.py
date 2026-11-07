def test_usage_table_initializes_and_returns_rows(monkeypatch, tmp_path):
    from app.config import get_settings
    from app.db import init_db, log_usage, recent_usage
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'usage.db'}")
    get_settings.cache_clear()
    init_db()
    log_usage("demo", "m1", 200, {"prompt_tokens": 2, "completion_tokens": 3, "total_tokens": 5}, 42)
    rows = recent_usage(10)
    assert rows[0]["total_tokens"] == 5
    assert rows[0]["latency_ms"] == 42
    get_settings.cache_clear()


def test_recent_usage_limit_is_respected(monkeypatch, tmp_path):
    from app.config import get_settings
    from app.db import init_db, log_usage, recent_usage
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'usage-limit.db'}")
    get_settings.cache_clear()
    init_db()
    for index in range(3):
        log_usage("demo", f"m{index}", 200)
    assert len(recent_usage(2)) == 2
    get_settings.cache_clear()
