from typing import List, Dict, Any

BROWSER_TOOLS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "navigate",
            "description": "Navigate the browser active tab to a specific website URL.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The destination URL (e.g. 'https://wikipedia.org')."
                    }
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_page_content",
            "description": "Inspect the active webpage via CDP to extract URL, title, visible text, and interactive elements with coordinates.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "take_screenshot",
            "description": "Capture a screenshot of the current viewport for visual verification.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "click_element",
            "description": "Click an element at specific (x, y) coordinates on the page.",
            "parameters": {
                "type": "object",
                "properties": {
                    "x": {
                        "type": "integer",
                        "description": "X coordinate in viewport pixels."
                    },
                    "y": {
                        "type": "integer",
                        "description": "Y coordinate in viewport pixels."
                    }
                },
                "required": ["x", "y"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "fill_input",
            "description": "Click an input control at coordinates (x, y) and type text into it.",
            "parameters": {
                "type": "object",
                "properties": {
                    "x": {
                        "type": "integer",
                        "description": "X coordinate of the input box."
                    },
                    "y": {
                        "type": "integer",
                        "description": "Y coordinate of the input box."
                    },
                    "text": {
                        "type": "string",
                        "description": "The text to type into the input."
                    }
                },
                "required": ["x", "y", "text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "scroll_page",
            "description": "Scroll the active webpage vertically.",
            "parameters": {
                "type": "object",
                "properties": {
                    "delta_y": {
                        "type": "integer",
                        "description": "Vertical scroll delta (positive for downwards, negative for upwards)."
                    }
                },
                "required": ["delta_y"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "open_new_tab",
            "description": "Open a new browser tab with an optional URL.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "Initial URL for the new tab."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Search the web for information using browser search.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query string."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "export_csv",
            "description": "Export tabular data gathered by the agent to a CSV file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Filename (e.g. 'results.csv')."
                    },
                    "headers": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of column headers."
                    },
                    "rows": {
                        "type": "array",
                        "items": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "description": "List of data rows."
                    }
                },
                "required": ["filename", "headers", "rows"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "evaluate_javascript",
            "description": "Execute JavaScript directly in the active browser page to inspect window state, extract dynamic DOM tables, read option chain values, or interact with web elements.",
            "parameters": {
                "type": "object",
                "properties": {
                    "script": {
                        "type": "string",
                        "description": "The JavaScript code to execute in the page context."
                    }
                },
                "required": ["script"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "extract_table_data",
            "description": "Automatically extract structured tabular data from the active webpage, such as Option Chain strikes, call/put prices, OI, or financial grids.",
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {
                        "type": "string",
                        "description": "Optional CSS selector targeting a specific table element (e.g. 'table', '.option-chain-table')."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "inspect_visual_chart",
            "description": "Capture the viewport and analyze HTML5 canvas/WebGL charts (like TradingView) with a high-capacity Vision-Language Model to identify price trends, timeframe, indicators, or coordinates of buttons/canvas elements.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "What specific chart feature, timeframe, price action, or element coordinate to analyze."
                    }
                },
                "required": ["question"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "press_hotkey",
            "description": "Send a keyboard key or hotkey to the active page (e.g. 'Enter', 'Escape', 'ArrowDown').",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "The key to press (e.g. 'Enter', 'Escape', 'Tab', 'Space')."
                    }
                },
                "required": ["key"]
            }
        }
    }
]
