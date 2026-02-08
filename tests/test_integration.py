import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from worker.executor import ExecutionController, ExecutionState
from worker.discovery import InteractionElement
from worker.planner import ActionPlan


@pytest.fixture
def mock_components():
    browser = AsyncMock()
    browser.navigate = AsyncMock()
    browser.get_current_url = AsyncMock(return_value="https://example.com")
    browser.scroll_page = AsyncMock()
    browser.click_element = AsyncMock(return_value=True)

    discovery = MagicMock()
    discovery.scan_elements = AsyncMock(return_value=[])
    discovery.filter_unvisited = MagicMock(return_value=[])
    discovery.mark_visited = MagicMock()

    planner = AsyncMock()
    planner.rank_interactions = AsyncMock(return_value=[])

    return browser, discovery, planner


class TestIntegration:
    @pytest.mark.asyncio
    async def test_full_execution_flow(self, mock_components):
        browser, discovery, planner = mock_components

        elem1 = InteractionElement(
            "btn1", "button", "Features", "button", "", True, True
        )
        elem2 = InteractionElement("btn2", "button", "About", "button", "", True, True)

        discovery.scan_elements = AsyncMock(side_effect=[[elem1, elem2], [elem2], []])
        discovery.filter_unvisited = MagicMock(
            side_effect=[[elem1, elem2], [elem2], []]
        )

        plan1 = ActionPlan("btn1", "click", 1, "test")
        plan2 = ActionPlan("btn2", "click", 1, "test")
        planner.rank_interactions = AsyncMock(side_effect=[[plan1], [plan2], []])

        executor = ExecutionController(max_clicks=5, max_depth=3, max_runtime=60)

        await executor.execute_demo("https://example.com", browser, discovery, planner)

        assert executor.state == ExecutionState.COMPLETE
        assert executor.click_count == 2
        assert discovery.mark_visited.call_count == 2

    @pytest.mark.asyncio
    async def test_blacklist_prevents_dangerous_actions(self, mock_components):
        browser, discovery, planner = mock_components

        safe_elem = InteractionElement(
            "btn1", "button", "Learn More", "button", "", True, True
        )
        danger_elem = InteractionElement(
            "btn2", "button", "Delete Account", "button", "", True, True
        )

        discovery.scan_elements = AsyncMock(return_value=[safe_elem, danger_elem])
        discovery.filter_unvisited = MagicMock(return_value=[safe_elem, danger_elem])

        from worker.planner import InteractionPlanner

        real_planner = InteractionPlanner(api_key=None)

        elements = [safe_elem.to_dict(), danger_elem.to_dict()]
        plans = await real_planner.rank_interactions(elements, "https://example.com")

        plan_selectors = [p.selector for p in plans]
        assert "btn2" not in plan_selectors

    @pytest.mark.asyncio
    async def test_loop_detection_prevents_infinite_execution(self, mock_components):
        browser, discovery, planner = mock_components

        elem = InteractionElement("btn", "button", "Toggle", "button", "", True, True)

        discovery.scan_elements = AsyncMock(return_value=[elem])
        discovery.filter_unvisited = MagicMock(return_value=[elem])

        plan = ActionPlan("btn", "click", 1, "test")
        planner.rank_interactions = AsyncMock(return_value=[plan])

        executor = ExecutionController(max_clicks=100, max_depth=10, max_runtime=60)

        await executor.execute_demo("https://example.com", browser, discovery, planner)

        assert executor.click_count < 5

    @pytest.mark.asyncio
    async def test_network_failure_handling(self, mock_components):
        browser, discovery, planner = mock_components

        browser.navigate = AsyncMock(side_effect=Exception("Network error"))

        executor = ExecutionController()

        with pytest.raises(Exception):
            await executor.execute_demo(
                "https://example.com", browser, discovery, planner
            )

        assert executor.state == ExecutionState.FAILED

    @pytest.mark.asyncio
    async def test_browser_crash_recovery(self, mock_components):
        browser, discovery, planner = mock_components

        elem = InteractionElement("btn", "button", "Click", "button", "", True, True)
        discovery.scan_elements = AsyncMock(return_value=[elem])
        discovery.filter_unvisited = MagicMock(return_value=[elem])

        plan = ActionPlan("btn", "click", 1, "test")
        planner.rank_interactions = AsyncMock(return_value=[plan])

        browser.click_element = AsyncMock(side_effect=Exception("Browser crashed"))

        executor = ExecutionController()

        with pytest.raises(Exception):
            await executor.execute_demo(
                "https://example.com", browser, discovery, planner
            )

    @pytest.mark.asyncio
    async def test_planner_failure_uses_fallback(self, mock_components):
        browser, discovery, planner = mock_components

        elem = InteractionElement("btn", "button", "Click", "button", "", True, True)
        discovery.scan_elements = AsyncMock(return_value=[elem])
        discovery.filter_unvisited = MagicMock(return_value=[elem])

        planner.rank_interactions = AsyncMock(side_effect=Exception("LLM API failed"))

        executor = ExecutionController()

        with pytest.raises(Exception):
            await executor.execute_demo(
                "https://example.com", browser, discovery, planner
            )

    @pytest.mark.asyncio
    async def test_concurrent_job_execution(self):
        async def run_job(job_id):
            browser = AsyncMock()
            browser.navigate = AsyncMock()
            browser.get_current_url = AsyncMock(
                return_value=f"https://example{job_id}.com"
            )
            browser.scroll_page = AsyncMock()
            browser.click_element = AsyncMock(return_value=True)

            discovery = MagicMock()
            discovery.scan_elements = AsyncMock(return_value=[])
            discovery.filter_unvisited = MagicMock(return_value=[])

            planner = AsyncMock()
            planner.rank_interactions = AsyncMock(return_value=[])

            executor = ExecutionController(max_runtime=5)
            await executor.execute_demo(
                f"https://example{job_id}.com", browser, discovery, planner
            )

            return executor.state

        tasks = [run_job(i) for i in range(3)]
        results = await asyncio.gather(*tasks)

        assert all(state == ExecutionState.COMPLETE for state in results)
