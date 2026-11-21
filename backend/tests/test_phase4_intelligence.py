import pytest
import io
import os
import csv
import json
from unittest.mock import AsyncMock, patch
from pypdf import PdfWriter
from backend.app.research.service import ResearchService
from backend.app.documents.pdf_service import PDFService
from backend.app.agents.data_agent import DataAgent
from backend.app.tools.executor import ToolExecutor
from backend.app.database.engine import init_db, AsyncSessionLocal
from backend.app.database.repository import Repository

def create_sample_pdf(tmp_path) -> str:
    """Helper to create a small 2-page PDF file with known content."""
    pdf_path = str(tmp_path / "sample_report.pdf")
    writer = PdfWriter()
    
    # Add page 1
    page1 = writer.add_blank_page(width=612, height=792)
    # Note: pypdf blank page doesn't have text streams by default, but we can write synthetic content or test reader
    with open(pdf_path, "wb") as f:
        writer.write(f)
    return pdf_path

@pytest.mark.asyncio
async def test_deep_research_synthesis():
    await init_db()
    
    with patch("backend.app.tools.executor.ToolExecutor.execute", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = {
            "status": "ok",
            "results": [
                {
                    "title": "Agentic AI Overview",
                    "url": "https://example.com/agentic-ai",
                    "snippet": "Agentic AI browsers perform autonomous web automation, self-correct on step failure, and preserve user privacy."
                },
                {
                    "title": "State of AI Browsing 2026",
                    "url": "https://example.com/state-of-ai",
                    "snippet": "Modern AI browsers combine native CDP page inspection with hybrid workflow engines and cooperative human checkpoints."
                }
            ]
        }
        
        report = await ResearchService.synthesize(
            topic="Agentic AI Browsers",
            depth="quick"
        )
        
        assert report["status"] == "completed"
        assert report["topic"] == "Agentic AI Browsers"
        assert report["sources_count"] >= 2
        assert "Executive Summary" in report["content_markdown"]
        assert "Comparative Matrix" in report["content_markdown"]
        assert "Source Index" in report["content_markdown"]
        assert report["report_id"] is not None

        # Verify DB persistence
        async with AsyncSessionLocal() as session:
            repo = Repository(session)
            db_report = await repo.get_research_report(report["report_id"])
            assert db_report is not None
            assert db_report.topic == "Agentic AI Browsers"

            # Clean up
            await repo.delete_research_report(report["report_id"])


@pytest.mark.asyncio
async def test_pdf_service_mocked():
    # Test PDFService logic with simulated pages
    with patch("backend.app.documents.pdf_service.PDFService.read_pdf", new_callable=AsyncMock) as mock_read:
        mock_read.return_value = {
            "status": "ok",
            "title": "AI Browser Whitepaper",
            "total_pages": 3,
            "pages": [
                {"page_number": 1, "text": "AI Browser architecture combines native CDP automation with multi-agent planning."},
                {"page_number": 2, "text": "Safety protocols require human approval before any sensitive form submission."},
                {"page_number": 3, "text": "Performance benchmarks demonstrate 98 percent selector resolution reliability."}
            ]
        }
        
        summary = await PDFService.summarize_pdf("dummy.pdf")
        assert summary["status"] == "ok"
        assert summary["total_pages"] == 3
        assert "[Page 1]" in summary["summary"]
        assert "[Page 2]" in summary["summary"]

        search_res = await PDFService.search_pdf("dummy.pdf", query="safety")
        assert search_res["status"] == "ok"
        assert search_res["matches_count"] == 1
        assert search_res["matches"][0]["page_number"] == 2


def test_data_agent_export():
    sample_data = [
        {"product": "Laptop", "price": 1200, "currency": "USD"},
        {"product": "Mouse", "price": 45, "currency": "USD"},
        {"product": "Monitor", "price": 300, "currency": "USD"}
    ]
    
    # JSON Export
    json_res = DataAgent.export_data(sample_data, format="json", filename="items.json")
    assert json_res["status"] == "ok"
    assert json_res["format"] == "json"
    assert json_res["row_count"] == 3
    parsed = json.loads(json_res["data"])
    assert len(parsed) == 3
    assert parsed[0]["product"] == "Laptop"

    # CSV Export
    csv_res = DataAgent.export_data(sample_data, format="csv", filename="items.csv")
    assert csv_res["status"] == "ok"
    assert csv_res["format"] == "csv"
    assert "product" in csv_res["data"]
    assert "price" in csv_res["data"]
    assert "Laptop" in csv_res["data"]


@pytest.mark.asyncio
async def test_data_agent_table_extraction():
    # Simulate page content with pipe-separated tabular rows
    with patch("backend.app.tools.executor.ToolExecutor.execute", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = {
            "status": "ok",
            "title": "Pricing Table",
            "text": "Plan | Monthly | Storage\nBasic | $10 | 50GB\nPro | $25 | 200GB\nEnterprise | $99 | 1TB"
        }
        
        extracted = await DataAgent.extract_table_data(max_pages=1)
        assert extracted["status"] == "ok"
        assert extracted["pages_scraped"] == 1
        assert extracted["total_rows"] >= 3


@pytest.mark.asyncio
async def test_phase4_tool_executor_dispatch():
    # Test ToolExecutor executes 'export_data' cleanly
    data = [{"name": "Item A", "score": 98}]
    res = await ToolExecutor.execute("export_data", {"data": data, "format": "json"})
    assert res["status"] == "ok"
    assert res["row_count"] == 1
