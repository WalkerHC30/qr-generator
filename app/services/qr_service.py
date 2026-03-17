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
import os
from datetime import datetime, timezone
from pathlib import Path

import qrcode
from qrcode.constants import ERROR_CORRECT_L
from qrcode.image.pure import PyPNGImage

from app.core.config import settings


class QRService:
    def __init__(self):
        # Phase 1 暫用：記憶體儲存
        # Phase 3 換成資料庫後這裡會移除
        self._records: dict[str, dict] = {}

        # 確保儲存資料夾存在
        self.storage_path = Path(settings.storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

    async def generate(self, url: str, size: int, border: int) -> dict:
        """
        生成 QR Code 並儲存

        流程：
        1. 產生唯一 ID
        2. 用 qrcode library 生成圖片
        3. 儲存到檔案系統
        4. 記錄 metadata（Phase 1 存記憶體、Phase 3 存資料庫）
        5. 回傳結果
        """
        # 1. 產生唯一 ID
        qr_id = str(uuid.uuid4())

        # 2. 生成 QR Code
        qr = qrcode.QRCode(
            version=None,           # None = 自動選擇最小夠用的版本（1–40）
            error_correction=ERROR_CORRECT_L,
            # error_correction 選項（容錯率）：
            # ERROR_CORRECT_L = 7%   → 圖片小，掃描環境好時用
            # ERROR_CORRECT_M = 15%  → 預設推薦值
            # ERROR_CORRECT_Q = 25%  → 有部分遮擋時用
            # ERROR_CORRECT_H = 30%  → 最大容錯，適合印在不平整表面
            box_size=size,
            border=border,
        )
        qr.add_data(url)
        qr.make(fit=True)  # fit=True：讓 QR Code 自動選最小版本

        # 3. 儲存圖片
        image_path = self.storage_path / f"{qr_id}.png"
        
        img = qr.make_image(fill_color="black", back_color="white")
        with open(image_path, "wb") as f:
            img.save(f)
        # img.save(str(image_path)) # type: ignore

        # 4. 儲存 metadata
        now = datetime.now(timezone.utc)
        record = {
            "id": qr_id,
            "original_url": url,
            "image_path": str(image_path),
            "image_url": f"/qr/{qr_id}/image",
            "scan_count": 0,
            "created_at": now,
        }

        # Phase 1：暫存在記憶體
        self._records[qr_id] = record

        return record

    async def get_image_path(self, qr_id: str) -> str | None:
        """取得圖片的檔案路徑"""
        record = self._records.get(qr_id)
        if not record:
            return None

        image_path = record["image_path"]
        if not os.path.exists(image_path):
            return None

        return image_path

    async def get_record(self, qr_id: str) -> dict | None:
        """查詢單筆記錄"""
        return self._records.get(qr_id)

    async def list_records(self) -> list[dict]:
        """列出所有記錄（依建立時間倒序）"""
        records = list(self._records.values())
        return sorted(records, key=lambda r: r["created_at"], reverse=True)