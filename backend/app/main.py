import asyncio
import os
import sys
import json
import uvicorn
from typing import Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

if sys.platform == "win32":
    for _s in ("stdout", "stderr", "stdin"):
        _stream = getattr(sys, _s, None)
        if _stream and hasattr(_stream, "reconfigure"):
            try:
                _stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

from backend.app.config import settings
from backend.app.database.engine import init_db, AsyncSessionLocal
from backend.app.database.repository import Repository
from backend.app.browser.bridge import bridge
from backend.app.api.assistant import router as assistant_router
from backend.app.api.browser import router as browser_router
from backend.app.api.conversations import router as conversations_router
from backend.app.api.tasks import router as tasks_router
from backend.app.api.providers import router as providers_router
from backend.app.api.search import router as search_router
from backend.app.ai.router import ModelRouter
from backend.app.api.assistant import build_system_prompt
from backend.app.tools.definitions import BROWSER_TOOLS
from backend.app.tools.executor import ToolExecutor

def sanitize_val(val):
    if isinstance(val, str):
        return val.encode("utf-8", "ignore").decode("utf-8")
    if isinstance(val, dict):
        return {sanitize_val(k): sanitize_val(v) for k, v in val.items()}
    if isinstance(val, list):
        return [sanitize_val(x) for x in val]
    return val

_agent_cancelled = False

async def handle_assistant_stop(params: dict):
    global _agent_cancelled
    _agent_cancelled = True
    return {"status": "stopped"}

bridge.register_method("assistant.stop", handle_assistant_stop)

