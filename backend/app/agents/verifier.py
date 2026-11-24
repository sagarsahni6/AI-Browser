import os
import re
import json
import logging
from typing import Dict, Any, Optional, List
from backend.app.tools.executor import ToolExecutor

logger = logging.getLogger("verifier_agent")

class VerifierAgent:
    """
    Goal-Based Objective Verification Agent.
    Evaluates concrete observable evidence (DOM element presence/state, URL matching,
    data record schemas, file validation, and form submission confirmations)
    rather than superficial screenshot checks.
    """

    @classmethod
    async def verify_dom_assertion(cls, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Objective DOM assertion: verifies element selector presence, visibility,
        text match, or absence.
        """
        selector = parameters.get("selector", "")
        expected_text = parameters.get("text")
        expected_state = parameters.get("expected_state", "present").lower() # present, absent, visible, hidden
        exact_match = parameters.get("exact_match", False)

        if not selector:
            return {
                "status": "error",
                "verified": False,
                "error": "No selector specified for DOM assertion",
                "evidence": {}
            }

        js_script = f"""
        (() => {{
            const el = document.querySelector({json.dumps(selector)});
            if (!el) return {{ found: false, text: "", visible: false, value: null }};
            const style = window.getComputedStyle(el);
            const visible = Boolean(
                style && style.display !== 'none' &&
                style.visibility !== 'hidden' &&
                style.opacity !== '0' &&
                (el.offsetWidth > 0 || el.offsetHeight > 0 || el.getClientRects().length > 0)
            );
            return {{
                found: true,
                text: (el.innerText || el.textContent || "").trim(),
                value: el.value || null,
                visible: visible
            }};
        }})()
        """
        eval_res = await ToolExecutor.execute("evaluate_javascript", {"script": js_script}, bypass_approval=True)
        dom_data = eval_res.get("result") if isinstance(eval_res.get("result"), dict) else {}

        found = dom_data.get("found", False)
        visible = dom_data.get("visible", False)
        actual_text = dom_data.get("text", "")

        evidence = {
            "selector": selector,
            "found": found,
            "visible": visible,
            "actual_text": actual_text
        }

        if expected_state == "absent":
            verified = not found
            reason = None if verified else f"Element '{selector}' was expected to be absent but was found."
            return {"status": "success", "verified": verified, "evidence": evidence, "reason": reason}

        if not found:
            return {
                "status": "success",
                "verified": False,
                "evidence": evidence,
                "reason": f"Element '{selector}' was not found in the DOM."
            }

        if expected_state == "visible" and not visible:
            return {
                "status": "success",
                "verified": False,
                "evidence": evidence,
                "reason": f"Element '{selector}' is present but not visible."
            }

        if expected_text is not None:
            if exact_match:
                matches = actual_text == expected_text
            else:
                matches = expected_text.lower() in actual_text.lower()
            if not matches:
                return {
                    "status": "success",
                    "verified": False,
                    "evidence": evidence,
                    "reason": f"Element '{selector}' text '{actual_text}' did not match expected '{expected_text}'."
                }

        return {"status": "success", "verified": True, "evidence": evidence, "reason": None}

    @classmethod
    async def verify_url_match(cls, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Objective URL matching: verifies current page URL matches regex pattern,
        domain, or path substring.
        """
        pattern = parameters.get("pattern")
        expected_url = parameters.get("expected_url")
        domain = parameters.get("domain")

        page_res = await ToolExecutor.execute("get_page_content", {})
        current_url = page_res.get("url") or (page_res.get("result", {}).get("url") if isinstance(page_res.get("result"), dict) else "") or ""

        evidence = {
            "current_url": current_url,
            "target": pattern or expected_url or domain
        }

        if not current_url:
            return {
                "status": "success",
                "verified": False,
                "evidence": evidence,
                "reason": "Current page URL could not be retrieved."
            }

        if pattern:
            matched = bool(re.search(pattern, current_url))
            return {
                "status": "success",
                "verified": matched,
                "evidence": evidence,
                "reason": None if matched else f"URL '{current_url}' did not match regex pattern '{pattern}'."
            }

        if expected_url:
            matched = expected_url in current_url
            return {
                "status": "success",
                "verified": matched,
                "evidence": evidence,
                "reason": None if matched else f"URL '{current_url}' does not contain expected '{expected_url}'."
            }

        if domain:
            matched = domain.lower() in current_url.lower()
            return {
                "status": "success",
                "verified": matched,
                "evidence": evidence,
                "reason": None if matched else f"URL '{current_url}' does not belong to domain '{domain}'."
            }

        return {"status": "success", "verified": True, "evidence": evidence, "reason": None}

    @classmethod
    def verify_data_validation(cls, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Objective data validation: verifies extracted dataset row count > 0 and
        validates required schema keys across records.
        """
        records = parameters.get("records") or parameters.get("data")
        min_records = int(parameters.get("min_records", 1))
        required_fields: List[str] = parameters.get("required_fields", [])

        if not isinstance(records, list):
            return {
                "status": "success",
                "verified": False,
                "evidence": {"records_type": type(records).__name__},
                "reason": "Records payload is not a list."
            }

        count = len(records)
        evidence = {
            "record_count": count,
            "min_required": min_records,
            "required_fields": required_fields
        }

        if count < min_records:
            return {
                "status": "success",
                "verified": False,
                "evidence": evidence,
                "reason": f"Extracted {count} records, fewer than required minimum {min_records}."
            }

        if required_fields and records:
            missing_fields = []
            for field in required_fields:
                if not any(isinstance(r, dict) and field in r for r in records):
                    missing_fields.append(field)
            if missing_fields:
                evidence["missing_fields"] = missing_fields
                return {
                    "status": "success",
                    "verified": False,
                    "evidence": evidence,
                    "reason": f"Required fields missing from extracted dataset: {missing_fields}."
                }

        evidence["sample"] = records[0] if records else None
        return {"status": "success", "verified": True, "evidence": evidence, "reason": None}

    @classmethod
    def verify_file_validation(cls, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Objective file validation: verifies that an exported file exists on disk
        and has non-empty file size.
        """
        raw_path = parameters.get("file_path") or parameters.get("path") or parameters.get("filename")
        min_size = int(parameters.get("min_size_bytes", 1))

        if not raw_path:
            return {
                "status": "error",
                "verified": False,
                "error": "No file path provided for validation",
                "evidence": {}
            }

        resolved_path = str(raw_path)
        if not os.path.isabs(resolved_path):
            candidate1 = os.path.join(os.getcwd(), resolved_path)
            candidate2 = os.path.join(os.getcwd(), "data", resolved_path)
            if os.path.exists(candidate1):
                resolved_path = candidate1
            elif os.path.exists(candidate2):
                resolved_path = candidate2
            else:
                resolved_path = candidate1

        exists = os.path.exists(resolved_path)
        size = os.path.getsize(resolved_path) if exists else 0

        evidence = {
            "file_path": resolved_path,
            "exists": exists,
            "size_bytes": size,
            "min_size_bytes": min_size
        }

        if not exists:
            return {
                "status": "success",
                "verified": False,
                "evidence": evidence,
                "reason": f"File '{resolved_path}' does not exist on disk."
            }

        if size < min_size:
            return {
                "status": "success",
                "verified": False,
                "evidence": evidence,
                "reason": f"File '{resolved_path}' is empty ({size} bytes < {min_size})."
            }

        return {"status": "success", "verified": True, "evidence": evidence, "reason": None}

    @classmethod
    async def verify_form_submission(cls, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Objective form submission verification: verifies submission feedback,
        confirmation message, redirect URL, or absence of form error indicators.
        """
        confirmation_selector = parameters.get("confirmation_selector")
        success_text = parameters.get("success_text")
        redirect_url = parameters.get("redirect_url")
        error_selector = parameters.get("error_selector")

        page_res = await ToolExecutor.execute("get_page_content", {})
        dom_text = (page_res.get("visible_text_snippet") or page_res.get("text") or "")
        current_url = page_res.get("url", "")

        evidence = {
            "current_url": current_url,
            "has_dom_text": bool(dom_text)
        }

        if error_selector:
            err_check = await ToolExecutor.execute("evaluate_javascript", {
                "script": f"Boolean(document.querySelector({json.dumps(error_selector)}))"
            })
            if err_check.get("result") is True:
                evidence["error_selector_found"] = True
                return {
                    "status": "success",
                    "verified": False,
                    "evidence": evidence,
                    "reason": f"Error banner '{error_selector}' detected after form submission."
                }

        if confirmation_selector:
            conf_check = await ToolExecutor.execute("evaluate_javascript", {
                "script": f"Boolean(document.querySelector({json.dumps(confirmation_selector)}))"
            })
            if conf_check.get("result") is not True:
                evidence["confirmation_selector_found"] = False
                return {
                    "status": "success",
                    "verified": False,
                    "evidence": evidence,
                    "reason": f"Confirmation element '{confirmation_selector}' was not found."
                }
            evidence["confirmation_selector_found"] = True

        if success_text:
            matched = success_text.lower() in dom_text.lower()
            evidence["success_text_matched"] = matched
            if not matched:
                return {
                    "status": "success",
                    "verified": False,
                    "evidence": evidence,
                    "reason": f"Success confirmation text '{success_text}' not observed on page."
                }

        if redirect_url:
            matched = redirect_url in current_url
            evidence["redirect_matched"] = matched
            if not matched:
                return {
                    "status": "success",
                    "verified": False,
                    "evidence": evidence,
                    "reason": f"Form submission expected redirect to '{redirect_url}', current URL is '{current_url}'."
                }

        if not any([confirmation_selector, success_text, redirect_url, error_selector]):
            if not dom_text and not current_url:
                return {
                    "status": "success",
                    "verified": False,
                    "evidence": evidence,
                    "reason": "No submission feedback or valid browser state detected."
                }

        return {"status": "success", "verified": True, "evidence": evidence, "reason": None}

    @classmethod
    async def execute_step(cls, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Dispatches verification to the appropriate objective check based on action
        or embedded strategy/parameters.
        """
        logger.info(f"VerifierAgent running objective verification for '{action}'")
        try:
            if action == "dom_assertion":
                return await cls.verify_dom_assertion(parameters)

            elif action == "url_match":
                return await cls.verify_url_match(parameters)

            elif action == "data_validation":
                return cls.verify_data_validation(parameters)

            elif action == "file_validation":
                return cls.verify_file_validation(parameters)

            elif action == "form_submission":
                return await cls.verify_form_submission(parameters)

            elif action in ("verify_task", "verify_state"):
                strategy = parameters.get("strategy")
                if strategy == "dom_assertion" or "selector" in parameters:
                    return await cls.verify_dom_assertion(parameters)
                elif strategy == "url_match" or any(k in parameters for k in ("pattern", "expected_url", "domain")):
                    return await cls.verify_url_match(parameters)
                elif strategy == "data_validation" or any(k in parameters for k in ("records", "required_fields")):
                    return cls.verify_data_validation(parameters)
                elif strategy == "file_validation" or any(k in parameters for k in ("file_path", "path")):
                    return cls.verify_file_validation(parameters)
                elif strategy == "form_submission" or any(k in parameters for k in ("confirmation_selector", "success_text", "redirect_url")):
                    return await cls.verify_form_submission(parameters)
                else:
                    # General task state verification: evaluate concrete page observation
                    screenshot_res = await ToolExecutor.execute("take_screenshot", {})
                    page_res = await ToolExecutor.execute("get_page_content", {})
                    url = page_res.get("url") or (page_res.get("result", {}).get("url") if isinstance(page_res.get("result"), dict) else "") or ""
                    title = page_res.get("title") or (page_res.get("result", {}).get("title") if isinstance(page_res.get("result"), dict) else "") or ""
                    has_content = bool(url and url != "about:blank")
                    return {
                        "status": "success",
                        "verified": has_content,
                        "url": url,
                        "title": title,
                        "screenshot_verified": screenshot_res.get("status") in ("ok", "success"),
                        "evidence": {
                            "url": url,
                            "title": title,
                            "has_content": has_content
                        },
                        "reason": None if has_content else "Page is uninitialized (about:blank)"
                    }

            return await ToolExecutor.execute(action, parameters)

        except Exception as e:
            logger.error(f"VerifierAgent error: {e}")
            return {"status": "error", "error": str(e), "verified": False, "evidence": {}}
