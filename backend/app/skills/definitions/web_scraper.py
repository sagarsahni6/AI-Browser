import os
import csv
import json
from typing import Dict, Any, List
from backend.app.skills.base import BaseSkill, SkillManifest, SkillTool
from backend.app.browser.bridge import bridge


class WebScraperSkill(BaseSkill):
    def __init__(self):
        self.manifest = SkillManifest(
            id="web_scraper",
            name="Deep Web Miner & Scraper",
            description="Advanced DOM data mining, structured table extraction, repeating element scraper, and CSV/JSON export.",
            category="scraping",
            icon="Table",
            enabled=True,
            triggers=[
                "scrape", "extract table", "miner", "extract list", "tabular",
                "csv", "data mining", "gather data", "products", "prices", "table"
            ],
            tools=[
                SkillTool(
                    name="scrape_table_schema",
                    description="Extract structured tables from the active page with automatic column header detection and numeric cleaning.",
                    parameters={
                        "type": "object",
                        "properties": {
                            "selector": {"type": "string", "description": "Optional CSS selector for the table element."},
                            "clean_numbers": {"type": "boolean", "description": "Whether to strip currency symbols and format numbers."}
                        }
                    },
                    risk_tier="green"
                ),
                SkillTool(
                    name="scrape_repeating_cards",
                    description="Scrape repeating cards/items (e.g. products, search results, articles) by container and card selectors.",
                    parameters={
                        "type": "object",
                        "properties": {
                            "card_selector": {"type": "string", "description": "CSS selector matching each repeating card/item."},
                            "title_selector": {"type": "string", "description": "Relative selector for card title/name."},
                            "price_or_meta_selector": {"type": "string", "description": "Relative selector for price, date, or metadata."},
                            "link_selector": {"type": "string", "description": "Relative selector for item link href."},
                            "limit": {"type": "integer", "description": "Maximum number of items to extract (default: 30)."}
                        },
                        "required": ["card_selector"]
                    },
                    risk_tier="green"
                ),
                SkillTool(
                    name="paginate_and_mine",
                    description="Automate clicking 'Next' / pagination to mine data across multiple pages.",
                    parameters={
                        "type": "object",
                        "properties": {
                            "card_or_table_selector": {"type": "string", "description": "Selector for the target data elements."},
                            "next_button_selector": {"type": "string", "description": "Selector for the 'Next' page button or link."},
                            "max_pages": {"type": "integer", "description": "Max pages to paginate through (default: 3)."}
                        },
                        "required": ["card_or_table_selector", "next_button_selector"]
                    },
                    risk_tier="yellow"
                ),
                SkillTool(
                    name="export_dataset_file",
                    description="Save mined datasets directly to disk as CSV or JSON in the local data directory.",
                    parameters={
                        "type": "object",
                        "properties": {
                            "data": {"type": "array", "description": "List of dictionary records to export."},
                            "format": {"type": "string", "enum": ["csv", "json"], "description": "Export file format."},
                            "filename": {"type": "string", "description": "Custom file name."}
                        },
                        "required": ["data", "format"]
                    },
                    risk_tier="yellow"
                )
            ]
        )

    def get_system_prompt_snippet(self) -> str:
        return (
            "When extracting web data, use `scrape_table_schema` for HTML tables or `scrape_repeating_cards` "
            "for e-commerce product grids, news feeds, and search listings. If records span multiple pages, "
            "use `paginate_and_mine`. Always offer to save clean datasets via `export_dataset_file`."
        )

    async def execute_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if tool_name == "scrape_table_schema":
            selector = params.get("selector")
            script = f"""
            (() => {{
                const target = {f'document.querySelector("{selector}")' if selector else 'document.querySelector("table")'};
                if (!target) return {{ found: false, error: "No matching table found" }};
                const headers = Array.from(target.querySelectorAll('th')).map(th => th.innerText.trim());
                const rows = Array.from(target.querySelectorAll('tbody tr, tr')).filter(r => r.querySelectorAll('td').length > 0).map(tr => {{
                    return Array.from(tr.querySelectorAll('td')).map(td => td.innerText.trim());
                }});
                return {{
                    found: true,
                    headers: headers.length > 0 ? headers : rows[0] || [],
                    rows: headers.length > 0 ? rows.slice(0, 50) : rows.slice(1, 51),
                    total_rows: rows.length
                }};
            }})()
            """
            res = await bridge.call("browser.evaluate_js", {"script": script})
            return {"status": "success", "data": res}

        elif tool_name == "scrape_repeating_cards":
            card_sel = params.get("card_selector", "")
            title_sel = params.get("title_selector", "h1, h2, h3, h4, .title, a")
            meta_sel = params.get("price_or_meta_selector", ".price, .meta, span, p")
            link_sel = params.get("link_selector", "a")
            limit = int(params.get("limit", 30))

            script = f"""
            (() => {{
                const cards = Array.from(document.querySelectorAll("{card_sel}")).slice(0, {limit});
                return cards.map(c => {{
                    const titleEl = c.querySelector("{title_sel}");
                    const metaEl = c.querySelector("{meta_sel}");
                    const linkEl = c.querySelector("{link_sel}");
                    return {{
                        title: titleEl ? titleEl.innerText.trim() : "",
                        meta: metaEl ? metaEl.innerText.trim() : "",
                        link: linkEl ? linkEl.href : "",
                        text_snippet: c.innerText.trim().slice(0, 150)
                    }};
                }}).filter(item => item.title || item.text_snippet);
            }})()
            """
            items = await bridge.call("browser.evaluate_js", {"script": script})
            return {"status": "success", "count": len(items or []), "items": items or []}

        elif tool_name == "paginate_and_mine":
            card_sel = params.get("card_or_table_selector", "")
            next_sel = params.get("next_button_selector", "")
            max_pages = min(int(params.get("max_pages", 3)), 5)

            accumulated_items: List[Any] = []
            pages_crawled = 0

            for p in range(max_pages):
                pages_crawled += 1
                extract_script = f"""
                (() => {{
                    const els = Array.from(document.querySelectorAll("{card_sel}")).slice(0, 20);
                    return els.map(e => e.innerText.trim()).filter(Boolean);
                }})()
                """
                page_data = await bridge.call("browser.evaluate_js", {"script": extract_script})
                if page_data:
                    accumulated_items.extend(page_data)

                # Check and click next button
                if p < max_pages - 1:
                    has_next = await bridge.call("browser.click_selector", {"selector": next_sel})
                    if not has_next or (isinstance(has_next, dict) and has_next.get("error")):
                        break
                    import asyncio
                    await asyncio.sleep(1.5)

            return {
                "status": "success",
                "pages_crawled": pages_crawled,
                "total_items_extracted": len(accumulated_items),
                "items": accumulated_items[:60]
            }

        elif tool_name == "export_dataset_file":
            data = params.get("data", [])
            fmt = params.get("format", "json").lower()
            filename = params.get("filename") or f"mined_data_{int(os.times().elapsed)}.{fmt}"

            out_dir = os.path.join(os.getcwd(), "data")
            os.makedirs(out_dir, exist_ok=True)
            filepath = os.path.join(out_dir, filename)

            if fmt == "csv":
                if data and isinstance(data[0], dict):
                    headers = list(data[0].keys())
                    with open(filepath, "w", newline="", encoding="utf-8") as f:
                        writer = csv.DictWriter(f, fieldnames=headers)
                        writer.writeheader()
                        writer.writerows(data)
                elif data and isinstance(data[0], list):
                    with open(filepath, "w", newline="", encoding="utf-8") as f:
                        writer = csv.writer(f)
                        writer.writerows(data)
            else:
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

            return {
                "status": "success",
                "filepath": filepath,
                "format": fmt,
                "records_count": len(data)
            }

        return {"status": "error", "message": f"Unknown tool '{tool_name}'"}
