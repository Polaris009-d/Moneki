"""经营洞察：从真实数据规则化计算，杜绝任何数字幻觉。

每个洞察的标题/文案/数字都直接来自数据库查询，LLM 不参与数字生成，
因此看板上的洞察在无 API key 时也能稳定运行、且天然可信。
"""
from collections import defaultdict
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import Sale, Store
from . import analytics


def get_insights(db: Session) -> list[dict]:
    out = []
    out.append(_mom_growth(db))
    out.append(_weekend_effect(db))
    out.append(_membership(db))
    out.append(_top_product(db))
    out.extend(_anomalies(db))
    return out


def _mom_growth(db: Session) -> dict:
    may = analytics.summary(db, "2026-05-01", "2026-05-31")["revenue"]
    jun = analytics.summary(db, "2026-06-01", "2026-06-30")["revenue"]
    jul = analytics.summary(db, "2026-07-01", "2026-07-31")["revenue"]
    pct_jul = (jul - jun) / jun * 100 if jun else 0.0
    direction = "增长" if pct_jul >= 0 else "下降"
    return {
        "type": "mom_growth",
        "title": "环比趋势",
        "severity": "positive" if pct_jul >= 0 else "negative",
        "text": f"7 月净营业额 ¥{jul:,.0f}，环比 6 月{direction} {abs(pct_jul):.1f}%（6 月 ¥{jun:,.0f}，5 月 ¥{may:,.0f}）。",
        "data": {"may": round(may, 2), "jun": round(jun, 2), "jul": round(jul, 2), "jul_change_pct": round(pct_jul, 2)},
    }


def _weekend_effect(db: Session) -> dict:
    daily = analytics.daily_trend(db)
    wd_sum = wd_n = we_sum = we_n = 0
    for d in daily:
        dt = datetime.strptime(d["date"], "%Y-%m-%d")
        if dt.weekday() >= 5:  # 周六=5 周日=6
            we_sum += d["revenue"]
            we_n += 1
        else:
            wd_sum += d["revenue"]
            wd_n += 1
    wd_avg = wd_sum / wd_n if wd_n else 0.0
    we_avg = we_sum / we_n if we_n else 0.0
    pct = (we_avg - wd_avg) / wd_avg * 100 if wd_avg else 0.0
    return {
        "type": "weekend_effect",
        "title": "周末效应",
        "severity": "info",
        "text": f"周末日均营业额 ¥{we_avg:,.0f}，比工作日日均 ¥{wd_avg:,.0f} 高 {pct:.1f}%。",
        "data": {"weekday_avg": round(wd_avg, 2), "weekend_avg": round(we_avg, 2), "change_pct": round(pct, 2)},
    }


def _membership(db: Session) -> dict:
    rows = analytics.payment_breakdown(db)
    total = sum(r["revenue"] for r in rows)
    member = next((r["revenue"] for r in rows if r["payment"] == "会员储值"), 0.0)
    ratio = member / total * 100 if total else 0.0
    return {
        "type": "membership",
        "title": "会员储值占比",
        "severity": "info",
        "text": f"会员储值支付 ¥{member:,.0f}，占总营业额 {ratio:.1f}%，反映会员预充值粘性。",
        "data": {"member_revenue": round(member, 2), "total_revenue": round(total, 2), "ratio_pct": round(ratio, 2)},
    }


def _top_product(db: Session) -> dict:
    top = analytics.top_products(db, limit=1)[0]
    return {
        "type": "top_product",
        "title": "热销商品",
        "severity": "info",
        "text": f"销售额最高商品是「{top['product_name']}」，累计 ¥{top['revenue']:,.0f}。",
        "data": top,
    }


def _anomalies(db: Session, threshold: float = 2.0, limit: int = 3) -> list[dict]:
    """异常销售预警：每门店每日营业额偏离自身均值超过 threshold 个标准差。"""
    rows = db.execute(
        select(Sale.store_id, Sale.date, func.sum(Sale.amount))
        .join(Store, Sale.store_id == Store.store_id)
        .group_by(Sale.store_id, Sale.date)
    ).all()
    store_names = dict(db.execute(select(Store.store_id, Store.store_name)).all())

    daily = defaultdict(list)
    for sid, date, rev in rows:
        daily[sid].append((date, float(rev or 0)))

    anomalies = []
    for sid, lst in daily.items():
        revs = [r for _, r in lst]
        mean = sum(revs) / len(revs)
        std = (sum((r - mean) ** 2 for r in revs) / len(revs)) ** 0.5
        if std < 1:
            continue
        for date, rev in lst:
            z = (rev - mean) / std
            if abs(z) >= threshold:
                anomalies.append(
                    {
                        "store_id": sid,
                        "store_name": store_names.get(sid, sid),
                        "date": date,
                        "revenue": round(rev, 2),
                        "z_score": round(z, 2),
                        "direction": "偏高" if z > 0 else "偏低",
                    }
                )

    anomalies.sort(key=lambda a: -abs(a["z_score"]))
    top = anomalies[:limit]
    if not top:
        return [{"type": "anomaly", "title": "异常销售预警", "severity": "info", "text": "近期各门店日营业额无显著异常。", "data": []}]

    texts = [
        f"{a['store_name']} 在 {a['date']} 营业额{a['direction']}（¥{a['revenue']:,.0f}，偏离均值 {abs(a['z_score']):.1f} 个标准差）"
        for a in top
    ]
    return [{"type": "anomaly", "title": "异常销售预警", "severity": "warning", "text": "；".join(texts) + "。", "data": top}]
