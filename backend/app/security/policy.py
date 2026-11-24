import ipaddress
import re
import socket
from enum import Enum
from typing import Dict, Any, Optional, Tuple, Set
from urllib.parse import urlparse
from pydantic import BaseModel, Field

class RiskTier(str, Enum):
    GREEN = "green"                         # Safe read-only inspection
    YELLOW = "yellow"                       # Low-risk navigation/clicks
    REQUIRES_APPROVAL = "requires_approval" # Financial, sensitive forms, desktop input, app launch
    BLOCKED = "blocked"                     # Shell commands, loopback SSRF, file:// protocol

class PolicyResult(BaseModel):
    tier: RiskTier
    reason: str
    requires_approval: bool = False
    is_blocked: bool = False

class OriginBarrier:
    """Enforces that an active tab hasn't navigated to a different origin during user approval."""

    @staticmethod
    def capture_origin(url: Optional[str]) -> Optional[str]:
        if not url:
            return None
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return None
        return f"{parsed.scheme}://{parsed.netloc}"

    @staticmethod
    def validate_origin(expected_origin: Optional[str], current_url: Optional[str]) -> Tuple[bool, Optional[str]]:
        if not expected_origin:
            return True, None
        current_origin = OriginBarrier.capture_origin(current_url)
        if not current_origin:
            return False, "Origin mismatch: Active tab has invalid or missing origin URL."
        
        parsed_expected = urlparse(expected_origin)
        parsed_current = urlparse(current_origin)
        
        if parsed_expected.netloc.lower() != parsed_current.netloc.lower():
            return False, (
                f"Origin mismatch: Active tab navigated away from target origin during approval "
                f"({parsed_expected.netloc} != {parsed_current.netloc})"
            )
        return True, None

class SSRFDefense:
    """Detects and prevents SSRF attacks targeting private networks, loopbacks, and cloud metadata."""

    BLOCKED_HOSTS: Set[str] = {
        "localhost", "127.0.0.1", "::1", "0.0.0.0",
        "metadata.google.internal", "instance-data",
    }

    PRIVATE_NETWORKS = [
        ipaddress.ip_network("127.0.0.0/8"),      # Loopback
        ipaddress.ip_network("10.0.0.0/8"),       # Class A Private
        ipaddress.ip_network("172.16.0.0/12"),    # Class B Private
        ipaddress.ip_network("192.168.0.0/16"),   # Class C Private
        ipaddress.ip_network("169.254.0.0/16"),   # Link-Local / Cloud Metadata (169.254.169.254)
        ipaddress.ip_network("fc00::/7"),         # IPv6 Unique Local
        ipaddress.ip_network("fe80::/10"),        # IPv6 Link-Local
        ipaddress.ip_network("::1/128"),          # IPv6 Loopback
    ]

    @classmethod
    def is_safe_url(cls, url: str) -> Tuple[bool, Optional[str]]:
        if not url:
            return False, "Empty URL"
        try:
            parsed = urlparse(url.strip())
        except Exception as e:
            return False, f"Invalid URL structure: {e}"

        scheme = (parsed.scheme or "").lower()
        if scheme not in ("http", "https"):
            return False, f"Prohibited scheme: '{scheme}'. Only http and https are permitted."

        hostname = (parsed.hostname or "").lower()
        if not hostname:
            return False, "Missing hostname in URL"

        if hostname in cls.BLOCKED_HOSTS or hostname.endswith(".local") or hostname.endswith(".internal"):
            return False, f"Blocked target host: '{hostname}'"

        # Check IP address directly or resolve hostname
        try:
            ip = ipaddress.ip_address(hostname)
            for net in cls.PRIVATE_NETWORKS:
                if ip in net:
                    return False, f"Blocked destination: '{hostname}' resolves to private/metadata IP range ({net})"
            return True, None
        except ValueError:
            # Hostname is a domain name, resolve it
            try:
                resolved_ips = socket.gethostbyname_ex(hostname)[2]
                for rip in resolved_ips:
                    ip_obj = ipaddress.ip_address(rip)
                    for net in cls.PRIVATE_NETWORKS:
                        if ip_obj in net:
                            return False, f"Blocked destination: '{hostname}' ({rip}) resolves to private/metadata IP range ({net})"
            except Exception:
                # If DNS resolution fails, let network request handle standard NXDOMAIN later
                pass

        return True, None

class PromptInjectionDefense:
    """Tags untrusted external content and detects known prompt injection attack signatures."""

    INJECTION_PATTERNS = [
        re.compile(r"ignore\s+previous\s+instructions", re.IGNORECASE),
        re.compile(r"disregard\s+(all\s+)?(previous|prior)\s+instructions", re.IGNORECASE),
        re.compile(r"system\s+prompt\s+override", re.IGNORECASE),
        re.compile(r"you\s+are\s+now\s+in\s+developer\s+mode", re.IGNORECASE),
        re.compile(r"dan\s+mode\s+enabled", re.IGNORECASE),
        re.compile(r"bypass\s+all\s+safety\s+filters", re.IGNORECASE),
    ]

    @classmethod
    def wrap_untrusted(cls, content: str, source: str = "web", url: Optional[str] = None) -> str:
        safe_content = content.replace("</untrusted_content>", "&lt;/untrusted_content&gt;")
        url_attr = f' url="{url}"' if url else ""
        return f'<untrusted_content source="{source}"{url_attr}>\n{safe_content}\n</untrusted_content>'

    @classmethod
    def detect_injection(cls, text: str) -> Tuple[bool, Optional[str]]:
        for pattern in cls.INJECTION_PATTERNS:
            if pattern.search(text):
                return True, f"Prompt injection pattern detected: '{pattern.pattern}'"
        return False, None

