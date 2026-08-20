"""FastAPI 应用入口。"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import chat, dashboard, insights

app = FastAPI(title="Moneki Analytics", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dashboard.router)
app.include_router(chat.router)
app.include_router(insights.router)


@app.get("/health")
def health():
    return {"status": "ok"}
