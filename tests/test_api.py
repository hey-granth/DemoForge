import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
import json
from datetime import datetime

from api.main import app


@pytest_asyncio.fixture
async def mock_redis():
    mock = AsyncMock()
    mock.setex = AsyncMock(return_value=True)
    mock.lpush = AsyncMock(return_value=1)
    mock.get = AsyncMock()
    mock.delete = AsyncMock(return_value=1)
    mock.ping = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def sample_job_data():
    return {
        "job_id": "test-job-123",
        "url": "https://example.com",
        "status": "pending",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }


class TestAPIEndpoints:
    @patch("api.main.redis_client")
    def test_create_demo_valid_url(self, mock_redis_client, client):
        mock_redis_client.setex = AsyncMock(return_value=True)
        mock_redis_client.lpush = AsyncMock(return_value=1)

        response = client.post("/demo/run", json={"url": "https://example.com"})

        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "pending"
        assert "created_at" in data

    def test_create_demo_invalid_url(self, client):
        response = client.post("/demo/run", json={"url": "not-a-url"})
        assert response.status_code == 422

    def test_create_demo_missing_url(self, client):
        response = client.post("/demo/run", json={})
        assert response.status_code == 422

    @patch("api.main.redis_client")
    def test_get_status_found(self, mock_redis_client, client, sample_job_data):
        mock_redis_client.get = AsyncMock(
            return_value=json.dumps(sample_job_data).encode()
        )

        response = client.get(f"/demo/status/{sample_job_data['job_id']}")

        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == sample_job_data["job_id"]
        assert data["status"] == sample_job_data["status"]

    @patch("api.main.redis_client")
    def test_get_status_not_found(self, mock_redis_client, client):
        mock_redis_client.get = AsyncMock(return_value=None)

        response = client.get("/demo/status/nonexistent")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @patch("api.main.redis_client")
    def test_export_video_job_not_complete(
        self, mock_redis_client, client, sample_job_data
    ):
        incomplete_job = sample_job_data.copy()
        incomplete_job["status"] = "processing"
        mock_redis_client.get = AsyncMock(
            return_value=json.dumps(incomplete_job).encode()
        )

        response = client.get(f"/demo/export/{sample_job_data['job_id']}")

        assert response.status_code == 400
        assert "not completed" in response.json()["detail"].lower()

    @patch("api.main.redis_client")
    def test_export_video_not_found(self, mock_redis_client, client):
        mock_redis_client.get = AsyncMock(return_value=None)

        response = client.get("/demo/export/nonexistent")

        assert response.status_code == 404

    @patch("api.main.redis_client")
    def test_export_video_success(self, mock_redis_client, client, sample_job_data):
        complete_job = sample_job_data.copy()
        complete_job["status"] = "completed"
        mock_redis_client.get = AsyncMock(
            return_value=json.dumps(complete_job).encode()
        )
        mock_redis_client.get.side_effect = [
            json.dumps(complete_job).encode(),
            b"fake_video_data",
        ]
        mock_redis_client.delete = AsyncMock(return_value=2)

        response = client.get(f"/demo/export/{sample_job_data['job_id']}")

        assert response.status_code == 200
        assert response.headers["content-type"] == "video/mp4"

    @patch("api.main.redis_client")
    def test_cleanup_job_success(self, mock_redis_client, client):
        mock_redis_client.delete = AsyncMock(return_value=2)

        response = client.delete("/demo/cleanup/test-job")

        assert response.status_code == 200
        assert response.json()["status"] == "deleted"

    @patch("api.main.redis_client")
    def test_cleanup_job_not_found(self, mock_redis_client, client):
        mock_redis_client.delete = AsyncMock(return_value=0)

        response = client.delete("/demo/cleanup/nonexistent")

        assert response.status_code == 404

    @patch("api.main.redis_client")
    def test_health_check_success(self, mock_redis_client, client):
        mock_redis_client.ping = AsyncMock(return_value=True)

        response = client.get("/health")

        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_health_check_redis_unavailable(self, client):
        with patch("api.main.redis_client", None):
            response = client.get("/health")
            assert response.status_code == 503

    def test_concurrent_job_creation(self, client):
        with patch("api.main.redis_client") as mock_redis:
            mock_redis.setex = AsyncMock(return_value=True)
            mock_redis.lpush = AsyncMock(return_value=1)

            responses = []
            for _ in range(10):
                response = client.post("/demo/run", json={"url": "https://example.com"})
                responses.append(response)

            job_ids = [r.json()["job_id"] for r in responses]
            assert len(job_ids) == len(set(job_ids))
