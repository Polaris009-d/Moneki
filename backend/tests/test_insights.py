"""经营洞察测试：洞察由真实数据规则化计算，数字应可复现。"""
from app.services import insights


def test_insights_contain_all_types(db):
    result = insights.get_insights(db)
    types = {i["type"] for i in result}
    assert {"mom_growth", "weekend_effect", "membership", "top_product", "anomaly"} <= types


def test_insights_have_real_data(db):
    for i in insights.get_insights(db):
        assert i["text"]
        assert "data" in i


def test_api_insights(client):
    r = client.get("/api/insights").json()
    assert len(r["insights"]) >= 5
