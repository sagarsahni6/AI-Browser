from typing import Dict, Any, List
from backend.app.skills.base import BaseSkill, SkillManifest, SkillTool
from backend.app.browser.bridge import bridge
from backend.app.ai.router import ModelRouter


class FinancialAnalystSkill(BaseSkill):
    def __init__(self):
        self.manifest = SkillManifest(
            id="financial_analyst",
            name="Financial & Market Analyst",
            description="Specialist analysis for option chains, stock price grids, financial metrics, and visual chart inspection.",
            category="finance",
            icon="TrendingUp",
            enabled=True,
            triggers=[
                "finance", "stock", "option chain", "ticker", "greeks",
                "chart", "candlestick", "balance sheet", "market", "tradingview", "trading", "crypto"
            ],
            tools=[
                SkillTool(
                    name="parse_financial_table",
                    description="Extract and structure financial tables: Option chains (Calls/Puts, Strikes, OI, IV), quotes, or earnings reports.",
                    parameters={
                        "type": "object",
                        "properties": {
                            "table_type": {
                                "type": "string",
                                "enum": ["option_chain", "stock_quotes", "financial_statement", "general"],
                                "description": "Type of financial data to extract."
                            }
                        }
                    },
                    risk_tier="green"
                ),
                SkillTool(
                    name="analyze_chart_pattern",
                    description="Inspect the active chart/canvas using a Vision-Language Model to identify trends, support/resistance, and indicators.",
                    parameters={
                        "type": "object",
                        "properties": {
                            "question": {"type": "string", "description": "Specific feature or price action question to analyze."}
                        },
                        "required": ["question"]
                    },
                    risk_tier="green"
                ),
                SkillTool(
                    name="compare_assets",
                    description="Generate a side-by-side comparison matrix for financial tickers or crypto assets.",
                    parameters={
                        "type": "object",
                        "properties": {
                            "tickers": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of ticker symbols (e.g. ['AAPL', 'MSFT', 'NVDA'])."
                            },
                            "metrics": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Optional list of metrics (e.g. ['P/E', 'Market Cap', '52-Week High'])."
                            }
                        },
                        "required": ["tickers"]
                    },
                    risk_tier="green"
                )
            ]
        )

    def get_system_prompt_snippet(self) -> str:
        return (
            "When analyzing financial pages or charts, use `parse_financial_table` for option chains and quotes, "
            "`analyze_chart_pattern` for TradingView or canvas candlestick charts, and `compare_assets` for comparative ratios. "
            "Always state prices with clear currency units and timestamps where available."
        )

    async def execute_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if tool_name == "parse_financial_table":
            script = """
            (() => {
                const tables = Array.from(document.querySelectorAll('table, [role="grid"], .option-chain'));
                if (tables.length === 0) return { found: false, message: "No financial table or grid detected on page" };
                const t = tables[0];
                const headers = Array.from(t.querySelectorAll('th, [role="columnheader"]')).map(th => th.innerText.trim()).filter(Boolean);
                const rows = Array.from(t.querySelectorAll('tbody tr, [role="row"]')).slice(0, 40).map(tr => {
                    return Array.from(tr.querySelectorAll('td, [role="gridcell"]')).map(td => td.innerText.trim());
                }).filter(r => r.length > 0);
                return { found: true, headers, row_count: rows.length, rows };
            })()
            """
            res = await bridge.call("browser.evaluate_js", {"script": script})
            return {"status": "success", "financial_data": res}

        elif tool_name == "analyze_chart_pattern":
            question = params.get("question", "Identify the trend, key support and resistance levels, and notable patterns.")
            b64_img = await bridge.call("browser.capture_screenshot", {})
            raw_b64 = b64_img.split(",", 1)[-1] if "," in b64_img else b64_img

            v_provider, v_model = ModelRouter.route_for_task(task_type="vision")
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"You are a Senior Financial Market Technical Analyst. Examine this chart: {question}"},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{raw_b64}"}}
                    ]
                }
            ]
            res = await v_provider.chat_completion(messages=messages, model=v_model)
            return {"status": "success", "analysis": res.content, "model": v_model}

        elif tool_name == "compare_assets":
            tickers = params.get("tickers", [])
            metrics = params.get("metrics") or ["Price", "Market Cap", "P/E Ratio", "52-Week Range", "Day Change"]
            from backend.app.search.registry import search_registry
            search_prov = search_registry.get("duckduckgo")
            query = f"compare stock metrics {' '.join(tickers)}"
            items = await search_prov.search(query, limit=4)
            snippets = "\n".join([f"- {it.title}: {it.snippet}" for it in items])

            provider, model = ModelRouter.route_for_task(task_type="reasoning")
            prompt = (
                f"Create a Markdown comparison table for tickers: {', '.join(tickers)}\n"
                f"Metrics: {', '.join(metrics)}\n"
                f"Market Information:\n{snippets}\n\n"
                f"Synthesize current values and executive summary:"
            )
            res = await provider.chat_completion(messages=[{"role": "user", "content": prompt}], model=model)
            return {"status": "success", "tickers": tickers, "comparison_table": res.content}

        return {"status": "error", "message": f"Unknown tool '{tool_name}'"}
