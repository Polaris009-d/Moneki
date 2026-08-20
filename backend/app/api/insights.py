"""经营洞察接口：返回规则化计算的真实洞察（无 LLM 依赖）。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..services import insights

router = APIRouter(prefix="/api/insights", tags=["insights"])


@router.get("")
def get_insights(db: Session = Depends(get_db)):
    return {"insights": insights.get_insights(db)}
