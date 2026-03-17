# QR Code Generator API

> 系統設計練習：從零到百萬級請求

## 快速開始

```bash
# 1. 安裝 uv（如果還沒有）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. 安裝依賴
uv sync

# 3. 啟動開發伺服器
uv run uvicorn app.main:app --reload

# 4. 開啟文件
open http://localhost:8000/docs
```

## 執行測試

```bash
uv run pytest tests/ -v
```

## 學習進度

| Phase | 主題 | 狀態 |
|-------|------|------|
| 1 | FastAPI 基礎建置 & 資料夾結構 | ✅ 進行中 |
| 2 | QR Code 生成功能 | ⬜ |
| 3 | SQLite 資料庫整合 | ⬜ |
| 4 | 百萬請求擴展（Redis、Celery） | ⬜ |

## 專案結構

```
qr-generator/
├── app/
│   ├── main.py          # FastAPI 入口、lifespan、middleware
│   ├── core/
│   │   └── config.py    # 設定管理（pydantic-settings）
│   ├── routers/
│   │   └── qr.py        # HTTP 路由（薄層，只做轉發）
│   ├── schemas/
│   │   └── qr.py        # Pydantic 輸入/輸出模型
│   ├── models/          # Phase 3：SQLAlchemy ORM 模型
│   └── services/
│       └── qr_service.py # 業務邏輯（可測試、可替換）
├── tests/
│   └── test_qr.py
├── storage/
│   └── qr_codes/        # 生成的 QR Code 圖片
├── .env
└── pyproject.toml
```

## API 端點

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | `/health` | 健康檢查 |
| POST | `/qr/generate` | 生成 QR Code |
| GET | `/qr/{id}` | 查詢記錄 |
| GET | `/qr/{id}/image` | 下載圖片 |
| GET | `/qr/` | 列出所有記錄 |