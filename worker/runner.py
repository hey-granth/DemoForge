import os
import json
import asyncio
import tempfile
import shutil
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone
import redis.asyncio as redis
from playwright.async_api import Error as PlaywrightError
from .browser import BrowserSession
from .discovery import InteractionDiscovery
from .planner import InteractionPlanner
from .executor import ExecutionController
from .recorder import VideoProcessor


# Redis config with socket timeout
REDIS_SOCKET_TIMEOUT = 5.0
REDIS_SOCKET_CONNECT_TIMEOUT = 5.0

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "2"))
MAX_CLICKS = int(os.getenv("MAX_CLICKS", "10"))
MAX_DEPTH = int(os.getenv("MAX_DEPTH", "3"))
MAX_RUNTIME = int(os.getenv("MAX_RUNTIME", "300"))


class DemoWorker:
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.running = True

    async def start(self):
        self.redis_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            decode_responses=False,
            socket_timeout=REDIS_SOCKET_TIMEOUT,
            socket_connect_timeout=REDIS_SOCKET_CONNECT_TIMEOUT,
            retry_on_timeout=True,
            health_check_interval=30,
        )

        try:
            await self.redis_client.ping()
            print(f"Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
        except (redis.RedisError, OSError) as e:
            print(f"Failed to connect to Redis: {e}")
            raise

        print(f"Worker started. Polling queue every {POLL_INTERVAL}s", flush=True)

        while self.running:
            try:
                try:
                    # Check connection before popping
                    await self.redis_client.ping()
                except redis.ConnectionError:
                    print("Redis connection lost. Reconnecting...")
                    await asyncio.sleep(1)
                    continue

                result = await self.redis_client.brpop(
                    ["demo:queue"], timeout=POLL_INTERVAL
                )

                if result:
                    job_id_str = result[1].decode()
                    await self.process_job(job_id_str)

            except KeyboardInterrupt:
                self.running = False
            except (redis.RedisError, OSError, ValueError) as e:
                print(f"Worker error: {e}")
                await asyncio.sleep(POLL_INTERVAL)

        await self.redis_client.close()

    async def process_job(self, job_id: str):
        if not self.redis_client:
            print("Redis client not available")
            return

        print(f"Processing job: {job_id}", flush=True)

        try:
            await self._update_job_status(job_id, "processing")

            job_data = await self.redis_client.get(f"job:{job_id}")
            if not job_data:
                print(f"Job {job_id} not found")
                return

            data = json.loads(job_data)
            url = data["url"]

            video_path = await self._run_demo(url, job_id)

            with open(video_path, "rb") as f:
                video_data = f.read()

            await self.redis_client.setex(f"video:{job_id}", 3600, video_data)

            video_path.unlink()

            await self._update_job_status(job_id, "completed")
            print(f"Job {job_id} completed")

        except (
            redis.RedisError,
            json.JSONDecodeError,
            KeyError,
            OSError,
            RuntimeError,
        ) as e:
            print(f"Job {job_id} failed: {e}")
            await self._update_job_status(job_id, "failed", error=str(e))

    async def _run_demo(self, url: str, job_id: str) -> Path:
        # 1. Create unique temp directory
        temp_dir = Path(tempfile.mkdtemp())
        video_dir = temp_dir / "raw"
        video_dir.mkdir(exist_ok=True)

        browser = None

        try:
            # 2. Start recording
            browser = BrowserSession(video_dir=video_dir)
            await browser.start()

            if not browser.page:
                raise RuntimeError("Browser page failed to initialize")

            # 3. Execute interaction
            discovery = InteractionDiscovery(browser.page)
            planner = InteractionPlanner()
            executor = ExecutionController(
                max_clicks=MAX_CLICKS, max_depth=MAX_DEPTH, max_runtime=MAX_RUNTIME
            )

            await executor.execute_demo(url, browser, discovery, planner)

            # 4. Close browser context explicitly to flush video
            await browser.stop()
            browser = None  # Prevent double close in finally

            # 5. Discover recorded file
            processor = VideoProcessor()
            raw_video = processor.discover_video_file(video_dir)

            # 6. Convert to MP4
            output_path = temp_dir / f"{job_id}.mp4"
            final_video = processor.process_video(raw_video, output_path)

            # 7. Validate output
            if not final_video.exists():
                raise RuntimeError("Final MP4 file missing")

            if final_video.stat().st_size == 0:
                raise RuntimeError("Generated video is empty")

            return final_video

        finally:
            if browser:
                try:
                    await browser.stop()
                except PlaywrightError:
                    pass

            if video_dir.exists():
                try:
                    shutil.rmtree(video_dir, ignore_errors=True)
                except OSError:
                    pass

    async def _update_job_status(
        self, job_id: str, status: str, error: Optional[str] = None
    ):
        if not self.redis_client:
            return

        job_data = await self.redis_client.get(f"job:{job_id}")

        if not job_data:
            return

        data = json.loads(job_data)
        data["status"] = status
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        if error:
            data["error"] = error

        await self.redis_client.setex(f"job:{job_id}", 3600, json.dumps(data))


async def main():
    worker = DemoWorker()
    await worker.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except (OSError, RuntimeError, redis.RedisError) as e:
        print(f"Fatal worker error: {e}")
        exit(1)
