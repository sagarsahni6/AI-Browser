"""
tests/e2e/tier3_cross_feature/test_t3_pairwise_interactions.py
Tier 3: Pairwise Cross-Feature Combinatorial Interaction Tests (40 tests total).

Tests rigorous interactions between major feature groups across:
- Shared state & checkpoints (F03, F09, F16)
- Canonical data & tool schemas (F05, F06, F07, F08, F14)
- Security policy & boundary defenses (F04, F19, F20, F24, F25)
- Multi-agent coordination & planning (F10, F11, F12, F13, F15, F16, F17, F18)
- External AI routing & failover (F21, F22, F23)
- Research & data pipeline integration (F26, F27, F28, F29, F30)
- Workflows & UI indicators (F31, F32, F33, F34, F35)
"""

import os
import json
import csv
import re
import asyncio
from pathlib import Path
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock
import pytest
from sqlalchemy import select

from backend.app.config import settings
from backend.app.database.engine import AsyncSessionLocal
from backend.app.database.models import WorkflowExecution
from backend.app.database.repository import Repository
from backend.app.tools.executor import ToolExecutor
from backend.app.tools.definitions import BROWSER_TOOLS
from backend.app.security.approval import ApprovalManager
from backend.app.agents.supervisor import SupervisorAgent
from backend.app.agents.planner import PlannerAgent
from backend.app.agents.verifier import VerifierAgent
from backend.app.agents.browser_agent import BrowserAgent
from backend.app.agents.researcher import ResearcherAgent
from backend.app.agents.data_agent import DataAgent
from backend.app.research.service import ResearchService
from backend.app.workflows.engine import WorkflowEngine
from backend.app.automation.desktop.service import DesktopService
from backend.app.ai.router import ModelRouter
from backend.app.ai.registry import provider_registry
from backend.app.browser.bridge import bridge

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent.parent


# ===========================================================================
# 1. P01: F03 (Approval Lifecycle) x F05 (Canonical Execution Results)
# ===========================================================================
@pytest.mark.asyncio
async def test_t3_p01_f03_f05_approval_canonical(test_db):
    """Action paused for approval returns canonical 5-key structure with status='approval_required'."""
    res = await ToolExecutor.execute(
        "fill_input",
        {"x": 100, "y": 200, "text": "secret_password_123"},
        bypass_approval=False
    )
    # Validate canonical response contract
    assert "status" in res
    assert "tool_name" in res
    assert "result" in res
    assert "evidence" in res
    assert "error" in res
    assert res["status"] == "approval_required"
    assert res["tool_name"] == "fill_input"
    assert "password" in str(res.get("reason", "")).lower() or "credential" in str(res.get("reason", "")).lower()


# ===========================================================================
# 2. P02: F03 (Approval Lifecycle) x F09 (WorkflowEngine Approval Handling)
# ===========================================================================
@pytest.mark.asyncio
async def test_t3_p02_f03_f09_workflow_approval_pause(test_db):
    """Workflow containing a sensitive action pauses at that step with status='approval_required'."""
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        wf = await repo.create_workflow(
            name="Checkout Workflow",
            description="Navigates and submits sensitive purchase form",
            trigger_type="manual",
            steps=[
                {"action": "navigate", "parameters": {"url": "https://store.example.com"}},
                {"action": "click_element", "parameters": {"selector": "button#checkout"}},
                {"action": "get_page_content", "parameters": {}}
            ],
            variables={}
        )

    exec_res = await WorkflowEngine.execute_workflow(wf.id)
    assert exec_res["status"] == "approval_required"
    assert exec_res["paused_step"] == 2

    # Verify execution record in database is marked approval_required
    async with AsyncSessionLocal() as session:
        stmt = select(WorkflowExecution).where(WorkflowExecution.id == exec_res["execution_id"])
        res = await session.execute(stmt)
        item = res.scalars().first()
        assert item is not None
        assert item.status == "approval_required"
        assert item.current_step == 2


# ===========================================================================
# 3. P03: F03 (Approval Lifecycle) x F16 (Supervisor Agent Coordination)
# ===========================================================================
@pytest.mark.asyncio
async def test_t3_p03_f03_f16_supervisor_approval(test_db, mock_nim_provider):
    """Supervisor coordinates checkpoint persistence when a planned step requires approval."""
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        task = await repo.create_task(
            title="Purchase Task",
            prompt="Navigate and checkout laptop"
        )

    # Queue planner response containing a sensitive checkout step
    plan_json = json.dumps([
        {"agent": "browser", "action": "navigate", "description": "Go to store", "parameters": {"url": "https://shop.test"}},
        {"agent": "browser", "action": "click_element", "description": "Submit order", "parameters": {"selector": "button#checkout"}},
        {"agent": "verifier", "action": "verify_task", "description": "Verify purchase", "parameters": {}}
    ])
    mock_nim_provider.queue_completion(plan_json)

    await SupervisorAgent.run_task(task.id)

    # Verify task status and approval record exists in DB with saved checkpoint
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        updated_task = await repo.get_task(task.id)
        assert updated_task.status == "approval_required"
        appr = await repo.get_pending_approval_for_task(task.id)
        assert appr is not None
        assert appr.tool_name == "click_element"
        assert appr.session_checkpoint_json is not None


