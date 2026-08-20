"""Pydantic 请求/响应模型。"""
from pydantic import BaseModel


class SummaryOut(BaseModel):
    revenue: float
    order_count: int
    valid_order_count: int
    avg_order_value: float


class DailyPoint(BaseModel):
    date: str
    revenue: float
    order_count: int
    avg_order_value: float


class TopProduct(BaseModel):
    product_name: str
    product_category: str
    revenue: float
    qty: float
    order_count: int


class StoreCategory(BaseModel):
    category: str
    revenue: float
    order_count: int


class StoreRank(BaseModel):
    store_id: str
    store_name: str
    category: str
    district: str
    revenue: float


class PaymentItem(BaseModel):
    payment: str
    revenue: float
    order_count: int


class ChatRequest(BaseModel):
    question: str
    conversation_id: str | None = None


class Evidence(BaseModel):
    tool: str
    metric: str
    period: str
    record_count: int


class ChatResponse(BaseModel):
    answer: str
    data: dict
    evidence: Evidence | None = None
    tool_used: str | None = None
