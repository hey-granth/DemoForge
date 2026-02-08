import hashlib
from typing import List, Dict, Set
from playwright.async_api import Page, ElementHandle


class InteractionElement:
    def __init__(
        self,
        selector: str,
        tag: str,
        text: str,
        role: str,
        href: str,
        visible: bool,
        enabled: bool,
    ):
        self.selector = selector
        self.tag = tag
        self.text = text
        self.role = role
        self.href = href
        self.visible = visible
        self.enabled = enabled
        self.fingerprint = self._generate_fingerprint()

    def _generate_fingerprint(self) -> str:
        components = f"{self.tag}:{self.text}:{self.role}:{self.href}"
        return hashlib.md5(components.encode()).hexdigest()

    def to_dict(self) -> dict:
        return {
            "selector": self.selector,
            "tag": self.tag,
            "text": self.text,
            "role": self.role,
            "href": self.href,
            "fingerprint": self.fingerprint,
        }


class InteractionDiscovery:
    def __init__(self, page: Page):
        self.page = page
        self.visited_fingerprints: Set[str] = set()

    async def scan_elements(self) -> List[InteractionElement]:
        elements = []

        button_elements = await self._scan_buttons()
        link_elements = await self._scan_links()
        role_elements = await self._scan_role_buttons()

        all_elements = button_elements + link_elements + role_elements

        filtered = []
        seen_fingerprints = set()

        for elem in all_elements:
            if elem.fingerprint not in seen_fingerprints:
                seen_fingerprints.add(elem.fingerprint)
                filtered.append(elem)

        return filtered

    async def _scan_buttons(self) -> List[InteractionElement]:
        elements = []

        buttons = await self.page.query_selector_all("button")

        for idx, button in enumerate(buttons):
            try:
                visible = await button.is_visible()
                enabled = await button.is_enabled()

                if not visible or not enabled:
                    continue

                text = await button.inner_text()
                text = text.strip()[:100]

                role = await button.get_attribute("role") or "button"

                btn_id = await button.get_attribute("id")
                if btn_id:
                    selector = f"button#{btn_id}"
                else:
                    selector = f"button:nth-of-type({idx + 1})"

                elem = InteractionElement(
                    selector=selector,
                    tag="button",
                    text=text,
                    role=role,
                    href="",
                    visible=visible,
                    enabled=enabled,
                )

                elements.append(elem)
            except:
                continue

        return elements

    async def _scan_links(self) -> List[InteractionElement]:
        elements = []

        links = await self.page.query_selector_all("a[href]")

        for idx, link in enumerate(links):
            try:
                visible = await link.is_visible()

                if not visible:
                    continue

                href = await link.get_attribute("href") or ""

                if href.startswith("javascript:") or href == "#":
                    continue

                text = await link.inner_text()
                text = text.strip()[:100]

                role = await link.get_attribute("role") or "link"

                link_id = await link.get_attribute("id")
                if link_id:
                    selector = f"a#{link_id}"
                else:
                    selector = f"a[href]:nth-of-type({idx + 1})"

                elem = InteractionElement(
                    selector=selector,
                    tag="a",
                    text=text,
                    role=role,
                    href=href,
                    visible=visible,
                    enabled=True,
                )

                elements.append(elem)
            except:
                continue

        return elements

    async def _scan_role_buttons(self) -> List[InteractionElement]:
        elements = []

        role_buttons = await self.page.query_selector_all("[role=button]")

        for idx, button in enumerate(role_buttons):
            try:
                tag_name = await button.evaluate("el => el.tagName.toLowerCase()")

                if tag_name in ["button", "a"]:
                    continue

                visible = await button.is_visible()

                if not visible:
                    continue

                text = await button.inner_text()
                text = text.strip()[:100]

                selector = f"[role=button]:nth-of-type({idx + 1})"

                elem = InteractionElement(
                    selector=selector,
                    tag=tag_name,
                    text=text,
                    role="button",
                    href="",
                    visible=visible,
                    enabled=True,
                )

                elements.append(elem)
            except:
                continue

        return elements

    def mark_visited(self, fingerprint: str):
        self.visited_fingerprints.add(fingerprint)

    def is_visited(self, fingerprint: str) -> bool:
        return fingerprint in self.visited_fingerprints

    def filter_unvisited(
        self, elements: List[InteractionElement]
    ) -> List[InteractionElement]:
        return [e for e in elements if not self.is_visited(e.fingerprint)]
