import logging
from typing import Dict, Any, Optional
from backend.app.browser.bridge import bridge
from backend.app.ai.router import ModelRouter
from backend.app.ai.registry import provider_registry
from backend.app.tools.executor import _normalize_response

logger = logging.getLogger("vision_agent")

class VisionAgent:
    """
    Specialist agent for visual inspection, bounding box analysis,
    and visual state verification using multimodal LLMs.
    """

    @classmethod
    async def execute_step(cls, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        tab_id = parameters.get("tab_id")

        if action == "inspect_visual_chart":
            question = parameters.get("question", "Describe what is shown in this chart.")
            res = await cls.inspect_visual_chart(question, tab_id)
            return _normalize_response(res, action)

        elif action == "locate_element_visually":
            description = parameters.get("description", "")
            res = await cls.locate_element_visually(description, tab_id)
            return _normalize_response(res, action)

        elif action == "verify_visual_state":
            expected_state = parameters.get("expected_state", "")
            res = await cls.verify_visual_state(expected_state, tab_id)
            return _normalize_response(res, action)

        elif action == "take_screenshot":
            payload = {}
            if tab_id:
                payload["tab_id"] = tab_id
            screenshot = await bridge.call("browser.capture_screenshot", payload)
            return _normalize_response({"status": "success", "screenshot_length": len(screenshot)}, action)

        else:
            from backend.app.tools.executor import ToolExecutor
            return await ToolExecutor.execute(action, parameters)

    @classmethod
    async def inspect_visual_chart(cls, question: str, tab_id: Optional[str] = None) -> Dict[str, Any]:
        payload = {}
        if tab_id:
            payload["tab_id"] = tab_id
        b64_img = await bridge.call("browser.capture_screenshot", payload) or ""
        raw_b64 = b64_img.split(",", 1)[-1] if "," in b64_img else b64_img

        v_provider, v_model = ModelRouter.route_for_task(task_type="vision")
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": f"Examine this visual view: {question}"},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{raw_b64}"}}
                ]
            }
        ]
        provider_inst = provider_registry.get(v_provider)
        reply = await provider_inst.chat_complete(messages, model=v_model)
        return {
            "status": "success",
            "analysis": reply.content,
            "provider": v_provider,
            "model": v_model
        }

    @classmethod
    async def locate_element_visually(cls, description: str, tab_id: Optional[str] = None) -> Dict[str, Any]:
        payload = {}
        if tab_id:
            payload["tab_id"] = tab_id
        b64_img = await bridge.call("browser.capture_screenshot", payload) or ""
        raw_b64 = b64_img.split(",", 1)[-1] if "," in b64_img else b64_img

        v_provider, v_model = ModelRouter.route_for_task(task_type="vision")
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"Identify the pixel coordinates or bounding box of '{description}' in this interface. Respond with (x, y) centroid coordinates."
                    },
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{raw_b64}"}}
                ]
            }
        ]
        provider_inst = provider_registry.get(v_provider)
        reply = await provider_inst.chat_complete(messages, model=v_model)
        return {
            "status": "success",
            "coordinates_description": reply.content,
            "target": description
        }

    @classmethod
    async def verify_visual_state(cls, expected_state: str, tab_id: Optional[str] = None) -> Dict[str, Any]:
        payload = {}
        if tab_id:
            payload["tab_id"] = tab_id
        b64_img = await bridge.call("browser.capture_screenshot", payload) or ""
        raw_b64 = b64_img.split(",", 1)[-1] if "," in b64_img else b64_img

        v_provider, v_model = ModelRouter.route_for_task(task_type="vision")
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"Verify whether the current screen displays the expected state: '{expected_state}'. Answer YES or NO, followed by concise explanation."
                    },
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{raw_b64}"}}
                ]
            }
        ]
        provider_inst = provider_registry.get(v_provider)
        reply = await provider_inst.chat_complete(messages, model=v_model)
        is_verified = "yes" in reply.content.lower()[:20]
        return {
            "status": "success",
            "verified": is_verified,
            "visual_evaluation": reply.content,
            "expected_state": expected_state
        }
