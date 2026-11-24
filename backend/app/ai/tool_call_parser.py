import re
import json
from typing import List, Dict, Any

def extract_tool_calls_from_text(content: str) -> List[Dict[str, Any]]:
    """
    Extracts tool calls from raw LLM text when a model formats tool calls
    as XML tags (<tool_call>), Markdown JSON code blocks, or bracket notations
    instead of native API tool_calls.
    """
    calls: List[Dict[str, Any]] = []
    if not content or not isinstance(content, str):
        return calls

    call_counter = 1

    # 1. Pattern: <tool_call>...</tool_call>
    tool_blocks = re.findall(r'<tool_call>(.*?)</tool_call>', content, re.DOTALL | re.IGNORECASE)
    for block in tool_blocks:
        block_str = block.strip()
        # Check XML-style: <function=name> ... </function> or <function name="name"> ... </function>
        fn_match = re.search(
            r'<function(?:=|\s+name=)[\"\']?([a-zA-Z0-9_\-]+)[\"\']?>(.*?)</function>',
            block_str,
            re.DOTALL | re.IGNORECASE
        )
        if fn_match:
            fn_name = fn_match.group(1).strip()
            body = fn_match.group(2)
            params: Dict[str, Any] = {}
            param_matches = re.findall(
                r'<parameter(?:=|\s+name=)[\"\']?([a-zA-Z0-9_\-]+)[\"\']?>(.*?)</parameter>',
                body,
                re.DOTALL | re.IGNORECASE
            )
            for p_name, p_val in param_matches:
                p_key = p_name.strip()
                p_value = p_val.strip()
                # Attempt to parse json value if formatted as JSON
                if (p_value.startswith("{") and p_value.endswith("}")) or (p_value.startswith("[") and p_value.endswith("]")):
                    try:
                        p_value = json.loads(p_value)
                    except Exception:
                        pass
                params[p_key] = p_value

            calls.append({
                "id": f"call-{call_counter}",
                "type": "function",
                "function": {
                    "name": fn_name,
                    "arguments": json.dumps(params)
                }
            })
            call_counter += 1
            continue

        # Check JSON inside <tool_call>
        try:
            j = json.loads(block_str)
            if isinstance(j, dict):
                fn_name = j.get("name") or j.get("function") or j.get("tool") or j.get("action")
                args = j.get("arguments") or j.get("parameters") or j.get("params") or {}
                if fn_name:
                    calls.append({
                        "id": f"call-{call_counter}",
                        "type": "function",
                        "function": {
                            "name": fn_name,
                            "arguments": json.dumps(args) if isinstance(args, dict) else str(args)
                        }
                    })
                    call_counter += 1
                    continue
            elif isinstance(j, list):
                for item in j:
                    if isinstance(item, dict):
                        fn_name = item.get("name") or item.get("function") or item.get("tool")
                        args = item.get("arguments") or item.get("parameters") or {}
                        if fn_name:
                            calls.append({
                                "id": f"call-{call_counter}",
                                "type": "function",
                                "function": {
                                    "name": fn_name,
                                    "arguments": json.dumps(args) if isinstance(args, dict) else str(args)
                                }
                            })
                            call_counter += 1
                if calls:
                    continue
        except Exception:
            pass

    # 2. Pattern: ```json ... ``` code blocks containing tool calls
    if not calls:
        code_blocks = re.findall(r'```(?:json)?\s*([\{\[].*?[\}\]])\s*```', content, re.DOTALL | re.IGNORECASE)
        for cb in code_blocks:
            try:
                j = json.loads(cb.strip())
                if isinstance(j, dict):
                    fn_name = j.get("name") or j.get("function") or j.get("tool") or j.get("action")
                    args = j.get("arguments") or j.get("parameters") or j.get("params") or {}
                    if fn_name:
                        calls.append({
                            "id": f"call-{call_counter}",
                            "type": "function",
                            "function": {
                                "name": fn_name,
                                "arguments": json.dumps(args) if isinstance(args, dict) else str(args)
                            }
                        })
                        call_counter += 1
                elif isinstance(j, list):
                    for item in j:
                        if isinstance(item, dict):
                            fn_name = item.get("name") or item.get("function") or item.get("tool")
                            args = item.get("arguments") or item.get("parameters") or {}
                            if fn_name:
                                calls.append({
                                    "id": f"call-{call_counter}",
                                    "type": "function",
                                    "function": {
                                        "name": fn_name,
                                        "arguments": json.dumps(args) if isinstance(args, dict) else str(args)
                                    }
                                })
                                call_counter += 1
            except Exception:
                pass

    # 3. Pattern: Direct unclosed <tool_call>...<function=...> without closing tags (streaming cuts or loose formats)
    if not calls and "<function" in content and ("<parameter" in content or "script>" in content):
        fn_match = re.search(
            r'<function(?:=|\s+name=)[\"\']?([a-zA-Z0-9_\-]+)[\"\']?>',
            content,
            re.IGNORECASE
        )
        if fn_match:
            fn_name = fn_match.group(1).strip()
            params = {}
            param_matches = re.findall(
                r'<parameter(?:=|\s+name=)[\"\']?([a-zA-Z0-9_\-]+)[\"\']?>(.*?)(?:</parameter>|$)',
                content,
                re.DOTALL | re.IGNORECASE
            )
            for p_name, p_val in param_matches:
                params[p_name.strip()] = p_val.strip()
            if params or fn_name:
                calls.append({
                    "id": f"call-{call_counter}",
                    "type": "function",
                    "function": {
                        "name": fn_name,
                        "arguments": json.dumps(params)
                    }
                })

    return calls

def clean_tool_calls_from_text(content: str) -> str:
    """
    Strips raw tool call XML/code artifacts from user-facing text responses.
    """
    if not content or not isinstance(content, str):
        return ""
    # Strip <tool_call>...</tool_call>
    cleaned = re.sub(r'<tool_call>.*?</tool_call>', '', content, flags=re.DOTALL | re.IGNORECASE)
    # Strip lingering unclosed <tool_call> tags
    cleaned = re.sub(r'<tool_call>.*', '', cleaned, flags=re.DOTALL | re.IGNORECASE)
    # Strip lingering <function=...>...</function>
    cleaned = re.sub(r'<function.*?>.*?</function>', '', cleaned, flags=re.DOTALL | re.IGNORECASE)
    return cleaned.strip()