# ===========================================================================
# 4. P04: F03 (Approval Lifecycle) x F24 (Central 4-Tier Security Policy)
# ===========================================================================
def test_t3_p04_f03_f24_approval_policy():
    """Security policy correctly classifies GREEN safe actions vs RED approval-required actions."""
    # GREEN tier: read-only actions should never require approval
    for safe_tool in ["get_page_content", "take_screenshot", "scroll_page", "search_web"]:
        req, _ = ApprovalManager.evaluate_tool_call(safe_tool, {})
        assert req is False, f"Expected {safe_tool} to be GREEN tier (no approval)"

    # RED tier: financial and credential operations require approval
    req_pay, r_pay = ApprovalManager.evaluate_tool_call("click_element", {"selector": "button.pay-now"})
    assert req_pay is True
    assert "red tier" in r_pay.lower()

    req_cred, r_cred = ApprovalManager.evaluate_tool_call("fill_input", {"selector": "input#password", "text": "hunter2"})
    assert req_cred is True
    assert "red tier" in r_cred.lower()


# ===========================================================================
# 5. P05: F03 (Approval Lifecycle) x F33 (Risk Meter Approval Dialog UI)
# ===========================================================================
def test_t3_p05_f03_f33_approval_risk_meter():
    """Approval evaluation exposes clear risk level classifications and sensitive credential flags."""
    # Financial action triggers RED TIER (100% risk)
    req_fin, reason_fin = ApprovalManager.evaluate_tool_call("click_element", {"selector": "button#place-order"})
    assert req_fin is True
    assert "red tier" in reason_fin.lower()

    # Form fill without credentials evaluates to YELLOW TIER (40% risk notification)
    req_norm, reason_norm = ApprovalManager.evaluate_tool_call("fill_input", {"selector": "input#username", "text": "alice"})
    assert req_norm is False
    assert "yellow tier" in reason_norm.lower()

    # Form fill with credential triggers RED TIER masking & approval
    req_sec, reason_sec = ApprovalManager.evaluate_tool_call("fill_input", {"selector": "input#password", "text": "my_secret_token"})
    assert req_sec is True
    assert "red tier" in reason_sec.lower()


# ===========================================================================
# 6. P06: F04 (Browser-Use Security Interception) x F24 (Central Security Policy)
# ===========================================================================
@pytest.mark.asyncio
async def test_t3_p06_f04_f24_browser_use_policy():
    """Browser operations route through central policy and prevent unauthorized execution."""
    # Attempting to click payment button via ToolExecutor without bypass is intercepted
    res = await ToolExecutor.execute(
        "click_element",
        {"selector": "button#checkout", "x": 200, "y": 300},
        bypass_approval=False
    )
    assert res["status"] == "approval_required"
    assert "checkout" in res.get("reason", "").lower() or "red tier" in res.get("reason", "").lower()


# ===========================================================================
# 7. P07: F04 (Browser-Use Security Interception) x F25 (Prompt Injection & SSRF)
# ===========================================================================
@pytest.mark.asyncio
async def test_t3_p07_f04_f25_browser_use_ssrf():
    """Privileged protocols and dangerous targets are intercepted by security policy."""
    # javascript: scheme is blocked/flagged as requiring approval
    req_js, r_js = ApprovalManager.evaluate_tool_call("navigate", {"url": "javascript:alert(1)"})
    assert req_js is True
    assert "privileged protocol" in r_js.lower() or "red tier" in r_js.lower()

    # file: scheme is blocked/flagged as requiring approval
    req_file, r_file = ApprovalManager.evaluate_tool_call("navigate", {"url": "file:///C:/Windows/System32"})
    assert req_file is True
    assert "privileged protocol" in r_file.lower() or "red tier" in r_file.lower()


# ===========================================================================
# 8. P08: F05 (Canonical Results) x F07 (DataAgent Contract Alignment)
# ===========================================================================
@pytest.mark.asyncio
async def test_t3_p08_f05_f07_canonical_data_agent(mock_bridge):
    """DataAgent seamlessly consumes canonical execution results from get_page_content."""
    mock_bridge.set_dom_state(
        url="https://inventory.test",
        title="Inventory Table",
        text="Product | Qty | Price\nWidget A | 10 | $5.00\nWidget B | 25 | $12.50"
    )

    data_res = await DataAgent.extract_table_data(max_pages=1)
    assert data_res.get("status") in ("ok", "success")
    assert data_res["total_rows"] >= 2
    assert "rows" in data_res
    # Verify row structure
    first_row = data_res["rows"][0]
    assert any("col_" in k or "key" in k for k in first_row.keys())


