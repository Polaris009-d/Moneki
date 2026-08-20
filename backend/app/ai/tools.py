"""AI 业务工具。

每个工具对应一个真实 SQL 查询（走 analytics 统一口径）。LLM 只决定「调用哪个工具 + 传什么参数」，
具体怎么算完全由这里的真实查询控制，从而保证 AI 数字 == 第一关接口数字。
"""
import difflib

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models import Product, Sale
from ..services import analytics

# 数据固定时间范围（与 data/*.csv 一致）
FULL_START = "2026-05-01"
FULL_END = "2026-07-31"


def _period(start_date, end_date):
    s = start_date or FULL_START
    e = end_date or FULL_END
    return f"{s} ~ {e}"


def _product_names(db: Session) -> list[str]:
    return [r for (r,) in db.query(Product.product_name).all()]


def _match_product(db: Session, query: str) -> str | None:
    """精确匹配 → 包含匹配 → 编辑距离模糊匹配，都失败返回 None。"""
    names = _product_names(db)
    q = (query or "").strip()
    if not q:
        return None
    if q in names:
        return q
    for n in names:
        if q in n or n in q:
            return n
    m = difflib.get_close_matches(q, names, n=1, cutoff=0.35)
    return m[0] if m else None


def _row_count(db: Session, start_date=None, end_date=None, product_name=None):
    q = db.query(func.count(Sale.id))
    if product_name:
        q = q.join(Product, Sale.product_id == Product.product_id).filter(
            Product.product_name == product_name
        )
    if start_date:
        q = q.filter(Sale.date >= start_date)
    if end_date:
        q = q.filter(Sale.date <= end_date)
    return int(q.scalar() or 0)


def _ev(tool, metric, period, record_count):
    return {"tool": tool, "metric": metric, "period": period, "record_count": record_count}


# ---------------- 工具实现 ----------------


def tool_summary(db, start_date=None, end_date=None):
    d = analytics.summary(db, start_date, end_date)
    period = _period(start_date, end_date)
    text = (
        f"汇总({period})：净营业额 ¥{d['revenue']:.2f}，订单数 {d['order_count']}，"
        f"客单价 ¥{d['avg_order_value']:.2f}。"
    )
    return {
        "data": d,
        "evidence": _ev("get_summary", "SUM(amount) / COUNT(DISTINCT order_id)", period, d["valid_order_count"]),
        "text": text,
    }


def tool_daily_trend(db, start_date=None, end_date=None):
    rows = analytics.daily_trend(db, start_date, end_date)
    period = _period(start_date, end_date)
    lines = [f"{r['date']}: 营业额 ¥{r['revenue']:.2f} / 订单 {r['order_count']} / 客单价 ¥{r['avg_order_value']:.2f}" for r in rows]
    text = f"每日趋势({period})：\n" + "\n".join(lines)
    return {
        "data": rows,
        "evidence": _ev("get_daily_trend", "SUM(amount) GROUP BY date", period, len(rows)),
        "text": text,
    }


def tool_product_revenue(db, product_name=None, start_date=None, end_date=None):
    period = _period(start_date, end_date)
    matched = _match_product(db, product_name or "")
    if not matched:
        names = _product_names(db)
        suggest = "、".join(names[:6])
        return {
            "data": {"product_name": product_name, "found": False},
            "evidence": _ev("get_product_revenue", "SUM(amount) WHERE product=?", period, 0),
            "text": f"未找到商品「{product_name}」。数据中的商品包括：{suggest} 等。请据此提示用户并给出最接近的建议，不要编造数字。",
        }
    result = analytics.product_revenue(db, matched, start_date, end_date)
    is_fuzzy = matched != (product_name or "").strip()
    if not result:
        return {
            "data": {"product_name": matched, "found": True, "revenue": 0.0, "qty": 0.0, "order_count": 0},
            "evidence": _ev("get_product_revenue", "SUM(amount) WHERE product=?", period, 0),
            "text": f"商品「{matched}」在 {period} 无销售记录。",
        }
    rc = _row_count(db, start_date, end_date, product_name=matched)
    result["matched"] = matched
    result["fuzzy_matched"] = is_fuzzy
    prefix = f"（注：用户问的是「{product_name}」，已模糊匹配到「{matched}」）" if is_fuzzy else ""
    text = (
        f"{prefix}商品「{matched}」在 {period}：销售额 ¥{result['revenue']:.2f}，"
        f"销量 {result['qty']:.2f}，涉及订单 {result['order_count']} 个，匹配流水 {rc} 条。"
    )
    return {
        "data": result,
        "evidence": _ev("get_product_revenue", "SUM(amount) WHERE product=?", period, rc),
        "text": text,
    }


def tool_revenue_by_store_category(db, start_date=None, end_date=None):
    rows = analytics.store_category_revenue(db, start_date, end_date)
    period = _period(start_date, end_date)
    lines = [f"- {r['category']}: ¥{r['revenue']:.2f}（订单 {r['order_count']}）" for r in rows]
    text = f"门店品类营业额({period})，按净营业额降序：\n" + "\n".join(lines)
    rc = _row_count(db, start_date, end_date)
    return {
        "data": rows,
        "evidence": _ev("get_revenue_by_store_category", "SUM(amount) JOIN stores GROUP BY category", period, rc),
        "text": text,
    }


