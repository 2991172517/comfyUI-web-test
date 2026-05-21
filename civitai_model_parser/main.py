"""
独立启动：uvicorn main:app --reload --app-dir CustomProject/civitai_model_parser
或从 CustomProject/civitai_model_parser 目录：uvicorn main:app --reload
"""
from __future__ import annotations

import sys
from pathlib import Path

# 复用 backEnd 中的 model_parser 包
_BACKEND = Path(__file__).resolve().parents[1] / "backEnd"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.model_sources import router as model_sources_router

app = FastAPI(title="civitai_model_parser", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(model_sources_router)


@app.get("/health")
def health():
    return {"ok": True}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8010, reload=True)
