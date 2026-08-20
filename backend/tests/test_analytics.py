"""第一关：Dashboard API 数字正确性测试。"""
from app.services import analytics


def test_summary_core_metrics(db):
    s = analytics.summary(db)
    assert s["revenue"] == 425855.0
    assert s["order_count"] == 12051
    assert s["valid_order_count"] == 11931
    assert s["avg_order_value"] == 35.69


def test_daily_trend_covers_full_range(db):
    d = analytics.daily_trend(db)
    assert len(d) == 92  # 2026-05-01 ~ 2026-07-31
    assert d[0]["date"] == "2026-05-01"
    assert d[-1]["date"] == "2026-07-31"


def test_top_products_join(db):
    top = analytics.top_products(db, limit=1)[0]
    assert top["product_name"] == "牛肉poke"
    assert top["revenue"] == 39774.0


def test_store_category_join(db):
    rows = analytics.store_category_revenue(db)
    assert rows[0]["category"] == "日料"
    assert rows[0]["revenue"] == 88536.0


def test_june_summary(db):
    s = analytics.summary(db, "2026-06-01", "2026-06-30")
    assert s["revenue"] == 133140.0
    assert s["order_count"] == 3849


def test_api_summary(client):
    r = client.get("/api/dashboard/summary").json()
    assert r["revenue"] == 425855.0
    assert r["avg_order_value"] == 35.69


def test_api_dirty_fk_excluded_from_join(client):
    # 脏外键 S99/P99 不应出现在维度统计里
    ranks = client.get("/api/dashboard/store-rank").json()
    assert all(r["store_id"] != "S99" for r in ranks)
    assert len(ranks) == 5
