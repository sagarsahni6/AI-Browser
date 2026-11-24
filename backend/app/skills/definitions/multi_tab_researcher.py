from typing import Dict, Any, List
from backend.app.skills.base import BaseSkill, SkillManifest, SkillTool
from backend.app.browser.bridge import bridge
from backend.app.ai.router import ModelRouter


class MultiTabResearcherSkill(BaseSkill):
    def __init__(self):
        self.manifest = SkillManifest(
            id="multi_tab_researcher",
            name="Multi-Tab Swarm Deep Researcher",
            description="Parallel tab coordination, cross-tab comparative synthesis, and cited deep web research memos.",
            category="research",
            icon="BookOpen",
            enabled=True,
            triggers=[
                "research", "compare tabs", "multi-tab", "deep research",
                "cross examine", "synthesize tabs", "swarm", "compare products"
            ],
            tools=[
                SkillTool(
                    name="cluster_open_tabs",
                    description="Inspect and group all currently open tabs by topic, domain, and relevance to the user's research goal.",
                    parameters={
                        "type": "object",
                        "properties": {}
                    },
                    risk_tier="green"
                ),
                SkillTool(
                    name="cross_tab_extract",
                    description="Query and extract specific comparative data across open tabs in parallel.",
                    parameters={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Specific question or comparison to evaluate across tabs."}
                        },
                        "required": ["query"]
                    },
                    risk_tier="green"
                ),
                SkillTool(
                    name="synthesize_deep_research",
                    description="Generate an authoritative, multi-perspective research synthesis with bracketed numerical citations [1], [2].",
                    parameters={
                        "type": "object",
                        "properties": {
                            "topic": {"type": "string", "description": "The research question or topic."},
                            "depth": {"type": "string", "enum": ["quick", "deep"], "description": "Depth of analysis (default: 'deep')."}
                        },
                        "required": ["topic"]
                    },
                    risk_tier="green"
                )
            ]
        )

    def get_system_prompt_snippet(self) -> str:
        return (
            "When researching across multiple websites or tabs, call `cluster_open_tabs` to survey open sources, "
            "`cross_tab_extract` to extract aligned datapoints, and `synthesize_deep_research` for thorough reports. "
            "Always include numerical inline citations formatted as [1], [2] referencing the source URLs."
        )

    async def execute_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if tool_name == "cluster_open_tabs":
            tabs = await bridge.call("browser.get_tabs", {})
            tab_list = tabs or []
            clusters: Dict[str, List[Dict[str, Any]]] = {}
            for t in tab_list:
                domain = t.get("url", "").split("/")[2] if "://" in t.get("url", "") else "other"
                clusters.setdefault(domain, []).append({
                    "id": t.get("id"),
                    "title": t.get("title"),
                    "url": t.get("url")
                })
            return {
                "status": "success",
                "total_tabs": len(tab_list),
                "cluster_count": len(clusters),
                "clusters": clusters
            }

        elif tool_name == "cross_tab_extract":
            query = params.get("query", "")
            tabs_obs = await bridge.call("browser.inspect_all_tabs", {})
            provider, model = ModelRouter.route_for_task(task_type="reasoning")

            prompt = (
                f"You are the Multi-Tab Swarm Researcher.\n"
                f"User Query: {query}\n\n"
                f"Observed Tab Data:\n{tabs_obs}\n\n"
                f"Extract and cross-compare relevant findings from each tab. Present structured bullet points and comparison table."
            )
            res = await provider.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                model=model
            )
            return {"status": "success", "query": query, "synthesis": res.content}

        elif tool_name == "synthesize_deep_research":
            topic = params.get("topic", "")
            depth = params.get("depth", "deep")
            from backend.app.research.service import ResearchService
            return await ResearchService.synthesize(topic=topic, depth=depth)

        return {"status": "error", "message": f"Unknown tool '{tool_name}'"}
