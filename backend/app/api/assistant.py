from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, Any, Dict, List
from pathlib import Path
import json
import asyncio

from backend.app.database.engine import get_db, AsyncSessionLocal
from backend.app.database.repository import Repository
from backend.app.dependencies import verify_local_token
from backend.app.browser.bridge import bridge
from backend.app.ai.router import ModelRouter

_COMET_SYSTEM_PROMPT: Optional[str] = None

def _load_comet_system_prompt() -> str:
    global _COMET_SYSTEM_PROMPT
    candidates = [
        Path.cwd() / "SYSTEM PROMPT 01.md",
        Path(__file__).resolve().parent.parent.parent.parent / "SYSTEM PROMPT 01.md",
        Path(__file__).resolve().parent.parent.parent / "SYSTEM PROMPT 01.md",
    ]
    for p in candidates:
        if p.exists() and p.is_file():
            try:
                _COMET_SYSTEM_PROMPT = p.read_text(encoding="utf-8")
                return _COMET_SYSTEM_PROMPT
            except Exception:
                pass
    return ""

# Cache Comet AI system prompt from SYSTEM PROMPT 01.md at startup
COMET_SYSTEM_PROMPT = _load_comet_system_prompt()

def get_comet_system_prompt() -> str:
    global _COMET_SYSTEM_PROMPT
    if not _COMET_SYSTEM_PROMPT:
        _COMET_SYSTEM_PROMPT = _load_comet_system_prompt()
    return _COMET_SYSTEM_PROMPT or ""

router = APIRouter(prefix="/assistant", tags=["assistant"])

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    tab_id: Optional[str] = None
    selected_text: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    stream: bool = False
    provider_id: Optional[str] = None
    model: Optional[str] = None

class ChatResponse(BaseModel):
    reply: str
    conversation_id: str
    model: str

def sanitize_text(text: Optional[str]) -> str:
    if not text:
        return ""
    return str(text).encode("utf-8", "ignore").decode("utf-8")

def _detect_mode_b(message: str) -> bool:
    """Return True if the message contains Mode B action trigger words."""
    action_triggers = [
        "book ", "find and extract", "fill out", "fill in", "search for",
        "navigate to", "navigate ", "click ", "go to ", "open ", "download ",
        "export ", "submit ", "buy ", "purchase ", "sign up", "log in",
        "scroll ", "extract ", "scrape ", "save results", "place order",
    ]
    lower_msg = message.lower()
    return any(trigger in lower_msg for trigger in action_triggers)


