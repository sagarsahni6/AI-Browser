import logging
import json
import csv
import io
import os
import re
import time
import hashlib
import asyncio
from typing import Dict, Any, List, Optional
from backend.app.browser.bridge import bridge
from backend.app.tools.executor import ToolExecutor

logger = logging.getLogger("data_agent")

class DataAgent:
    """
    Specialist agent for data extraction, multi-page pagination scraping,
    JSON/CSV/XLSX exporting, and structured dataset formatting with formula injection defense.
    """

    @staticmethod
    def sanitize_cell(val: Any) -> Any:
        """
        Sanitize formula injection triggers (=, +, -, @, \\t, \\r) by prepending a single quote.
        Neutralizes execution when loaded into spreadsheet applications (Excel, LibreOffice, Sheets).
        """
        if isinstance(val, str) and val.startswith(("=", "+", "-", "@", "\t", "\r")):
            return f"'{val}"
        return val

    @staticmethod
    def infer_column_types(rows: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        Infer column data types across rows: currency, number, date, url, text.
        """
        if not rows:
            return {}
        keys = {k for r in rows for k in r.keys() if k != "page"}
        schema = {}
        for k in keys:
            values = [str(r[k]).strip() for r in rows if k in r and r[k] is not None and str(r[k]).strip()]
            if not values:
                schema[k] = "text"
                continue
            if all(re.match(r"^[\$€£¥]\s*[\d,]+(\.\d+)?$", v) or re.match(r"^[\d,]+(\.\d+)?\s*[\$€£¥]$", v) for v in values):
                schema[k] = "currency"
            elif all(re.match(r"^https?://", v, re.IGNORECASE) for v in values):
                schema[k] = "url"
            elif all(re.match(r"^\d{4}-\d{2}-\d{2}", v) or re.match(r"^\d{1,2}/\d{1,2}/\d{2,4}", v) for v in values):
                schema[k] = "date"
            elif all(re.match(r"^-?\d+(\.\d+)?$", v.replace(",", "")) for v in values):
                schema[k] = "number"
            else:
                schema[k] = "text"
        return schema

    @classmethod
    async def extract_table_data(
        cls,
        selector: Optional[str] = None,
        pagination_next_selector: Optional[str] = None,
        max_pages: int = 1
    ) -> Dict[str, Any]:
        """
        Extract structured table/list data from the active webpage with de-duplication,
        schema inference, DOM client-side extraction, and pagination tracking.
        """
        pages_limit = min(max(int(max_pages or 1), 1), 3)

        all_rows: List[Dict[str, Any]] = []
        seen_hashes = set()
        duplicate_count = 0
        malformed_rows = 0
        pages_scraped = 0

        # JavaScript extraction script for DOM-native extraction
        selector_json = json.dumps(selector) if selector else "null"
        js_extract_script = f"""
        (() => {{
          try {{
            const customSelector = {selector_json};
            const results = [];
            const clean = (s) => (s || '').replace(/\\s+/g, ' ').trim();

            // 1. Try custom selector if provided
            if (customSelector) {{
              try {{
                const container = document.querySelector(customSelector);
                if (container) {{
                  const table = container.tagName === 'TABLE' ? container : container.querySelector('table');
                  if (table) {{
                    const headers = Array.from(table.querySelectorAll('th')).map(th => clean(th.innerText));
                    const rows = Array.from(table.querySelectorAll('tbody tr, tr')).filter(r => !r.querySelector('th'));
                    rows.forEach((tr, rIdx) => {{
                      const cells = Array.from(tr.querySelectorAll('td')).map(td => clean(td.innerText));
                      if (cells.length > 0) {{
                        const rowObj = {{}};
                        cells.forEach((c, cIdx) => {{
                          const headerName = headers[cIdx] || ('col_' + (cIdx + 1));
                          rowObj[headerName] = c;
                        }});
                        results.push(rowObj);
                      }}
                    }});
                  }}
                  if (results.length === 0) {{
                    const items = Array.from(container.querySelectorAll('li, [class*="item"], [class*="card"], [class*="row"]'));
                    items.forEach((item, idx) => {{
                      const heading = item.querySelector('h1, h2, h3, h4, a, [class*="title"]');
                      const text = clean(item.innerText);
                      if (text && text.length > 2) {{
                        results.push({{
                          index: idx + 1,
                          title: heading ? clean(heading.innerText) : text.split('\\n')[0].slice(0, 100),
                          content: text.slice(0, 300)
                        }});
                      }}
                    }});
                  }}
                }}
              }} catch (e) {{}}
            }}

            // 2. Auto-detect <table> elements on page
            if (results.length === 0) {{
              try {{
                const tables = Array.from(document.querySelectorAll('table'));
                for (const table of tables) {{
                  const headers = Array.from(table.querySelectorAll('th')).map(th => clean(th.innerText));
                  const rows = Array.from(table.querySelectorAll('tbody tr, tr')).filter(r => !r.querySelector('th'));
                  if (rows.length >= 2) {{
                    rows.slice(0, 50).forEach((tr) => {{
                      const cells = Array.from(tr.querySelectorAll('td')).map(td => clean(td.innerText));
                      if (cells.length > 0) {{
                        const rowObj = {{}};
                        cells.forEach((c, cIdx) => {{
                          const headerName = headers[cIdx] || ('col_' + (cIdx + 1));
                          rowObj[headerName] = c;
                        }});
                        results.push(rowObj);
                      }}
                    }});
                    if (results.length > 0) break;
                  }}
                }}
              }} catch (e) {{}}
            }}

            // 3. Auto-detect structured ranked list items (IMDb, listicles, ol/ul)
            if (results.length === 0) {{
              try {{
                const selectors = [
                  '.ipc-metadata-list li',
                  '.lister-list .lister-item',
                  '[data-testid="list-item"]',
                  'ol > li',
                  'ul[class*="list"] > li',
                  '[class*="movie"]',
                  '[class*="ranking"]'
                ];
                for (const sel of selectors) {{
                  const items = Array.from(document.querySelectorAll(sel));
                  if (items.length >= 2) {{
                    items.slice(0, 50).forEach((item, idx) => {{
                      const titleEl = item.querySelector('h3, h2, h4, a[href*="/title/"], [class*="title"]');
                      const text = clean(item.innerText);
                      if (text) {{
                        results.push({{
                          rank: idx + 1,
                          title: titleEl ? clean(titleEl.innerText) : text.split('\\n')[0].slice(0, 100),
                          content: text.slice(0, 300)
                        }});
                      }}
                    }});
                    if (results.length > 0) break;
                  }}
                }}
              }} catch (e) {{}}
            }}

            // 4. Auto-detect numbered headings / items (e.g. 1. Title, 2. Title)
            if (results.length === 0) {{
              try {{
                const headings = Array.from(document.querySelectorAll('h1, h2, h3, h4, p, li'));
                const numbered = headings.filter(el => /^\\s*\\d+[.)]\\s+/.test(clean(el.innerText)));
                if (numbered.length >= 2) {{
                  numbered.slice(0, 50).forEach((el, idx) => {{
                    const text = clean(el.innerText);
                    results.push({{
                      rank: idx + 1,
                      title: text,
                      content: text
                    }});
                  }});
                }}
              }} catch (e) {{}}
            }}

            return results.slice(0, 50);
          }} catch (outer) {{
            return [];
          }}
        }})()
        """

        for current_page in range(1, pages_limit + 1):
            pages_scraped += 1
            page_rows: List[Dict[str, Any]] = []

            # Step A: Attempt client-side DOM evaluation via evaluate_js
            try:
                js_res = await asyncio.wait_for(
                    bridge.call("browser.evaluate_js", {"script": js_extract_script}),
                    timeout=5.0
                )
                if isinstance(js_res, list) and len(js_res) > 0:
                    for item in js_res:
                        if isinstance(item, dict):
                            item["page"] = current_page
                            page_rows.append(item)
            except Exception as e:
                logger.warning(f"Client-side DOM evaluation fallback: {e}")

            # Step B: Fallback to get_page_content text parsing if DOM eval returned no rows
            if not page_rows:
                try:
                    dom_res = await asyncio.wait_for(
                        ToolExecutor.execute("get_page_content", {}),
                        timeout=5.0
                    )
                    text_content = (
                        dom_res.get("text")
                        or dom_res.get("visible_text_snippet")
                        or (dom_res.get("result", {}).get("visible_text_snippet", "") if isinstance(dom_res.get("result"), dict) else "")
                        or ""
                    )

                    # Regex for numbered list items (e.g., '1. Gol Maal', '2. Black Friday')
                    numbered_matches = re.findall(r'^\s*(\d+)[\.\)]\s+(.+)', text_content, re.MULTILINE)
                    if numbered_matches:
                        for rank_str, title_str in numbered_matches[:50]:
                            page_rows.append({
                                "rank": int(rank_str),
                                "title": title_str.strip(),
                                "content": title_str.strip(),
                                "page": current_page
                            })
                    else:
                        lines = [line.strip() for line in text_content.split("\n") if len(line.strip()) > 1]
                        for idx, line in enumerate(lines[:50]):
                            if "|" in line:
                                cols = [c.strip() for c in line.split("|") if c.strip()]
                                if len(cols) >= 2:
                                    row = {f"col_{i+1}": col for i, col in enumerate(cols)}
                                    row["page"] = current_page
                                    page_rows.append(row)
                                else:
                                    malformed_rows += 1
                            elif ":" in line:
                                parts = line.split(":", 1)
                                k, v = parts[0].strip(), parts[1].strip()
                                if k:
                                    page_rows.append({"key": k, "value": v, "page": current_page})
                                else:
                                    malformed_rows += 1
                            else:
                                page_rows.append({"index": len(page_rows) + 1, "content": line, "page": current_page})
                except Exception as e:
                    logger.warning(f"get_page_content text parsing failed: {e}")

            # Step C: De-duplicate rows across pages
            for r in page_rows:
                content_for_hash = {k: v for k, v in r.items() if k != "page"}
                r_hash = hashlib.sha256(json.dumps(content_for_hash, sort_keys=True).encode()).hexdigest()
                if r_hash in seen_hashes:
                    duplicate_count += 1
                    continue
                seen_hashes.add(r_hash)
                all_rows.append(r)

            # Step D: Pagination next selector
            if pagination_next_selector and current_page < pages_limit:
                try:
                    click_res = await asyncio.wait_for(
                        ToolExecutor.execute("click_selector", {"selector": pagination_next_selector}),
                        timeout=4.0
                    )
                    res_obj = click_res.get("result", {})
                    if click_res.get("status") != "success" or (isinstance(res_obj, dict) and not res_obj.get("success", True)):
                        break
                    await asyncio.sleep(0.5)
                except Exception:
                    break

        schema = cls.infer_column_types(all_rows)

        return {
            "status": "ok",
            "pages_scraped": pages_scraped,
            "total_records": len(all_rows),
            "total_rows": len(all_rows),
            "row_count": len(all_rows),
            "duplicate_count": duplicate_count,
            "malformed_rows": malformed_rows,
            "schema": schema,
            "rows": all_rows,
            "data": all_rows
        }

    @classmethod
    def export_data(
        cls,
        data: List[Dict[str, Any]],
        format: str = "json",
        filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Export a list of records to CSV, JSON, or XLSX format with formula injection defense.
        """
        fmt = format.lower().strip()
        timestamp = int(time.time())
        extension = fmt if fmt in ("json", "csv", "xlsx") else "json"
        default_name = f"export_{timestamp}.{extension}"
        target_filename = filename or default_name

        if fmt == "csv":
            if not data:
                csv_content = ""
            else:
                ordered_keys = []
                for row in data:
                    for k in row.keys():
                        if k not in ordered_keys:
                            ordered_keys.append(k)

                output = io.StringIO()
                writer = csv.DictWriter(output, fieldnames=ordered_keys, lineterminator="\r\n")
                writer.writeheader()
                for row in data:
                    sanitized_row = {k: cls.sanitize_cell(row.get(k, "")) for k in ordered_keys}
                    writer.writerow(sanitized_row)
                csv_content = output.getvalue()

            return {
                "status": "ok",
                "format": "csv",
                "filename": target_filename,
                "row_count": len(data),
                "data": csv_content
            }
        elif fmt == "xlsx":
            try:
                from openpyxl import Workbook
                wb = Workbook()
                ws = wb.active
                ws.title = "Extracted Data"
                if data:
                    ordered_keys = []
                    for row in data:
                        for k in row.keys():
                            if k not in ordered_keys:
                                ordered_keys.append(k)
                    ws.append(ordered_keys)
                    for row in data:
                        ws.append([cls.sanitize_cell(row.get(k, "")) for k in ordered_keys])

                out_dir = os.path.join(os.getcwd(), "data")
                os.makedirs(out_dir, exist_ok=True)
                filepath = os.path.join(out_dir, target_filename)
                wb.save(filepath)

                return {
                    "status": "ok",
                    "format": "xlsx",
                    "filename": target_filename,
                    "row_count": len(data),
                    "file_path": filepath,
                    "data": filepath
                }
            except ImportError:
                logger.warning("openpyxl not available, falling back to csv export")
                return cls.export_data(data, format="csv", filename=target_filename.replace(".xlsx", ".csv"))
        else:
            json_content = json.dumps(data, indent=2, ensure_ascii=False)
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
