"""第二关：AI 数据问答接口，含对话上下文（对话追问）。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import schemas
from ..ai.agent import DeepSeekClient, run_agent
from ..config import settings
from ..database import get_db

router = APIRouter(prefix="/api/chat", tags=["chat"])

# 进程内上下文存储（单机 demo 够用；按 conversation_id 存最近 20 条消息）
_CONTEXTS: dict[str, list] = {}


def _get_client():
    if not settings.deepseek_api_key:
        return None
    return DeepSeekClient(
        settings.deepseek_api_key,
        settings.deepseek_base_url,
        settings.deepseek_model,
    )


@router.post("", response_model=schemas.ChatResponse)
def chat(req: schemas.ChatRequest, db: Session = Depends(get_db)):
    client = _get_client()
    if client is None:
        return {
            "answer": "尚未配置 DEEPSEEK_API_KEY，请在 backend/.env 中填写后重启服务。",
            "data": {},
            "evidence": None,
            "tool_used": None,
        }

    history = _CONTEXTS.get(req.conversation_id, [])
    result = run_agent(db, req.question, client, history=history)

    # 记录上下文（截断防止无限增长）
    history.append({"role": "user", "content": req.question})
    history.append({"role": "assistant", "content": result["answer"]})
    _CONTEXTS[req.conversation_id] = history[-20:]

    return result
