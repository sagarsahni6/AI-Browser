import logging
import json
import csv
import io
import os
import time
from typing import Dict, Any, List, Optional
from backend.app.tools.executor import ToolExecutor

logger = logging.getLogger("data_agent")

class DataAgent:
    """
    Specialist agent for data extraction, multi-page pagination scraping,
    JSON/CSV exporting, and structured dataset formatting.
    """

    @classmethod
    async def extract_table_data(
        cls,
        selector: Optional[str] = None,
        pagination_next_selector: Optional[str] = None,
        max_pages: int = 1
    ) -> Dict[str, Any]:
        """
        Extract structured table/list data from the active webpage.
        If pagination_next_selector is given, clicks next up to max_pages and collects all rows.
        """
        all_rows: List[Dict[str, Any]] = []
        pages_scraped = 0

        for current_page in range(1, max_pages + 1):
            pages_scraped += 1
            # 1. Inspect DOM via get_page_content
            dom_res = await ToolExecutor.execute("get_page_content", {})
            if dom_res.get("status") != "ok":
                break

            text_content = dom_res.get("text", "")
            url = dom_res.get("url", "")
            title = dom_res.get("title", "")

            # Heuristic tabular extraction: extract structured lines or key-values
            lines = [line.strip() for line in text_content.split("\n") if len(line.strip()) > 3]
            page_rows = []
            
            for idx, line in enumerate(lines[:30]):
                if "|" in line:
                    cols = [c.strip() for c in line.split("|") if c.strip()]
                    if len(cols) >= 2:
                        page_rows.append({f"col_{i+1}": col for i, col in enumerate(cols)})
                elif ":" in line:
                    k, v = line.split(":", 1)
                    page_rows.append({"key": k.strip(), "value": v.strip(), "page": current_page})
                else:
                    page_rows.append({"index": len(page_rows) + 1, "content": line, "page": current_page})

            all_rows.extend(page_rows)

            # If pagination next selector is provided and not on last page, click it
            if pagination_next_selector and current_page < max_pages:
                click_res = await ToolExecutor.execute(
                    "click_selector",
                    {"selector": pagination_next_selector}
                )
                if click_res.get("status") == "error":
                    break
                await ToolExecutor.execute("sleep", {"seconds": 1.0})

        return {
            "status": "ok",
            "pages_scraped": pages_scraped,
            "total_rows": len(all_rows),
            "rows": all_rows
        }

    @classmethod
    def export_data(
        cls,
        data: List[Dict[str, Any]],
        format: str = "json",
        filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Export a list of records to CSV or JSON format.
        """
        fmt = format.lower().strip()
        timestamp = int(time.time())
        default_name = f"export_{timestamp}.{fmt if fmt in ('json', 'csv') else 'json'}"
        target_filename = filename or default_name

        if fmt == "csv":
            if not data:
                csv_content = ""
            else:
                fieldnames = list({k for row in data for k in row.keys()})
                output = io.StringIO()
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()
                for row in data:
                    writer.writerow(row)
                csv_content = output.getvalue()

            return {
                "status": "ok",
                "format": "csv",
                "filename": target_filename,
                "row_count": len(data),
                "data": csv_content
            }
        else:
            json_content = json.dumps(data, indent=2)
            return {
                "status": "ok",
                "format": "json",
                "filename": target_filename,
                "row_count": len(data),
                "data": json_content
            }

    @classmethod
    async def execute_step(cls, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch execution for data agent actions."""
        logger.info(f"DataAgent executing action '{action}'")
        try:
            if action == "extract_table_data":
                return await cls.extract_table_data(
                    selector=parameters.get("selector"),
                    pagination_next_selector=parameters.get("pagination_next_selector"),
                    max_pages=parameters.get("max_pages", 1)
                )
            elif action == "export_data":
                return cls.export_data(
                    data=parameters.get("data", []),
                    format=parameters.get("format", "json"),
                    filename=parameters.get("filename")
                )
            else:
                return await ToolExecutor.execute(action, parameters)
        except Exception as e:
            logger.error(f"DataAgent step failed: {e}")
            return {"status": "error", "error": str(e)}
