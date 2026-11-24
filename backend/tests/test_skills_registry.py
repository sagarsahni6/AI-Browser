import os
import pytest
from backend.app.skills.registry import skill_registry
from backend.app.security.approval import ApprovalManager
from backend.app.tools.executor import ToolExecutor


@pytest.mark.asyncio
async def test_skills_auto_discovery():
    manifests = skill_registry.list_manifests()
    assert len(manifests) == 7

    skill_ids = {m["id"] for m in manifests}
    expected_ids = {
        "web_scraper",
        "form_automation",
        "session_inspector",
        "asset_downloader",
        "multi_tab_researcher",
        "financial_analyst",
        "dev_seo_auditor"
    }
    assert expected_ids.issubset(skill_ids)

    # Check manifest properties
    for m in manifests:
        assert m["id"]
        assert m["name"]
        assert m["description"]
        assert m["category"]
        assert m["icon"]
        assert isinstance(m["triggers"], list)
        assert len(m["tools"]) >= 2


@pytest.mark.asyncio
async def test_skills_toggle():
    skill_id = "dev_seo_auditor"
    # Disable skill
    new_state = skill_registry.toggle_skill(skill_id, False)
    assert new_state is False

    manifest = skill_registry.get_skill(skill_id).manifest
    assert manifest.enabled is False

    # Active tools should exclude this skill's tools
    active_tools = skill_registry.get_all_active_tools()
    tool_names = [t["function"]["name"] for t in active_tools]
    assert "audit_seo_metadata" not in tool_names

    # Re-enable skill
    re_enabled = skill_registry.toggle_skill(skill_id, True)
    assert re_enabled is True
    active_tools_re = skill_registry.get_all_active_tools()
    tool_names_re = [t["function"]["name"] for t in active_tools_re]
    assert "audit_seo_metadata" in tool_names_re


@pytest.mark.asyncio
async def test_dynamic_intent_matching():
    # Slash command matching
    matched_slash = skill_registry.match_skills("/skill:web_scraper Extract this table")
    assert any(s.manifest.id == "web_scraper" for s in matched_slash)

    # Trigger keyword matching
    matched_seo = skill_registry.match_skills("Please check broken links and audit seo tags on this page")
    assert any(s.manifest.id == "dev_seo_auditor" for s in matched_seo)

    # System prompt generation
    prompt_snippet = skill_registry.get_active_system_prompts("Please check broken links and audit seo tags")
    assert "SEO" in prompt_snippet or "DEVELOPER" in prompt_snippet


@pytest.mark.asyncio
async def test_skills_security_tiers():
    # Red tier tool: clear_site_storage
    req_appr_red, reason_red = ApprovalManager.evaluate_tool_call("clear_site_storage", {})
    assert req_appr_red is True
    assert "RED TIER" in reason_red

    # Red tier tool: submit_form
    req_appr_form, reason_form = ApprovalManager.evaluate_tool_call("submit_form", {})
    assert req_appr_form is True
    assert "RED TIER" in reason_form

    # Green tier tool: scrape_table_schema
    req_appr_green, reason_green = ApprovalManager.evaluate_tool_call("scrape_table_schema", {})
    assert req_appr_green is False
    assert "GREEN TIER" in reason_green

    # Yellow tier tool: download_file_asset
    req_appr_yellow, reason_yellow = ApprovalManager.evaluate_tool_call("download_file_asset", {"url": "https://example.com/data.pdf"})
    assert req_appr_yellow is False
    assert "YELLOW TIER" in reason_yellow


@pytest.mark.asyncio
async def test_skill_tools_execution_via_executor():
    # Execute export_dataset_file tool via ToolExecutor
    test_data = [
        {"item": "Laptop A", "price": "$1200", "rating": "4.8"},
        {"item": "Laptop B", "price": "$950", "rating": "4.5"}
    ]
    res = await ToolExecutor.execute("export_dataset_file", {
        "data": test_data,
        "format": "json",
        "filename": "test_skills_export.json"
    })

    assert res["status"] == "success"
    assert res["records_count"] == 2
    assert os.path.exists(res["filepath"])

    # Clean up
    if os.path.exists(res["filepath"]):
        os.remove(res["filepath"])
