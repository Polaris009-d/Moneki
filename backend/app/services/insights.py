"""经营洞察：从真实数据规则化计算，杜绝任何数字幻觉。

所有洞察均按所选日期区间计算；无 LLM 参与数字生成，因此无 key 也能稳定运行且天然可信。
"""
from collections import defaultdict
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import Sale, Store
from . import analytics


def get_insights(db: Session, start_date: str | None = None, end_date: str | None = None) -> list[dict]:
    out = []
    out.append(_period_comparison(db, start_date, end_date))
    out.append(_weekend_effect(db, start_date, end_date))
    out.append(_membership(db, start_date, end_date))
    out.append(_top_product(db, start_date, end_date))
    out.extend(_anomalies(db, start_date, end_date))
    return out


def _period_comparison(db: Session, start_date, end_date) -> dict:
    """环比：所选区间 vs 上一等长区间；上一区间无数据时回退为最近完整月 vs 上月。"""
    if start_date and end_date:
        cur = analytics.summary(db, start_date, end_date)["revenue"]
        d1 = datetime.strptime(start_date, "%Y-%m-%d")
        d2 = datetime.strptime(end_date, "%Y-%m-%d")
        length = (d2 - d1).days + 1
        prev_e = d1 - timedelta(days=1)
        prev_s = prev_e - timedelta(days=length - 1)
        prev = analytics.summary(db, prev_s.strftime("%Y-%m-%d"), prev_e.strftime("%Y-%m-%d"))["revenue"]
        if prev > 0:
            return _build_comparison(cur, prev)
    return _last_month_mom(db)


def _last_month_mom(db: Session) -> dict:
    """数据最近完整月 vs 上月（用于无上一周期数据时的回退）。"""
    max_date = db.execute(select(func.max(Sale.date))).scalar()
    d = datetime.strptime(max_date, "%Y-%m-%d")
    cur_s = d.replace(day=1).strftime("%Y-%m-%d")
    cur_e = d.strftime("%Y-%m-%d")
    prev_e = (d.replace(day=1) - timedelta(days=1)).strftime("%Y-%m-%d")
    prev_s = prev_e[:8] + "01"
    cur = analytics.summary(db, cur_s, cur_e)["revenue"]
    prev = analytics.summary(db, prev_s, prev_e)["revenue"]
    return _build_comparison(cur, prev)


def _build_comparison(cur: float, prev: float) -> dict:
    if prev > 0:
        pct = (cur - prev) / prev * 100
        direction = "增长" if pct >= 0 else "下降"
        text = f"本期净营业额 ¥{cur:,.0f}，较上一周期{direction} {abs(pct):.1f}%（上期 ¥{prev:,.0f}）。"
        severity = "positive" if pct >= 0 else "negative"
    else:
        text = f"本期净营业额 ¥{cur:,.0f}（上一周期无销售数据）。"
        severity = "info"
        pct = None
    return {
        "type": "period_comparison",
        "title": "环比趋势",
        "severity": severity,
        "text": text,
        "data": {
            "current_revenue": round(cur, 2),
            "previous_revenue": round(prev, 2),
            "change_pct": round(pct, 2) if pct is not None else None,
        },
    }


def _weekend_effect(db: Session, start_date, end_date) -> dict:
    daily = analytics.daily_trend(db, start_date, end_date)
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


def _membership(db: Session, start_date, end_date) -> dict:
    rows = analytics.payment_breakdown(db, start_date, end_date)
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


def _top_product(db: Session, start_date, end_date) -> dict:
    top = analytics.top_products(db, start_date, end_date, limit=1)
    if not top:
        return {"type": "top_product", "title": "热销商品", "severity": "info", "text": "该区间无销售数据。", "data": {}}
    top = top[0]
    return {
        "type": "top_product",
        "title": "热销商品",
        "severity": "info",
        "text": f"销售额最高商品是「{top['product_name']}」，累计 ¥{top['revenue']:,.0f}。",
        "data": top,
    }


def _anomalies(db: Session, start_date, end_date, threshold: float = 2.0, limit: int = 3) -> list[dict]:
    """异常销售预警：每门店每日营业额偏离自身均值超过 threshold 个标准差。"""
    q = (
        select(Sale.store_id, Sale.date, func.sum(Sale.amount))
        .join(Store, Sale.store_id == Store.store_id)
        .group_by(Sale.store_id, Sale.date)
    )
    if start_date:
        q = q.where(Sale.date >= start_date)
    if end_date:
        q = q.where(Sale.date <= end_date)
    rows = db.execute(q).all()
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
        return [{"type": "anomaly", "title": "异常销售预警", "severity": "info", "text": "所选区间内各门店日营业额无显著异常。", "data": []}]

    texts = [
        f"{a['store_name']} 在 {a['date']} 营业额{a['direction']}（¥{a['revenue']:,.0f}，偏离均值 {abs(a['z_score']):.1f} 个标准差）"
        for a in top
    ]
    return [{"type": "anomaly", "title": "异常销售预警", "severity": "warning", "text": "；".join(texts) + "。", "data": top}]
