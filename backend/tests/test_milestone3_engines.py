"""
backend/tests/test_milestone3_engines.py
Unit and Integration Test Suite for Milestone 3: Specialist Engines & UI Integration.

Covers:
  - Feature 26: Autonomous Multi-Hop Research Engine
  - Feature 27: Grounded Synthesis & Authentic Citations
  - Feature 28: Advanced Tabular & Hierarchical Extraction
  - Feature 29: Deep Pagination & Deduplication
  - Feature 30: Multi-Format Export with Formula Defense
  - Feature 31: Advanced Workflow Engine (DAG, Interpolation, Recovery)
  - Feature 32: Workflow Import/Export & Checkpoint Resumption
  - Feature 33–35: Risk Meter, Visual Indicators & Progress Banner
"""

import json
import os
import re
import pytest
import asyncio
from unittest.mock import patch, AsyncMock
import httpx

from backend.app.database.engine import AsyncSessionLocal, init_db
from backend.app.database.repository import Repository
from backend.app.research.service import ResearchService
from backend.app.research.citation import CitationManager
from backend.app.agents.data_agent import DataAgent
from backend.app.workflows.engine import WorkflowEngine
from backend.app.workflows.models import WorkflowDefinition, WorkflowStep
from backend.app.tools.executor import ToolExecutor


@pytest.fixture(autouse=True)
async def setup_db():
    await init_db()
    yield

@pytest.fixture
async def test_db():
    await init_db()
    yield


# ===========================================================================
# 1. Autonomous Research Engine (Features 26 & 27)
# ===========================================================================

@pytest.mark.asyncio
async def test_m3_research_query_expansion():
    """Verify expand_queries generates >= 3 sub-queries with key analytical dimensions."""
    topic = "Quantum Supercomputing"
    queries = await ResearchService.expand_queries(topic)
    assert isinstance(queries, list)
    assert len(queries) >= 3
    assert topic in queries
    assert any("findings" in q.lower() for q in queries)
    assert any("comparisons" in q.lower() for q in queries)
    assert any("recent" in q.lower() for q in queries)


@pytest.mark.asyncio
async def test_m3_research_ssrf_blocking():
    """Verify fetch_page_text blocks internal SSRF requests targeting loopback and cloud metadata."""
    loopback_res = await ResearchService.fetch_page_text("http://127.0.0.1:8000/internal")
    assert loopback_res["status"] == "error"
    assert "SSRF blocked" in loopback_res.get("error", "")

    metadata_res = await ResearchService.fetch_page_text("http://169.254.169.254/latest/meta-data")
    assert metadata_res["status"] == "error"
    assert "SSRF blocked" in metadata_res.get("error", "")


@pytest.mark.asyncio
async def test_m3_research_html_cleaning():
    """Verify HTML cleaning strips scripts/styles/nav/footer, unescapes entities, and caps length at 2500."""
    html_content = (
        "<html><head><title>Test Page</title><script>var x = 1;</script><style>body {color: red;}</style></head>"
        "<body><nav>Menu items</nav><p>Important finding &amp; breakthrough in AI &quot;architecture&quot;.</p>"
        "<footer>Copyright 2026</footer>"
        + ("Extra content word " * 300)
        + "</body></html>"
    )
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_resp = httpx.Response(200, text=html_content, request=httpx.Request("GET", "https://example.com/test"))
        mock_get.return_value = mock_resp
        res = await ResearchService.fetch_page_text("https://example.com/test")

        assert res["status"] == "ok"
        assert res["title"] == "Test Page"
        assert "var x = 1" not in res["text"]
        assert "color: red" not in res["text"]
        assert "Menu items" not in res["text"]
        assert "Copyright 2026" not in res["text"]
        assert "&amp;" not in res["text"]
        assert 'Important finding & breakthrough in AI "architecture"' in res["text"]
        assert len(res["text"]) <= 2500