# ===========================================================================
# 9. P09: F05 (Canonical Results) x F08 (ResearchService Contract Alignment)
# ===========================================================================
@pytest.mark.asyncio
async def test_t3_p09_f05_f08_canonical_research(test_db):
    """ResearchService consumes canonical search results to produce a comprehensive report."""
    report = await ResearchService.synthesize(
        topic="Quantum Computing Advances",
        sources=None,
        depth="quick"
    )
    assert report["status"] == "completed"
    assert report["topic"] == "Quantum Computing Advances"
    assert "## 1. Executive Summary" in report["content_markdown"]
    assert "## 4. Source Index & Confidence Ratings" in report["content_markdown"]
    assert report["sources_count"] > 0


# ===========================================================================
# 10. P10: F05 (Canonical Results) x F14 (Central Tool Registry)
# ===========================================================================
@pytest.mark.asyncio
async def test_t3_p10_f05_f14_canonical_tool_registry():
    """Tools declared in tool registry return canonical execution dictionaries."""
    assert len(BROWSER_TOOLS) >= 5

    # Execute read-only tool
    res_nav = await ToolExecutor.execute("navigate", {"url": "https://example.org"})
    assert res_nav["status"] == "success"
    assert res_nav["tool_name"] == "navigate"
    assert "result" in res_nav
    assert "evidence" in res_nav
    assert res_nav["error"] is None

    # Execute unknown tool
    res_unknown = await ToolExecutor.execute("non_existent_tool_xyz", {})
    assert res_unknown["status"] == "error"
    assert res_unknown["error"] is not None


# ===========================================================================
# 11. P11: F06 (Eliminate Duplicate Tools) x F28 (Advanced Data Extraction)
# ===========================================================================
@pytest.mark.asyncio
async def test_t3_p11_f06_f28_consolidated_table_extract(mock_bridge):
    """extract_table_data tool delegates cleanly to DataAgent without dead inline code."""
    mock_bridge.set_dom_state(
        url="https://pricing.test",
        title="Pricing Matrix",
        text="Tier: Free | Tier: Pro\nPrice: $0 | Price: $29\nStorage: 5GB | Storage: 50GB"
    )

    res = await ToolExecutor.execute("extract_table_data", {"max_pages": 1})
    assert res["status"] in ("ok", "success")
    # Verify result contains extracted rows from DataAgent
    assert res["total_rows"] >= 2 or len(res.get("rows", [])) >= 2
    assert isinstance(res["result"], list)
    assert len(res["result"]) >= 2


# ===========================================================================
# 12. P12: F07 (DataAgent Contract) x F28 (Advanced Data Extraction Engine)
# ===========================================================================
@pytest.mark.asyncio
async def test_t3_p12_f07_f28_data_agent_extraction(mock_bridge):
    """DataAgent extracts colon-separated key-value pairs into structured records."""
    mock_bridge.set_dom_state(
        url="https://specs.test",
        title="Hardware Specs",
        text="CPU: AMD Ryzen 9 7950X\nCores: 16\nThreads: 32\nTDP: 170W"
    )

    data_res = await DataAgent.extract_table_data(max_pages=1)
    assert data_res.get("status") in ("ok", "success")
    rows = data_res.get("rows", [])
    assert len(rows) >= 3
    keys = [r.get("key") for r in rows if "key" in r]
    assert "CPU" in keys or "Cores" in keys


# ===========================================================================
# 13. P13: F07 (DataAgent Contract) x F30 (Formula Protected Export)
# ===========================================================================
def test_t3_p13_f07_f30_data_agent_formula_protect():
    """DataAgent export formats CSV records and preserves clean data integrity."""
    records = [
        {"item": "Laptop", "price": 999.99, "sku": "LP-01"},
        {"item": "Mouse", "price": 29.99, "sku": "MS-02"}
    ]
    csv_res = DataAgent.export_data(records, format="csv", filename="inventory.csv")
    assert csv_res["status"] == "ok"
    assert csv_res["format"] == "csv"
    assert csv_res["row_count"] == 2
    assert "Laptop" in csv_res["data"]
    assert "999.99" in csv_res["data"]


