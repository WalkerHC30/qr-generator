"""
QR Code 路由（Router）

Phase 2 新增：
- generate 接收更多參數（顏色、容錯等級、輸出格式）
- POST /qr/generate-with-logo：上傳 Logo 並生成

Router 的職責：
- 定義 HTTP 方法和路徑
- 接收請求、呼叫 service、回傳結果
- 不包含業務邏輯（那是 service 的事）
"""
import os
import tempfile

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse

from app.schemas.qr import (
    QRGenerateRequest,
    QRGenerateResponse,
    QRRecordResponse,
    ErrorCorrection,
    OutputFormat,
)
from app.services.qr_service import QRService

router = APIRouter(
    prefix="/qr",
    tags=["QR Code"],
)

qr_service = QRService()


@router.post(
    "/generate",
    response_model=QRGenerateResponse,
    summary="生成 QR Code",
    status_code=201,
)
async def generate_qr(request: QRGenerateRequest):
    """
    生成 QR Code

    - **url**: 要編碼的網址（必填）
    - **size**: 方格像素大小（預設 10）
    - **border**: 邊框方格數（預設 4）
    - **fill_color**: 前景色，支援名稱或 Hex（預設 black）
    - **back_color**: 背景色，支援名稱或 Hex（預設 white）
    - **error_correction**: 容錯等級 L/M/Q/H（預設 M）
    - **output_format**: file 存檔回傳 URL，base64 直接回傳圖片字串
    """
    try:
        result = await qr_service.generate(
            url=str(request.url),
            size=request.size,
            border=request.border,
            fill_color=request.fill_color,
            back_color=request.back_color,
            error_correction=request.error_correction,
            output_format=request.output_format,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/generate-with-logo",
    response_model=QRGenerateResponse,
    summary="生成含 Logo 的 QR Code",
    status_code=201,
)
async def generate_qr_with_logo(
    # Form 欄位：因為同時上傳檔案，必須用 multipart/form-data
    # 不能再用 JSON body（兩種格式不能混用）
    url: str = Form(..., description="要編碼的網址"),
    size: int = Form(default=10, ge=1, le=50),
    border: int = Form(default=4, ge=0, le=20),
    fill_color: str = Form(default="black"),
    back_color: str = Form(default="white"),
    error_correction: ErrorCorrection = Form(default=ErrorCorrection.H),
    # 加 Logo 時強烈建議用 H 等級，這裡預設改為 H
    logo: UploadFile = File(..., description="Logo 圖片（PNG/JPG，建議正方形）"),
):
    """
    生成含 Logo 的 QR Code

    **注意**：加 Logo 時容錯等級預設為 H（30%），
    因為 Logo 會遮住中央約 28% 的區域。
    """
    # 驗證 Logo 格式
    allowed_types = {"image/png", "image/jpeg", "image/jpg", "image/webp"}
    if logo.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"不支援的圖片格式：{logo.content_type}，請上傳 PNG 或 JPG"
        )

    # 把上傳的 Logo 暫存到磁碟
    # tempfile.NamedTemporaryFile：系統自動管理的暫存檔案
    # delete=False 讓我們可以在 with 區塊外繼續讀取
    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=os.path.splitext(logo.filename or "logo.png")[1]
    ) as tmp:
        content = await logo.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        result = await qr_service.generate(
            url=url,
            size=size,
            border=border,
            fill_color=fill_color,
            back_color=back_color,
            error_correction=error_correction,
            output_format=OutputFormat.FILE,
            logo_path=tmp_path,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # 無論成功失敗都要清理暫存檔
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


@router.get(
    "/{qr_id}/image",
    summary="下載 QR Code 圖片",
)
async def get_qr_image(qr_id: str):
    """回傳 QR Code PNG 圖片"""
    image_path = await qr_service.get_image_path(qr_id)

    if not image_path:
        raise HTTPException(status_code=404, detail="QR Code 不存在或為 base64 格式（無檔案）")

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
)
async def list_qr_codes():
    """列出所有已建立的 QR Code"""
    records = await qr_service.list_records()
    return {"total": len(records), "items": records}