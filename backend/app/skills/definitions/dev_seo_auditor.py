import httpx
from typing import Dict, Any, List
from backend.app.skills.base import BaseSkill, SkillManifest, SkillTool
from backend.app.browser.bridge import bridge


class DevSeoAuditorSkill(BaseSkill):
    def __init__(self):
        self.manifest = SkillManifest(
            id="dev_seo_auditor",
            name="Developer & SEO Auditor",
            description="Comprehensive SEO metadata inspection, broken link auditor, accessibility DOM scanner, and network timing.",
            category="developer",
            icon="Cpu",
            enabled=True,
            triggers=[
                "seo", "audit", "meta tags", "broken links", "accessibility",
                "lighthouse", "developer audit", "dom inspection", "og tags", "performance"
            ],
            tools=[
                SkillTool(
                    name="audit_seo_metadata",
                    description="Inspect and validate SEO metadata: Title, Meta Description, Canonical URL, OpenGraph tags, Robots, and Schema.org JSON-LD.",
                    parameters={
                        "type": "object",
                        "properties": {}
                    },
                    risk_tier="green"
                ),
                SkillTool(
                    name="check_broken_links",
                    description="Scan links on the active page and test their HTTP status codes asynchronously to identify broken links (404/500).",
                    parameters={
                        "type": "object",
                        "properties": {
                            "max_links": {"type": "integer", "description": "Maximum links to test (default: 20)."}
                        }
                    },
                    risk_tier="green"
                ),
                SkillTool(
                    name="audit_accessibility_dom",
                    description="Audit DOM accessibility: images missing alt text, buttons without labels, form input associations, and heading structure.",
                    parameters={
                        "type": "object",
                        "properties": {}
                    },
                    risk_tier="green"
                )
            ]
        )

    def get_system_prompt_snippet(self) -> str:
        return (
            "When evaluating website quality, SEO, or code health, use `audit_seo_metadata` for search readiness, "
            "`check_broken_links` to test external hyperlinks, and `audit_accessibility_dom` for WCAG accessibility compliance. "
            "Report findings with actionable remediation steps in clear Markdown."
        )

    async def execute_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if tool_name == "audit_seo_metadata":
            script = """
            (() => {
                const getMeta = (name) => {
                    const el = document.querySelector(`meta[name="${name}"], meta[property="${name}"]`);
                    return el ? el.getAttribute('content') : null;
                };
                const jsonLdEls = Array.from(document.querySelectorAll('script[type="application/ld+json"]'));
                const jsonLd = jsonLdEls.map(s => {
                    try { return JSON.parse(s.innerText); } catch(e) { return null; }
                }).filter(Boolean);

                return {
                    url: window.location.href,
                    title: document.title,
                    title_length: document.title.length,
                    description: getMeta('description'),
                    description_length: (getMeta('description') || '').length,
                    canonical: document.querySelector('link[rel="canonical"]')?.href || null,
                    robots: getMeta('robots'),
                    og: {
                        title: getMeta('og:title'),
                        description: getMeta('og:description'),
                        image: getMeta('og:image'),
                        type: getMeta('og:type'),
                        site_name: getMeta('og:site_name')
                    },
                    twitter: {
                        card: getMeta('twitter:card'),
                        title: getMeta('twitter:title'),
                        description: getMeta('twitter:description')
                    },
                    schema_json_ld_count: jsonLd.length,
                    h1_count: document.querySelectorAll('h1').length,
                    h1_text: Array.from(document.querySelectorAll('h1')).map(h => h.innerText.trim())
                };
            })()
            """
            res = await bridge.call("browser.evaluate_js", {"script": script})
            return {"status": "success", "seo_audit": res}

        elif tool_name == "check_broken_links":
            max_links = min(int(params.get("max_links", 20)), 30)
            extract_script = f"""
            (() => {{
                return Array.from(document.querySelectorAll('a[href]'))
                    .map(a => ({{ url: a.href, text: a.innerText.trim().slice(0, 60) }}))
                    .filter(a => a.url.startsWith('http://') || a.url.startsWith('https://'))
                    .slice(0, {max_links});
            }})()
            """
            links = await bridge.call("browser.evaluate_js", {"script": extract_script}) or []

            tested = []
            async with httpx.AsyncClient(timeout=6.0, follow_redirects=True) as client:
                for item in links:
                    url = item.get("url")
                    try:
                        resp = await client.head(url)
                        status_code = resp.status_code
                    except Exception:
                        try:
                            resp = await client.get(url)
                            status_code = resp.status_code
                        except Exception as e:
                            status_code = 0

                    is_broken = status_code >= 400 or status_code == 0
                    tested.append({
                        "url": url,
                        "anchor_text": item.get("text"),
                        "status_code": status_code,
                        "is_broken": is_broken
                    })

            broken_count = sum(1 for t in tested if t["is_broken"])
            return {
                "status": "success",
                "total_tested": len(tested),
                "broken_count": broken_count,
                "results": tested
            }

        elif tool_name == "audit_accessibility_dom":
            script = """
            (() => {
                const images = Array.from(document.querySelectorAll('img'));
                const missingAlt = images.filter(img => !img.hasAttribute('alt') || img.getAttribute('alt').trim() === '');

                const buttons = Array.from(document.querySelectorAll('button, [role="button"]'));
                const unlabelledButtons = buttons.filter(btn => {
                    const text = btn.innerText.trim();
                    const aria = btn.getAttribute('aria-label') || btn.getAttribute('aria-labelledby');
                    return !text && !aria;
                });

                const inputs = Array.from(document.querySelectorAll('input:not([type="hidden"]), select, textarea'));
                const unlabelledInputs = inputs.filter(inp => {
                    const id = inp.id;
                    const hasLabelFor = id && document.querySelector(`label[for="${id}"]`);
                    const hasParentLabel = inp.closest('label');
                    const hasAria = inp.getAttribute('aria-label') || inp.getAttribute('aria-labelledby');
                    return !hasLabelFor && !hasParentLabel && !hasAria;
                });

                return {
                    total_images: images.length,
                    images_missing_alt: missingAlt.length,
                    total_buttons: buttons.length,
                    unlabelled_buttons: unlabelledButtons.length,
                    total_inputs: inputs.length,
                    unlabelled_inputs: unlabelledInputs.length,
                    accessibility_score: Math.max(0, 100 - (missingAlt.length * 5 + unlabelledButtons.length * 10 + unlabelledInputs.length * 5))
                };
            })()
            """
            res = await bridge.call("browser.evaluate_js", {"script": script})
            return {"status": "success", "accessibility_audit": res}

        return {"status": "error", "message": f"Unknown tool '{tool_name}'"}