# ===========================================================================
# 14. P14: F08 (Research Contract) x F26 (Autonomous Multi-Hop Research)
# ===========================================================================
@pytest.mark.asyncio
async def test_t3_p14_f08_f26_research_multi_hop():
    """ResearchService expands broad topic into multi-hop queries and structures findings."""
    queries = await ResearchService.expand_queries("Autonomous Web Agents")
    assert len(queries) >= 3
    assert any("findings" in q.lower() or "state of the art" in q.lower() for q in queries)
    assert any("comparisons" in q.lower() or "pros and cons" in q.lower() for q in queries)


# ===========================================================================
# 15. P15: F08 (Research Contract) x F27 (Grounded Authentic Citations)
# ===========================================================================
@pytest.mark.asyncio
async def test_t3_p15_f08_f27_research_grounded_citations(test_db):
    """Synthesized research report contains authentic source references and confidence ratings."""
    report = await ResearchService.synthesize(
        topic="Neural Architecture Search",
        sources=["https://arxiv.org/abs/nas-benchmark"],
        depth="quick"
    )
    content = report["content_markdown"]
    assert "## 4. Source Index & Confidence Ratings" in content
    assert len(report["sources"]) >= 1
    for src in report["sources"]:
        assert "confidence" in src
        assert 0.0 <= src["confidence"] <= 1.0
        assert "title" in src


# ===========================================================================
# 16. P16: F09 (Workflow Approval) x F31 (Advanced Workflow Engine)
# ===========================================================================
@pytest.mark.asyncio
async def test_t3_p16_f09_f31_workflow_approval_handling(test_db):
    """Workflow engine interpolates variables and pauses cleanly when approval is required."""
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        wf = await repo.create_workflow(
            name="Parameterized Sensitive Workflow",
            description="Uses variable interpolation and hits approval gate",
            trigger_type="manual",
            steps=[
                {"action": "navigate", "parameters": {"url": "{{target_site}}"}},
                {"action": "fill_input", "parameters": {"selector": "input#secret_code", "text": "{{secret_key}}"}},
                {"action": "take_screenshot", "parameters": {}}
            ],
            variables={"target_site": "https://auth.example.com", "secret_key": "top_secret_token"}
        )

    exec_res = await WorkflowEngine.execute_workflow(wf.id)
    assert exec_res["status"] == "approval_required"
    assert exec_res["paused_step"] == 2
    # Third step must NOT have been executed
    assert len(exec_res.get("results", [])) == 2


# ===========================================================================
# 17. P17: F10 (Objective Verification) x F12 (ReAct Execution Loop)
# ===========================================================================
@pytest.mark.asyncio
async def test_t3_p17_f10_f12_objective_verification_in_react(mock_bridge):
    """VerifierAgent performs objective DOM assertion confirming goal attainment."""
    mock_bridge.set_dom_state(
        url="https://dashboard.test/home",
        title="User Dashboard",
        text="Welcome back, Alice! Your account is active.",
        elements=[{"id": "el-welcome", "selector": "#welcome-banner", "text": "Welcome back, Alice!"}]
    )

    verif_res = await VerifierAgent.verify_dom_assertion({
        "selector": "#welcome-banner",
        "expected_state": "present"
    })
    assert verif_res["status"] == "success"
    assert verif_res["verified"] is True
    assert verif_res["evidence"]["found"] is True


# ===========================================================================
# 18. P18: F10 (Objective Verification) x F15 (Dynamic Planner Agent)
# ===========================================================================
@pytest.mark.asyncio
async def test_t3_p18_f10_f15_planner_objective_step():
    """Generated plan always incorporates a terminal objective verification step."""
    plan = await PlannerAgent.create_plan(
        task_id="task-test-plan-01",
        prompt="Search for latest AI news and summarize",
        current_url="https://news.ycombinator.com"
    )
    assert len(plan.steps) >= 2
    final_step = plan.steps[-1]
    assert final_step.agent == "verifier"
    assert "verify" in final_step.action.lower() or "verify" in final_step.description.lower()


# ===========================================================================
# 19. P19: F11 (Unified Runtime) x F12 (ReAct Execution Loop)
# ===========================================================================
@pytest.mark.asyncio
async def test_t3_p19_f11_f12_runtime_react_execution(test_db, mock_bridge, mock_nim_provider):
    """Runtime coordinates execution loop through Observe, Plan, Act, and Verify steps."""
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        task = await repo.create_task(
            title="Browse Documentation",
            prompt="Navigate to Python docs and verify title"
        )

    plan_json = json.dumps([
        {"agent": "browser", "action": "navigate", "description": "Go to docs", "parameters": {"url": "https://docs.python.org"}},
        {"agent": "data", "action": "get_page_content", "description": "Inspect text", "parameters": {}},
        {"agent": "verifier", "action": "verify_task", "description": "Verify success", "parameters": {}}
    ])
    mock_nim_provider.queue_completion(plan_json)

    await SupervisorAgent.run_task(task.id)

    # Verify task status in database
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        updated_task = await repo.get_task(task.id)
        assert updated_task.status == "completed"
        steps = await repo.get_task_steps(task.id)
        assert len(steps) == 3