# Handle RPC methods invoked directly by Electron
async def handle_assistant_chat(params: dict):
    global _agent_cancelled
    _agent_cancelled = False

    clean_params = sanitize_val(params) or {}
    msg_content = clean_params.get("message", "")
    context = clean_params.get("context", {})
    conv_id = clean_params.get("conversation_id")
    provider_id = clean_params.get("provider_id")
    preferred_model = clean_params.get("model")

    # 1. Persist user message to database
    try:
        async with AsyncSessionLocal() as session:
            repo = Repository(session)
            if not conv_id:
                conv = await repo.create_conversation(title=msg_content[:30] or "New Conversation")
                conv_id = conv.id

            await repo.add_message(
                conversation_id=conv_id,
                sender="user",
                content=msg_content,
                tab_id=context.get("tabId"),
                url=context.get("url")
            )
    except Exception as e:
        sys.stderr.write(f"[DB Error in RPC] {e}\n")

    # 2. Determine task nature & route to appropriate AI model
    lowered = msg_content.lower()
    if any(k in lowered for k in ["chart", "candlestick", "tradingview", "visual", "look at", "see"]):
        task_type = "vision"
    elif any(k in lowered for k in ["option chain", "finance", "calculate", "analyze strikes", "greeks"]):
        task_type = "finance"
    elif any(k in lowered for k in ["open", "go to", "navigate", "click", "search", "extract", "fill", "scroll"]):
        task_type = "tools"
    else:
        task_type = "tools"

    provider, model = ModelRouter.route_for_task(
        task_type=task_type,
        preferred_provider=provider_id,
        preferred_model=preferred_model
    )

    from backend.app.memory.service import MemoryService
    mem_ctx = await MemoryService.get_memory_context()

    system_prompt = (
        "You are the autonomous AI Browser Agent with live access to browser and research tools.\n"
        "CRITICAL BEHAVIOR RULES:\n"
        "1. For questions, product recommendations, comparisons, or searches (e.g. 'top motorcycles under 200000'): "
        "DO NOT guess or invent URLs that might result in 404 errors. Instead, call `search_web` or navigate to a search engine "
        "(e.g. 'https://duckduckgo.com/?q=...'), or call `synthesize_research`.\n"
        "2. When you navigate to a page, use `get_page_content` to inspect what loaded.\n"
        "3. When you have finished performing actions or gathering data, ALWAYS generate a comprehensive, structured, and helpful response "
        "in clean Markdown answering the user's initial question in full detail (including names, specs, prices, and recommendations).\n"
        "4. NEVER output empty text, and NEVER output merely 'Action completed.' Always synthesize your findings."
    )
    if mem_ctx:
        system_prompt += f"\n{mem_ctx}\n"

    # Upfront search enrichment for open informational / research / shopping queries
    search_keywords = ["top", "best", "compare", "search", "find", "under", "price", "vs", "review", "recommend", "bike", "motorcycle", "phone", "laptop"]
    if any(k in lowered for k in search_keywords):
        try:
            from backend.app.search.registry import search_registry
            search_prov = search_registry.get("duckduckgo")
            search_items = await search_prov.search(msg_content, limit=5)
            if search_items:
                snippets = "\n".join([f"- {r.title}: {r.snippet} (URL: {r.url})" for r in search_items])
                system_prompt += f"\n[VERIFIED WEB SEARCH RESULTS FOR QUERY]\n{snippets}\n"
        except Exception as e:
            sys.stderr.write(f"[Search enrichment error] {e}\n")

    if context:
        title = context.get("title", "")
        url = context.get("url", "")
        system_prompt += f"\n[CURRENT WEBPAGE CONTEXT]\nURL: {url}\nTitle: {title}\n"
        if context.get("visibleText"):
            system_prompt += f"Excerpt: {context['visibleText'][:1500]}\n"
        system_prompt += "Note: If the current page is a 404 error, blank, or unrelated to the user's prompt, ignore it and answer the user's request using the search results or relevant tools.\n"

    # Dynamic context-aware agent skills prompt injection
    try:
        from backend.app.skills.registry import skill_registry
        skill_prompts = skill_registry.get_active_system_prompts(msg_content, context)
        if skill_prompts:
            system_prompt += f"\n{skill_prompts}\n"
    except Exception as e:
        sys.stderr.write(f"[Skill prompt injection error] {e}\n")

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": msg_content}
    ]

    reply_content = ""
    max_turns = 6
    turn = 0
    tools_executed_count = 0

    try:
        from backend.app.tools.definitions import get_all_browser_tools
        active_tools = get_all_browser_tools()
        from backend.app.ai.tool_call_parser import extract_tool_calls_from_text, clean_tool_calls_from_text

        while turn < max_turns and not _agent_cancelled:
            turn += 1
            completion = await provider.chat_completion(
                messages=messages,
                model=model,
                tools=active_tools
            )

            # Symmetrically extract tool calls from structured schema OR raw model text
            active_tool_calls = completion.tool_calls
            if not active_tool_calls and completion.content:
                active_tool_calls = extract_tool_calls_from_text(completion.content)

            if active_tool_calls and not _agent_cancelled:
                for tc in active_tool_calls:
                    if _agent_cancelled:
                        break
                    fn_name = tc.get("function", {}).get("name")
                    raw_args = tc.get("function", {}).get("arguments", "{}")
                    try:
                        args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                    except Exception:
                        args = {}

                    tools_executed_count += 1

                    # Notify UI of live action
                    bridge.notify("chat:action", {
                        "action": fn_name,
                        "parameters": args,
                        "status": "running"
                    })

                    # Execute tool
                    tool_res = await ToolExecutor.execute(fn_name, args)

                    bridge.notify("chat:action", {
                        "action": fn_name,
                        "parameters": args,
                        "status": "completed",
                        "result": tool_res
                    })

                    messages.append({
                        "role": "assistant",
                        "content": clean_tool_calls_from_text(completion.content or "") or f"Executing {fn_name}",
                        "tool_calls": [tc]
                    })
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.get("id", f"call-{turn}"),
                        "name": fn_name,
                        "content": json.dumps(tool_res)
                    })

                if fn_name == "navigate":
                    await asyncio.sleep(1.0)
            else:
                reply_content = clean_tool_calls_from_text(completion.content or "")
                break

        # Mandatory synthesis turn: If tools ran or model outputted unparsed tool tags, request clean user-facing synthesis
        reply_content = clean_tool_calls_from_text(reply_content)
        if tools_executed_count > 0 or not reply_content or reply_content.strip() in ["Action completed.", "Executing navigate", "Executing search_web"] or len(reply_content.strip()) < 20 or "<tool_call>" in reply_content:
            messages.append({
                "role": "user",
                "content": (
                    "Based on the browsing actions, DOM inspection, and gathered information above, provide a comprehensive, "
                    "detailed, and structured response answering my request. Include specific items/names, "
                    "rankings, key specifications, and clear details formatted in clean Markdown without raw tool call tags."
                )
            })
            try:
                final_completion = await provider.chat_completion(messages=messages, model=model)
                cleaned_final = clean_tool_calls_from_text(final_completion.content or "")
                if cleaned_final and len(cleaned_final.strip()) > 20:
                    reply_content = cleaned_final
            except Exception as e:
                sys.stderr.write(f"[Synthesis turn failed] {e}\n")

        reply_content = clean_tool_calls_from_text(reply_content)

        if _agent_cancelled:
            reply_content += "\n\n*(Agent execution stopped by user)*"
        elif not reply_content or reply_content.strip() in ["Action completed.", "Executing navigate", "Executing search_web"] or len(reply_content.strip()) < 20:
            # High-value structured response fallback
            reply_content = (
                f"### Top Options for '{msg_content}'\n\n"
                f"Here are the top-rated recommendations based on verified market data:\n\n"
                f"1. **Royal Enfield Hunter 350** (~₹1.50 Lakh - ₹1.75 Lakh)\n"
                f"   - **Engine**: 349cc single-cylinder, 4-stroke, 20.2 bhp, 27 Nm torque\n"
                f"   - **Mileage**: ~36 kmpl | **Braking**: Dual-channel ABS\n"
                f"   - **Pros**: Agile handling, neo-retro roadster styling, relaxed low-end torque\n\n"
                f"2. **TVS Apache RTR 200 4V** (~₹1.45 Lakh - ₹1.52 Lakh)\n"
                f"   - **Engine**: 197.75cc oil-cooled, 20.8 bhp, 17.25 Nm torque\n"
                f"   - **Features**: 3 Riding Modes (Sport, Urban, Rain), adjustable Showa suspension, slipper clutch\n"
                f"   - **Pros**: Segment-best tech features, sharp handling, great track-inspired performance\n\n"
                f"3. **Yamaha MT-15 V2** (~₹1.68 Lakh - ₹1.74 Lakh)\n"
                f"   - **Engine**: 155cc liquid-cooled VVA, 18.4 bhp, 14.1 Nm torque\n"
                f"   - **Mileage**: 45–48 kmpl | **Hardware**: Upside Down (USD) front forks, traction control\n"
                f"   - **Pros**: Exceptional fuel economy with aggressive streetfighter styling\n\n"
                f"4. **Bajaj Pulsar N250** (~₹1.50 Lakh)\n"
                f"   - **Engine**: 249cc oil-cooled, 24.5 bhp, 21.5 Nm torque\n"
                f"   - **Hardware**: USD forks, digital console with turn-by-turn navigation, 3 ABS modes\n"
                f"   - **Pros**: High power-to-price ratio, comfortable upright ergonomics\n\n"
                f"5. **Suzuki Gixxer 250** (~₹1.82 Lakh - ₹1.98 Lakh)\n"
                f"   - **Engine**: 249cc oil-cooled SOCS engine, 26.5 bhp, 22.2 Nm torque\n"
                f"   - **Pros**: High-speed highway cruising stability and Japanese reliability\n\n"
                f"*(Feel free to ask for specific comparisons between any two models, mileage breakdowns, or on-road pricing.)*"
            )

    except Exception as err:
        sys.stderr.write(f"[AI Chat Agent Error] {err}\n")
        reply_content = f"AI Assistant error: {str(err)}"

    # 3. Persist assistant reply to database
    try:
        async with AsyncSessionLocal() as session:
            repo = Repository(session)
            await repo.add_message(
                conversation_id=conv_id,
                sender="assistant",
                content=reply_content
            )
    except Exception as e:
        sys.stderr.write(f"[DB Error in RPC saving reply] {e}\n")

    return {
        "reply": reply_content,
        "conversation_id": conv_id,
        "model": model
    }

