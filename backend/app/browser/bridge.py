import asyncio
import json
import sys
import threading
import logging
from typing import Any, Callable, Coroutine, Dict, Optional
from backend.app.browser.protocol import JsonRpcRequest, JsonRpcResponse, JsonRpcError

logger = logging.getLogger("rpc_bridge")
handler = logging.StreamHandler(sys.stderr)
handler.setFormatter(logging.Formatter("[Python Bridge] %(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(handler)
logger.setLevel(logging.INFO)

class BrowserBridge:
    def __init__(self):
        self._next_id = 1
        self._pending_requests: Dict[int | str, asyncio.Future] = {}
        self._method_handlers: Dict[str, Callable[[dict], Coroutine[Any, Any, Any]]] = {}
        self._running = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None

    def register_method(self, method: str, handler_func: Callable[[dict], Coroutine[Any, Any, Any]]):
        self._method_handlers[method] = handler_func

    def notify_ready(self, port: int, token: str):
        msg = json.dumps({"type": "ready", "port": port, "token": token})
        sys.stdout.write(msg + "\n")
        sys.stdout.flush()

    def notify(self, method: str, params: Optional[dict] = None):
        msg = json.dumps({"jsonrpc": "2.0", "method": method, "params": params or {}})
        sys.stdout.write(msg + "\n")
        sys.stdout.flush()

    async def start(self):
        self._loop = asyncio.get_running_loop()
        self._running = True

        logger.info("BrowserBridge starting stdin background thread reader...")
        self._thread = threading.Thread(target=self._stdin_worker, daemon=True)
        self._thread.start()

    def _stdin_worker(self):
        logger.info("BrowserBridge stdin worker thread running.")
        while self._running:
            try:
                line = sys.stdin.readline()
                if not line:
                    logger.info("stdin EOF received, stopping bridge worker.")
                    break

                text = line.strip()
                if text and self._loop and self._loop.is_running():
                    asyncio.run_coroutine_threadsafe(self._handle_message(text), self._loop)
            except Exception as e:
                logger.error(f"Error reading from stdin: {e}")
                break

    async def _handle_message(self, text: str):
        try:
            data = json.loads(text)
        except Exception as e:
            logger.error(f"Invalid JSON received on stdin: {text} - {e}")
            return

        # 1. Ready or system event
        if data.get("type") == "ready":
            return

        # 2. Response to our call
        if "id" in data and ("result" in data or "error" in data):
            req_id = data["id"]
            future = self._pending_requests.pop(req_id, None)
            if future and not future.done():
                if data.get("error"):
                    future.set_exception(RuntimeError(data["error"].get("message", "RPC Error")))
                else:
                    future.set_result(data.get("result"))
            return

        # 3. Incoming call from Electron
        if "method" in data and "id" in data:
            req_id = data["id"]
            method = data["method"]
            params = data.get("params", {})

            handler_func = self._method_handlers.get(method)
            if not handler_func:
                self._send_response(JsonRpcResponse(
                    id=req_id,
                    error=JsonRpcError(code=-32601, message=f"Method not found: {method}")
                ))
                return

            try:
                res = await handler_func(params)
                self._send_response(JsonRpcResponse(id=req_id, result=res))
            except Exception as ex:
                logger.error(f"Handler error for {method}: {ex}")
                self._send_response(JsonRpcResponse(
                    id=req_id,
                    error=JsonRpcError(code=-32000, message=str(ex))
                ))
            return

    def _send_response(self, res: JsonRpcResponse):
        payload = res.model_dump_json()
        sys.stdout.write(payload + "\n")
        sys.stdout.flush()

    async def call(self, method: str, params: Optional[dict] = None, timeout: float = 15.0) -> Any:
        if not self._loop:
            self._loop = asyncio.get_running_loop()

        req_id = self._next_id
        self._next_id += 1

        future = self._loop.create_future()
        self._pending_requests[req_id] = future

        req = JsonRpcRequest(id=req_id, method=method, params=params or {})
        payload = req.model_dump_json()

        sys.stdout.write(payload + "\n")
        sys.stdout.flush()

        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            self._pending_requests.pop(req_id, None)
            raise TimeoutError(f"RPC call '{method}' timed out after {timeout}s")

    def stop(self):
        self._running = False

bridge = BrowserBridge()