class SecurityPolicy:
    """Central 4-tier security policy manager."""

    BLOCKED_SHELLS = frozenset([
        "cmd.exe", "cmd", "powershell.exe", "powershell", "pwsh.exe", "pwsh",
        "wscript.exe", "cscript.exe", "bash.exe", "bash", "sh.exe", "sh",
        "reg.exe", "regedit.exe", "certutil.exe", "mshta.exe"
    ])

    BLOCKED_JS_PATTERNS = (
        "document.cookie", "localStorage.clear", "sessionStorage.clear",
    )

    SENSITIVE_SELECTORS = (
        "password", "pwd", "cvv", "creditcard", "credit-card", "pin", "ssn", "secret",
    )

    SENSITIVE_ACTIONS = (
        "checkout", "purchase", "pay", "place-order", "confirm-payment",
        "delete-account", "transfer-funds", "buy-now",
    )

    @classmethod
    def evaluate(cls, tool_name: str, params: Dict[str, Any]) -> PolicyResult:
        # 1. Check BLOCKED Tier
        # Prohibited protocols & SSRF
        if tool_name in ("navigate", "open_new_tab"):
            url = str(params.get("url", "")).strip()
            url_lower = url.lower()
            if url_lower.startswith("javascript:") or url_lower.startswith("file:"):
                return PolicyResult(
                    tier=RiskTier.BLOCKED,
                    reason=f"Navigation to privileged/local protocol in '{url}' is permanently blocked.",
                    is_blocked=True
                )
            is_safe, ssrf_err = SSRFDefense.is_safe_url(url)
            if not is_safe:
                return PolicyResult(
                    tier=RiskTier.BLOCKED,
                    reason=f"Navigation blocked by SSRF defense: {ssrf_err}",
                    is_blocked=True
                )

        # Restricted JavaScript
        if tool_name == "evaluate_javascript":
            script = str(params.get("script", ""))
            for pattern in cls.BLOCKED_JS_PATTERNS:
                if pattern in script:
                    return PolicyResult(
                        tier=RiskTier.BLOCKED,
                        reason=f"Execution of prohibited JavaScript snippet '{pattern}' is blocked.",
                        is_blocked=True
                    )

        # 2. Check REQUIRES_APPROVAL Tier
        # Desktop app launches
        if tool_name == "desktop_launch_app":
            app_name = params.get("app_name", "unknown")
            return PolicyResult(
                tier=RiskTier.REQUIRES_APPROVAL,
                reason=f"Launching desktop application '{app_name}' requires explicit user approval.",
                requires_approval=True
            )

        # Desktop hotkeys (e.g. system termination)
        if tool_name == "desktop_hotkey":
            keys = [str(k).lower() for k in params.get("keys", [])]
            if any(k in ("f4", "del", "delete", "tab", "win") for k in keys):
                return PolicyResult(
                    tier=RiskTier.REQUIRES_APPROVAL,
                    reason="System-level or window-closing hotkey requires explicit user approval.",
                    requires_approval=True
                )

        # Desktop click / typing
        if tool_name in ("desktop_click", "desktop_type"):
            return PolicyResult(
                tier=RiskTier.REQUIRES_APPROVAL,
                reason=f"Desktop automated action '{tool_name}' requires explicit user approval.",
                requires_approval=True
            )

        # JavaScript evaluation
        if tool_name == "evaluate_javascript":
            return PolicyResult(
                tier=RiskTier.REQUIRES_APPROVAL,
                reason="Arbitrary JavaScript evaluation requires explicit user approval.",
                requires_approval=True
            )

        # Sensitive form fill (passwords, payment)
        if tool_name in ("fill_input", "fill_selector"):
            text = str(params.get("text", "")).lower()
            selector = str(params.get("selector", "")).lower()
            if any(s in text for s in cls.SENSITIVE_SELECTORS) or any(s in selector for s in cls.SENSITIVE_SELECTORS):
                return PolicyResult(
                    tier=RiskTier.REQUIRES_APPROVAL,
                    reason="Filling sensitive credential or financial information requires explicit user approval.",
                    requires_approval=True
                )

        # Clicks on sensitive actions
        if tool_name in ("click_element", "click_selector"):
            selector = str(params.get("selector", "")).lower()
            if any(a in selector for a in cls.SENSITIVE_ACTIONS):
                return PolicyResult(
                    tier=RiskTier.REQUIRES_APPROVAL,
                    reason="Action appears to perform a purchase, checkout, or irreversible operation and requires approval.",
                    requires_approval=True
                )

        # 3. Check YELLOW Tier
        yellow_tools = frozenset([
            "fill_input", "fill_selector", "open_new_tab", "export_csv", "export_data",
            "press_hotkey", "click_element", "click_selector", "navigate",
        ])
        if tool_name in yellow_tools:
            return PolicyResult(
                tier=RiskTier.YELLOW,
                reason=f"State-altering tool '{tool_name}' permitted with visibility notification.",
                requires_approval=False
            )

        # 4. GREEN Tier (default read-only / inspections)
        return PolicyResult(
            tier=RiskTier.GREEN,
            reason=f"Safe read-only or query tool '{tool_name}' permitted autonomously.",
            requires_approval=False
        )
