import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
from worker.runner import DemoWorker


@pytest.fixture
def mock_redis():
    redis_mock = AsyncMock()
    redis_mock.brpop = AsyncMock()
    redis_mock.get = AsyncMock()
    redis_mock.setex = AsyncMock()
    redis_mock.close = AsyncMock()
    return redis_mock


@pytest.fixture
def sample_job_data():
    return {
        "job_id": "test-job-123",
        "url": "https://example.com",
        "status": "pending",
        "created_at": "2026-01-01T00:00:00",
        "updated_at": "2026-01-01T00:00:00",
    }


class TestDemoWorker:
    @pytest.mark.asyncio
    async def test_initialization(self):
        worker = DemoWorker()

        assert worker.redis_client is None
        assert worker.running is True

    @pytest.mark.asyncio
    @patch("worker.runner.redis.Redis")
    async def test_start_connects_to_redis(self, mock_redis_class):
        mock_redis_instance = AsyncMock()
        mock_redis_class.return_value = mock_redis_instance
        mock_redis_instance.brpop = AsyncMock(return_value=None)

        worker = DemoWorker()
        worker.running = False

        await worker.start()

        assert mock_redis_class.called

    @pytest.mark.asyncio
    async def test_process_job_updates_status(self, mock_redis, sample_job_data):
        worker = DemoWorker()
        worker.redis_client = mock_redis

        mock_redis.get.return_value = json.dumps(sample_job_data).encode()

        with patch.object(
            worker, "_run_demo", AsyncMock(return_value=Path("/tmp/video.mp4"))
        ):
            with patch("builtins.open", MagicMock()):
                with patch.object(Path, "unlink"):
                    await worker.process_job("test-job-123")

        assert mock_redis.setex.called

    @pytest.mark.asyncio
    async def test_process_job_handles_missing_job(self, mock_redis):
        worker = DemoWorker()
        worker.redis_client = mock_redis

        mock_redis.get.return_value = None

        await worker.process_job("nonexistent")

    @pytest.mark.asyncio
    async def test_process_job_handles_execution_failure(
        self, mock_redis, sample_job_data
    ):
        worker = DemoWorker()
        worker.redis_client = mock_redis

        mock_redis.get.return_value = json.dumps(sample_job_data).encode()

        with patch.object(
            worker, "_run_demo", AsyncMock(side_effect=Exception("Execution failed"))
        ):
            await worker.process_job("test-job-123")

        calls = [str(call) for call in mock_redis.setex.call_args_list]
        assert any("failed" in str(call) for call in calls)

    @pytest.mark.asyncio
    async def test_run_demo_initializes_components(self, tmp_path):
        worker = DemoWorker()

        with patch("worker.runner.BrowserSession") as mock_browser_class:
            mock_browser = AsyncMock()
            mock_browser.start = AsyncMock()
            mock_browser.stop = AsyncMock()
            mock_browser.page = MagicMock()
            mock_browser.get_video_path = AsyncMock(
                return_value=tmp_path / "video.webm"
            )
            mock_browser_class.return_value = mock_browser

            (tmp_path / "video.webm").write_bytes(b"fake_video")

            with patch("worker.runner.ExecutionController") as mock_executor_class:
                mock_executor = AsyncMock()
                mock_executor.execute_demo = AsyncMock()
                mock_executor_class.return_value = mock_executor

                with patch("worker.runner.VideoProcessor") as mock_processor_class:
                    mock_processor = MagicMock()
                    mock_processor.process_video = MagicMock(
                        return_value=tmp_path / "output.mp4"
                    )
                    mock_processor_class.return_value = mock_processor

                    (tmp_path / "output.mp4").write_bytes(b"processed_video")

                    result = await worker._run_demo("https://example.com", "test-job")

                    assert mock_browser.start.called
                    assert mock_executor.execute_demo.called

    @pytest.mark.asyncio
    async def test_run_demo_cleans_up_on_failure(self, tmp_path):
        worker = DemoWorker()

        with patch("worker.runner.BrowserSession") as mock_browser_class:
            mock_browser = AsyncMock()
            mock_browser.start = AsyncMock()
            mock_browser.stop = AsyncMock()
            mock_browser.page = MagicMock()
            mock_browser_class.return_value = mock_browser

            with patch("worker.runner.ExecutionController") as mock_executor_class:
                mock_executor = AsyncMock()
                mock_executor.execute_demo = AsyncMock(
                    side_effect=Exception("Test error")
                )
                mock_executor_class.return_value = mock_executor

                with pytest.raises(Exception):
                    await worker._run_demo("https://example.com", "test-job")

                assert mock_browser.stop.called

    @pytest.mark.asyncio
    async def test_run_demo_validates_page_initialization(self, tmp_path):
        worker = DemoWorker()

        with patch("worker.runner.BrowserSession") as mock_browser_class:
            mock_browser = AsyncMock()
            mock_browser.start = AsyncMock()
            mock_browser.page = None
            mock_browser_class.return_value = mock_browser

            with pytest.raises(RuntimeError, match="page failed to initialize"):
                await worker._run_demo("https://example.com", "test-job")

    @pytest.mark.asyncio
    async def test_update_job_status_without_redis(self):
        worker = DemoWorker()
        worker.redis_client = None

        await worker._update_job_status("test-job", "completed")

    @pytest.mark.asyncio
    async def test_update_job_status_with_error(self, mock_redis, sample_job_data):
        worker = DemoWorker()
        worker.redis_client = mock_redis

        mock_redis.get.return_value = json.dumps(sample_job_data).encode()

        await worker._update_job_status("test-job", "failed", error="Test error")

        assert mock_redis.setex.called
        call_args = mock_redis.setex.call_args[0]
        job_data = json.loads(call_args[2])
        assert job_data["status"] == "failed"
        assert job_data["error"] == "Test error"

    @pytest.mark.asyncio
    async def test_run_demo_cleanup_temp_directory(self, tmp_path):
        worker = DemoWorker()

        with patch("worker.runner.tempfile.mkdtemp", return_value=str(tmp_path)):
            with patch("worker.runner.BrowserSession") as mock_browser_class:
                mock_browser = AsyncMock()
                mock_browser.start = AsyncMock()
                mock_browser.stop = AsyncMock()
                mock_browser.page = MagicMock()
                mock_browser.get_video_path = AsyncMock(
                    return_value=tmp_path / "video.webm"
                )
                mock_browser_class.return_value = mock_browser

                (tmp_path / "video.webm").write_bytes(b"fake")

                with patch("worker.runner.ExecutionController") as mock_executor_class:
                    mock_executor = AsyncMock()
                    mock_executor.execute_demo = AsyncMock()
                    mock_executor_class.return_value = mock_executor

                    with patch("worker.runner.VideoProcessor") as mock_processor_class:
                        mock_processor = MagicMock()
                        output_path = tmp_path / "output.mp4"
                        mock_processor.process_video = MagicMock(
                            return_value=output_path
                        )
                        mock_processor_class.return_value = mock_processor

                        output_path.write_bytes(b"processed")

                        with patch("worker.runner.shutil.rmtree") as mock_rmtree:
                            result = await worker._run_demo(
                                "https://example.com", "test-job"
                            )

                            assert mock_rmtree.called
