import pytest
from backend.app.ai.tool_call_parser import extract_tool_calls_from_text, clean_tool_calls_from_text

def test_extract_xml_tool_call_with_evaluate_javascript():
    raw = r"""<tool_call>
<function=evaluate_javascript>
<parameter=script>
document.querySelectorAll('text, li, div, span').forEach(el => {
if(el.textContent.trim().match(/^\d+\./))
console.log(el.textContent.trim()); });
</parameter>
<parameter=url>
https://fictionhorizon.com/50-best-bollywood-movies-of-all-time-ranked/
</parameter>
</function>
</tool_call>"""

    calls = extract_tool_calls_from_text(raw)
    assert len(calls) == 1
    call = calls[0]
    assert call["type"] == "function"
    assert call["function"]["name"] == "evaluate_javascript"
    import json
    args = json.loads(call["function"]["arguments"])
    assert "document.querySelectorAll" in args["script"]
    assert args["url"] == "https://fictionhorizon.com/50-best-bollywood-movies-of-all-time-ranked/"

def test_extract_json_tool_call():
    raw = """```json
{"name": "navigate", "arguments": {"url": "https://google.com"}}
```"""
    calls = extract_tool_calls_from_text(raw)
    assert len(calls) == 1
    assert calls[0]["function"]["name"] == "navigate"

def test_clean_tool_calls_from_text():
    raw = """<tool_call>
<function=navigate>
<parameter=url>https://example.com</parameter>
</function>
</tool_call>
Here are the top ranked results:
1. Movie A
2. Movie B"""
    cleaned = clean_tool_calls_from_text(raw)
    assert "<tool_call>" not in cleaned
    assert "</tool_call>" not in cleaned
    assert "Here are the top ranked results:" in cleaned
    assert "1. Movie A" in cleaned
