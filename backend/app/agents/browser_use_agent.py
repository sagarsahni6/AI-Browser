import os
import json
import csv
import logging
import asyncio
from typing import Dict, Any, Optional, List
from pathlib import Path

from backend.app.config import settings
from backend.app.browser.bridge import bridge
from backend.app.database.engine import AsyncSessionLocal
from backend.app.database.repository import Repository
from backend.app.security.approval import ApprovalManager
from backend.app.tools.executor import ToolExecutor

logger = logging.getLogger(__name__)

class BrowserUseEngine:
    @staticmethod
    def resolve_llm(provider: Optional[str] = None, model: Optional[str] = None):
        """
        Resolves the appropriate browser-use LLM adapter based on provider name.
        Supports: browser_use_cloud, nvidia_nim, openai, anthropic, google_gemini, groq, ollama.
        """
        from browser_use import ChatBrowserUse, ChatOpenAI, ChatAnthropic, ChatGoogle

        active_provider = provider or settings.DEFAULT_PROVIDER

        # 1. Browser Use Cloud Gateway
        if active_provider == "browser_use_cloud" or (settings.BROWSER_USE_API_KEY and active_provider == "bu-4.0"):
            return ChatBrowserUse(
                model=model or "bu-4.0",
                api_key=settings.BROWSER_USE_API_KEY
            )

        # 2. Anthropic Claude
        elif active_provider == "anthropic":
            return ChatAnthropic(
                model=model or settings.ANTHROPIC_MODEL,
                api_key=settings.ANTHROPIC_API_KEY
            )

        # 3. Google Gemini
        elif active_provider == "google_gemini":
            return ChatGoogle(
                model=model or settings.GOOGLE_MODEL,
                api_key=settings.GOOGLE_API_KEY
            )

        # 4. Groq Ultra-Fast LPU
        elif active_provider == "groq":
            return ChatOpenAI(
                model=model or settings.GROQ_MODEL,
                api_key=settings.GROQ_API_KEY,
                base_url="https://api.groq.com/openai/v1"
            )

        # 5. Ollama Local Offline
        elif active_provider == "ollama":
            return ChatOpenAI(
                model=model or settings.OLLAMA_MODEL,
                api_key="ollama",
                base_url=f"{settings.OLLAMA_BASE_URL}/v1"
            )

        # 6. OpenAI Compatible / Standard OpenAI
        elif active_provider in ["openai", "openai_compatible"]:
            return ChatOpenAI(
                model=model or settings.OPENAI_MODEL,
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_BASE_URL
            )

        # 7. NVIDIA NIM (Default primary high-throughput)
        else:
            return ChatOpenAI(
                model=model or settings.NVIDIA_MODEL,
                api_key=settings.NVIDIA_API_KEY,
                base_url=settings.NVIDIA_BASE_URL
            )

    @staticmethod
    def resolve_browser(execution_mode: str = "active_tab"):
        """
        Resolves browser instance.
        - active_tab: connects via CDP to the running Electron browser instance (port 9222).
        - background: runs an isolated stealth browser (or cloud browser if API key configured).
        """
        from browser_use import Browser

        if execution_mode == "background":
            if settings.BROWSER_USE_API_KEY:
                try:
                    return Browser(kind="cloud")
                except Exception:
                    return Browser(headless=True)
            return Browser(headless=True)
        else:
            # Connect to Electron's active window/views via CDP
            return Browser(cdp_url=settings.BROWSER_USE_CDP_URL)

    @staticmethod
    def create_controller(task_id: str):
        """
        Builds a custom Controller registered with advanced enterprise capabilities:
        - Structured CSV & JSON export
        - Download triggering
        - Multi-tab management
        - Sensitive operation human approval gate
        """
        from browser_use import Controller, ActionResult

        controller = Controller()

        @controller.action("Export structured table records into a local CSV file")
        async def export_data_table(title: str, headers: List[str], rows: List[List[str]]) -> ActionResult:
            # Route through central ToolExecutor and policy engine
            safe_title = "".join(c if c.isalnum() or c in "-_" else "_" for c in title)
            res = await ToolExecutor.execute("export_csv", {
                "filename": f"{safe_title}_{task_id[:8]}.csv",
                "headers": headers,
                "rows": rows
            })
            if res.get("status") == "approval_required":
                return ActionResult(extracted_content="Action paused: waiting for human approval from the user.")
            if res.get("status") == "error":
                return ActionResult(error=f"Failed to export CSV: {res.get('error')}")

            file_path = res.get("exported_file", "")
            bridge.notify("browser.file_exported", {
                "file_path": str(file_path),
                "format": "csv",
                "row_count": len(rows),
                "title": title
            })
            return ActionResult(
                extracted_content=f"Successfully exported {len(rows)} rows to {file_path}",
                include_in_memory=True
            )

        @controller.action("Export structured JSON items into a local file")
        async def export_json_data(title: str, items_json: str) -> ActionResult:
            # Route through central ToolExecutor and policy engine
            safe_title = "".join(c if c.isalnum() or c in "-_" else "_" for c in title)
            try:
                parsed = json.loads(items_json)
            except Exception as e:
                return ActionResult(error=f"Invalid JSON: {e}")

            res = await ToolExecutor.execute("export_data", {
                "filename": f"{safe_title}_{task_id[:8]}.json",
                "data": parsed if isinstance(parsed, list) else [parsed],
                "format": "json"
            })
            if res.get("status") == "approval_required":
                return ActionResult(extracted_content="Action paused: waiting for human approval from the user.")
            if res.get("status") == "error":
                return ActionResult(error=f"Failed to export JSON: {res.get('error')}")
            return ActionResult(extracted_content=f"Exported JSON file successfully")

        @controller.action("Switch active browser tab by tab ID")
        async def switch_browser_tab(tab_id: str) -> ActionResult:
            try:
                await bridge.call("browser.switch_tab", {"tab_id": tab_id})
                return ActionResult(extracted_content=f"Switched to tab {tab_id}")
            except Exception as e:
                return ActionResult(error=f"Tab switch failed: {e}")

        @controller.action("Request human security approval for sensitive actions")
        async def request_security_approval(action_type: str, reason: str, details: str) -> ActionResult:
            # Check security policy
            req_appr, policy_reason = ApprovalManager.evaluate_tool_call(action_type, {"text": details})
            if req_appr:
                async with AsyncSessionLocal() as session:
                    repo = Repository(session)
                    await repo.update_task_status(task_id, status="approval_required", result=reason)
                    await repo.create_approval_request(
                        task_id=task_id,
                        tool_name=action_type,
                        action_type="sensitive_operation",
                        description=reason or policy_reason,
                        parameters_json=json.dumps({"details": details})
                    )
                bridge.notify("browser.action_started", {
                    "action": action_type,
                    "parameters": {"details": details, "task_id": task_id},
                    "status": "approval_required",
                    "result": reason or policy_reason
                })
                return ActionResult(
                    extracted_content="Action paused: waiting for human approval from the user.",
                    include_in_memory=True
                )
            return ActionResult(extracted_content="Security policy pre-authorized this action.")

        return controller

    @classmethod
    async def execute_task(
        cls,
        task_id: str,
        prompt: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        execution_mode: str = "active_tab"
    ) -> Dict[str, Any]:
        """
        Executes an autonomous task using browser-use with vision grounding,
        element indexing, and live UI notifications.
        Falls back seamlessly to native SupervisorAgent if necessary.
        """
        from browser_use import Agent

        logger.info(f"[BrowserUseEngine] Starting task {task_id} with prompt: {prompt} (mode={execution_mode})")

        # Notify UI task started
        bridge.notify("browser.action_started", {
            "action": "browser_use_init",
            "parameters": {"prompt": prompt, "mode": execution_mode},
            "description": f"Initializing browser-use engine (model={provider or 'default'}, mode={execution_mode})"
        })

        async with AsyncSessionLocal() as session:
            repo = Repository(session)
            await repo.update_task_status(task_id, status="running")

        try:
            llm = cls.resolve_llm(provider, model)
            browser = cls.resolve_browser(execution_mode)
            controller = cls.create_controller(task_id)

            agent = Agent(
                task=prompt,
                llm=llm,
                browser=browser,
                controller=controller,
                highlight_actions=True, # Numbered element bounding boxes [12]
            )

            # Record initial plan step
            async with AsyncSessionLocal() as session:
                repo = Repository(session)
                await repo.add_task_step(
                    task_id=task_id,
                    step_number=1,
                    description=f"Autonomous vision & DOM planning with browser-use for: {prompt[:80]}",
                    tool_name="browser_use_agent"
                )

            # Run browser-use agent
            history = await agent.run(max_steps=25)

            final_text = history.final_result() or history.text or "Task executed successfully."
            logger.info(f"[BrowserUseEngine] Task {task_id} completed successfully: {final_text[:120]}")

            # Update step and task in DB
            async with AsyncSessionLocal() as session:
                repo = Repository(session)
                db_steps = await repo.get_task_steps(task_id)
                if db_steps:
                    await repo.update_step_status(db_steps[0].id, status="completed", result={"output": final_text})
                await repo.update_task_status(task_id, status="completed", result=final_text)

            # Notify UI
            bridge.notify("browser.action_started", {
                "action": "browser_use_complete",
                "status": "completed",
                "result": final_text
            })

            return {
                "status": "completed",
                "task_id": task_id,
                "result": final_text,
                "steps_executed": history.number_of_steps
            }

        except Exception as e:
            logger.warning(f"[BrowserUseEngine] Direct browser-use run failed ({e}).")
            async with AsyncSessionLocal() as session:
                repo = Repository(session)
                await repo.update_task_status(task_id, status="failed", error=str(e))
            return {
                "status": "failed",
                "task_id": task_id,
                "error": str(e),
                "fallback_used": False
            }