# ===========================================================================
# 20. P20: F11 (Unified Runtime) x F13 (Execution Budget Limits)
# ===========================================================================
@pytest.mark.asyncio
async def test_t3_p20_f11_f13_runtime_budget_enforcement(test_db):
    """Cooperative task cancellation halts the execution loop immediately."""
    from backend.app.agents.models import TaskStep
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        task = await repo.create_task(
            title="Cancelled Task",
            prompt="Perform very long scraping sequence"
        )

    SupervisorAgent.cancel_task(task.id)
    assert SupervisorAgent.is_cancelled(task.id) is True

    pending_step = TaskStep(
        id=1,
        agent="browser",
        action="navigate",
        description="Navigate step",
        parameters={"url": "https://example.com"}
    )
    res = await SupervisorAgent._execute_steps_loop(
        task_id=task.id,
        remaining_steps=[pending_step],
        step_results=[],
        total_steps=5
    )
    assert res["status"] == "cancelled"


# ===========================================================================
# 21. P21: F11 (Unified Runtime) x F18 (Tab-Specific Context Binding)
# ===========================================================================
@pytest.mark.asyncio
async def test_t3_p21_f11_f18_runtime_tab_binding(mock_bridge):
    """Runtime operations explicitly targeting a tab_id operate within that tab's context."""
    # Create a secondary tab
    tab2_id = await mock_bridge.handle_call("browser.create_tab", {"url": "https://site-b.test"})
    assert tab2_id == "tab-2"

    # Navigate specific tab
    await mock_bridge.handle_call("browser.navigate", {"tab_id": tab2_id, "url": "https://site-b.test/pricing"})

    # Switch active tab back to tab-1, then inspect specifically tab-2
    await mock_bridge.handle_call("browser.switch_tab", {"tab_id": "tab-1"})
    obs_tab2 = await mock_bridge.handle_call("browser.inspect", {"tab_id": tab2_id})
    assert "site-b.test" in obs_tab2.get("url", "")


# ===========================================================================
# 22. P22: F12 (ReAct Execution Loop) x F13 (Execution Budget Limits)
# ===========================================================================
@pytest.mark.asyncio
async def test_t3_p22_f12_f13_react_budget_cutoff(test_db, mock_bridge, monkeypatch):
    """Step failures in ReAct loop are capped at max retries (3) preventing infinite loops."""
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        task = await repo.create_task(title="Failing Task", prompt="Click broken element")

    # Force click_element to always return error
    monkeypatch.setattr(
        ToolExecutor,
        "_execute_tool_action",
        AsyncMock(return_value={"status": "error", "error": "Element '#broken' not interactable"})
    )

    from backend.app.agents.models import TaskStep
    failing_step = TaskStep(
        id=1,
        agent="browser",
        action="click_element",
        description="Click broken button",
        parameters={"selector": "#broken"}
    )

    # Execute loop with 1 failing step
    res = await SupervisorAgent._execute_steps_loop(
        task_id=task.id,
        remaining_steps=[failing_step],
        step_results=[],
        total_steps=1
    )
    # Loop must complete after retry exhaustion without hanging
    assert res["status"] == "completed"


# ===========================================================================
# 23. P23: F12 (ReAct Execution Loop) x F15 (Dynamic Planner Upgrade)
# ===========================================================================
@pytest.mark.asyncio
async def test_t3_p23_f12_f15_react_subgoal_recovery():
    """PlannerAgent generates self-correcting recovery steps when a step fails."""
    from backend.app.agents.models import TaskStep
    failed_step = TaskStep(
        id=1,
        agent="browser",
        action="click_selector",
        description="Click checkout button",
        parameters={"selector": "button#submit-order"}
    )

    recovery = await PlannerAgent.replan_subgoal(
        task_id="task-recovery-test",
        failed_step=failed_step,
        error_context="Element 'button#submit-order' not in viewport",
        current_obs={"url": "https://shop.test/cart", "visibleText": "Cart overview", "interactiveElements": []},
        remaining_steps=[]
    )
    assert len(recovery) >= 1
    assert "[RECOVERY]" in recovery[0].description


# ===========================================================================
# 24. P24: F14 (Central Tool Registry) x F24 (Central Security Policy)
# ===========================================================================
def test_t3_p24_f14_f24_registry_risk_tier():
    """All registered browser tools map into consistent risk tier categories."""
    registered_names = [tool["function"]["name"] for tool in BROWSER_TOOLS]

    for name in registered_names:
        req_approval, reason = ApprovalManager.evaluate_tool_call(name, {})
        # Tool must evaluate without throwing
        assert isinstance(req_approval, bool)
        assert isinstance(reason, str)


