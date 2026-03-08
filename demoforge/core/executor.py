import asyncio
import hashlib
from typing import Set, List
from urllib.parse import urlparse
from demoforge.core.browser import BrowserSession
from demoforge.core.discovery import InteractionDiscovery, InteractionElement
from demoforge.core.planner import InteractionPlanner


class ExecutionState:
    INITIAL = "initial"
    NAVIGATING = "navigating"
    DISCOVERING = "discovering"
    PLANNING = "planning"
    EXECUTING = "executing"
    COMPLETE = "complete"
    FAILED = "failed"


class SafetyViolation(Exception):
    pass


class ExecutionController:
    def __init__(
        self,
        max_clicks: int = 10,
        max_depth: int = 3,
        max_runtime: int = 300,
        interaction_delay: float = 2.0,
    ):
        self.max_clicks = max_clicks
        self.max_depth = max_depth
        self.max_runtime = max_runtime
        self.interaction_delay = interaction_delay

        self.state = ExecutionState.INITIAL
        self.click_count = 0
        self.current_depth = 0
        self.visited_urls: Set[str] = set()
        self.visited_states: Set[str] = set()
        self.start_time = None

    async def execute_demo(
        self,
        url: str,
        browser: BrowserSession,
        discovery: InteractionDiscovery,
        planner: InteractionPlanner,
    ):
        self.start_time = asyncio.get_event_loop().time()
        base_domain = self._extract_domain(url)

        try:
            self.state = ExecutionState.NAVIGATING
            await browser.navigate(url)
            self._check_runtime()

            initial_url = await browser.get_current_url()
            self.visited_urls.add(initial_url)

            await browser.scroll_page()
            await asyncio.sleep(self.interaction_delay)

            while (
                self.click_count < self.max_clicks
                and self.current_depth < self.max_depth
            ):
                self._check_runtime()

                current_url = await browser.get_current_url()
                current_domain = self._extract_domain(current_url)

                if current_domain != base_domain:
                    break

                if self._is_auth_page(current_url):
                    break

                self.state = ExecutionState.DISCOVERING
                elements = await discovery.scan_elements()
                unvisited = discovery.filter_unvisited(elements)

                if not unvisited:
                    break

                state_hash = self._compute_state_hash(current_url, unvisited)
                if state_hash in self.visited_states:
                    break
                self.visited_states.add(state_hash)

                self.state = ExecutionState.PLANNING
                element_dicts = [e.to_dict() for e in unvisited]
                plans = await planner.rank_interactions(
                    element_dicts, current_url, max_actions=3
                )

                if not plans:
                    break

                self.state = ExecutionState.EXECUTING
                executed = False

                for plan in plans:
                    matching_elements = [
                        e for e in unvisited if e.selector == plan.selector
                    ]

                    if not matching_elements:
                        continue

                    element = matching_elements[0]

                    success = await browser.click_element(element.selector)

                    if success:
                        self.click_count += 1
                        discovery.mark_visited(element.fingerprint)

                        await asyncio.sleep(self.interaction_delay)

                        new_url = await browser.get_current_url()
                        if new_url != current_url and new_url not in self.visited_urls:
                            self.visited_urls.add(new_url)
                            self.current_depth += 1

                        executed = True
                        break

                if not executed:
                    break

            self.state = ExecutionState.COMPLETE

        except SafetyViolation:
            self.state = ExecutionState.FAILED
            raise
        except Exception:
            self.state = ExecutionState.FAILED
            raise

    def _extract_domain(self, url: str) -> str:
        parsed = urlparse(url)
        return parsed.netloc

    def _is_auth_page(self, url: str) -> bool:
        auth_indicators = [
            "/login",
            "/signin",
            "/sign-in",
            "/register",
            "/signup",
            "/sign-up",
            "/auth",
            "/authentication",
        ]

        url_lower = url.lower()
        return any(indicator in url_lower for indicator in auth_indicators)

    def _check_runtime(self):
        if self.start_time is None:
            return

        elapsed = asyncio.get_event_loop().time() - self.start_time

        if elapsed > self.max_runtime:
            raise SafetyViolation(f"Runtime exceeded {self.max_runtime}s")

    def _compute_state_hash(self, url: str, elements: List[InteractionElement]) -> str:
        fingerprints = sorted([e.fingerprint for e in elements[:10]])
        state_repr = f"{url}:{'|'.join(fingerprints)}"
        return hashlib.md5(state_repr.encode()).hexdigest()

    def get_metrics(self) -> dict:
        elapsed = 0
        if self.start_time:
            elapsed = asyncio.get_event_loop().time() - self.start_time

        return {
            "state": self.state,
            "clicks": self.click_count,
            "depth": self.current_depth,
            "visited_urls": len(self.visited_urls),
            "runtime": round(elapsed, 2),
        }
