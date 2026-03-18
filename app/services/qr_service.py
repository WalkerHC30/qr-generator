"""
QR Code Service（業務邏輯層）

Service 的職責：
- 實際執行業務邏輯（生成 QR Code、儲存檔案）
- 呼叫資料庫（Phase 3 之後）
- 不直接處理 HTTP 請求/回應

Phase 1: 用記憶體 dict 暫存資料（不用資料庫）
Phase 3: 換成真正的 SQLite 操作
"""
import uuid
import base64
import os
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import cast

import qrcode
from qrcode.constants import (
    ERROR_CORRECT_L,
    ERROR_CORRECT_M,
    ERROR_CORRECT_Q,
    ERROR_CORRECT_H,
)
from PIL import Image

from app.core.config import settings
from app.schemas.qr import ErrorCorrection, OutputFormat


# error_correction 選項（容錯率）：
# ERROR_CORRECT_L = 7%   → 圖片小，掃描環境好時用
# ERROR_CORRECT_M = 15%  → 預設推薦值
# ERROR_CORRECT_Q = 25%  → 有部分遮擋時用
# ERROR_CORRECT_H = 30%  → 最大容錯，適合加 Logo 或印在不平整表面
ERROR_CORRECTION_MAP = {
    ErrorCorrection.L: ERROR_CORRECT_L,
    ErrorCorrection.M: ERROR_CORRECT_M,
    ErrorCorrection.Q: ERROR_CORRECT_Q,
    ErrorCorrection.H: ERROR_CORRECT_H,
}


class QRService:
    def __init__(self):
        # Phase 1 暫用：記憶體儲存
        # Phase 3 換成資料庫後這裡會移除
        self._records: dict[str, dict] = {}

        # 確保儲存資料夾存在
        self.storage_path = Path(settings.storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

    async def generate(
        self,
        url: str,
        size: int,
        border: int,
        fill_color: str = "black",
        back_color: str = "white",
        error_correction: ErrorCorrection = ErrorCorrection.M,
        output_format: OutputFormat = OutputFormat.FILE,
        logo_path: str | None = None,
    ) -> dict:
        """
        生成 QR Code

        流程：
        1. 產生唯一 ID
        2. 建立 QRCode 物件並生成圖片
        3. （選用）疊加 Logo
        4. 依 output_format 決定存檔或轉 base64
        5. 儲存 metadata 並回傳
        """
        # ── 1. 產生唯一 ID ────────────────────────────────────
        qr_id = str(uuid.uuid4())

        # ── 2. 建立 QR Code ───────────────────────────────────
        qr = qrcode.QRCode(
            version=None,  # 自動選擇最小夠用的版本（1–40）
            error_correction=ERROR_CORRECTION_MAP[error_correction],
            box_size=size,
            border=border,
        )
        qr.add_data(url)
        qr.make(fit=True)  # fit=True：讓 QR Code 自動選最小版本

        # make_image 回傳 Pillow Image 物件
        # .convert("RGBA") 確保支援透明度，疊加 Logo 時需要
        raw = qr.make_image(fill_color=fill_color, back_color=back_color)
        img: Image.Image = cast(Image.Image, raw).convert("RGBA")

        # ── 3. 疊加 Logo（選用）──────────────────────────────
        if logo_path:
            img = self._add_logo(img, logo_path)

        # ── 4. 輸出：存檔 or base64 ───────────────────────────
        image_url: str | None = None
        image_base64: str | None = None

        if output_format == OutputFormat.FILE:
            image_path = self.storage_path / f"{qr_id}.png"
            # 存檔前轉回 RGB（去掉透明通道，相容性更好）
            img.convert("RGB").save(str(image_path))
            image_url = f"/qr/{qr_id}/image"

        else:  # OutputFormat.BASE64
            # BytesIO = 記憶體中的虛擬檔案，不寫磁碟直接轉 base64
            buffer = BytesIO()
            img.convert("RGB").save(buffer, format="PNG")
            buffer.seek(0)  # 讀取位置移回開頭
            b64_data = base64.b64encode(buffer.read()).decode("utf-8")
            # data URI 格式，前端可直接放在 <img src="..."> 裡
            image_base64 = f"data:image/png;base64,{b64_data}"

        # ── 5. 儲存 metadata ──────────────────────────────────
        now = datetime.now(timezone.utc)
        record = {
            "id": qr_id,
            "original_url": url,
            # file 模式才有實體路徑，base64 模式為 None
            "image_path": str(self.storage_path / f"{qr_id}.png")
            if output_format == OutputFormat.FILE
            else None,
            "image_url": image_url,
            "image_base64": image_base64,
            "fill_color": fill_color,
            "back_color": back_color,
            "error_correction": error_correction.value,
            "scan_count": 0,
            "created_at": now,
        }

        # Phase 1：暫存在記憶體；Phase 3 換成資料庫寫入
        self._records[qr_id] = record
        return record

    def _add_logo(self, qr_img: Image.Image, logo_path: str) -> Image.Image:
        """
        在 QR Code 中央疊加 Logo

        原理：
        - QR Code 用四個角的「定位點」來對齊，中央區域相對不重要
        - H 容錯等級允許 30% 的區域損毀仍可掃描
        - 所以 Logo 最多佔整體約 28%，保留一些容錯餘裕
        """
        if not os.path.exists(logo_path):
            raise FileNotFoundError(f"Logo 檔案不存在：{logo_path}")

        logo = Image.open(logo_path).convert("RGBA")

        # Logo 最大尺寸 = QR Code 寬度的 28%
        qr_width, qr_height = qr_img.size
        max_logo_size = int(qr_width * 0.28)

        # thumbnail() 等比例縮放，不超過指定尺寸
        # LANCZOS = 高品質縮放演算法（適合縮小圖片）
        logo.thumbnail((max_logo_size, max_logo_size), Image.Resampling.LANCZOS)

        # 計算置中座標
        logo_w, logo_h = logo.size
        pos_x = (qr_width - logo_w) // 2
        pos_y = (qr_height - logo_h) // 2

        # 先貼白色背景（讓 Logo 在深色 QR Code 上清楚可見）
        padding = 6
        bg = Image.new("RGBA", (logo_w + padding * 2, logo_h + padding * 2), "white")
        qr_img.paste(bg, (pos_x - padding, pos_y - padding))

        # 再貼 Logo，mask=logo 讓透明區域不覆蓋 QR Code
        qr_img.paste(logo, (pos_x, pos_y), mask=logo)

        return qr_img

    async def get_image_path(self, qr_id: str) -> str | None:
        """取得圖片的檔案路徑（base64 模式的記錄會回傳 None）"""
        record = self._records.get(qr_id)
        if not record or not record.get("image_path"):
            return None
        if not os.path.exists(record["image_path"]):
            return None
        return record["image_path"]

    async def get_record(self, qr_id: str) -> dict | None:
        """查詢單筆記錄"""
        return self._records.get(qr_id)

    async def list_records(self) -> list[dict]:
        """列出所有記錄（依建立時間倒序）"""
        records = list(self._records.values())
        return sorted(records, key=lambda r: r["created_at"], reverse=True)