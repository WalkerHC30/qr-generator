"""
QR Code 路由（Router）

Router 的職責：
- 定義 HTTP 方法和路徑（GET /qr/{id}、POST /qr/generate）
- 接收請求、呼叫 service、回傳結果
- 不包含業務邏輯（那是 service 的事）

設計原則：Router 要盡量薄，邏輯放 service。
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.schemas.qr import QRGenerateRequest, QRGenerateResponse, QRRecordResponse
from app.services.qr_service import QRService

# 建立這個模組的 Router，之後掛到 main.py
router = APIRouter(
    prefix="/qr",       # 所有路由都會加上 /qr 前綴
    tags=["QR Code"],   # 在 Swagger 文件中的分組名稱
)

# 建立 service 實例
# Phase 3 之後會改用 Depends() 做依賴注入
qr_service = QRService()


@router.post(
    "/generate",
    response_model=QRGenerateResponse,
    summary="生成 QR Code",
    description="傳入 URL，生成對應的 QR Code 圖片並儲存記錄。",
    status_code=201,    # 資源建立成功通常回 201
)
async def generate_qr(request: QRGenerateRequest):
    """
    生成 QR Code

    - **url**: 要編碼的網址（必填）
    - **size**: 圖片尺寸（選填，預設 10）
    - **border**: 邊框大小（選填，預設 4）
    """
    try:
        result = await qr_service.generate(
            url=str(request.url),
            size=request.size,
            border=request.border,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{qr_id}/image",
    summary="下載 QR Code 圖片",
    description="用 ID 取得 QR Code 的 PNG 圖片檔。",
)
async def get_qr_image(qr_id: str):
    """回傳 QR Code PNG 圖片"""
    image_path = await qr_service.get_image_path(qr_id)

    if not image_path:
        raise HTTPException(status_code=404, detail="QR Code 不存在")

    # FileResponse：FastAPI 內建，直接回傳檔案給 client
    return FileResponse(
        path=image_path,
        media_type="image/png",
        filename=f"qr_{qr_id}.png",
    )


@router.get(
    "/{qr_id}",
    response_model=QRRecordResponse,
    summary="查詢 QR Code 記錄",
)
async def get_qr_record(qr_id: str):
    """查詢單筆 QR Code 的詳細資訊"""
    record = await qr_service.get_record(qr_id)

    if not record:
        raise HTTPException(status_code=404, detail="QR Code 不存在")

    return record


@router.get(
    "/",
    summary="列出所有 QR Code",
    description="列出最近建立的 QR Code 記錄（Phase 3 前為暫存在記憶體）。",
)
async def list_qr_codes():
    """列出所有已建立的 QR Code（Phase 3 之後才會從資料庫讀取）"""
    records = await qr_service.list_records()
    return {"total": len(records), "items": records}