def tool_store_revenue_rank(db, start_date=None, end_date=None):
    rows = analytics.store_revenue_rank(db, start_date, end_date)
    period = _period(start_date, end_date)
    lines = [f"- {r['store_name']}({r['category']}/{r['district']}): ¥{r['revenue']:.2f}" for r in rows]
    text = f"各门店营业额({period})，降序：\n" + "\n".join(lines)
    rc = _row_count(db, start_date, end_date)
    return {
        "data": rows,
        "evidence": _ev("get_store_revenue_rank", "SUM(amount) GROUP BY store", period, rc),
        "text": text,
    }


def tool_payment_breakdown(db, start_date=None, end_date=None):
    rows = analytics.payment_breakdown(db, start_date, end_date)
    period = _period(start_date, end_date)
    lines = [f"- {r['payment']}: ¥{r['revenue']:.2f}（订单 {r['order_count']}）" for r in rows]
    text = f"支付方式分布({period})：\n" + "\n".join(lines)
    rc = _row_count(db, start_date, end_date)
    return {
        "data": rows,
        "evidence": _ev("get_payment_breakdown", "SUM(amount) GROUP BY payment", period, rc),
        "text": text,
    }


def tool_avg_order_value_trend(db, window_days=14):
    d = analytics.avg_order_value_trend(db, window_days)
    cur, prev = d["current"], d["previous"]
    direction = {"up": "上涨", "down": "下降", "flat": "持平"}[d["trend"]]
    text = (
        f"客单价趋势：最近{window_days}天({cur['start']}~{cur['end']}) ¥{cur['avg_order_value']:.2f}，"
        f"前{window_days}天({prev['start']}~{prev['end']}) ¥{prev['avg_order_value']:.2f}，"
        f"变化 {d['change_percent']:+.2f}%，即{direction}。"
    )
    return {
        "data": d,
        "evidence": _ev("get_avg_order_value_trend", "avg_order_value (最近N天 vs 前N天)", f"{prev['start']} ~ {cur['end']}", _row_count(db, cur["start"], cur["end"])),
        "text": text,
    }


# ---------------- 注册表 & schema ----------------


TOOL_REGISTRY = {
    "get_summary": tool_summary,
    "get_daily_trend": tool_daily_trend,
    "get_product_revenue": tool_product_revenue,
    "get_revenue_by_store_category": tool_revenue_by_store_category,
    "get_store_revenue_rank": tool_store_revenue_rank,
    "get_payment_breakdown": tool_payment_breakdown,
    "get_avg_order_value_trend": tool_avg_order_value_trend,
}


def execute(db: Session, name: str, args: dict) -> dict:
    fn = TOOL_REGISTRY.get(name)
    if not fn:
        return {
            "data": {},
            "evidence": _ev(name, "", "", 0),
            "text": f"未知工具：{name}",
        }
    return fn(db, **args)


def _date_param(desc):
    return {"type": "string", "description": f"{desc}，格式 YYYY-MM-DD，可选"}


def _schema(name, desc, properties, required=None):
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": desc,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required or [],
            },
        },
    }


TOOL_SCHEMAS = [
    _schema(
        "get_summary",
        "查询指定日期区间的汇总指标：净营业额、订单数、客单价。用于「总营业额多少」「客单价多少」等整体问题。",
        {"start_date": _date_param("起始日期"), "end_date": _date_param("结束日期")},
    ),
    _schema(
        "get_daily_trend",
        "查询每日营业额、订单数、客单价趋势。用于「趋势怎么样」「每天卖多少」等问题。",
        {"start_date": _date_param("起始日期"), "end_date": _date_param("结束日期")},
    ),
    _schema(
        "get_product_revenue",
        "查询某个商品的销售额、销量、涉及订单数。用于「XX 卖了多少钱」等问题。商品名传用户提到的名字（可能是简称，后端会模糊匹配）。",
        {
            "product_name": {"type": "string", "description": "商品名称，如「牛肉poke」"},
            "start_date": _date_param("起始日期"),
            "end_date": _date_param("结束日期"),
        },
        ["product_name"],
    ),
    _schema(
        "get_revenue_by_store_category",
        "查询各门店品类（拉面/轻食/点心/三明治/日料）的营业额对比。用于「哪个品类的门店营业额最高」等问题。",
        {"start_date": _date_param("起始日期"), "end_date": _date_param("结束日期")},
    ),
    _schema(
        "get_store_revenue_rank",
        "查询各门店的营业额排名。用于「哪个门店卖得最好」「门店对比」等问题。",
        {"start_date": _date_param("起始日期"), "end_date": _date_param("结束日期")},
    ),
    _schema(
        "get_payment_breakdown",
        "查询各支付方式（微信/支付宝/银行卡/现金/会员储值）的营业额分布。",
        {"start_date": _date_param("起始日期"), "end_date": _date_param("结束日期")},
    ),
    _schema(
        "get_avg_order_value_trend",
        "查询客单价最近一段时间是涨还是跌（最近 N 天 vs 前 N 天）。用于「客单价最近涨了还是跌了」等问题。",
        {"window_days": {"type": "integer", "description": "时间窗口天数，默认 14"}},
    ),
]
