import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from worker.browser import BrowserSession


@pytest.fixture
def temp_video_dir(tmp_path):
    return tmp_path / "videos"


class TestBrowserSession:
    @pytest.mark.asyncio
    async def test_initialization(self, temp_video_dir):
        browser = BrowserSession(video_dir=temp_video_dir)

        assert browser.viewport_width == 1280
        assert browser.viewport_height == 720
        assert browser.video_dir == temp_video_dir
        assert browser.page is None
        assert browser.browser is None

    @pytest.mark.asyncio
    async def test_start_creates_browser(self, temp_video_dir):
        browser = BrowserSession(video_dir=temp_video_dir)

        with patch("demoforge.core.browser.async_playwright") as mock_pw:
            mock_playwright = AsyncMock()
            mock_pw.return_value.start = AsyncMock(return_value=mock_playwright)

            mock_browser = AsyncMock()
            mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)

            mock_context = AsyncMock()
            mock_browser.new_context = AsyncMock(return_value=mock_context)

            mock_page = AsyncMock()
            mock_context.new_page = AsyncMock(return_value=mock_page)

            await browser.start()

            assert browser.browser is not None
            assert browser.context is not None
            assert browser.page is not None

    @pytest.mark.asyncio
    async def test_navigate_requires_page(self, temp_video_dir):
        browser = BrowserSession(video_dir=temp_video_dir)

        with pytest.raises(RuntimeError, match="not initialized"):
            await browser.navigate("https://example.com")

    @pytest.mark.asyncio
    async def test_navigate_with_page(self, temp_video_dir):
        browser = BrowserSession(video_dir=temp_video_dir)
        browser.page = AsyncMock()

        await browser.navigate("https://example.com")

        browser.page.goto.assert_called_once()

    @pytest.mark.asyncio
    async def test_scroll_page_without_page(self, temp_video_dir):
        browser = BrowserSession(video_dir=temp_video_dir)

        await browser.scroll_page()

    @pytest.mark.asyncio
    async def test_scroll_page_with_page(self, temp_video_dir):
        browser = BrowserSession(video_dir=temp_video_dir)
        browser.page = AsyncMock()
        browser.page.evaluate = AsyncMock(side_effect=[1500, None, None, None, None])

        await browser.scroll_page()

        assert browser.page.evaluate.call_count >= 3

    @pytest.mark.asyncio
    async def test_click_element_without_page(self, temp_video_dir):
        browser = BrowserSession(video_dir=temp_video_dir)

        result = await browser.click_element("button")

        assert result is False

    @pytest.mark.asyncio
    async def test_click_element_success(self, temp_video_dir):
        browser = BrowserSession(video_dir=temp_video_dir)
        browser.page = AsyncMock()
        browser.page.click = AsyncMock()
        browser.page.wait_for_load_state = AsyncMock()

        result = await browser.click_element("button")

        assert result is True
        browser.page.click.assert_called_once()

    @pytest.mark.asyncio
    async def test_click_element_failure(self, temp_video_dir):
        browser = BrowserSession(video_dir=temp_video_dir)
        browser.page = AsyncMock()
        browser.page.click = AsyncMock(side_effect=Exception("Click failed"))

        result = await browser.click_element("button")

        assert result is False

    @pytest.mark.asyncio
    async def test_get_current_url_without_page(self, temp_video_dir):
        browser = BrowserSession(video_dir=temp_video_dir)

        url = await browser.get_current_url()

        assert url == ""

    @pytest.mark.asyncio
    async def test_get_current_url_with_page(self, temp_video_dir):
        browser = BrowserSession(video_dir=temp_video_dir)
        browser.page = MagicMock()
        browser.page.url = "https://example.com"

        url = await browser.get_current_url()

        assert url == "https://example.com"

    @pytest.mark.asyncio
    async def test_stop_cleanup_all_resources(self, temp_video_dir):
        browser = BrowserSession(video_dir=temp_video_dir)

        mock_video = MagicMock()
        mock_video.path = AsyncMock(return_value="/tmp/video.webm")

        browser.page = MagicMock()
        browser.page.video = mock_video
        browser.context = AsyncMock()
        browser.browser = AsyncMock()
        browser.playwright = AsyncMock()

        await browser.stop()

        browser.context.close.assert_called_once()
        browser.browser.close.assert_called_once()
        browser.playwright.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_handles_errors_gracefully(self, temp_video_dir):
        browser = BrowserSession(video_dir=temp_video_dir)
        browser.page = MagicMock()
        browser.page.video = None
        browser.context = AsyncMock()
        browser.context.close = AsyncMock(side_effect=Exception("Close failed"))

        await browser.stop()

    @pytest.mark.asyncio
    async def test_get_video_path_none_when_no_video(self, temp_video_dir):
        browser = BrowserSession(video_dir=temp_video_dir)

        path = await browser.get_video_path()

        assert path is None

    @pytest.mark.asyncio
    async def test_get_video_path_returns_path(self, temp_video_dir):
        browser = BrowserSession(video_dir=temp_video_dir)
        browser.video_path = Path("/tmp/video.webm")

        path = await browser.get_video_path()

        assert path == Path("/tmp/video.webm")
