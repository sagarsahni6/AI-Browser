import pytest
import os
from httpx import AsyncClient, ASGITransport
from backend.app.main import app
from backend.app.tools.executor import ToolExecutor
from backend.app.security.approval import ApprovalManager

@pytest.mark.asyncio
async def test_tool_executor_csv_export():
    res = await ToolExecutor.execute("export_csv", {
        "filename": "test_export.csv",
        "headers": ["Rank", "Topic", "Confidence"],
        "rows": [["1", "Quantum Teleportation", "0.99"], ["2", "Qubits", "0.95"]]
    })
    assert res["status"] == "success"
    assert "test_export.csv" in res["exported_file"]
    assert os.path.exists(res["exported_file"])

    # Clean up test export
    if os.path.exists(res["exported_file"]):
        os.remove(res["exported_file"])

@pytest.mark.asyncio
async def test_approval_policy():
    # Sensitive password input
    req_appr, reason = ApprovalManager.evaluate_tool_call("fill_input", {"x": 100, "y": 200, "text": "secret password"})
    assert req_appr is True
    assert "sensitive" in reason.lower()

    # Read-only tool
    req_appr2, _ = ApprovalManager.evaluate_tool_call("get_page_content", {})
    assert req_appr2 is False

@pytest.mark.asyncio
async def test_search_and_citations():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/v1/search", json={
            "query": "Quantum Computing",
            "generate_summary": True
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["query"] == "Quantum Computing"
        assert len(data["results"]) >= 1
        assert data["cited_summary"] is not None
