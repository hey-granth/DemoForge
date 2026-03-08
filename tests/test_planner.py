import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from worker.planner import InteractionPlanner, ActionPlan


class TestBlacklistEnforcement:
    @pytest.mark.asyncio
    async def test_filters_delete_actions(self):
        planner = InteractionPlanner()

        elements = [
            {"selector": "btn1", "text": "Delete Account", "tag": "button"},
            {"selector": "btn2", "text": "Save", "tag": "button"},
        ]

        result = await planner.rank_interactions(elements, "https://example.com")

        selectors = [p.selector for p in result]
        assert "btn1" not in selectors

    @pytest.mark.asyncio
    async def test_filters_payment_actions(self):
        planner = InteractionPlanner()

        elements = [
            {"selector": "btn1", "text": "Checkout", "tag": "button"},
            {"selector": "btn2", "text": "Pay Now", "tag": "button"},
            {"selector": "btn3", "text": "Learn More", "tag": "button"},
        ]

        result = await planner.rank_interactions(elements, "https://example.com")

        selectors = [p.selector for p in result]
        assert "btn1" not in selectors
        assert "btn2" not in selectors

    @pytest.mark.asyncio
    async def test_filters_unsubscribe_actions(self):
        planner = InteractionPlanner()

        elements = [
            {"selector": "link1", "text": "Unsubscribe", "tag": "a"},
            {"selector": "link2", "text": "Subscribe", "tag": "a"},
        ]

        result = await planner.rank_interactions(elements, "https://example.com")

        selectors = [p.selector for p in result]
        assert "link1" not in selectors

    @pytest.mark.asyncio
    async def test_case_insensitive_blacklist(self):
        planner = InteractionPlanner()

        elements = [
            {"selector": "btn1", "text": "DELETE ACCOUNT", "tag": "button"},
            {"selector": "btn2", "text": "Continue", "tag": "button"},
        ]

        result = await planner.rank_interactions(elements, "https://example.com")

        selectors = [p.selector for p in result]
        assert "btn1" not in selectors


class TestInteractionPlanner:
    @pytest.mark.asyncio
    async def test_fallback_ranking_no_api_key(self):
        planner = InteractionPlanner(api_key=None)

        elements = [
            {"selector": "btn1", "text": "Features", "tag": "button"},
            {"selector": "btn2", "text": "About", "tag": "button"},
        ]

        result = await planner.rank_interactions(elements, "https://example.com")

        assert len(result) > 0
        assert all(isinstance(p, ActionPlan) for p in result)

    @pytest.mark.asyncio
    async def test_fallback_ranking_prioritizes_keywords(self):
        planner = InteractionPlanner(api_key=None)

        elements = [
            {"selector": "btn1", "text": "Random", "tag": "button"},
            {"selector": "btn2", "text": "Features", "tag": "button"},
            {"selector": "btn3", "text": "Pricing", "tag": "button"},
        ]

        result = await planner.rank_interactions(elements, "https://example.com")

        top_selectors = [p.selector for p in result[:2]]
        assert "btn2" in top_selectors or "btn3" in top_selectors

    @pytest.mark.asyncio
    async def test_respects_max_actions_limit(self):
        planner = InteractionPlanner(api_key=None)

        elements = [
            {"selector": f"btn{i}", "text": f"Button {i}", "tag": "button"}
            for i in range(20)
        ]

        result = await planner.rank_interactions(
            elements, "https://example.com", max_actions=3
        )

        assert len(result) <= 3

    @pytest.mark.asyncio
    async def test_handles_empty_elements(self):
        planner = InteractionPlanner(api_key=None)

        result = await planner.rank_interactions([], "https://example.com")

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_handles_all_blacklisted(self):
        planner = InteractionPlanner(api_key=None)

        elements = [
            {"selector": "btn1", "text": "Delete", "tag": "button"},
            {"selector": "btn2", "text": "Remove", "tag": "button"},
        ]

        result = await planner.rank_interactions(elements, "https://example.com")

        assert len(result) == 0

    @pytest.mark.asyncio
    @patch("worker.planner.genai")
    async def test_gemini_api_failure_fallback(self, mock_genai):
        mock_model = MagicMock()
        mock_model.generate_content_async = AsyncMock(
            side_effect=Exception("API Error")
        )

        planner = InteractionPlanner(api_key="test-key")
        planner.model = mock_model

        elements = [{"selector": "btn1", "text": "Click", "tag": "button"}]

        result = await planner.rank_interactions(elements, "https://example.com")

        assert len(result) > 0

    @pytest.mark.asyncio
    @patch("worker.planner.genai")
    async def test_gemini_response_parsing(self, mock_genai):
        mock_response = MagicMock()
        mock_response.text = (
            '[{"selector":"btn1","action":"click","priority":1,"reason":"test"}]'
        )

        mock_model = MagicMock()
        mock_model.generate_content_async = AsyncMock(return_value=mock_response)

        planner = InteractionPlanner(api_key="test-key")
        planner.model = mock_model

        elements = [{"selector": "btn1", "text": "Click", "tag": "button"}]

        result = await planner.rank_interactions(elements, "https://example.com")

        assert len(result) == 1
        assert result[0].selector == "btn1"

    @pytest.mark.asyncio
    @patch("worker.planner.genai")
    async def test_gemini_handles_markdown_wrapped_json(self, mock_genai):
        mock_response = MagicMock()
        mock_response.text = '```json\n[{"selector":"btn1","action":"click","priority":1,"reason":"test"}]\n```'

        mock_model = MagicMock()
        mock_model.generate_content_async = AsyncMock(return_value=mock_response)

        planner = InteractionPlanner(api_key="test-key")
        planner.model = mock_model

        elements = [{"selector": "btn1", "text": "Click", "tag": "button"}]

        result = await planner.rank_interactions(elements, "https://example.com")

        assert len(result) == 1


class TestActionPlan:
    def test_action_plan_creation(self):
        plan = ActionPlan(
            selector="button#submit", action="click", priority=1, reason="Primary CTA"
        )

        assert plan.selector == "button#submit"
        assert plan.action == "click"
        assert plan.priority == 1
        assert plan.reason == "Primary CTA"
