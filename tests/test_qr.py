"""
Phase 1 基本測試

學習重點：
- 用 httpx.AsyncClient 測試 FastAPI
- 每個測試函數是一個獨立情境
- 測試命名：test_動詞_情境
"""
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.fixture
async def client():
    """
    建立測試用的 HTTP client。

    使用 ASGITransport 讓 httpx 直接呼叫 FastAPI，
    不需要真正啟動 server。
    """
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac


# ── 健康檢查 ───────────────────────────────────────────────────

async def test_health_check(client):
    """健康檢查端點應回傳 200"""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


# ── QR Code 生成 ───────────────────────────────────────────────

async def test_generate_qr_success(client):
    """正常生成 QR Code 應回傳 201 和正確格式"""
    response = await client.post(
        "/qr/generate",
        json={"url": "https://example.com"}
    )
    assert response.status_code == 201

    data = response.json()
    assert "id" in data
    assert data["original_url"] == "https://example.com"
    assert "/image" in data["image_url"]


async def test_generate_qr_invalid_url(client):
    """傳入無效 URL 應回傳 422（Validation Error）"""
    response = await client.post(
        "/qr/generate",
        json={"url": "not-a-valid-url"}
    )
    assert response.status_code == 422


async def test_generate_qr_custom_size(client):
    """自訂 size 和 border 應成功"""
    response = await client.post(
        "/qr/generate",
        json={"url": "https://example.com", "size": 20, "border": 2}
    )
    assert response.status_code == 201


async def test_generate_qr_size_out_of_range(client):
    """size 超出範圍應回傳 422"""
    response = await client.post(
        "/qr/generate",
        json={"url": "https://example.com", "size": 999}  # 最大 50
    )
    assert response.status_code == 422


# ── QR Code 查詢 ───────────────────────────────────────────────

async def test_get_qr_record(client):
    """先建立再查詢，應取得相同資料"""
    # 先建立
    create_response = await client.post(
        "/qr/generate",
        json={"url": "https://github.com"}
    )
    qr_id = create_response.json()["id"]

    # 再查詢
    get_response = await client.get(f"/qr/{qr_id}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == qr_id


async def test_get_qr_not_found(client):
    """查詢不存在的 ID 應回傳 404"""
    response = await client.get("/qr/non-existent-id")
    assert response.status_code == 404


async def test_get_qr_image(client):
    """取得圖片應回傳 PNG 格式"""
    # 先建立
    create_response = await client.post(
        "/qr/generate",
        json={"url": "https://fastapi.tiangolo.com"}
    )
    qr_id = create_response.json()["id"]

    # 取得圖片
    image_response = await client.get(f"/qr/{qr_id}/image")
    assert image_response.status_code == 200
    assert image_response.headers["content-type"] == "image/png"


async def test_list_qr_codes(client):
    """建立後列表應包含該筆記錄"""
    # 建立一筆
    await client.post("/qr/generate", json={"url": "https://python.org"})

    # 列表
    response = await client.get("/qr/")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1


# ── Phase 2：新功能測試 ────────────────────────────────────────

async def test_generate_qr_with_custom_color(client):
    """自訂顏色應成功生成"""
    response = await client.post(
        "/qr/generate",
        json={
            "url": "https://example.com",
            "fill_color": "#1a1a2e",
            "back_color": "#ffffff",
        }
    )
    assert response.status_code == 201


async def test_generate_qr_invalid_hex_color(client):
    """無效 Hex 顏色格式應回傳 422"""
    response = await client.post(
        "/qr/generate",
        json={
            "url": "https://example.com",
            "fill_color": "#GGGGGG",   # G 不是合法 hex 字元
        }
    )
    assert response.status_code == 422


async def test_generate_qr_base64_output(client):
    """base64 格式應回傳 data URI 而非 image_url"""
    response = await client.post(
        "/qr/generate",
        json={
            "url": "https://example.com",
            "output_format": "base64",
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["image_base64"].startswith("data:image/png;base64,")
    assert data["image_url"] is None


async def test_generate_qr_error_correction_h(client):
    """H 容錯等級應成功生成"""
    response = await client.post(
        "/qr/generate",
        json={
            "url": "https://example.com",
            "error_correction": "H",
        }
    )
    assert response.status_code == 201


async def test_generate_qr_file_has_image_url(client):
    """file 格式應有 image_url 且無 base64"""
    response = await client.post(
        "/qr/generate",
        json={
            "url": "https://example.com",
            "output_format": "file",
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["image_url"] is not None
    assert data["image_base64"] is None