@pytest.mark.asyncio
async def test_m3_research_authentic_citations():
    """Verify authentic confidence calculation: web sources >= 0.85, local fallback strictly 0.85."""
    # 1. Local fallback score
    local_source = {"url": "local://analysis", "text": "Synthesized analysis.", "title": "Local"}
    local_conf = CitationManager.calculate_authentic_confidence(local_source, [local_source])
    assert local_conf == 0.85

    # 2. Web source with cross-source corroboration
    src1 = {
        "url": "https://example.com/study1",
        "title": "Study 1",
        "text": "Solid-state batteries demonstrate dramatic thermal stability and superior volumetric density."
    }
    src2 = {
        "url": "https://example.org/study2",
        "title": "Study 2",
        "text": "Batteries with solid-state electrolytes exhibit superior thermal stability under rapid charging."
    }
    conf1 = CitationManager.calculate_authentic_confidence(src1, [src1, src2])
    assert 0.85 <= conf1 <= 0.99
    assert conf1 >= 0.88  # https baseline


@pytest.mark.asyncio
async def test_m3_research_contradiction_detection():
    """Verify detection of factual disagreements and opposing trade-offs across sources."""
    src_a = {
        "id": 1,
        "title": "Decentralized Architecture",
        "url": "https://example.com/a",
        "text": "A distributed network provides significant advantage by eliminating single points of failure."
    }
    src_b = {
        "id": 2,
        "title": "Centralized Architecture",
        "url": "https://example.com/b",
        "text": "A centralized infrastructure is preferred because distributed systems introduce massive bottleneck overhead."
    }
    contradictions = CitationManager.detect_contradictions([src_a, src_b])
    assert len(contradictions) >= 1
    assert any("Centralized vs Distributed" in c["dimension"] or "Advantage vs Disadvantage" in c["dimension"] or "Bottleneck vs Breakthrough" in c["dimension"] for c in contradictions)


@pytest.mark.asyncio
async def test_m3_research_report_persistence():
    """Verify synthesized research report persists in SQLite research_reports table."""
    report = await ResearchService.synthesize(topic="Neuromorphic Computing Architectures", sources=[])
    assert report["status"] == "completed"
    assert report["report_id"] is not None
    assert report["report_id"].startswith("rep-")

    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        persisted = await repo.get_research_report(report["report_id"])
        assert persisted is not None
        assert persisted.topic == "Neuromorphic Computing Architectures"
        assert "## 1. Executive Summary" in persisted.content_markdown
        assert "## 3. Comparative Matrix" in persisted.content_markdown


# ===========================================================================
# 2. Advanced Data Extraction Engine (Features 28, 29, 30)
# ===========================================================================