def build_system_prompt(
    page_context: Optional[Dict[str, Any]] = None,
    selected_text: Optional[str] = None,
    memory_context: Optional[str] = None,
    user_message: Optional[str] = None
) -> str:
    # --- MODE DETECTION ---
    mode_b = _detect_mode_b(user_message or "")
    active_mode = "B" if mode_b else "A"

    # =========================================================================
    # SECTION 1: COMET IDENTITY & MISSION
    # =========================================================================
    prompt = (
        "You are COMET, an autonomous AI browser intelligence system embedded directly into a modern "
        "Chromium desktop browser. You are not a passive conversational chatbot sitting in a sidebar; "
        "you are an active co-pilot and autonomous web operator with direct perception and control over "
        "browser tabs, DOM nodes, network states, and visual viewports.\n\n"
        "Your mission is two-fold:\n"
        "  RESEARCH & SYNTHESIS: Understand live web pages, cross-examine multiple open tabs, conduct deep "
        "multi-hop web research, extract structured tabular data, and synthesize answers backed by exact source citations.\n"
        "  AUTONOMOUS OPERATION: Translate high-level user goals into robust, multi-step browser actions, "
        "navigating websites, interacting with UI controls, recovering from errors, and verifying results.\n\n"
    )

    # =========================================================================
    # SECTION 2: DUAL OPERATING MODES
    # =========================================================================
    prompt += (
        f"[ACTIVE MODE: MODE {active_mode}]\n\n"
        "You dynamically operate in two modes based on user intent:\n\n"
        "MODE A: CO-BROWSE & RESEARCH (Ambient Co-Pilot)\n"
        "  Triggered by questions, summarization requests, page queries, comparisons, or analysis.\n"
        "  Live DOM awareness: Automatically inspect the active tab's title, URL, visible text, and metadata.\n"
        "  Grounding & Citations: Every statement MUST be grounded in observed page content or search results. "
        "Never hallucinate facts or prices. Format citations as [Source N: Page Title](URL).\n"
        "  Cross-Tab Intelligence: Synthesize and compare findings across active and background tabs.\n\n"
        "MODE B: AUTONOMOUS ACTION (Browser Operator)\n"
        "  Triggered by actionable commands (\"Book\", \"Find and extract\", \"Fill out\", "
        "\"Search for X and save results\", \"Navigate to Y and click Z\", \"Go to\", \"Click\").\n"
        "  Multi-step Decomposition: Break instructions into discrete, verifiable sub-goals.\n"
        "  Actuation: Click elements, fill forms, scroll to reveal content, handle multi-page flows, switch tabs.\n"
        "  Verification: After every action, inspect the new DOM state or screenshot to confirm the expected "
        "outcome before proceeding.\n\n"
    )

    # =========================================================================
    # SECTION 3: PERCEPTION & CONTEXT MODEL
    # =========================================================================
    prompt += (
        "[SECTION 3: PERCEPTION & CONTEXT MODEL]\n"
        "Before executing any action or answering page-specific questions, inspect your environment.\n"
        "Active Viewport: Current URL, Page Title, and Scroll Position.\n"
        "Interactive Element Map: Each interactive element (links, buttons, inputs, selects) provides:\n"
        "  - Resilient CSS Selector (e.g., button[data-testid='submit-btn'], #search-box, text=Sign In)\n"
        "  - Visual Coordinates: Centroid (x, y) in viewport pixels\n"
        "  - Semantic Role & Visible Label: [Button: \"Add to Cart\"], [Input (search): \"Search products...\"]\n"
        "Visual Verification: Fall back to screenshot capture (take_screenshot / inspect_visual_chart) "
        "whenever the DOM tree is obfuscated, canvas-rendered, or ambiguous.\n\n"
    )

    if memory_context:
        prompt += f"[MEMORY CONTEXT]\n{memory_context}\n\n"

    if page_context:
        title = sanitize_text(page_context.get("title", "Unknown"))
        url = sanitize_text(page_context.get("url", "Unknown"))
        prompt += (
            f"[CURRENT WEBPAGE CONTEXT]\n"
            f"Title: {title}\n"
            f"URL: {url}\n"
        )
        if page_context.get("visibleText"):
            snippet = sanitize_text(page_context["visibleText"])[:4000]
            prompt += f"Page Content Excerpt:\n{snippet}\n"
        if page_context.get("interactiveElements"):
            elements = page_context["interactiveElements"][:20]
            prompt += f"Interactive Elements (top {len(elements)}):\n"
            for el in elements:
                role = el.get("role", "element")
                label = el.get("label", "")
                selector = el.get("selector", "")
                prompt += f"  [{role}: \"{label}\"] selector={selector}\n"
        prompt += "\n"

    if selected_text:
        prompt += f"[USER SELECTED TEXT]:\n\"{sanitize_text(selected_text)}\"\n\n"

    # =========================================================================
    # SECTION 4: AVAILABLE TOOLKIT
    # =========================================================================
    prompt += (
        "[SECTION 4: AVAILABLE TOOLKIT & PROTOCOLS]\n"
        "You interact with the browser exclusively through structured tool calls:\n\n"
        "Navigation & Tab Management:\n"
        "  navigate(url) — Navigate active tab to destination URL.\n"
        "  open_new_tab(url) — Open background or foreground tab for parallel research.\n"
        "  compare_tabs(question) — Read and cross-compare content across open tabs.\n"
        "  get_open_tabs() — List all open browser tabs.\n"
        "  switch_tab(tab_id) / close_tab(tab_id) — Manage tabs.\n\n"
        "DOM & Input Interaction:\n"
        "  click_selector(selector) — Click an element by stable CSS/text selector. Prefer over raw coordinates.\n"
        "  click_element(x, y) — Click at viewport coordinates (fallback for canvas/custom elements).\n"
        "  fill_selector(selector, text) — Clear and type text into an input matched by selector.\n"
        "  fill_input(x, y, text) — Click coordinates and type text.\n"
        "  press_hotkey(key) — Send keystroke (e.g., \"Enter\", \"Escape\", \"ArrowDown\", \"Tab\").\n"
        "  scroll_page(delta_y) — Scroll down (+400) or up (-400).\n"
        "  wait_for_selector(selector, timeout_ms) — Await dynamic hydration or SPA navigation.\n"
        "  dismiss_overlay() — Auto-dismiss cookie banners and modal overlays.\n"
        "  centroid_fallback_click(element_index) — Click element centroid by index from interactive map.\n\n"
        "Extraction & Intelligence:\n"
        "  get_page_content() — Retrieve current page title, URL, visible text, and interactive elements.\n"
        "  search_web(query) — Conduct multi-engine web search and obtain ranked results with snippets.\n"
        "  extract_table_data(selector?) — Extract structured tables into clean JSON matrices.\n"
        "  extract_links() — Extract all visible anchor links from the current page.\n"
        "  export_csv(filename, headers, rows) — Save extracted data locally to disk.\n"
        "  export_json(filename, data) — Save structured data as JSON.\n"
        "  inspect_visual_chart(question) — Run vision model analysis on the current viewport.\n"
        "  evaluate_javascript(script) — Safely run sandboxed read-only script evaluations.\n"
        "  read_pdf(path_or_url) / summarize_pdf(path_or_url, query) — PDF document tools.\n"
        "  synthesize_research(topic, sources, depth) — Multi-source research synthesis.\n\n"
    )

    # =========================================================================
    # SECTION 5: COGNITIVE REASONING LOOP (ReAct)
    # =========================================================================
    prompt += (
        "[SECTION 5: COGNITIVE REASONING LOOP (ReAct)]\n"
        "For every step of an autonomous task, format your output using structured tags:\n\n"
        "<thought>\n"
        "Analyze the current page state, previous action result, and what needs to happen next.\n"
        "Identify potential obstacles (e.g., cookie banners, dynamic overlays, login walls).\n"
        "</thought>\n"
        "<plan>\n"
        "1. [Completed] Past step description\n"
        "2. [Current] Target step description\n"
        "3. [Pending] Future step description\n"
        "</plan>\n"
        "<action>\n"
        "tool_name({\"param_key\": \"param_value\"})\n"
        "</action>\n\n"
        "When receiving an <observation> from the browser, verify whether the state changed as expected:\n"
        "  If SUCCESS: Proceed to the next step in <plan>.\n"
        "  If FAILED or STALLED: Initiate Self-Healing Heuristics (Section 6).\n\n"
    )

    # =========================================================================
    # SECTION 6: SELF-HEALING & ANTI-STALL HEURISTICS
    # =========================================================================
    prompt += (
        "[SECTION 6: SELF-HEALING & ANTI-STALL HEURISTICS]\n"
        "Websites are dynamic, noisy, and unpredictable. Handle obstacles gracefully:\n\n"
        "  Overlays & Cookie Banners: If a click fails or an element is occluded, call dismiss_overlay() "
        "to auto-detect and dismiss cookie/modal banners, then retry the original action.\n"
        "  Dynamic Hydration & Stalls: If a page is loading or elements haven't rendered, call "
        "wait_for_selector or issue a gentle scroll_page(delta_y=200) to trigger lazy-loading.\n"
        "  Selector Drift: If click_selector fails, switch to centroid_fallback_click(element_index) "
        "derived from get_page_content() interactive elements.\n"
        "  Infinite Scrolling: When gathering search or list results, issue incremental scrolls followed "
        "by short pauses, accumulating items up to the requested target.\n"
        "  Verification Failures: Never assume an action succeeded. If typing into a search box was "
        "attempted, verify the input value exists before pressing Enter.\n\n"
    )

    # =========================================================================
    # SECTION 7: HUMAN-IN-THE-LOOP (HITL) SAFETY GUARDRAILS
    # =========================================================================
    prompt += (
        "[SECTION 7: HUMAN-IN-THE-LOOP (HITL) SAFETY GUARDRAILS]\n"
        "You enforce a strict 3-tier security gate to protect the user:\n\n"
        "  GREEN TIER (Autonomous — execute automatically):\n"
        "    Reading pages, clicking search results, scrolling, extracting public tables, "
        "switching tabs, running web searches, taking screenshots, inspecting visual charts.\n\n"
        "  YELLOW TIER (Notify — execute with user visibility):\n"
        "    Filling non-sensitive form inputs, opening external links in new tabs, "
        "downloading public PDFs/CSV files, exporting data.\n\n"
        "  RED TIER (MANDATORY APPROVAL GATE — halt and await approval):\n"
        "    - Submitting payment credentials, credit card details, or financial transactions.\n"
        "    - Final \"Place Order\", \"Book Now\", \"Confirm Purchase\", or \"Checkout\" buttons.\n"
        "    - Deleting account data, modifying passwords, or granting OAuth permissions.\n"
        "    - Entering credentials into unknown or suspicious login forms.\n"
        "    - Running JavaScript containing fetch(), XMLHttpRequest, localStorage.clear, "
        "document.cookie mutation, or window.location reassignment.\n\n"
        "RULE: When encountering a RED TIER action, immediately halt execution, return "
        "status=approval_required with an explicit human-readable risk description, and "
        "await user approval before proceeding.\n\n"
    )

    # =========================================================================
    # SECTION 8: SYNTHESIS & OUTPUT STANDARDS (PERPLEXITY STYLE)
    # =========================================================================
    prompt += (
        "[SECTION 8: SYNTHESIS & OUTPUT STANDARDS]\n"
        "When presenting final research or workflow outcomes:\n\n"
        "  1. Lead with the direct, concise answer or executive summary.\n"
        "  2. Structure complex information with Markdown tables, bold bullet points, and key metrics.\n"
        "  3. Anchor every claim with numerical inline citations: [1], [2].\n"
        "  4. Append a \"Sources & Verification\" section listing URLs, page titles, and access timestamps.\n"
        "  5. If structured records were extracted, display the first 5 rows in chat and confirm "
        "the local CSV export path.\n"
    )

    # =========================================================================
    # SECTION 9: ACTIVE AGENT SKILLS
    # =========================================================================
    try:
        from backend.app.skills.registry import skill_registry
        skill_prompts = skill_registry.get_active_system_prompts(user_message or "", page_context)
        if skill_prompts:
            prompt += f"\n[SECTION 9: ACTIVE AGENT SKILLS]\n{skill_prompts}\n\n"
    except Exception:
        pass

    return prompt

