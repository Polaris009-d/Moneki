"""统一统计口径的服务层。

Dashboard API 与 AI Tool 都只调用这里，保证「第一关接口数字 == AI 数字」。

口径：
    - 营业额   = SUM(amount)，负数(退款)自然扣减，即净营业额
    - 订单数   = COUNT(DISTINCT order_id)
    - 客单价   = 净营业额 / 有效订单数（至少有一条有效 amount 的 order_id）
"""
from datetime import datetime, timedelta

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from ..models import Product, Sale, Store


def _date_where(q, start_date, end_date):
    if start_date:
        q = q.where(Sale.date >= start_date)
    if end_date:
        q = q.where(Sale.date <= end_date)
    return q


def _summary_core(db: Session, start_date=None, end_date=None):
    """统一口径核心：返回 (revenue, order_count, valid_order_count, avg_order_value)。"""
    q = select(
        func.coalesce(func.sum(Sale.amount), 0.0),
        func.count(func.distinct(Sale.order_id)),
        func.count(func.distinct(case((Sale.amount.isnot(None), Sale.order_id)))),
    )
    q = _date_where(q, start_date, end_date)
    revenue, order_count, valid_count = db.execute(q).one()
    revenue = round(float(revenue), 2)
    order_count = int(order_count)
    valid_count = int(valid_count)
    avg = round(revenue / valid_count, 2) if valid_count else 0.0
    return revenue, order_count, valid_count, avg


def summary(db: Session, start_date=None, end_date=None):
    revenue, order_count, valid_count, avg = _summary_core(db, start_date, end_date)
    return {
        "revenue": revenue,
        "order_count": order_count,
        "valid_order_count": valid_count,
        "avg_order_value": avg,
    }


def daily_trend(db: Session, start_date=None, end_date=None):
    q = (
        select(
            Sale.date,
            func.coalesce(func.sum(Sale.amount), 0.0),
            func.count(func.distinct(Sale.order_id)),
            func.count(func.distinct(case((Sale.amount.isnot(None), Sale.order_id)))),
        )
        .group_by(Sale.date)
        .order_by(Sale.date)
    )
    q = _date_where(q, start_date, end_date)
    out = []
    for date, rev, oc, vc in db.execute(q):
        rev = round(float(rev), 2)
        vc = int(vc)
        out.append(
            {
                "date": date,
                "revenue": rev,
                "order_count": int(oc),
                "avg_order_value": round(rev / vc, 2) if vc else 0.0,
            }
        )
    return out


def top_products(db: Session, start_date=None, end_date=None, limit=10):
    q = (
        select(
            Product.product_name,
            Product.product_category,
            func.coalesce(func.sum(Sale.amount), 0.0),
            func.sum(Sale.qty),
            func.count(func.distinct(Sale.order_id)),
        )
        .join(Product, Sale.product_id == Product.product_id)
        .group_by(Product.product_name, Product.product_category)
        .order_by(func.sum(Sale.amount).desc())
        .limit(limit)
    )
    q = _date_where(q, start_date, end_date)
    return [
        {
            "product_name": name,
            "product_category": cat,
            "revenue": round(float(rev), 2),
            "qty": round(float(qty or 0), 2),
            "order_count": int(oc),
        }
        for name, cat, rev, qty, oc in db.execute(q)
    ]


def store_category_revenue(db: Session, start_date=None, end_date=None):
    q = (
        select(
            Store.category,
            func.coalesce(func.sum(Sale.amount), 0.0),
            func.count(func.distinct(Sale.order_id)),
        )
        .join(Store, Sale.store_id == Store.store_id)
        .group_by(Store.category)
        .order_by(func.sum(Sale.amount).desc())
    )
    q = _date_where(q, start_date, end_date)
    return [
        {"category": c, "revenue": round(float(r), 2), "order_count": int(oc)}
        for c, r, oc in db.execute(q)
    ]


def store_revenue_rank(db: Session, start_date=None, end_date=None):
    q = (
        select(
            Store.store_id,
            Store.store_name,
            Store.category,
            Store.district,
            func.coalesce(func.sum(Sale.amount), 0.0),
        )
        .join(Store, Sale.store_id == Store.store_id)
        .group_by(Store.store_id, Store.store_name, Store.category, Store.district)
        .order_by(func.sum(Sale.amount).desc())
    )
    q = _date_where(q, start_date, end_date)
    return [
        {
            "store_id": s,
            "store_name": n,
            "category": c,
            "district": d,
            "revenue": round(float(r), 2),
        }
        for s, n, c, d, r in db.execute(q)
    ]


def product_revenue(db: Session, product_name, start_date=None, end_date=None):
    """按商品名查销售额（精确匹配；模糊匹配在 AI 工具层做）。查无返回 None。"""
    q = (
        select(
            Product.product_name,
            Product.product_category,
            func.coalesce(func.sum(Sale.amount), 0.0),
            func.sum(Sale.qty),
            func.count(func.distinct(Sale.order_id)),
        )
        .join(Product, Sale.product_id == Product.product_id)
        .where(Product.product_name == product_name)
        .group_by(Product.product_name, Product.product_category)
    )
    q = _date_where(q, start_date, end_date)
    row = db.execute(q).first()
    if not row:
        return None
    name, cat, rev, qty, oc = row
    return {
        "product_name": name,
        "product_category": cat,
        "revenue": round(float(rev), 2),
        "qty": round(float(qty or 0), 2),
        "order_count": int(oc),
    }


def payment_breakdown(db: Session, start_date=None, end_date=None):
    q = (
        select(
            Sale.payment,
            func.coalesce(func.sum(Sale.amount), 0.0),
            func.count(func.distinct(Sale.order_id)),
        )
        .group_by(Sale.payment)
        .order_by(func.sum(Sale.amount).desc())
    )
    q = _date_where(q, start_date, end_date)
    return [
        {"payment": p, "revenue": round(float(r), 2), "order_count": int(oc)}
        for p, r, oc in db.execute(q)
    ]


def avg_order_value_trend(db: Session, window_days=14):
    """客单价趋势：最近 window_days 天 vs 前 window_days 天。"""
    max_date = db.execute(select(func.max(Sale.date))).scalar()
    end = datetime.strptime(max_date, "%Y-%m-%d")
    cur_start = end - timedelta(days=window_days - 1)
    prev_end = cur_start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=window_days - 1)

    cur = _summary_core(db, cur_start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
    prev = _summary_core(db, prev_start.strftime("%Y-%m-%d"), prev_end.strftime("%Y-%m-%d"))

    change_pct = round((cur[3] - prev[3]) / prev[3] * 100, 2) if prev[3] else 0.0
    trend = "up" if change_pct > 0 else ("down" if change_pct < 0 else "flat")

    return {
        "metric": "avg_order_value",
        "current": {
            "start": cur_start.strftime("%Y-%m-%d"),
            "end": end.strftime("%Y-%m-%d"),
            "avg_order_value": cur[3],
            "revenue": cur[0],
        },
        "previous": {
            "start": prev_start.strftime("%Y-%m-%d"),
            "end": prev_end.strftime("%Y-%m-%d"),
            "avg_order_value": prev[3],
            "revenue": prev[0],
        },
        "change_percent": change_pct,
        "trend": trend,
    }