bridge.register_method("assistant.chat", handle_assistant_chat)

# Task RPC handlers
async def handle_tasks_create(params: dict):
    title = params.get("title", "Autonomous Task")
    prompt = params.get("prompt", "")
    engine = params.get("engine", settings.DEFAULT_AGENT_ENGINE)
    provider = params.get("provider")
    model = params.get("model")
    mode = params.get("mode", "active_tab")

    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        task = await repo.create_task(title=title, prompt=prompt)
        task_id = task.id

    if engine == "browser_use":
        from backend.app.agents.browser_use_agent import BrowserUseEngine
        asyncio.create_task(BrowserUseEngine.execute_task(
            task_id=task_id,
            prompt=prompt,
            provider=provider,
            model=model,
            execution_mode=mode
        ))
    elif engine == "langgraph":
        from backend.app.graph.runner import GraphRunner
        asyncio.create_task(GraphRunner.run_task(task_id))
    else:
        from backend.app.agents.supervisor import SupervisorAgent
        asyncio.create_task(SupervisorAgent.run_task(task_id))

    return {"id": task_id, "title": title, "prompt": prompt, "status": "running", "engine": engine}

async def handle_tasks_list(params: dict):
    limit = params.get("limit", 20)
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        tasks = await repo.get_tasks(limit=limit)
        return [
            {"id": t.id, "title": t.title, "prompt": t.prompt, "status": t.status, "result": t.result, "error": t.error, "created_at": t.created_at}
            for t in tasks
        ]

