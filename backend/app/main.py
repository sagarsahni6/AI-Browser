import asyncio
import os
import sys
import json
import uvicorn
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

    system_prompt = (
        "You are the autonomous AI Browser Agent with direct access to live browser tools.\n"
        "You can navigate to websites, inspect HTML and dynamic canvas/charts, evaluate JavaScript, "
        "extract Option Chain tables, click elements, fill inputs, take screenshots, and export CSV files.\n"
        "When the user asks you to open a site, search, extract data, inspect a chart, or interact, "
        "CALL THE RELEVANT TOOL IMMEDIATELY.\n"
        "After actions complete, provide a clear, helpful confirmation with structured data or key metrics."
    )
    if context:
        title = context.get("title", "")
        url = context.get("url", "")
        system_prompt += f"\n[CURRENT WEBPAGE CONTEXT]\nURL: {url}\nTitle: {title}\n"
        if context.get("visibleText"):
            system_prompt += f"Excerpt: {context['visibleText'][:1500]}\n"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": msg_content}
    ]

    reply_content = ""
    max_turns = 6
    turn = 0

    try:
        while turn < max_turns and not _agent_cancelled:
            turn += 1
            completion = await provider.chat_completion(
                messages=messages,
                model=model,
                tools=BROWSER_TOOLS
            )

            if completion.tool_calls and not _agent_cancelled:
                for tc in completion.tool_calls:
                    if _agent_cancelled:
                        break
                    fn_name = tc.get("function", {}).get("name")
                    raw_args = tc.get("function", {}).get("arguments", "{}")
                    try:
                        args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                    except Exception:
                        args = {}

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
                        "content": completion.content or f"Executing {fn_name}",
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
                reply_content = completion.content or "Action completed."
                break

        if _agent_cancelled:
            reply_content += "\n\n*(Agent execution stopped by user)*"
        elif not reply_content:
            reply_content = "Action completed."

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
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        await repo.update_task_status(task_id, status="cancelled", error="Cancelled by user")
        return {"status": "cancelled", "id": task_id}

async def handle_tasks_approve(params: dict):
    task_id = params.get("task_id")
    decision = params.get("decision", True)
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        if decision:
            await repo.update_task_status(task_id, status="running")
            # In a full flow this resumes the pending agent task or marks step approved
            return {"status": "approved", "id": task_id}
        else:
            await repo.update_task_status(task_id, status="cancelled", error="Action rejected by user")
            return {"status": "rejected", "id": task_id}

async def handle_tasks_reject(params: dict):
    task_id = params.get("task_id")
    reason = params.get("reason", "Action rejected by user")
    async with AsyncSessionLocal() as session:
        repo = Repository(session)
        await repo.update_task_status(task_id, status="cancelled", error=reason)
        return {"status": "rejected", "id": task_id, "reason": reason}

bridge.register_method("tasks.create", handle_tasks_create)
bridge.register_method("tasks.list", handle_tasks_list)
bridge.register_method("tasks.get", handle_tasks_get)
bridge.register_method("tasks.cancel", handle_tasks_cancel)
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

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Initialize SQLite database schema
    await init_db()

    # 2. Start stdin/stdout bridge in background task
    bridge_task = asyncio.create_task(bridge.start())

    # 3. Notify Electron that backend is ready
    bridge.notify_ready(port=settings.PORT, token=settings.SECRET_TOKEN)

    yield

    # Cleanup
    bridge.stop()
    bridge_task.cancel()

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
