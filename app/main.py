"""
FastAPI 應用程式入口

1. 建立 FastAPI app 實例
2. 用 lifespan 管理啟動/關閉時要做的事（取代舊版 @app.on_event）
3. 掛載所有 Router
4. 設定全域中介層（CORS、例外處理等）
"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import qr
from app.schemas.qr import HealthResponse


# ── Lifespan（應用程式生命週期）──────────────────────────────────
# lifespan 是 FastAPI 0.93+ 的新寫法，取代 @app.on_event("startup")
# yield 前 = 啟動時執行
# yield 後 = 關閉時執行（清理資源）

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── 啟動 ──
    print(f"🚀 {settings.app_name} v{settings.app_version} 啟動中...")

    # 確保必要資料夾存在
    Path(settings.storage_path).mkdir(parents=True, exist_ok=True)
    print(f"📁 QR Code 儲存路徑：{settings.storage_path}")

    # Phase 3 在這裡初始化資料庫連線
    # Phase 4 在這裡初始化 Redis 連線

    print("✅ 啟動完成！文件：http://localhost:8000/docs")

    yield  # ← 應用程式在這裡運行

    # ── 關閉 ──
    print("👋 正在關閉應用程式...")
    # Phase 3 在這裡關閉資料庫連線


# ── 建立 FastAPI App ───────────────────────────────────────────
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
## QR Code Generator API

### 目前進度
- ✅ Phase 1：FastAPI 基礎建置
- ⬜ Phase 2：QR Code 生成
- ⬜ Phase 3：資料庫整合
- ⬜ Phase 4：百萬請求擴展
    """,
    lifespan=lifespan,
    docs_url="/docs",       # Swagger UI
    redoc_url="/redoc",     # ReDoc 文件
)


# ── 中介層（Middleware）────────────────────────────────────────
# CORS：允許前端從不同網域呼叫 API
# 開發階段先允許全部，正式環境要限縮 allow_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── 掛載 Router ────────────────────────────────────────────────
app.include_router(qr.router)


# ── 基本路由 ───────────────────────────────────────────────────
@app.get("/", include_in_schema=False)
async def root():
    """根路由，重導向到文件"""
    return {"message": "QR Code Generator API", "docs": "/docs"}


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["System"],
    summary="健康檢查",
)
async def health_check():
    """
    確認服務是否正常運行。

    監控系統（如 k8s liveness probe）會定期打這個端點，
    回傳 200 = 服務正常，非 200 = 需要重啟。
    """
    return HealthResponse(
        status="ok",
        version=settings.app_version,
        message="服務運行中",
    )