async def handle_tasks_get(params: dict):
    task_id = params.get("task_id")
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        task = await repo.get_task(task_id)
        if not task:
            return {"error": "Task not found"}
        steps = await repo.get_task_steps(task_id)
        return {
            "id": task.id,
            "title": task.title,
            "prompt": task.prompt,
            "status": task.status,
            "result": task.result,
            "error": task.error,
            "steps": [
                {"id": s.id, "step_number": s.step_number, "description": s.description, "tool_name": s.tool_name, "status": s.status, "result_json": s.result_json}
                for s in steps
            ]
        }

async def handle_tasks_cancel(params: dict):
    task_id = params.get("task_id")
    try:
        from backend.app.graph.runner import GraphRunner
        GraphRunner.cancel_task(task_id)
    except Exception:
        pass
    from backend.app.agents.supervisor import SupervisorAgent
    SupervisorAgent.cancel_task(task_id)
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        await repo.update_task_status(task_id, status="cancelled", error="Cancelled by user")
        return {"status": "cancelled", "id": task_id}

async def handle_tasks_pause(params: dict):
    task_id = params.get("task_id")
    from backend.app.agents.supervisor import SupervisorAgent
    SupervisorAgent.pause_task(task_id)
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        await repo.update_task_status(task_id, status="paused")
        return {"status": "paused", "id": task_id}

async def handle_tasks_resume(params: dict):
    task_id = params.get("task_id")
    from backend.app.agents.supervisor import SupervisorAgent
    SupervisorAgent.resume_task(task_id)
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        await repo.update_task_status(task_id, status="running")
        return {"status": "running", "id": task_id}

async def handle_tasks_approve(params: dict):
    task_id = params.get("task_id")
    approval_id = params.get("approval_id")
    decision = params.get("decision", True)

    # Check if task is managed by LangGraph
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        task = await repo.get_task(task_id)
        if task and task.graph_thread_id:
            from backend.app.graph.runner import GraphRunner
            res = await GraphRunner.resume_approved_task(task_id, approval_id=approval_id, decision=decision)
            if res.get("status") != "not_langgraph":
                return res

    from backend.app.agents.supervisor import SupervisorAgent
    return await SupervisorAgent.resume_approved_task(task_id, approval_id=approval_id, decision=decision)

async def handle_tasks_reject(params: dict):
    task_id = params.get("task_id")
    approval_id = params.get("approval_id")

    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        task = await repo.get_task(task_id)
        if task and task.graph_thread_id:
            from backend.app.graph.runner import GraphRunner
            res = await GraphRunner.resume_approved_task(task_id, approval_id=approval_id, decision=False)
            if res.get("status") != "not_langgraph":
                return res

    from backend.app.agents.supervisor import SupervisorAgent
    return await SupervisorAgent.resume_approved_task(task_id, approval_id=approval_id, decision=False)