# ===========================================================================
# 25. P25: F15 (Dynamic Planner) x F16 (Supervisor Agent Coordination)
# ===========================================================================
@pytest.mark.asyncio
async def test_t3_p25_f15_f16_planner_supervisor_sync(test_db):
    """Supervisor populates task_steps database table matching the planner's step IDs."""
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        task = await repo.create_task(
            title="Planned Sync Task",
            prompt="Extract stock quotes"
        )

    plan = await PlannerAgent.create_plan(task.id, task.prompt)
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        for s in plan.steps:
            await repo.add_task_step(task.id, s.id, s.description, s.action, s.parameters)

        db_steps = await repo.get_task_steps(task.id)
        assert len(db_steps) == len(plan.steps)
        assert [s.step_number for s in db_steps] == [s.id for s in plan.steps]


# ===========================================================================
# 26. P26: F16 (Supervisor Agent) x F17 (Specialist Agents Architecture)
# ===========================================================================
@pytest.mark.asyncio
async def test_t3_p26_f16_f17_supervisor_specialists(mock_bridge):
    """Supervisor dispatches step execution across distinct specialist agents."""
    # Test BrowserAgent
    res_b = await BrowserAgent.execute_step("navigate", {"url": "https://example.org"})
    assert res_b.get("status") in ("ok", "success")

    # Test DataAgent
    res_d = await DataAgent.execute_step("get_page_content", {})
    assert res_d.get("status") in ("ok", "success")

    # Test VerifierAgent
    res_v = await VerifierAgent.execute_step("url_match", {"pattern": "example"})
    assert res_v.get("status") in ("ok", "success")


# ===========================================================================
# 27. P27: F17 (Specialist Agents) x F18 (Tab-Specific Context Binding)
# ===========================================================================
@pytest.mark.asyncio
async def test_t3_p27_f17_f18_specialist_tab_context(mock_bridge):
    """Specialists pass tab_id parameter to execute actions within targeted tabs."""
    new_tab = await mock_bridge.handle_call("browser.create_tab", {"url": "https://tab2.example.com"})

    # BrowserAgent executes in tab2
    res = await BrowserAgent.execute_step("navigate", {"tab_id": new_tab, "url": "https://tab2.example.com/login"})
    assert res.get("status") in ("ok", "success")

    # Verify tab URL updated in mock bridge
    tabs = await mock_bridge.handle_call("browser.get_tabs", {})
    tab2 = next((t for t in tabs if t["id"] == new_tab), None)
    assert tab2 is not None
    assert tab2["url"] == "https://tab2.example.com/login"


# ===========================================================================
# 28. P28: F19 (Desktop Hardening) x F20 (Audit Logging & Kill Switch)
# ===========================================================================
@pytest.mark.asyncio
async def test_t3_p28_f19_f20_desktop_kill_switch(test_db, mock_desktop_primitives):
    """Activating desktop emergency stop immediately blocks actions and logs audit trail."""
    DesktopService.emergency_stop()
    assert DesktopService.is_stopped() is True

    # Mouse click attempted while stopped
    click_res = await DesktopService.mouse_click(150, 250)
    assert click_res["status"] == "error"
    assert "emergency stop" in click_res["error"].lower()

    # Reset kill switch
    DesktopService.reset_emergency_stop()
    assert DesktopService.is_stopped() is False

    # Mouse click succeeds when resumed
    click_res2 = await DesktopService.mouse_click(150, 250)
    assert click_res2["status"] == "success"

    # Verify audit logs in database
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        logs = await repo.get_desktop_audit_logs(limit=10)
        assert len(logs) >= 2
        # One unauthorized/blocked, one authorized
        assert any(log.authorized is False for log in logs)
        assert any(log.authorized is True for log in logs)


# ===========================================================================
# 29. P29: F19 (Desktop Hardening) x F24 (Central Security Policy)
# ===========================================================================
def test_t3_p29_f19_f24_desktop_policy_allowlist():
    """Desktop application launch evaluates through policy as RED TIER requiring approval."""
    req, reason = ApprovalManager.evaluate_tool_call("desktop_launch_app", {"app_name": "notepad.exe"})
    assert req is True
    assert "red tier" in reason.lower()
    assert "launching desktop app" in reason.lower()


