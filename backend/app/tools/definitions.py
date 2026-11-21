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
    },
    {
        "type": "function",
        "function": {
            "name": "get_open_tabs",
            "description": "Retrieve the list of all currently open browser tabs.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "switch_tab",
            "description": "Switch active focus to a specific browser tab ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tab_id": {
                        "type": "string",
                        "description": "The target tab ID to activate."
                    }
                },
                "required": ["tab_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "close_tab",
            "description": "Close a specific browser tab ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tab_id": {
                        "type": "string",
                        "description": "The tab ID to close."
                    }
                },
                "required": ["tab_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "extract_links",
            "description": "Extract all navigable anchor links and headlines from the active page.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "export_json",
            "description": "Export structured research or agent data to a local JSON file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Filename (e.g. 'findings.json')."
                    },
                    "data": {
                        "type": "object",
                        "description": "The structured data object to export."
                    }
                },
                "required": ["filename", "data"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "compare_tabs",
            "description": "Inspect and compare content across multiple open tabs to synthesize insights or price differences.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "Comparison question or goal (e.g. 'Compare the product price between tabs')."
                    }
                },
                "required": ["question"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "click_selector",
            "description": "Click an element matching a CSS selector or text target (e.g. 'button.submit', '#login-btn', 'text=Sign In').",
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {
                        "type": "string",
                        "description": "CSS selector or text selector (e.g. 'button[type=\"submit\"]', 'text=Submit', '#search-box')."
                    }
                },
                "required": ["selector"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "fill_selector",
            "description": "Target an input, textarea or search box by CSS or text selector, focus it, and type text into it.",
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {
                        "type": "string",
                        "description": "CSS selector targeting the input element (e.g. 'input[name=\"q\"]', '#username')."
                    },
                    "text": {
                        "type": "string",
                        "description": "The text to type into the targeted input field."
                    }
                },
                "required": ["selector", "text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "wait_for_selector",
            "description": "Wait until an element matching the given CSS selector is visible and present in the DOM.",
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {
                        "type": "string",
                        "description": "CSS selector to wait for (e.g. '.search-results', '#success-msg')."
                    },
                    "timeout_ms": {
                        "type": "integer",
                        "description": "Maximum time to wait in milliseconds (default: 5000)."
                    }
                },
                "required": ["selector"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "detect_forms",
            "description": "Scan the active page and identify all interactive forms, input fields, labels, input types, and values.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_accessibility_tree",
            "description": "Retrieve the full semantic accessibility tree of the active webpage via CDP.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_pdf",
            "description": "Parse local or remote PDF document with page-level text extraction and metadata.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path_or_url": {
                        "type": "string",
                        "description": "Local file path (e.g. 'C:/docs/paper.pdf') or remote URL to the PDF document."
                    },
                    "max_pages": {
                        "type": "integer",
                        "description": "Maximum number of pages to parse (default: 50)."
                    }
                },
                "required": ["path_or_url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "summarize_pdf",
            "description": "Generate page-cited summary and key insights from a PDF document.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path_or_url": {
                        "type": "string",
                        "description": "Local file path or remote URL to the PDF."
                    },
                    "query": {
                        "type": "string",
                        "description": "Optional specific question or research focus for the summary."
                    }
                },
                "required": ["path_or_url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "extract_table_data",
            "description": "Extract structured tables or repeating records from the active webpage, supporting pagination across multiple pages.",
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {
                        "type": "string",
                        "description": "Optional CSS selector targeting the table or records container."
                    },
                    "pagination_next_selector": {
                        "type": "string",
                        "description": "Optional CSS selector for the 'Next' page button to scrape across pages."
                    },
                    "max_pages": {
                        "type": "integer",
                        "description": "Maximum pages to paginate through (default: 1)."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "export_data",
            "description": "Export structured dataset records to JSON or CSV format.",
            "parameters": {
                "type": "object",
                "properties": {
                    "data": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "List of record dictionaries to export."
                    },
                    "format": {
                        "type": "string",
                        "enum": ["json", "csv"],
                        "description": "Target export format (default: 'json')."
                    },
                    "filename": {
                        "type": "string",
                        "description": "Optional file name."
                    }
                },
                "required": ["data"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "synthesize_research",
            "description": "Perform deep research on a topic across multi-angle queries and sources, generating a cited Markdown report.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "The research topic or question to investigate."
                    },
                    "sources": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional explicit URLs to synthesize."
                    },
                    "depth": {
                        "type": "string",
                        "enum": ["quick", "deep"],
                        "description": "Research depth (default: 'quick')."
                    }
                },
                "required": ["topic"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "desktop_click",
            "description": "Click at specific Windows desktop screen coordinates.",
            "parameters": {
                "type": "object",
                "properties": {
                    "x": {"type": "integer", "description": "X screen coordinate in pixels."},
                    "y": {"type": "integer", "description": "Y screen coordinate in pixels."},
                    "button": {"type": "string", "enum": ["left", "right"], "description": "Mouse button (default: 'left')."}
                },
                "required": ["x", "y"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "desktop_type",
            "description": "Type text into the currently active Windows application.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to type into active window."}
                },
                "required": ["text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "desktop_hotkey",
            "description": "Send a keyboard hotkey combination to Windows (e.g. ['ctrl', 'c'], ['alt', 'tab']).",
            "parameters": {
                "type": "object",
                "properties": {
                    "keys": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Key sequence to press concurrently."
                    }
                },
                "required": ["keys"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "desktop_capture_screen",
            "description": "Capture the primary Windows desktop screen.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "desktop_launch_app",
            "description": "Launch a desktop application executable.",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {"type": "string", "description": "Application executable path or system command (e.g. 'notepad.exe', 'calc.exe')."},
                    "args": {"type": "array", "items": {"type": "string"}, "description": "Optional CLI arguments."}
                },
                "required": ["app_name"]
            }
        }
    }
]