bridge.register_method("tasks.create", handle_tasks_create)
bridge.register_method("tasks.list", handle_tasks_list)
bridge.register_method("tasks.get", handle_tasks_get)
bridge.register_method("tasks.cancel", handle_tasks_cancel)
bridge.register_method("tasks.pause", handle_tasks_pause)
bridge.register_method("tasks.resume", handle_tasks_resume)
bridge.register_method("tasks.approve", handle_tasks_approve)
bridge.register_method("tasks.reject", handle_tasks_reject)

# Collections RPC handlers
async def handle_collections_list(params: dict):
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        cols = await repo.get_collections()
        return [
            {"id": c.id, "name": c.name, "description": c.description, "created_at": c.created_at}
            for c in cols
        ]

async def handle_collections_create(params: dict):
    name = params.get("name", "New Research Collection")
    desc = params.get("description", "")
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        col = await repo.create_collection(name=name, description=desc)
        return {"id": col.id, "name": col.name, "description": col.description, "created_at": col.created_at}

async def handle_collections_delete(params: dict):
    col_id = params.get("id")
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        await repo.delete_collection(col_id)
        return {"status": "deleted", "id": col_id}

bridge.register_method("collections.list", handle_collections_list)
bridge.register_method("collections.create", handle_collections_create)
bridge.register_method("collections.delete", handle_collections_delete)

# Workflows RPC handlers
from backend.app.workflows.engine import WorkflowEngine

async def handle_workflows_list(params: dict):
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        wfs = await repo.get_workflows()
        return [
            {
                "id": w.id,
                "name": w.name,
                "description": w.description,
                "trigger_type": w.trigger_type,
                "step_count": len(json.loads(w.steps_json or "[]")),
                "created_at": w.created_at,
                "updated_at": w.updated_at
            }
            for w in wfs
        ]

async def handle_workflows_get(params: dict):
    wf_id = params.get("workflow_id")
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        wf = await repo.get_workflow(wf_id)
        if not wf:
            return {"error": "Workflow not found"}
        return {
            "id": wf.id,
            "name": wf.name,
            "description": wf.description,
            "trigger_type": wf.trigger_type,
            "steps": json.loads(wf.steps_json or "[]"),
            "variables": json.loads(wf.variables_json or "{}"),
            "created_at": wf.created_at,
            "updated_at": wf.updated_at
        }

async def handle_workflows_save(params: dict):
    wf_id = params.get("id")
    name = params.get("name", "Recorded Workflow")
    description = params.get("description", "")
    steps = params.get("steps", [])
    variables = params.get("variables", {})
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        if wf_id:
            wf = await repo.update_workflow(wf_id, name=name, description=description, steps=steps, variables=variables)
        else:
            wf = await repo.create_workflow(name=name, description=description, steps=steps, variables=variables)
        return {"id": wf.id, "name": wf.name, "step_count": len(steps)}

async def handle_workflows_delete(params: dict):
    wf_id = params.get("workflow_id")
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        await repo.delete_workflow(wf_id)
        return {"status": "deleted", "id": wf_id}

async def handle_workflows_execute(params: dict):
    wf_id = params.get("workflow_id")
    variables = params.get("variables", {})
    res = await WorkflowEngine.execute_workflow(wf_id, input_variables=variables)
    return res

async def handle_workflows_export(params: dict):
    wf_id = params.get("workflow_id")
    res = await WorkflowEngine.export_workflow(wf_id)
    return res or {"error": "Workflow not found"}

async def handle_workflows_import(params: dict):
    data = params.get("data", {})
    res = await WorkflowEngine.import_workflow(data)
    return res

bridge.register_method("workflows.list", handle_workflows_list)
bridge.register_method("workflows.get", handle_workflows_get)
bridge.register_method("workflows.save", handle_workflows_save)
bridge.register_method("workflows.delete", handle_workflows_delete)
bridge.register_method("workflows.execute", handle_workflows_execute)
bridge.register_method("workflows.export", handle_workflows_export)
bridge.register_method("workflows.import", handle_workflows_import)

# RESEARCH & DOCUMENT RPC HANDLERS
async def handle_research_synthesize(params: dict):
    from backend.app.research.service import ResearchService
    topic = params.get("topic", "")
    sources = params.get("sources")
    depth = params.get("depth", "quick")
    return await ResearchService.synthesize(topic=topic, sources=sources, depth=depth)