@router.post("/chat")
async def chat(req: ChatRequest, db: AsyncSession = Depends(get_db)):
    repo = Repository(db)

    # 1. Fetch or create conversation
    conv_id = req.conversation_id
    if not conv_id:
        conv = await repo.create_conversation(title=req.message[:30] or "New Chat")
        conv_id = conv.id

    # 2. Extract or inspect current tab context if provided
    page_ctx = req.context or {}
    if req.tab_id and not page_ctx:
        try:
            obs = await bridge.call("browser.inspect", {})
            if obs:
                page_ctx = {
                    "url": obs.get("url"),
                    "title": obs.get("title"),
                    "visibleText": obs.get("visibleText")
                }
        except Exception:
            pass

    # 3. Store user message in DB
    await repo.add_message(
        conversation_id=conv_id,
        sender="user",
        content=req.message,
        tab_id=req.tab_id,
        url=page_ctx.get("url")
    )

    # 4. Route model and provider
    provider, model = ModelRouter.route_for_task(
        task_type="text",
        preferred_provider=req.provider_id,
        preferred_model=req.model
    )

    system_prompt = build_system_prompt(page_ctx, req.selected_text, user_message=req.message)
    comet_system_prompt = get_comet_system_prompt()
    messages = []
    if comet_system_prompt:
        messages.append({"role": "system", "content": comet_system_prompt})
    messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": req.message})

    # 5. Handle streaming or standard response
    if req.stream:
        async def event_generator():
            full_reply = ""
            try:
                async for chunk in provider.stream_completion(messages=messages, model=model):
                    full_reply += chunk
                    yield f"data: {json.dumps({'chunk': chunk, 'conversation_id': conv_id})}\n\n"
            finally:
                # Store assistant response in DB
                async with AsyncSessionLocal() as session:
                    r = Repository(session)
                    await r.add_message(
                        conversation_id=conv_id,
                        sender="assistant",
                        content=full_reply or "[No response generated]"
                    )
                yield f"data: [DONE]\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")
    else:
        result = await provider.chat_completion(messages=messages, model=model)
        reply_content = result.content

        # Store in DB
        await repo.add_message(
            conversation_id=conv_id,
            sender="assistant",
            content=reply_content
        )

        return ChatResponse(
            reply=reply_content,
            conversation_id=conv_id,
            model=model
        )
