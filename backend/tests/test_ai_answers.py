"""第二关核心测试：证明 AI 回答的数字 == 数据库真实查询数字。

分两层：
1. 工具链路测试（用 ScriptedClient 模拟 LLM 的「选择工具」，但工具执行的是真实 SQL）——
   不联网也能跑，验证工具返回的数据与独立查库结果一致。
2. 真实 LLM 测试（需要 DEEPSEEK_API_KEY，未配置时自动跳过）——
   验证 LLM 最终回答文本里引用的数字与查库一致。
"""
import pytest

from app.ai.agent import run_agent
from app.config import settings
from app.services import analytics


class ScriptedClient:
    """按脚本返回：第一次返回指定 tool_call，之后返回 final_answer。"""

    def __init__(self, tool_call, final_answer):
        self.tool_call = tool_call  # (name, args) 或 None
        self.final_answer = final_answer
        self._step = 0

    def complete(self, messages, tool_schemas):
        self._step += 1
        if self._step == 1 and self.tool_call:
            return "", [{"id": "c1", "name": self.tool_call[0], "args": self.tool_call[1]}]
        return self.final_answer, None


# ---------------- 工具链路测试（真实 SQL，无需 key） ----------------


def test_ai_product_answer_matches_db(db):
    """「牛肉poke 六月卖了多少钱」→ 工具返回的销售额 == 独立查库。"""
    q = "牛肉poke 六月卖了多少钱？"
    args = {"product_name": "牛肉poke", "start_date": "2026-06-01", "end_date": "2026-06-30"}
    client = ScriptedClient(("get_product_revenue", args), "牛肉poke 六月卖了 ¥13,440.00")

    res = run_agent(db, q, client)

    db_val = analytics.product_revenue(db, "牛肉poke", "2026-06-01", "2026-06-30")["revenue"]
    assert res["data"]["revenue"] == db_val == 13440.0
    assert res["evidence"]["tool"] == "get_product_revenue"
    assert res["evidence"]["record_count"] == 186


def test_ai_store_category_answer_matches_db(db):
    """「哪个品类的门店营业额最高」→ 工具返回的品类排名 == 独立查库。"""
    q = "哪个品类的门店营业额最高？"
    client = ScriptedClient(("get_revenue_by_store_category", {}), "日料门店营业额最高")

    res = run_agent(db, q, client)

    db_top = analytics.store_category_revenue(db)[0]
    assert res["data"][0]["category"] == db_top["category"] == "日料"
    assert res["data"][0]["revenue"] == db_top["revenue"]


def test_ai_aov_trend_matches_db(db):
    """「客单价最近涨了还是跌了」→ 工具返回的变化率 == 独立查库。"""
    q = "客单价最近是涨了还是跌了？"
    client = ScriptedClient(("get_avg_order_value_trend", {}), "客单价最近下降了 2.55%")

    res = run_agent(db, q, client)

    db_trend = analytics.avg_order_value_trend(db)
    assert res["data"]["change_percent"] == db_trend["change_percent"]
    assert res["data"]["trend"] == db_trend["trend"]


def test_ai_no_tool_no_fabrication(db):
    """非数据问题不调用工具 → 无 data/evidence，不编造。"""
    q = "今天天气怎么样？"
    client = ScriptedClient(None, "我只能回答经营数据相关问题。")

    res = run_agent(db, q, client)

    assert res["evidence"] is None
    assert res["data"] == {}


def test_ai_product_not_found_no_fabrication(db):
    """查无此商品 → 工具返回 found=False，不编造数字。"""
    from app.ai import tools

    r = tools.execute(db, "get_product_revenue", {"product_name": "完全不存在的商品xyz"})
    assert r["data"]["found"] is False
    assert "未找到" in r["text"]


def test_ai_fuzzy_match_product(db):
    """「牛肉饭」→ 模糊匹配到「牛肉poke」，返回真实数据。"""
    from app.ai import tools

    r = tools.execute(db, "get_product_revenue", {"product_name": "牛肉饭", "start_date": "2026-06-01", "end_date": "2026-06-30"})
    assert r["data"]["matched"] == "牛肉poke"
    assert r["data"]["revenue"] == 13440.0


# ---------------- 真实 LLM 测试（需 key，未配置则跳过） ----------------


@pytest.mark.skipif(not settings.deepseek_api_key, reason="需要 DEEPSEEK_API_KEY")
def test_real_llm_product_number_in_answer(db):
    from app.ai.agent import DeepSeekClient

    client = DeepSeekClient(settings.deepseek_api_key, settings.deepseek_base_url, settings.deepseek_model)
    res = run_agent(db, "牛肉poke 六月卖了多少钱？", client)

    db_val = analytics.product_revenue(db, "牛肉poke", "2026-06-01", "2026-06-30")["revenue"]
    # 答案文本（去掉千分位逗号）必须包含查库得到的整数金额
    assert str(int(db_val)) in res["answer"].replace(",", "").replace("，", "")


@pytest.mark.skipif(not settings.deepseek_api_key, reason="需要 DEEPSEEK_API_KEY")
def test_real_llm_store_category_number_in_answer(db):
    from app.ai.agent import DeepSeekClient

    client = DeepSeekClient(settings.deepseek_api_key, settings.deepseek_base_url, settings.deepseek_model)
    res = run_agent(db, "哪个品类的门店营业额最高？", client)

    db_top = analytics.store_category_revenue(db)[0]
    assert str(int(db_top["revenue"])) in res["answer"].replace(",", "").replace("，", "")
    assert db_top["category"] in res["answer"]