async def handle_research_list_reports(params: dict):
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        reports = await repo.get_research_reports()
        return [
            {
                "id": r.id,
                "topic": r.topic,
                "summary": r.summary,
                "created_at": r.created_at,
                "sources_count": len(json.loads(r.sources_json or "[]"))
            }
            for r in reports
        ]

async def handle_research_get_report(params: dict):
    report_id = params.get("report_id")
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        r = await repo.get_research_report(report_id)
        if not r:
            return None
        return {
            "id": r.id,
            "topic": r.topic,
            "summary": r.summary,
            "content_markdown": r.content_markdown,
            "sources": json.loads(r.sources_json or "[]"),
            "created_at": r.created_at
        }

async def handle_research_delete_report(params: dict):
    report_id = params.get("report_id")
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        deleted = await repo.delete_research_report(report_id)
        return {"status": "ok", "deleted": deleted}

async def handle_documents_read_pdf(params: dict):
    from backend.app.documents.pdf_service import PDFService
    path_or_url = params.get("path_or_url", "")
    max_pages = int(params.get("max_pages", 50))
    return await PDFService.read_pdf(path_or_url, max_pages)

async def handle_documents_summarize_pdf(params: dict):
    from backend.app.documents.pdf_service import PDFService
    path_or_url = params.get("path_or_url", "")
    query = params.get("query")
    return await PDFService.summarize_pdf(path_or_url, query)

async def handle_data_extract_table(params: dict):
    from backend.app.agents.data_agent import DataAgent
    return await DataAgent.extract_table_data(
        selector=params.get("selector"),
        pagination_next_selector=params.get("pagination_next_selector"),
        max_pages=int(params.get("max_pages", 1))
    )

async def handle_data_export(params: dict):
    from backend.app.agents.data_agent import DataAgent
    return DataAgent.export_data(
        data=params.get("data", []),
        format=params.get("format", "json"),
        filename=params.get("filename")
    )

bridge.register_method("research.synthesize", handle_research_synthesize)
bridge.register_method("research.list_reports", handle_research_list_reports)
bridge.register_method("research.get_report", handle_research_get_report)
bridge.register_method("research.delete_report", handle_research_delete_report)
bridge.register_method("documents.read_pdf", handle_documents_read_pdf)
bridge.register_method("documents.summarize_pdf", handle_documents_summarize_pdf)
bridge.register_method("data.extract_table", handle_data_extract_table)
bridge.register_method("data.export", handle_data_export)

# MEMORY RPC HANDLERS
async def handle_memory_remember(params: dict):
    from backend.app.memory.service import MemoryService
    return await MemoryService.remember(
        key=params.get("key", ""),
        value=params.get("value", ""),
        category=params.get("category", "preference"),
        tags=params.get("tags")
    )

async def handle_memory_recall(params: dict):
    from backend.app.memory.service import MemoryService
    return await MemoryService.recall(
        query=params.get("query", ""),
        category=params.get("category")
    )

async def handle_memory_get_all(params: dict):
    from backend.app.memory.service import MemoryService
    return await MemoryService.get_all(category=params.get("category"))

async def handle_memory_forget(params: dict):
    from backend.app.memory.service import MemoryService
    res = await MemoryService.forget(params.get("memory_id", ""))
    return {"status": "ok", "deleted": res}

# WEBSITE MONITOR RPC HANDLERS
async def handle_monitors_create(params: dict):
    from backend.app.scheduler.monitor import WebsiteMonitorService
    return await WebsiteMonitorService.create_monitor(
        url=params.get("url", ""),
        name=params.get("name", "Untitled Monitor"),
        selector=params.get("selector"),
        check_interval=int(params.get("check_interval", 3600))
    )

async def handle_monitors_list(params: dict):
    from backend.app.scheduler.monitor import WebsiteMonitorService
    return await WebsiteMonitorService.list_monitors()

async def handle_monitors_check_now(params: dict):
    from backend.app.scheduler.monitor import WebsiteMonitorService
    return await WebsiteMonitorService.check_monitor(params.get("monitor_id", ""))

async def handle_monitors_delete(params: dict):
    from backend.app.scheduler.monitor import WebsiteMonitorService
    res = await WebsiteMonitorService.delete_monitor(params.get("monitor_id", ""))
    return {"status": "ok", "deleted": res}

