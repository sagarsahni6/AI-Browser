import logging
import importlib
import inspect
from pathlib import Path
from typing import Dict, Any, List, Optional, Type
from backend.app.skills.base import BaseSkill, SkillManifest

logger = logging.getLogger("skill_registry")


class SkillRegistry:
    """
    Central Manager for the AI Browser Agent Skills Architecture.
    Handles discovery, registration, lifecycle states, intent matching,
    system prompt generation, and tool routing.
    """
    def __init__(self):
        self._skills: Dict[str, BaseSkill] = {}
        self._tool_to_skill: Dict[str, str] = {}
        self._discovered: bool = False

    def register(self, skill: BaseSkill):
        skill_id = skill.manifest.id
        self._skills[skill_id] = skill
        for tool in skill.manifest.tools:
            self._tool_to_skill[tool.name] = skill_id
        logger.info(f"Registered agent skill: '{skill.manifest.name}' ({skill_id}) with {len(skill.manifest.tools)} tools")

    def get_skill(self, skill_id: str) -> Optional[BaseSkill]:
        self._ensure_discovered()
        return self._skills.get(skill_id)

    def list_manifests(self) -> List[Dict[str, Any]]:
        self._ensure_discovered()
        return [skill.manifest.to_dict() for skill in self._skills.values()]

    def toggle_skill(self, skill_id: str, enabled: Optional[bool] = None) -> bool:
        self._ensure_discovered()
        skill = self._skills.get(skill_id)
        if not skill:
            return False
        if enabled is None:
            skill.manifest.enabled = not skill.manifest.enabled
        else:
            skill.manifest.enabled = bool(enabled)
        logger.info(f"Skill '{skill_id}' enabled state set to: {skill.manifest.enabled}")
        return skill.manifest.enabled

    def get_tool_risk_tier(self, tool_name: str) -> Optional[str]:
        self._ensure_discovered()
        skill_id = self._tool_to_skill.get(tool_name)
        if not skill_id:
            return None
        skill = self._skills.get(skill_id)
        if not skill:
            return None
        for t in skill.manifest.tools:
            if t.name == tool_name:
                return t.risk_tier
        return "green"

    def match_skills(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> List[BaseSkill]:
        """
        Dynamically finds skills matching user prompt, explicit slash commands, or active webpage context.
        """
        self._ensure_discovered()
        lowered_prompt = (prompt or "").lower()
        context = context or {}
        matched: List[BaseSkill] = []

        for skill in self._skills.values():
            if not skill.manifest.enabled:
                continue

            # 1. Explicit slash command: e.g. /skill:web_scraper or /skill:scraper
            slash_token = f"/skill:{skill.manifest.id}"
            if slash_token in lowered_prompt or f"/skill:{skill.manifest.id.replace('_', '')}" in lowered_prompt:
                matched.append(skill)
                continue

            # 2. Trigger keywords
            for trigger in skill.manifest.triggers:
                if trigger.lower() in lowered_prompt:
                    matched.append(skill)
                    break

        return matched

    def get_active_system_prompts(self, prompt: str = "", context: Optional[Dict[str, Any]] = None) -> str:
        """
        Generates enriched system instructions from all matching active skills.
        """
        self._ensure_discovered()
        matched = self.match_skills(prompt, context)
        # If no specific skill matched, include general prompts of enabled high-utility skills
        if not matched:
            matched = [s for s in self._skills.values() if s.manifest.enabled][:3]

        if not matched:
            return ""

        sections = ["[ACTIVE AGENT SKILLS]"]
        for s in matched:
            snippet = s.get_system_prompt_snippet()
            if snippet:
                sections.append(f"--- SKILL: {s.manifest.name.upper()} ---\n{snippet.strip()}")

        return "\n\n".join(sections)

    def get_all_active_tools(self) -> List[Dict[str, Any]]:
        """
        Aggregates function definitions for all enabled skills.
        """
        self._ensure_discovered()
        tools: List[Dict[str, Any]] = []
        for s in self._skills.values():
            if s.manifest.enabled:
                for tool in s.manifest.tools:
                    tools.append(tool.to_function_def())
        return tools

    def is_skill_tool(self, tool_name: str) -> bool:
        self._ensure_discovered()
        return tool_name in self._tool_to_skill

    async def execute_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        self._ensure_discovered()
        skill_id = self._tool_to_skill.get(tool_name)
        if not skill_id:
            return {"status": "error", "message": f"Skill tool '{tool_name}' not found"}

        skill = self._skills.get(skill_id)
        if not skill:
            return {"status": "error", "message": f"Skill '{skill_id}' not found"}

        if not skill.manifest.enabled:
            return {"status": "error", "message": f"Skill '{skill.manifest.name}' is currently disabled"}

        try:
            return await skill.execute_tool(tool_name, params)
        except Exception as e:
            logger.error(f"Error executing skill tool '{tool_name}' on skill '{skill_id}': {e}", exc_info=True)
            return {"status": "error", "tool_name": tool_name, "error": str(e)}

    def discover_skills(self):
        """Auto-discover skill definition modules in backend.app.skills.definitions"""
        import backend.app.skills.definitions as defs_pkg
        defs_dir = Path(defs_pkg.__file__).parent

        for py_file in defs_dir.glob("*.py"):
            if py_file.name.startswith("__"):
                continue
            module_name = f"backend.app.skills.definitions.{py_file.stem}"
            try:
                mod = importlib.import_module(module_name)
                for _, obj in inspect.getmembers(mod, inspect.isclass):
                    if issubclass(obj, BaseSkill) and obj is not BaseSkill:
                        try:
                            instance = obj()
                            self.register(instance)
                        except Exception as init_err:
                            logger.error(f"Failed to instantiate skill class {obj.__name__} from {module_name}: {init_err}")
            except Exception as e:
                logger.error(f"Error importing skill module {module_name}: {e}")

        self._discovered = True

    def _ensure_discovered(self):
        if not self._discovered:
            self.discover_skills()


skill_registry = SkillRegistry()
