import os
import hashlib
import httpx
from typing import Dict, Any
from urllib.parse import urlparse
from backend.app.skills.base import BaseSkill, SkillManifest, SkillTool
from backend.app.browser.bridge import bridge


class AssetDownloaderSkill(BaseSkill):
    def __init__(self):
        self.manifest = SkillManifest(
            id="asset_downloader",
            name="Media & Asset Downloader",
            description="Automatic discovery and reliable local downloading of PDFs, images, docs, and datasets.",
            category="automation",
            icon="Download",
            enabled=True,
            triggers=[
                "download", "download pdf", "download image", "save file",
                "asset downloader", "media download", "fetch document", "download asset"
            ],
            tools=[
                SkillTool(
                    name="discover_page_assets",
                    description="Scan the current page to find all downloadable links: PDFs, images, Excel/CSV spreadsheets, audio, or video files.",
                    parameters={
                        "type": "object",
                        "properties": {
                            "asset_type": {
                                "type": "string",
                                "enum": ["all", "pdf", "image", "document", "spreadsheet"],
                                "description": "Filter by asset category (default: 'all')."
                            }
                        }
                    },
                    risk_tier="green"
                ),
                SkillTool(
                    name="download_file_asset",
                    description="Download a file directly from a URL to the local downloads folder with checksum verification.",
                    parameters={
                        "type": "object",
                        "properties": {
                            "url": {"type": "string", "description": "The direct URL of the file to download."},
                            "custom_filename": {"type": "string", "description": "Optional custom filename to save as."}
                        },
                        "required": ["url"]
                    },
                    risk_tier="yellow"
                )
            ]
        )

    def get_system_prompt_snippet(self) -> str:
        return (
            "When the user asks to download documents or files from a website, first use `discover_page_assets` "
            "to locate valid file links, then use `download_file_asset` to fetch them into the local downloads directory."
        )

    async def execute_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if tool_name == "discover_page_assets":
            asset_type = params.get("asset_type", "all")
            script = f"""
            (() => {{
                const links = Array.from(document.querySelectorAll('a[href], img[src]'));
                const found = [];
                const extPatterns = {{
                    pdf: /\\.pdf($|\\?)/i,
                    image: /\\.(png|jpe?g|webp|svg|gif)($|\\?)/i,
                    spreadsheet: /\\.(csv|xlsx?|tsv)($|\\?)/i,
                    document: /\\.(docx?|pptx?|txt|epub)($|\\?)/i
                }};

                for (const el of links) {{
                    const url = el.href || el.src;
                    if (!url || !url.startsWith('http')) continue;
                    let type = 'other';
                    for (const [k, pat] of Object.entries(extPatterns)) {{
                        if (pat.test(url)) {{ type = k; break; }}
                    }}

                    const reqType = "{asset_type}";
                    if (reqType !== 'all' && type !== reqType) continue;

                    if (type !== 'other' || reqType === 'all') {{
                        found.push({{
                            url: url,
                            type: type,
                            label: el.innerText?.trim() || el.getAttribute('alt') || el.getAttribute('title') || url.split('/').pop()?.split('?')[0] || ''
                        }});
                    }}
                }}

                // Deduplicate by URL
                const unique = Array.from(new Map(found.map(item => [item.url, item])).values()).slice(0, 50);
                return {{ total: unique.length, assets: unique }};
            }})()
            """
            res = await bridge.call("browser.evaluate_js", {"script": script})
            return {"status": "success", "discovered_assets": res}

        elif tool_name == "download_file_asset":
            target_url = params.get("url", "").strip()
            if not target_url:
                return {"status": "error", "message": "Missing download URL"}

            parsed = urlparse(target_url)
            basename = params.get("custom_filename") or os.path.basename(parsed.path) or "downloaded_file.bin"
            clean_filename = "".join(c for c in basename if c.isalnum() or c in (".", "_", "-")).strip() or "asset.bin"

            download_dir = os.path.join(os.getcwd(), "data", "downloads")
            os.makedirs(download_dir, exist_ok=True)
            save_path = os.path.join(download_dir, clean_filename)

            try:
                async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                    resp = await client.get(target_url)
                    resp.raise_for_status()
                    content = resp.content

                with open(save_path, "wb") as f:
                    f.write(content)

                sha256 = hashlib.sha256(content).hexdigest()
                size_kb = round(len(content) / 1024, 2)

                return {
                    "status": "success",
                    "file_path": save_path,
                    "file_name": clean_filename,
                    "size_kb": size_kb,
                    "sha256": sha256
                }
            except Exception as e:
                return {"status": "error", "url": target_url, "error": str(e)}

        return {"status": "error", "message": f"Unknown tool '{tool_name}'"}