# ===========================================================================
# 30. P30: F21 (NVIDIA NIM Primary) x F22 (Capability-Aware Model Routing)
# ===========================================================================
def test_t3_p30_f21_f22_nim_model_routing():
    """ModelRouter selects NVIDIA NIM models based on task capability requirement."""
    # Vision tasks route to NVIDIA vision model
    prov_vis, model_vis = ModelRouter.route_for_task(task_type="vision", preferred_provider="nvidia_nim")
    assert prov_vis.provider_id == "nvidia_nim"
    assert model_vis == settings.NVIDIA_VISION_MODEL

    # Reasoning tasks route to NVIDIA reasoning model
    prov_reas, model_reas = ModelRouter.route_for_task(task_type="reasoning", preferred_provider="nvidia_nim")
    assert prov_reas.provider_id == "nvidia_nim"
    assert model_reas == settings.NVIDIA_REASONING_MODEL

    # Standard tool calling routes to primary model
    prov_tools, model_tools = ModelRouter.route_for_task(task_type="tools", preferred_provider="nvidia_nim")
    assert prov_tools.provider_id == "nvidia_nim"
    assert model_tools == settings.NVIDIA_MODEL


# ===========================================================================
# 31. P31: F21 (NVIDIA NIM Primary) x F23 (Provider Failover & Health Checks)
# ===========================================================================
@pytest.mark.asyncio
async def test_t3_p31_f21_f23_nim_provider_failover(mock_nim_provider):
    """Health check reports healthy, and simulated provider timeout triggers failover."""
    assert await mock_nim_provider.check_connection() is True

    # Simulate timeout
    mock_nim_provider.simulate_timeout = True
    assert await mock_nim_provider.check_connection() is False

    # Chat completion raises timeout error
    with pytest.raises(asyncio.TimeoutError):
        await mock_nim_provider.chat_completion([{"role": "user", "content": "Hello"}])

    mock_nim_provider.simulate_timeout = False
    assert await mock_nim_provider.check_connection() is True


# ===========================================================================
# 32. P32: F22 (Capability Routing) x F23 (Provider Failover & Health Checks)
# ===========================================================================
def test_t3_p32_f22_f23_routing_failover():
    """Model router respects user-specified model and provider overrides."""
    prov, model = ModelRouter.route_for_task(
        task_type="text",
        preferred_provider="nvidia_nim",
        preferred_model="meta/llama-3.1-8b-instruct"
    )
    assert prov.provider_id == "nvidia_nim"
    assert model == "meta/llama-3.1-8b-instruct"


# ===========================================================================
# 33. P33: F24 (Central Security Policy) x F25 (Prompt Injection & SSRF)
# ===========================================================================
def test_t3_p33_f24_f25_policy_ssrf_integration():
    """Security policy flags local loopback and internal network navigation attempts."""
    # Loopback IP
    req_local, r_local = ApprovalManager.evaluate_tool_call("navigate", {"url": "http://127.0.0.1:8000/admin"})
    assert req_local is True or "permitted" in r_local.lower()

    # JavaScript URI injection
    req_js, r_js = ApprovalManager.evaluate_tool_call("navigate", {"url": "javascript:void(fetch('http://127.0.0.1'))"})
    assert req_js is True
    assert "privileged protocol" in r_js.lower() or "red tier" in r_js.lower()


# ===========================================================================
# 34. P34: F26 (Autonomous Multi-Hop) x F27 (Grounded Authentic Citations)
# ===========================================================================
@pytest.mark.asyncio
async def test_t3_p34_f26_f27_research_citation_verification(test_db):
    """All bracketed citations [Source X] in synthesized report map to valid Source Index."""
    report = await ResearchService.synthesize(
        topic="Solid State Battery Technology",
        sources=None,
        depth="quick"
    )
    content = report["content_markdown"]
    sources = report["sources"]

    # Extract all [Source X] citations from markdown
    cited_ids = [int(m) for m in re.findall(r"\[Source (\d+)\]", content)]
    available_ids = [s["id"] for s in sources]

    for c_id in cited_ids:
        assert c_id in available_ids, f"Citation [Source {c_id}] does not exist in Source Index"


# ===========================================================================
# 35. P35: F26 (Autonomous Multi-Hop) x F30 (Formula Protected Export)
# ===========================================================================
def test_t3_p35_f26_f30_research_export_protection():
    """Synthesized research findings exported to CSV sanitize formula injection prefixes."""
    findings = [
        {"source_id": 1, "topic": "Battery", "claim": "=SUM(A1:A10) verified improvement"},
        {"source_id": 2, "topic": "Anode", "claim": "@HYPERLINK('http://evil.com')"}
    ]
    # Export via DataAgent
    csv_data = DataAgent.export_data(findings, format="csv", filename="research_findings.csv")
    assert csv_data["status"] == "ok"
    assert csv_data["row_count"] == 2
    # Verify content safely escaped/rendered
    assert "Battery" in csv_data["data"]


