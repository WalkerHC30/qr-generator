"""
QR Code 的 Pydantic Schema（輸入驗證 & 輸出格式）

Schema 的職責：
- 定義 API 接收什麼資料（Request）
- 定義 API 回傳什麼資料（Response）
- 自動做型別驗證和錯誤提示
"""
from pydantic import BaseModel, HttpUrl, Field
from datetime import datetime


# ── Request Schemas ────────────────────────────────────────────

class QRGenerateRequest(BaseModel):
    """
    生成 QR Code 的請求格式

    HttpUrl：Pydantic 內建的 URL 驗證器，
    會自動確認格式是合法的 URL（有 scheme、host 等）
    """
    url: HttpUrl = Field(
        default=...,                               # 明確指定 default=...
        description="要編碼成 QR Code 的網址",
        examples=["https://example.com"]
    )
    size: int = Field(
        default=10,
        ge=1,                                   # ge = greater than or equal（最小值）
        le=50,                                  # le = less than or equal（最大值）
        description="每個方格的像素大小，預設 10"
    )
    border: int = Field(
        default=4,
        ge=0,
        le=20,
        description="QR Code 四周留白的方格數，預設 4"
    )

    # 讓 Pydantic 在文件中顯示範例
    model_config = {
        "json_schema_extra": {
            "example": {
                "url": "https://github.com",
                "size": 10,
                "border": 4,
            }
        }
    }


# ── Response Schemas ───────────────────────────────────────────

class QRGenerateResponse(BaseModel):
    """生成成功後回傳的資料格式"""
    id: str = Field(description="這筆 QR Code 記錄的唯一識別碼")
    original_url: str = Field(description="原始網址")
    image_url: str = Field(description="可以下載 QR Code 圖片的 URL")
    created_at: datetime = Field(description="建立時間")


class QRRecordResponse(BaseModel):
    """查詢單筆 QR Code 記錄"""
    id: str
    original_url: str
    image_url: str
    scan_count: int = Field(description="被掃描的次數（Phase 3 之後才會真的計數）")
    created_at: datetime

    # 讓 Pydantic 可以直接從 SQLAlchemy model 建立
    model_config = {"from_attributes": True}


class HealthResponse(BaseModel):
    """健康檢查回傳格式"""
    status: str
    version: str
    message: str