"""
QR Code 的 Pydantic Schema（輸入驗證 & 輸出格式）

Schema 的職責：
- 定義 API 接收什麼資料（Request）
- 定義 API 回傳什麼資料（Response）
- 自動做型別驗證和錯誤提示
"""
from enum import Enum
from pydantic import BaseModel, HttpUrl, Field, field_validator
from datetime import datetime
import re


# ── Enums ──────────────────────────────────────────────────────

class ErrorCorrection(str, Enum):
    """
    QR Code 容錯等級

    容錯率越高 → QR Code 越複雜（方格越多）→ 但髒污或遮擋時仍可掃描
    加 Logo 至少要用 H，因為 Logo 會遮住中間區域
    """
    L = "L"   # 7%  容錯，圖片最小
    M = "M"   # 15% 容錯，一般用途
    Q = "Q"   # 25% 容錯，有輕微遮擋時
    H = "H"   # 30% 容錯，加 Logo 必用


class OutputFormat(str, Enum):
    """回傳格式"""
    FILE = "file"       # 儲存成 PNG 檔（預設）
    BASE64 = "base64"   # 回傳 base64 字串（前端直接顯示用）


# ── Request Schemas ────────────────────────────────────────────

class QRGenerateRequest(BaseModel):
    """
    生成 QR Code 的請求格式

    HttpUrl：Pydantic 內建的 URL 驗證器，
    會自動確認格式是合法的 URL（有 scheme、host 等）
    """
    url: HttpUrl = Field(
        ...,
        description="要編碼成 QR Code 的網址",
    )
    size: int = Field(
        default=10,
        ge=1,
        le=50,
        description="每個方格的像素大小，預設 10",
    )
    border: int = Field(
        default=4,
        ge=0,
        le=20,
        description="QR Code 四周留白的方格數，預設 4",
    )
    fill_color: str = Field(
        default="black",
        description="QR Code 前景色，支援顏色名稱（black）或 Hex（#1a1a2e）",
    )
    back_color: str = Field(
        default="white",
        description="QR Code 背景色，支援顏色名稱或 Hex",
    )
    error_correction: ErrorCorrection = Field(
        default=ErrorCorrection.M,
        description="容錯等級：L=7%, M=15%, Q=25%, H=30%。加 Logo 請用 H",
    )
    output_format: OutputFormat = Field(
        default=OutputFormat.FILE,
        description="回傳格式：file=存檔回傳 URL, base64=直接回傳圖片字串",
    )

    @field_validator("fill_color", "back_color")
    @classmethod
    def validate_color(cls, v: str) -> str:
        """
        驗證顏色格式：接受顏色名稱或 #RRGGBB hex
        Pillow 支援的顏色名稱非常多，這裡只做基本的 hex 格式檢查
        """
        if v.startswith("#"):
            if not re.match(r"^#[0-9a-fA-F]{6}$", v):
                raise ValueError("Hex 顏色格式錯誤，請使用 #RRGGBB 格式，例如 #ff0000")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "url": "https://github.com",
                "size": 10,
                "border": 4,
                "fill_color": "#1a1a2e",
                "back_color": "#ffffff",
                "error_correction": "M",
                "output_format": "file",
            }
        }
    }


# ── Response Schemas ───────────────────────────────────────────

class QRGenerateResponse(BaseModel):
    """生成成功後回傳的資料格式"""
    id: str = Field(description="這筆 QR Code 記錄的唯一識別碼")
    original_url: str = Field(description="原始網址")
    image_url: str | None = Field(default=None, description="下載圖片的 URL（output_format=file 時才有）")
    image_base64: str | None = Field(default=None, description="base64 圖片字串（output_format=base64 時才有）")
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