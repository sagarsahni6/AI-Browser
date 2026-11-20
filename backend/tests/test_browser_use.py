import pytest
import os
from pathlib import Path
from backend.app.agents.browser_use_agent import BrowserUseEngine
from backend.app.config import settings
from backend.app.database.engine import AsyncSessionLocal
from backend.app.database.repository import Repository

@pytest.mark.asyncio
async def test_browser_use_llm_resolution():
    # Test OpenAI resolution
    llm_openai = BrowserUseEngine.resolve_llm("openai_compatible", "gpt-4o")
    assert llm_openai is not None

    # Test Anthropic resolution
    llm_anthropic = BrowserUseEngine.resolve_llm("anthropic", "claude-3-5-sonnet-20241022")
    assert llm_anthropic is not None

    # Test Google Gemini resolution
    llm_gemini = BrowserUseEngine.resolve_llm("google_gemini", "gemini-2.0-flash")
    assert llm_gemini is not None

    # Test Groq resolution
    llm_groq = BrowserUseEngine.resolve_llm("groq", "llama-3.3-70b-versatile")
    assert llm_groq is not None

    # Test Ollama resolution
    llm_ollama = BrowserUseEngine.resolve_llm("ollama", "llama3.2")
    assert llm_ollama is not None

    # Test NVIDIA NIM resolution (default)
    llm_nim = BrowserUseEngine.resolve_llm("nvidia_nim")
    assert llm_nim is not None

@pytest.mark.asyncio
async def test_browser_use_controller_actions():
    task_id = "test-task-123"
    controller = BrowserUseEngine.create_controller(task_id)
    assert controller is not None

    # Check registered actions
    registry = controller.registry
    action_names = list(registry.actions.keys()) if hasattr(registry, "actions") else []
    assert len(action_names) >= 4 or len(controller.functions) >= 4

@pytest.mark.asyncio
async def test_browser_use_resilient_fallback():
    # Test that execute_task falls back cleanly when CDP is not running
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        task = await repo.create_task("Test Fallback Task", "Search quantum papers and export")
        task_id = task.id

    result = await BrowserUseEngine.execute_task(
        task_id=task_id,
        prompt="Search quantum papers and export",
        provider="nvidia_nim",
        execution_mode="active_tab"
    )

    assert result["status"] in ["completed", "running", "approval_required"]
    assert result["task_id"] == task_id
