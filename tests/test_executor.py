import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from worker.executor import ExecutionController, ExecutionState, SafetyViolation
from worker.discovery import InteractionElement


@pytest.fixture
def mock_browser():
    browser = AsyncMock()
    browser.navigate = AsyncMock()
    browser.get_current_url = AsyncMock(return_value="https://example.com")
    browser.scroll_page = AsyncMock()
    browser.click_element = AsyncMock(return_value=True)
    return browser


@pytest.fixture
def mock_discovery():
    discovery = MagicMock()
    discovery.scan_elements = AsyncMock(return_value=[])
    discovery.filter_unvisited = MagicMock(return_value=[])
    discovery.mark_visited = MagicMock()
    return discovery


@pytest.fixture
def mock_planner():
    planner = AsyncMock()
    planner.rank_interactions = AsyncMock(return_value=[])
    return planner


class TestExecutionController:
    
    @pytest.mark.asyncio
    async def test_enforces_max_clicks(self, mock_browser, mock_discovery, mock_planner):
        executor = ExecutionController(max_clicks=3, max_depth=10, max_runtime=300)
        
        elem = InteractionElement("btn", "button", "Click", "button", "", True, True)
        mock_discovery.scan_elements = AsyncMock(return_value=[elem])
        mock_discovery.filter_unvisited = MagicMock(return_value=[elem])
        
        from worker.planner import ActionPlan
        plan = ActionPlan("btn", "click", 1, "test")
        mock_planner.rank_interactions = AsyncMock(return_value=[plan])
        
        mock_browser.click_element = AsyncMock(return_value=True)
        
        await executor.execute_demo("https://example.com", mock_browser, mock_discovery, mock_planner)
        
        assert executor.click_count <= 3
    
    @pytest.mark.asyncio
    async def test_enforces_max_depth(self, mock_browser, mock_discovery, mock_planner):
        executor = ExecutionController(max_clicks=100, max_depth=2, max_runtime=300)
        
        elem = InteractionElement("link", "a", "Page", "link", "/page", True, True)
        mock_discovery.scan_elements = AsyncMock(return_value=[elem])
        mock_discovery.filter_unvisited = MagicMock(return_value=[elem])
        
        from worker.planner import ActionPlan
        plan = ActionPlan("link", "click", 1, "test")
        mock_planner.rank_interactions = AsyncMock(return_value=[plan])
        
        mock_browser.get_current_url = AsyncMock(side_effect=[
            "https://example.com",
            "https://example.com/page1",
            "https://example.com/page2",
            "https://example.com/page3"
        ])
        
        await executor.execute_demo("https://example.com", mock_browser, mock_discovery, mock_planner)
        
        assert executor.current_depth <= 2
    
    @pytest.mark.asyncio
    async def test_enforces_timeout(self, mock_browser, mock_discovery, mock_planner):
        executor = ExecutionController(max_clicks=100, max_depth=10, max_runtime=1)
        
        elem = InteractionElement("btn", "button", "Click", "button", "", True, True)
        mock_discovery.scan_elements = AsyncMock(return_value=[elem])
        mock_discovery.filter_unvisited = MagicMock(return_value=[elem])
        
        from worker.planner import ActionPlan
        plan = ActionPlan("btn", "click", 1, "test")
        mock_planner.rank_interactions = AsyncMock(return_value=[plan])
        
        async def slow_click(*args, **kwargs):
            await asyncio.sleep(2)
            return True
        
        mock_browser.click_element = slow_click
        
        with pytest.raises(SafetyViolation, match="Runtime exceeded"):
            await executor.execute_demo("https://example.com", mock_browser, mock_discovery, mock_planner)
    
    @pytest.mark.asyncio
    async def test_detects_loop(self, mock_browser, mock_discovery, mock_planner):
        executor = ExecutionController(max_clicks=100, max_depth=10, max_runtime=300)
        
        elem = InteractionElement("btn", "button", "Click", "button", "", True, True)
        mock_discovery.scan_elements = AsyncMock(return_value=[elem])
        mock_discovery.filter_unvisited = MagicMock(return_value=[elem])
        
        from worker.planner import ActionPlan
        plan = ActionPlan("btn", "click", 1, "test")
        mock_planner.rank_interactions = AsyncMock(return_value=[plan])
        
        await executor.execute_demo("https://example.com", mock_browser, mock_discovery, mock_planner)
        
        assert executor.state == ExecutionState.COMPLETE
    
    @pytest.mark.asyncio
    async def test_aborts_on_domain_change(self, mock_browser, mock_discovery, mock_planner):
        executor = ExecutionController(max_clicks=100, max_depth=10, max_runtime=300)
        
        elem = InteractionElement("link", "a", "External", "link", "https://other.com", True, True)
        mock_discovery.scan_elements = AsyncMock(return_value=[elem])
        mock_discovery.filter_unvisited = MagicMock(return_value=[elem])
        
        from worker.planner import ActionPlan
        plan = ActionPlan("link", "click", 1, "test")
        mock_planner.rank_interactions = AsyncMock(return_value=[plan])
        
        mock_browser.get_current_url = AsyncMock(side_effect=[
            "https://example.com",
            "https://other.com"
        ])
        
        await executor.execute_demo("https://example.com", mock_browser, mock_discovery, mock_planner)
        
        assert executor.state == ExecutionState.COMPLETE
        assert executor.click_count <= 1
    
    @pytest.mark.asyncio
    async def test_aborts_on_auth_page(self, mock_browser, mock_discovery, mock_planner):
        executor = ExecutionController(max_clicks=100, max_depth=10, max_runtime=300)
        
        elem = InteractionElement("link", "a", "Login", "link", "/login", True, True)
        mock_discovery.scan_elements = AsyncMock(return_value=[elem])
        mock_discovery.filter_unvisited = MagicMock(return_value=[elem])
        
        from worker.planner import ActionPlan
        plan = ActionPlan("link", "click", 1, "test")
        mock_planner.rank_interactions = AsyncMock(return_value=[plan])
        
        mock_browser.get_current_url = AsyncMock(side_effect=[
            "https://example.com",
            "https://example.com/login"
        ])
        
        await executor.execute_demo("https://example.com", mock_browser, mock_discovery, mock_planner)
        
        assert executor.state == ExecutionState.COMPLETE
    
    @pytest.mark.asyncio
    async def test_stops_when_no_unvisited_elements(self, mock_browser, mock_discovery, mock_planner):
        executor = ExecutionController(max_clicks=100, max_depth=10, max_runtime=300)
        
        mock_discovery.scan_elements = AsyncMock(return_value=[])
        mock_discovery.filter_unvisited = MagicMock(return_value=[])
        
        await executor.execute_demo("https://example.com", mock_browser, mock_discovery, mock_planner)
        
        assert executor.state == ExecutionState.COMPLETE
        assert executor.click_count == 0
    
    @pytest.mark.asyncio
    async def test_tracks_visited_urls(self, mock_browser, mock_discovery, mock_planner):
        executor = ExecutionController(max_clicks=5, max_depth=3, max_runtime=300)
        
        elem = InteractionElement("link", "a", "Next", "link", "/next", True, True)
        mock_discovery.scan_elements = AsyncMock(return_value=[elem])
        mock_discovery.filter_unvisited = MagicMock(return_value=[elem])
        
        from worker.planner import ActionPlan
        plan = ActionPlan("link", "click", 1, "test")
        mock_planner.rank_interactions = AsyncMock(return_value=[plan])
        
        urls = ["https://example.com", "https://example.com/page1", "https://example.com/page2"]
        mock_browser.get_current_url = AsyncMock(side_effect=urls + [urls[-1]] * 10)
        
        await executor.execute_demo("https://example.com", mock_browser, mock_discovery, mock_planner)
        
        assert len(executor.visited_urls) >= 2
    
    def test_get_metrics(self):
        executor = ExecutionController()
        
        metrics = executor.get_metrics()
        
        assert "state" in metrics
        assert "clicks" in metrics
        assert "depth" in metrics
        assert "runtime" in metrics
