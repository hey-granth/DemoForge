import pytest
from unittest.mock import AsyncMock, MagicMock
from worker.discovery import InteractionDiscovery, InteractionElement


@pytest.fixture
def mock_page():
    return AsyncMock()


class TestInteractionElement:
    def test_fingerprint_generation(self):
        elem = InteractionElement(
            selector="button#submit",
            tag="button",
            text="Submit",
            role="button",
            href="",
            visible=True,
            enabled=True,
        )

        assert elem.fingerprint is not None
        assert len(elem.fingerprint) == 32

    def test_fingerprint_stability(self):
        elem1 = InteractionElement(
            selector="button#submit",
            tag="button",
            text="Submit",
            role="button",
            href="",
            visible=True,
            enabled=True,
        )

        elem2 = InteractionElement(
            selector="button.different-selector",
            tag="button",
            text="Submit",
            role="button",
            href="",
            visible=True,
            enabled=True,
        )

        assert elem1.fingerprint == elem2.fingerprint

    def test_to_dict(self):
        elem = InteractionElement(
            selector="a#link",
            tag="a",
            text="Click here",
            role="link",
            href="/page",
            visible=True,
            enabled=True,
        )

        data = elem.to_dict()

        assert data["selector"] == "a#link"
        assert data["tag"] == "a"
        assert data["text"] == "Click here"
        assert data["fingerprint"] is not None


class TestInteractionDiscovery:
    @pytest.mark.asyncio
    async def test_scan_elements_empty_page(self, mock_page):
        mock_page.query_selector_all = AsyncMock(return_value=[])

        discovery = InteractionDiscovery(mock_page)
        elements = await discovery.scan_elements()

        assert len(elements) == 0

    @pytest.mark.asyncio
    async def test_scan_buttons(self, mock_page):
        mock_button = AsyncMock()
        mock_button.is_visible = AsyncMock(return_value=True)
        mock_button.is_enabled = AsyncMock(return_value=True)
        mock_button.inner_text = AsyncMock(return_value="Click me")
        mock_button.get_attribute = AsyncMock(
            side_effect=lambda x: None if x == "id" else "button"
        )

        mock_page.query_selector_all = AsyncMock(
            side_effect=lambda sel: [mock_button] if "button" in sel else []
        )

        discovery = InteractionDiscovery(mock_page)
        elements = await discovery.scan_elements()

        assert len(elements) >= 1
        assert any(e.tag == "button" for e in elements)

    @pytest.mark.asyncio
    async def test_scan_filters_invisible_elements(self, mock_page):
        mock_button = AsyncMock()
        mock_button.is_visible = AsyncMock(return_value=False)
        mock_button.is_enabled = AsyncMock(return_value=True)

        mock_page.query_selector_all = AsyncMock(
            side_effect=lambda sel: [mock_button] if "button" in sel else []
        )

        discovery = InteractionDiscovery(mock_page)
        elements = await discovery.scan_elements()

        assert len(elements) == 0

    @pytest.mark.asyncio
    async def test_scan_filters_disabled_buttons(self, mock_page):
        mock_button = AsyncMock()
        mock_button.is_visible = AsyncMock(return_value=True)
        mock_button.is_enabled = AsyncMock(return_value=False)

        mock_page.query_selector_all = AsyncMock(
            side_effect=lambda sel: [mock_button] if "button" in sel else []
        )

        discovery = InteractionDiscovery(mock_page)
        elements = await discovery.scan_elements()

        assert len(elements) == 0

    @pytest.mark.asyncio
    async def test_scan_filters_javascript_links(self, mock_page):
        mock_link = AsyncMock()
        mock_link.is_visible = AsyncMock(return_value=True)
        mock_link.get_attribute = AsyncMock(
            side_effect=lambda x: "javascript:void(0)" if x == "href" else "link"
        )
        mock_link.inner_text = AsyncMock(return_value="Link")

        mock_page.query_selector_all = AsyncMock(
            side_effect=lambda sel: [mock_link] if "a[href]" in sel else []
        )

        discovery = InteractionDiscovery(mock_page)
        elements = await discovery.scan_elements()

        assert len(elements) == 0

    @pytest.mark.asyncio
    async def test_prefers_id_selectors(self, mock_page):
        mock_button = AsyncMock()
        mock_button.is_visible = AsyncMock(return_value=True)
        mock_button.is_enabled = AsyncMock(return_value=True)
        mock_button.inner_text = AsyncMock(return_value="Submit")
        mock_button.get_attribute = AsyncMock(
            side_effect=lambda x: "submit-btn" if x == "id" else "button"
        )

        mock_page.query_selector_all = AsyncMock(
            side_effect=lambda sel: [mock_button] if sel == "button" else []
        )

        discovery = InteractionDiscovery(mock_page)
        elements = await discovery.scan_elements()

        assert len(elements) == 1
        assert "submit-btn" in elements[0].selector

    def test_mark_visited(self, mock_page):
        discovery = InteractionDiscovery(mock_page)

        discovery.mark_visited("fingerprint123")

        assert discovery.is_visited("fingerprint123")
        assert not discovery.is_visited("fingerprint456")

    def test_filter_unvisited(self, mock_page):
        discovery = InteractionDiscovery(mock_page)

        elem1 = InteractionElement("btn1", "button", "Click", "button", "", True, True)
        elem2 = InteractionElement("btn2", "button", "Submit", "button", "", True, True)

        discovery.mark_visited(elem1.fingerprint)

        filtered = discovery.filter_unvisited([elem1, elem2])

        assert len(filtered) == 1
        assert filtered[0].fingerprint == elem2.fingerprint

    @pytest.mark.asyncio
    async def test_deduplication(self, mock_page):
        mock_button1 = AsyncMock()
        mock_button1.is_visible = AsyncMock(return_value=True)
        mock_button1.is_enabled = AsyncMock(return_value=True)
        mock_button1.inner_text = AsyncMock(return_value="Click")
        mock_button1.get_attribute = AsyncMock(
            side_effect=lambda x: None if x == "id" else "button"
        )

        mock_button2 = AsyncMock()
        mock_button2.is_visible = AsyncMock(return_value=True)
        mock_button2.is_enabled = AsyncMock(return_value=True)
        mock_button2.inner_text = AsyncMock(return_value="Click")
        mock_button2.get_attribute = AsyncMock(
            side_effect=lambda x: None if x == "id" else "button"
        )

        mock_page.query_selector_all = AsyncMock(
            side_effect=lambda sel: (
                [mock_button1, mock_button2] if sel == "button" else []
            )
        )

        discovery = InteractionDiscovery(mock_page)
        elements = await discovery.scan_elements()

        assert len(elements) == 1