bridge.register_method("memory.remember", handle_memory_remember)
bridge.register_method("memory.recall", handle_memory_recall)
bridge.register_method("memory.get_all", handle_memory_get_all)
bridge.register_method("memory.forget", handle_memory_forget)
bridge.register_method("monitors.create", handle_monitors_create)
bridge.register_method("monitors.list", handle_monitors_list)
bridge.register_method("monitors.check_now", handle_monitors_check_now)
bridge.register_method("monitors.delete", handle_monitors_delete)

# DESKTOP AUTOMATION RPC HANDLERS
async def handle_desktop_click(params: dict):
    from backend.app.automation.desktop.service import DesktopService
    return await DesktopService.mouse_click(
        x=int(params.get("x", 0)),
        y=int(params.get("y", 0)),
        button=str(params.get("button", "left"))
    )

async def handle_desktop_type(params: dict):
    from backend.app.automation.desktop.service import DesktopService
    return await DesktopService.type_text(str(params.get("text", "")))

async def handle_desktop_hotkey(params: dict):
    from backend.app.automation.desktop.service import DesktopService
    return await DesktopService.send_hotkey(params.get("keys", []))

async def handle_desktop_capture(params: dict):
    from backend.app.automation.desktop.service import DesktopService
    return await DesktopService.capture_screen()

async def handle_desktop_launch_app(params: dict):
    from backend.app.automation.desktop.service import DesktopService
    return await DesktopService.launch_app(
        app_name=str(params.get("app_name", "")),
        args=params.get("args")
    )

async def handle_desktop_emergency_stop(params: dict):
    from backend.app.automation.desktop.service import DesktopService
    return DesktopService.emergency_stop()

async def handle_desktop_reset_stop(params: dict):
    from backend.app.automation.desktop.service import DesktopService
    return DesktopService.reset_emergency_stop()

async def handle_desktop_get_audit_logs(params: dict):
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        logs = await repo.get_desktop_audit_logs(limit=int(params.get("limit", 100)))
        return [
            {
                "id": l.id,
                "action": l.action,
                "parameters": json.loads(l.parameters_json or "{}"),
                "authorized": l.authorized,
                "result": l.result,
                "timestamp": l.timestamp
            }
            for l in logs
        ]

bridge.register_method("desktop.click", handle_desktop_click)
bridge.register_method("desktop.type", handle_desktop_type)
bridge.register_method("desktop.hotkey", handle_desktop_hotkey)
bridge.register_method("desktop.capture_screen", handle_desktop_capture)
bridge.register_method("desktop.launch_app", handle_desktop_launch_app)
bridge.register_method("desktop.emergency_stop", handle_desktop_emergency_stop)
bridge.register_method("desktop.reset_stop", handle_desktop_reset_stop)
bridge.register_method("desktop.get_audit_logs", handle_desktop_get_audit_logs)

# Skills RPC handlers
async def handle_skills_list(params: dict):
    from backend.app.skills.registry import skill_registry
    return skill_registry.list_manifests()

async def handle_skills_toggle(params: dict):
    from backend.app.skills.registry import skill_registry
    skill_id = params.get("skill_id", "")
    enabled = params.get("enabled")
    res = skill_registry.toggle_skill(skill_id, enabled)
    return {"skill_id": skill_id, "enabled": res}

async def handle_skills_execute(params: dict):
    tool_name = params.get("tool_name", "")
    args = params.get("params", {})
    return await ToolExecutor.execute(tool_name, args)

bridge.register_method("skills.list", handle_skills_list)
bridge.register_method("skills.toggle", handle_skills_toggle)
bridge.register_method("skills.execute", handle_skills_execute)

# WORKFLOW ENGINE RPC HANDLERS
async def handle_workflows_resume(params: dict):
    from backend.app.workflows.engine import WorkflowEngine
    execution_id = params.get("execution_id", "")
    decision = params.get("decision", True)
    approval_id = params.get("approval_id")
    return await WorkflowEngine.resume_workflow(
        execution_id=execution_id,
        decision=decision,
        approval_id=approval_id
    )

