"""AI 问答代理：LLM 决定调用哪个工具 → 工具执行真实查询 → LLM 组织回答。

LLMClient 是抽象层，便于测试时注入 mock（不联网也能验证工具调用链路）。
"""
import json

from sqlalchemy.orm import Session

from . import prompts, tools


class LLMClient:
    """LLM 抽象。complete 返回 (content, tool_calls)，tool_calls 为 [{"id","name","args"}] 或 None。"""

    def complete(self, messages, tool_schemas):
        raise NotImplementedError


class DeepSeekClient(LLMClient):
    def __init__(self, api_key, base_url, model):
        from openai import OpenAI

        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self._model = model

    def complete(self, messages, tool_schemas):
        resp = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            tools=tool_schemas,
            temperature=0,
        )
        msg = resp.choices[0].message
        content = msg.content or ""
        calls = []
        for tc in getattr(msg, "tool_calls", None) or []:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            calls.append({"id": tc.id, "name": tc.function.name, "args": args})
        return content, (calls or None)


def run_agent(db: Session, question: str, client: LLMClient, history: list | None = None) -> dict:
    """执行一次问答。返回 {answer, data, evidence, tool_used}。"""
    messages = [{"role": "system", "content": prompts.SYSTEM_PROMPT}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": question})

    content, calls = client.complete(messages, tools.TOOL_SCHEMAS)

    if not calls:
        # 未调用工具：直接返回（可能是非数据问题或兜底），无数据依据
        return {"answer": content, "data": {}, "evidence": None, "tool_used": None}

    # 执行工具，并把结果回填到对话
    primary = None
    for c in calls:
        result = tools.execute(db, c["name"], c["args"])
        if primary is None:
            primary = result
        messages.append(
            {
                "role": "assistant",
                "content": content or None,
                "tool_calls": [
                    {
                        "id": c["id"],
                        "type": "function",
                        "function": {
                            "name": c["name"],
                            "arguments": json.dumps(c["args"], ensure_ascii=False),
                        },
                    }
                ],
            }
        )
        messages.append({"role": "tool", "tool_call_id": c["id"], "content": result["text"]})

    # 二次调用，让 LLM 根据真实数据组织最终回答
    final_content, _ = client.complete(messages, tools.TOOL_SCHEMAS)

    return {
        "answer": final_content,
        "data": primary["data"] if primary else {},
        "evidence": primary["evidence"] if primary else None,
        "tool_used": primary["evidence"]["tool"] if primary and primary.get("evidence") else None,
    }
