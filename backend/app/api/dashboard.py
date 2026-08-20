"""第一关：数据看板 API。数字权威来源，AI 回答需与这里对照。"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .. import schemas
from ..database import get_db
from ..services import analytics

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=schemas.SummaryOut)
def get_summary(
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    db: Session = Depends(get_db),
):
    return analytics.summary(db, start_date, end_date)


@router.get("/daily", response_model=list[schemas.DailyPoint])
def get_daily(
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    db: Session = Depends(get_db),
):
    return analytics.daily_trend(db, start_date, end_date)


@router.get("/top-products", response_model=list[schemas.TopProduct])
def get_top_products(
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    return analytics.top_products(db, start_date, end_date, limit)


@router.get("/store-category", response_model=list[schemas.StoreCategory])
def get_store_category(
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    db: Session = Depends(get_db),
):
    return analytics.store_category_revenue(db, start_date, end_date)


@router.get("/store-rank", response_model=list[schemas.StoreRank])
def get_store_rank(
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    db: Session = Depends(get_db),
):
    return analytics.store_revenue_rank(db, start_date, end_date)


@router.get("/payment", response_model=list[schemas.PaymentItem])
def get_payment(
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    db: Session = Depends(get_db),
):
    return analytics.payment_breakdown(db, start_date, end_date)