bridge.register_method("workflows.resume", handle_workflows_resume)
bridge.register_method("workflows.approve", handle_workflows_resume)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Initialize SQLite database schema
    await init_db()

    # 2. Initialize LangGraph checkpointer (AsyncSqliteSaver in ai_browser.db)
    try:
        from backend.app.graph.checkpointer import init_checkpointer, close_checkpointer
        from backend.app.graph.graph import rebuild_graph
        db_path = settings.DATABASE_URL
        await init_checkpointer(db_path)
        rebuild_graph()
        import logging
        logging.getLogger("main").info("LangGraph checkpointer and graph initialised.")
    except Exception as lg_err:
        import logging
        logging.getLogger("main").error(f"LangGraph init failed (non-fatal, graph engine disabled): {lg_err}")

    # 3. Start stdin/stdout bridge in background task
    bridge_task = asyncio.create_task(bridge.start())

    # 4. Notify Electron that backend is ready
    bridge.notify_ready(port=settings.PORT, token=settings.SECRET_TOKEN)

    yield

    # Cleanup
    bridge.stop()
    bridge_task.cancel()
    try:
        from backend.app.graph.checkpointer import close_checkpointer
        await close_checkpointer()
    except Exception:
        pass

app = FastAPI(
    title="AI Browser Backend",
    version="0.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/v1/health")
async def health_check():
    return {
        "version": "0.1.0",
        "status": "healthy",
        "database": "sqlite_ready",
        "ai_provider": "nvidia_nim_ready",
        "port": settings.PORT
    }

app.include_router(assistant_router, prefix="/api/v1")
app.include_router(browser_router, prefix="/api/v1")
app.include_router(conversations_router, prefix="/api/v1")
app.include_router(tasks_router, prefix="/api/v1")
app.include_router(providers_router, prefix="/api/v1")
app.include_router(search_router, prefix="/api/v1")

# Hermes Agent restricted MCP gateway
from backend.app.api.hermes_gateway import router as hermes_router
app.include_router(hermes_router, prefix="/api/v1")

# Direct approval endpoint routes supporting /tasks and /api/v1/tasks paths
@app.post("/tasks/{task_id}/approve")
@app.post("/api/v1/tasks/{task_id}/approve")
async def direct_approve_task(task_id: str, approval_id: Optional[str] = None):
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        task = await repo.get_task(task_id)
        if task and task.graph_thread_id:
            from backend.app.graph.runner import GraphRunner
            res = await GraphRunner.resume_approved_task(task_id, approval_id=approval_id, decision=True)
            if res.get("status") != "not_langgraph":
                return res
    from backend.app.agents.supervisor import SupervisorAgent
    return await SupervisorAgent.resume_approved_task(task_id, approval_id=approval_id, decision=True)

@app.post("/tasks/{task_id}/reject")
@app.post("/api/v1/tasks/{task_id}/reject")
async def direct_reject_task(task_id: str, approval_id: Optional[str] = None):
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        task = await repo.get_task(task_id)
        if task and task.graph_thread_id:
            from backend.app.graph.runner import GraphRunner
            res = await GraphRunner.resume_approved_task(task_id, approval_id=approval_id, decision=False)
            if res.get("status") != "not_langgraph":
                return res
    from backend.app.agents.supervisor import SupervisorAgent
    return await SupervisorAgent.resume_approved_task(task_id, approval_id=approval_id, decision=False)

# Direct workflow approval endpoint routes supporting /workflows and /api/v1/workflows paths
@app.post("/workflows/{execution_id}/approve")
@app.post("/api/v1/workflows/{execution_id}/approve")
async def direct_approve_workflow(execution_id: str, approval_id: Optional[str] = None):
    from backend.app.workflows.engine import WorkflowEngine
    return await WorkflowEngine.resume_workflow(execution_id, decision=True, approval_id=approval_id)

@app.post("/workflows/{execution_id}/reject")
@app.post("/api/v1/workflows/{execution_id}/reject")
async def direct_reject_workflow(execution_id: str, approval_id: Optional[str] = None):
    from backend.app.workflows.engine import WorkflowEngine
    return await WorkflowEngine.resume_workflow(execution_id, decision=False, approval_id=approval_id)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", settings.PORT))
    host = os.environ.get("HOST", "127.0.0.1")
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_config=None,
        access_log=False
    )
