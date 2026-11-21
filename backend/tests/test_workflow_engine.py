import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from backend.app.workflows.engine import WorkflowEngine
from backend.app.database.engine import init_db, AsyncSessionLocal
from backend.app.database.repository import Repository

@pytest.mark.asyncio
async def test_workflow_repository_crud():
    await init_db()
    
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        wf = await repo.create_workflow(
            name="Test Search Workflow",
            description="Searches a query and extracts text",
            steps=[
                {"action": "navigate", "parameters": {"url": "https://example.com"}},
                {"action": "fill_selector", "parameters": {"selector": "#search", "value": "{{query}}"}}
            ],
            variables={"query": "agentic browser"}
        )
        wf_id = wf.id
        assert wf_id is not None
        assert wf.name == "Test Search Workflow"
        
        all_wfs = await repo.get_workflows()
        assert any(w.id == wf_id for w in all_wfs)
        
        fetched = await repo.get_workflow(wf_id)
        assert fetched is not None
        assert fetched.id == wf_id
        
        # Clean up / delete
        deleted = await repo.delete_workflow(wf_id)
        assert deleted is True
        
        assert await repo.get_workflow(wf_id) is None


@pytest.mark.asyncio
async def test_workflow_engine_interpolation():
    params = {
        "url": "https://example.com/search?q={{query}}",
        "nested": {"key": "{{user_name}}", "static": 123},
        "count": 5
    }
    variables = {
        "query": "deep learning",
        "user_name": "Alice"
    }
    
    interpolated = WorkflowEngine._interpolate(params, variables)
    assert interpolated["url"] == "https://example.com/search?q=deep learning"
    assert interpolated["nested"]["key"] == "Alice"
    assert interpolated["nested"]["static"] == 123
    assert interpolated["count"] == 5


@pytest.mark.asyncio
async def test_workflow_engine_execution_flow():
    await init_db()
    
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        wf = await repo.create_workflow(
            name="Quick Execution Test",
            steps=[
                {"action": "navigate", "parameters": {"url": "https://example.com/page?ref={{site}}"}}
            ],
            variables={"site": "ai"}
        )
        wf_id = wf.id

    with patch("backend.app.tools.executor.ToolExecutor.execute", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = {"status": "ok", "result": "navigated"}
        result = await WorkflowEngine.execute_workflow(wf_id, {"site": "production"})
        
        assert result["status"] == "completed"
        assert result["steps_executed"] == 1
        mock_exec.assert_called_once_with(
            "navigate",
            {"url": "https://example.com/page?ref=production"}
        )

    # Clean up
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        await repo.delete_workflow(wf_id)


@pytest.mark.asyncio
async def test_workflow_export_import():
    await init_db()
    
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        wf = await repo.create_workflow(
            name="Exportable Flow",
            description="Export & Import test",
            steps=[{"action": "navigate", "parameters": {"url": "https://test.com"}}],
            variables={"env": "prod"}
        )
        wf_id = wf.id

    exported = await WorkflowEngine.export_workflow(wf_id)
    assert exported is not None
    assert exported["version"] == "1.0"
    assert exported["name"] == "Exportable Flow"
    assert len(exported["steps"]) == 1

    imported = await WorkflowEngine.import_workflow(exported)
    assert imported["name"] == "Exportable Flow"
    assert imported["step_count"] == 1

    # Clean up
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        await repo.delete_workflow(wf_id)
        await repo.delete_workflow(imported["id"])
