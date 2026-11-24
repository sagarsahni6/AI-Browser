import os
import logging
from typing import Dict, Any, Optional
from backend.app.documents.pdf_service import PDFService
from backend.app.tools.executor import _normalize_response

logger = logging.getLogger("file_agent")

class FileAgent:
    """
    Specialist agent for safe filesystem operations, sandboxed file read/write,
    and PDF processing without directory traversal vulnerabilities.
    """

    ALLOWED_DIRECTORIES = [
        os.path.abspath(os.getcwd()),
        os.path.abspath(os.path.join(os.getcwd(), "data")),
        os.path.abspath(os.path.join(os.getcwd(), "downloads")),
    ]

    @classmethod
    def _is_safe_path(cls, path: str) -> bool:
        norm = os.path.abspath(os.path.expanduser(path))
        # Prevent traversal
        for allowed in cls.ALLOWED_DIRECTORIES:
            if norm.startswith(allowed):
                return True
        return False

    @classmethod
    async def execute_step(cls, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        if action == "read_file":
            path = parameters.get("path", "")
            if not cls._is_safe_path(path):
                return _normalize_response({"status": "error", "error": f"Access denied: path '{path}' outside sandbox."}, action)
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                return _normalize_response({"status": "success", "content": content, "path": path, "length": len(content)}, action)
            except Exception as e:
                return _normalize_response({"status": "error", "error": str(e)}, action)

        elif action == "write_file":
            path = parameters.get("path", "")
            content = parameters.get("content", "")
            overwrite = bool(parameters.get("overwrite", True))
            if not cls._is_safe_path(path):
                return _normalize_response({"status": "error", "error": f"Access denied: path '{path}' outside sandbox."}, action)
            try:
                os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
                mode = "w" if overwrite else "a"
                with open(path, mode, encoding="utf-8") as f:
                    f.write(content)
                return _normalize_response({"status": "success", "written_bytes": len(content), "path": path}, action)
            except Exception as e:
                return _normalize_response({"status": "error", "error": str(e)}, action)

        elif action == "read_pdf":
            path_or_url = parameters.get("path_or_url", "")
            max_pages = int(parameters.get("max_pages", 50))
            res = await PDFService.read_pdf(path_or_url, max_pages)
            return _normalize_response(res, action)

        elif action == "summarize_pdf":
            path_or_url = parameters.get("path_or_url", "")
            query = parameters.get("query")
            res = await PDFService.summarize_pdf(path_or_url, query)
            return _normalize_response(res, action)

        else:
            from backend.app.tools.executor import ToolExecutor
            return await ToolExecutor.execute(action, parameters)
