"""
設定管理
使用 pydantic-settings 讀取環境變數，並提供型別安全的設定存取。
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # 應用基本資訊
    app_name: str = "QR Code Generator"
    app_version: str = "0.1.0"
    debug: bool = False

    # 資料庫
    database_url: str = "sqlite+aiosqlite:///./storage/qr_generator.db"

    # 儲存路徑
    storage_path: str = "./storage/qr_codes"

    # QR Code 預設設定
    qr_default_size: int = 10    # box_size：每個方格的像素大小
    qr_default_border: int = 4   # 邊框寬度（單位：方格數）

    # 讀取 .env 檔案
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


# 建立全域 settings 實例（整個 app 共用同一個）
settings = Settings()