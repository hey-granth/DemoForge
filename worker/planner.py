import os
import json
from typing import List, Dict, Optional
import google.generativeai as genai


BLACKLIST_KEYWORDS = [
    "delete", "remove", "unsubscribe", "deactivate",
    "pay", "checkout", "purchase", "buy", "payment",
    "cancel", "close account", "sign out", "log out",
    "logout", "destroy", "erase", "clear"
]


class ActionPlan:
    def __init__(self, selector: str, action: str, priority: int, reason: str):
        self.selector = selector
        self.action = action
        self.priority = priority
        self.reason = reason


class InteractionPlanner:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
        else:
            self.model = None
    
    async def rank_interactions(
        self,
        elements: List[Dict],
        current_url: str,
        max_actions: int = 5
    ) -> List[ActionPlan]:
        
        filtered = self._apply_blacklist(elements)
        
        if not filtered:
            return []
        
        if not self.model:
            return self._fallback_ranking(filtered, max_actions)
        
        try:
            ranked = await self._llm_ranking(filtered, current_url, max_actions)
            return ranked
        except Exception as e:
            return self._fallback_ranking(filtered, max_actions)
    
    def _apply_blacklist(self, elements: List[Dict]) -> List[Dict]:
        filtered = []
        
        for elem in elements:
            text = elem.get("text", "").lower()
            
            is_blacklisted = any(
                keyword in text
                for keyword in BLACKLIST_KEYWORDS
            )
            
            if not is_blacklisted:
                filtered.append(elem)
        
        return filtered
    
    async def _llm_ranking(
        self,
        elements: List[Dict],
        current_url: str,
        max_actions: int
    ) -> List[ActionPlan]:
        
        elements_json = json.dumps(elements[:20], indent=2)
        
        prompt = f"""Rank UI interactions for demo video generation.

URL: {current_url}

Elements:
{elements_json}

Rank top {max_actions} interactions that showcase website features.
Prioritize: navigation, features, content.

Return only JSON array:
[{{"selector":"...","action":"click","priority":1,"reason":"..."}}]"""

        response = await self.model.generate_content_async(
            prompt,
            generation_config=genai.GenerationConfig(
                temperature=0.2,
                max_output_tokens=800
            )
        )
        
        content = response.text.strip()
        
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        
        content = content.strip()
        
        ranked_data = json.loads(content)
        
        plans = []
        for item in ranked_data[:max_actions]:
            plan = ActionPlan(
                selector=item["selector"],
                action=item.get("action", "click"),
                priority=item.get("priority", 0),
                reason=item.get("reason", "")
            )
            plans.append(plan)
        
        return plans
    
    def _fallback_ranking(self, elements: List[Dict], max_actions: int) -> List[ActionPlan]:
        priority_keywords = [
            "features", "product", "demo", "about",
            "services", "pricing", "learn", "explore",
            "gallery", "portfolio", "blog", "docs"
        ]
        
        scored = []
        for elem in elements:
            text = elem.get("text", "").lower()
            score = 0
            
            for keyword in priority_keywords:
                if keyword in text:
                    score += 10
            
            if elem.get("tag") == "button":
                score += 5
            
            if len(text) > 0:
                score += 1
            
            scored.append((score, elem))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        
        plans = []
        for idx, (score, elem) in enumerate(scored[:max_actions]):
            plan = ActionPlan(
                selector=elem["selector"],
                action="click",
                priority=idx + 1,
                reason=f"Fallback ranking: score {score}"
            )
            plans.append(plan)
        
        return plans