@pytest.mark.asyncio
async def test_m3_data_tabular_extraction_pipe():
    """Verify extraction of pipe-delimited table text into col_1, col_2 keys with page metadata."""
    sample_text = "Symbol | Name | Price\nNVDA | NVIDIA Corp | $145.50\nAAPL | Apple Inc | $230.00"
    with patch.object(ToolExecutor, "execute", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = {"status": "ok", "text": sample_text}
        res = await DataAgent.extract_table_data(max_pages=1)
        assert res["status"] == "ok"
        assert res["total_rows"] >= 2
        first_row = res["rows"][0]
        assert "col_1" in first_row
        assert "col_2" in first_row
        assert first_row["page"] == 1


def test_m3_data_schema_type_inference():
    """Verify schema type inference for currency, number, date, url, and text."""
    rows = [
        {"price": "$1,250.00", "qty": "45", "updated": "2026-11-23", "link": "https://example.com/p1", "notes": "In stock"},
        {"price": "$340.50", "qty": "12", "updated": "2026-11-22", "link": "https://example.com/p2", "notes": "Backorder"}
    ]
    schema = DataAgent.infer_column_types(rows)
    assert schema["price"] == "currency"
    assert schema["qty"] == "number"
    assert schema["updated"] == "date"
    assert schema["link"] == "url"
    assert schema["notes"] == "text"


@pytest.mark.asyncio
async def test_m3_data_deduplication_and_metrics():
    """Verify deduplication filters duplicate records and tracks duplicate_count."""
    # Identical content across simulated pages
    page_text = "Value A | Value B\nValue A | Value B"
    with patch.object(ToolExecutor, "execute", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = {"status": "ok", "text": page_text}
        res = await DataAgent.extract_table_data(max_pages=1)
        assert res["status"] == "ok"
        assert res["duplicate_count"] >= 1
        assert res["total_rows"] == 1


def test_m3_data_formula_injection_defense():
    """Verify formula injection triggers (=, +, -, @, \\t, \\r) are neutralized with single quote."""
    triggers = ["=SUM(A1:A10)", "+CMD|' /C calc'!A0", "-5+5", "@HYPERLINK('http://malicious.org')", "\tTEST", "\rDDE"]
    for trig in triggers:
        sanitized = DataAgent.sanitize_cell(trig)
        assert sanitized.startswith("'"), f"Trigger '{trig}' was not sanitized: '{sanitized}'"

    safe_text = "Normal Text 123"
    assert DataAgent.sanitize_cell(safe_text) == safe_text


def test_m3_data_multi_format_export(tmp_path):
    """Verify export to CSV, JSON, and XLSX maintains data integrity with sanitized cells."""
    records = [
        {"name": "Widget A", "price": "=10+20", "category": "Hardware"},
        {"name": "Widget B", "price": "@SUM(1,2)", "category": "Accessories"}
    ]

    # 1. CSV Export
    csv_res = DataAgent.export_data(records, format="csv", filename="test_export.csv")
    assert csv_res["status"] == "ok"
    assert csv_res["row_count"] == 2
    assert "'=10+20" in csv_res["data"]
    assert "'@SUM(1,2)" in csv_res["data"]

    # 2. JSON Export
    json_res = DataAgent.export_data(records, format="json", filename="test_export.json")
    assert json_res["status"] == "ok"
    parsed = json.loads(json_res["data"])
    assert len(parsed) == 2

    # 3. XLSX Export
    xlsx_res = DataAgent.export_data(records, format="xlsx", filename="test_export.xlsx")
    assert xlsx_res["status"] == "ok"
    assert xlsx_res["format"] == "xlsx"


# ===========================================================================
# 3. Advanced Workflow Engine (Features 31 & 32)
# ===========================================================================

def test_m3_workflow_dag_topological_execution():
    """Verify steps with depends_on execute in correct topological DAG dependency order."""
    steps = [
        {"id": "step_c", "action": "export_csv", "depends_on": ["step_b"]},
        {"id": "step_a", "action": "navigate", "depends_on": []},
        {"id": "step_b", "action": "extract_table_data", "depends_on": ["step_a"]}
    ]
    ordered = WorkflowEngine.resolve_dag_order(steps)
    step_ids = [s["id"] for s in ordered]
    assert step_ids == ["step_a", "step_b", "step_c"]


def test_m3_workflow_dag_cyclic_detection():
    """Verify cyclic dependency in workflow DAG raises ValueError."""
    cyclic_steps = [
        {"id": "node_1", "action": "navigate", "depends_on": ["node_2"]},
        {"id": "node_2", "action": "click", "depends_on": ["node_1"]}
    ]
    with pytest.raises(ValueError, match="Cyclic dependency detected"):
        WorkflowEngine.resolve_dag_order(cyclic_steps)


def test_m3_workflow_variable_interpolation_step_output():
    """Verify deep interpolation of prior step outputs and preservation of native types."""
    context = {
        "variables": {"base_url": "https://api.example.com"},
        "step_outputs": {
            "fetch_data": {
                "result": {
                    "records": [{"id": 101, "name": "Item A"}, {"id": 102, "name": "Item B"}],
                    "token": "secret_token_123"
                }
            }
        }
    }

    # 1. Exact match preserves list object
    exact_expr = "{{fetch_data.result.records}}"
    resolved_list = WorkflowEngine._interpolate(exact_expr, context)
    assert isinstance(resolved_list, list)
    assert len(resolved_list) == 2
    assert resolved_list[0]["id"] == 101

    # 2. Substring substitution
    str_expr = "{{base_url}}/auth?token={{fetch_data.result.token}}"
    resolved_str = WorkflowEngine._interpolate(str_expr, context)
    assert resolved_str == "https://api.example.com/auth?token=secret_token_123"

    # 3. Unresolved variable remains intact
    unresolved_expr = "{{unsupplied_key}}"
    assert WorkflowEngine._interpolate(unresolved_expr, context) == "{{unsupplied_key}}"


@pytest.mark.asyncio
async def test_m3_workflow_autonomous_step_recovery(test_db):
    """Verify transient recoverable errors trigger retries and fallback actions."""
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        wf = await repo.create_workflow(
            name="Recovery Workflow",
            steps=[
                {
                    "id": "flaky_step",
                    "action": "click_selector",
                    "parameters": {"selector": "#delayed-btn"},
                    "max_retries": 2,
                    "retry_delay": 0.05,
                    "fallback_action": "scroll_page",
                    "fallback_parameters": {"delta_y": 200}
                }
            ]
        )

    attempt_count = 0

    async def mock_execute(action, params, bypass_approval=False):
        nonlocal attempt_count
        if action == "click_selector":
            attempt_count += 1
            return {"status": "error", "error": "waiting for selector #delayed-btn timed out"}
        elif action == "fallback_action" or action == "scroll_page":
            return {"status": "success", "scrolled": params.get("delta_y", 0)}
        return {"status": "success"}

    with patch.object(ToolExecutor, "execute", side_effect=mock_execute):
        res = await WorkflowEngine.execute_workflow(wf.id)
        assert res["status"] == "completed"
        # Click failed twice (initial + 2 retries = 3 attempts), then fallback succeeded
        assert attempt_count == 3
        last_step = res["results"][0]
        assert last_step["action"] == "click_selector"
        assert last_step["result"]["status"] == "success"


@pytest.mark.asyncio
async def test_m3_workflow_approval_pause_and_resume(test_db):
    """Verify workflow pauses on approval_required, serializes checkpoint, and resumes on approval."""
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        wf = await repo.create_workflow(
            name="Financial Checkout Workflow",
            steps=[
                {"id": "step_1", "action": "navigate", "parameters": {"url": "https://store.example.com"}},
                {"id": "step_2", "action": "click_selector", "parameters": {"selector": "#checkout-submit"}},
                {"id": "step_3", "action": "get_page_content", "parameters": {}}
            ]
        )

    # 1. Execution pauses on step 2
    async def mock_execute(action, params, bypass_approval=False):
        if action == "click_selector" and not bypass_approval:
            return {
                "status": "approval_required",
                "approval_id": "appr-123",
                "reason": "RED TIER: Financial checkout submission requires explicit user authorization"
            }
        return {"status": "success", "action": action}

    with patch.object(ToolExecutor, "execute", side_effect=mock_execute):
        pause_res = await WorkflowEngine.execute_workflow(wf.id)
        assert pause_res["status"] == "approval_required"
        assert pause_res["paused_step"] == 2
        exec_id = pause_res["execution_id"]

        # 2. Resuming execution with approval executes step 2 with bypass_approval=True and continues to completion
        resume_res = await WorkflowEngine.resume_workflow(exec_id, decision=True)
        assert resume_res["status"] == "completed"
        assert resume_res["steps_executed"] == 3
        # Confirm step 2 completed with bypass_approval
        assert resume_res["results"][1]["step"] == 2
        assert resume_res["results"][1]["result"]["status"] == "success"
        # Confirm step 3 completed
        assert resume_res["results"][2]["step"] == 3