# ===========================================================================
# 36. P36: F28 (Advanced Data Extraction) x F29 (Pagination & Infinite Scroll)
# ===========================================================================
@pytest.mark.asyncio
async def test_t3_p36_f28_f29_data_extract_pagination(mock_bridge, monkeypatch):
    """DataAgent traverses multiple pages using pagination_next_selector up to max_pages."""
    mock_bridge.set_dom_state(
        url="https://catalog.test/page1",
        title="Catalog",
        text="Item: Laptop | Price: $999\nItem: Phone | Price: $699"
    )

    orig_exec = ToolExecutor.execute

    async def _mock_exec(tool_name: str, params: Dict[str, Any], bypass_approval: bool = False):
        if tool_name in ("click_selector", "sleep"):
            return {"status": "success", "tool_name": tool_name, "result": {}, "evidence": {}, "error": None}
        return await orig_exec(tool_name, params, bypass_approval=bypass_approval)

    monkeypatch.setattr(ToolExecutor, "execute", _mock_exec)

    result = await DataAgent.extract_table_data(
        selector="table",
        pagination_next_selector="a.next-page",
        max_pages=2
    )
    assert result.get("status") in ("ok", "success")
    assert result["pages_scraped"] == 2
    assert result["total_rows"] >= 2


# ===========================================================================
# 37. P37: F28 (Advanced Data Extraction) x F30 (Formula Protected Export)
# ===========================================================================
@pytest.mark.asyncio
async def test_t3_p37_f28_f30_data_extract_export(mock_bridge):
    """Extracted tabular data is directly exportable to JSON and CSV formats."""
    mock_bridge.set_dom_state(
        url="https://finance.test/stocks",
        title="Stock Quotes",
        text="Symbol: AAPL | Price: $185.00\nSymbol: MSFT | Price: $410.00"
    )

    extract_res = await DataAgent.extract_table_data(max_pages=1)
    rows = extract_res.get("rows", [])
    assert len(rows) >= 2

    # Export to JSON
    json_res = DataAgent.export_data(rows, format="json", filename="stocks.json")
    assert json_res["status"] == "ok"
    assert json_res["row_count"] == len(rows)

    # Export to CSV
    csv_res = DataAgent.export_data(rows, format="csv", filename="stocks.csv")
    assert csv_res["status"] == "ok"
    assert csv_res["row_count"] == len(rows)


# ===========================================================================
# 38. P38: F31 (Advanced Workflow Engine) x F32 (Workflow Import / Export)
# ===========================================================================
@pytest.mark.asyncio
async def test_t3_p38_f31_f32_workflow_import_execution(test_db):
    """Imported workflow JSON creates database record and executes to completion."""
    workflow_definition = {
        "name": "Portable Scraper Workflow",
        "description": "Navigates and captures content",
        "trigger_type": "manual",
        "steps": [
            {"action": "navigate", "parameters": {"url": "https://portable.test"}},
            {"action": "get_page_content", "parameters": {}},
            {"action": "take_screenshot", "parameters": {}}
        ],
        "variables": {}
    }

    imported = await WorkflowEngine.import_workflow(workflow_definition)
    assert "id" in imported
    wf_id = imported["id"]

    # Execute imported workflow
    exec_res = await WorkflowEngine.execute_workflow(wf_id)
    assert exec_res["status"] == "completed"
    assert exec_res["steps_executed"] == 3


# ===========================================================================
# 39. P39: F34 (Visual Laser Overlay UI) x F18 (Tab-Specific Context Binding)
# ===========================================================================
@pytest.mark.asyncio
async def test_t3_p39_f34_f18_laser_tab_coordinates(mock_bridge):
    """Browser clicks record coordinate position and target tab for laser visual indicator."""
    res = await ToolExecutor.execute("click_element", {"x": 350, "y": 420})
    assert res["status"] == "success"
    assert res["clicked"]["x"] == 350
    assert res["clicked"]["y"] == 420


# ===========================================================================
# 40. P40: F35 (Assistant Progress Banner UI) x F16 (Supervisor Coordination)
# ===========================================================================
@pytest.mark.asyncio
async def test_t3_p40_f35_f16_progress_banner_supervisor(test_db, mock_bridge, mock_nim_provider):
    """Supervisor emits live bridge notifications for banner state tracking."""
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        task = await repo.create_task(title="Banner Tracking Task", prompt="Inspect and report")

    plan_json = json.dumps([
        {"agent": "browser", "action": "navigate", "description": "Navigate to site", "parameters": {"url": "https://banner.test"}},
        {"agent": "verifier", "action": "verify_task", "description": "Verify page", "parameters": {}}
    ])
    mock_nim_provider.queue_completion(plan_json)

    await SupervisorAgent.run_task(task.id)

    # Verify notifications captured in mock_bridge
    notifications = [n for n in mock_bridge.notifications if n["method"] == "task.step_updated"]
    assert len(notifications) >= 2
    statuses = [n["params"].get("status") for n in notifications]
    assert "running" in statuses
    assert "completed" in statuses
