import os
import asyncio
from pathlib import Path
from typing import Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page


class BrowserSession:
    def __init__(
        self,
        viewport_width: int = 1280,
        viewport_height: int = 720,
        video_dir: Optional[Path] = None
    ):
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height
        self.video_dir = video_dir or Path("/tmp/videos")
        self.video_dir.mkdir(exist_ok=True)
        
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.video_path: Optional[Path] = None
    
    async def start(self):
        self.playwright = await async_playwright().start()
        
        self.browser = await self.playwright.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--no-sandbox"
            ]
        )
        
        self.context = await self.browser.new_context(
            viewport={"width": self.viewport_width, "height": self.viewport_height},
            record_video_dir=str(self.video_dir),
            record_video_size={"width": self.viewport_width, "height": self.viewport_height}
        )
        
        self.page = await self.context.new_page()
        
        await self.page.set_extra_http_headers({
            "Accept-Language": "en-US,en;q=0.9"
        })
    
    async def navigate(self, url: str, timeout: int = 30000):
        if not self.page:
            raise RuntimeError("Browser page not initialized")
        await self.page.goto(url, wait_until="networkidle", timeout=timeout)
        await asyncio.sleep(1)
    
    async def wait_for_idle(self, timeout: int = 5000):
        if not self.page:
            return
        try:
            await self.page.wait_for_load_state("networkidle", timeout=timeout)
        except:
            pass
    
    async def scroll_page(self):
        if not self.page:
            return
        
        total_height = await self.page.evaluate("document.body.scrollHeight")
        viewport_height = self.viewport_height
        
        current_position = 0
        while current_position < total_height:
            await self.page.evaluate(f"window.scrollTo(0, {current_position})")
            await asyncio.sleep(0.5)
            current_position += viewport_height
        
        await self.page.evaluate("window.scrollTo(0, 0)")
        await asyncio.sleep(0.5)
    
    async def click_element(self, selector: str, timeout: int = 5000):
        if not self.page:
            return False
        try:
            await self.page.click(selector, timeout=timeout)
            await self.wait_for_idle()
            return True
        except Exception as e:
            return False
    
    async def get_current_url(self) -> str:
        if not self.page:
            return ""
        return self.page.url
    
    async def screenshot(self, path: Path):
        if not self.page:
            return
        await self.page.screenshot(path=str(path))
    
    async def stop(self):
        try:
            if self.page and self.page.video:
                self.video_path = await self.page.video.path()
        except:
            pass
        
        try:
            if self.context:
                await self.context.close()
        except:
            pass
        
        try:
            if self.browser:
                await self.browser.close()
        except:
            pass
        
        try:
            if self.playwright:
                await self.playwright.stop()
        except:
            pass
    
    async def get_video_path(self) -> Optional[Path]:
        if self.video_path:
            return Path(self.video_path)
        return None
