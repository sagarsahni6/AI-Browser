import asyncio
import hashlib
import logging
import re
import time
from typing import Dict, Any, List, Optional
import httpx
from sqlalchemy import select
from backend.app.database.engine import AsyncSessionLocal
from backend.app.database.repository import Repository
from backend.app.database.models import WebsiteMonitor
from backend.app.browser.bridge import bridge

logger = logging.getLogger("website_monitor")

class WebsiteMonitorService:
    """
    Website Change Monitoring Service:
    Periodically checks target URLs or DOM selectors, calculates content hashes,
    and alerts the user when meaningful diffs occur.
    """

    @staticmethod
    def _compute_hash(text: str) -> str:
        clean = " ".join(text.split())
        return hashlib.sha256(clean.encode("utf-8")).hexdigest()

    @classmethod
    async def fetch_target_content(cls, url: str, selector: Optional[str] = None) -> Dict[str, Any]:
        """Fetch URL content via HTTP and extract relevant text."""
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0 AI-Browser-Monitor/1.0"})
                if resp.status_code == 200:
                    html = resp.text
                    clean = re.sub(r"<(script|style).*?</\1>", " ", html, flags=re.DOTALL | re.IGNORECASE)
                    clean = re.sub(r"<[^>]+>", " ", clean)
                    clean = " ".join(clean.split())
                    return {"status": "ok", "text": clean[:5000]}
                return {"status": "error", "error": f"HTTP status {resp.status_code}"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    @classmethod
    async def create_monitor(
        cls,
        url: str,
        name: str,
        selector: Optional[str] = None,
        check_interval: int = 3600
    ) -> Dict[str, Any]:
        """Create a new website monitor and perform initial baseline check."""
        async with AsyncSessionLocal() as session:
            repo = Repository(session)
            mon = await repo.create_website_monitor(
                url=url,
                name=name,
                selector=selector,
                check_interval=check_interval
            )
            mon_id = mon.id

        # Perform initial baseline fetch
        check_res = await cls.check_monitor(mon_id)
        return {
            "id": mon_id,
            "name": name,
            "url": url,
            "selector": selector,
            "baseline": check_res
        }

    @classmethod
    async def check_monitor(cls, monitor_id: str) -> Dict[str, Any]:
        """Check a monitor URL for changes against its stored baseline hash."""
        async with AsyncSessionLocal() as session:
            stmt = select(WebsiteMonitor).where(WebsiteMonitor.id == monitor_id)
            res = await session.execute(stmt)
            mon = res.scalars().first()
            if not mon:
                return {"status": "error", "error": "Monitor not found"}

            url = mon.url
            selector = mon.selector
            old_hash = mon.last_content_hash
            old_snippet = mon.last_text_snippet or ""

        fetch_res = await cls.fetch_target_content(url, selector)
        if fetch_res.get("status") != "ok":
            return {"status": "error", "error": fetch_res.get("error")}

        current_text = fetch_res.get("text", "")
        new_hash = cls._compute_hash(current_text)
        changed = False

        if old_hash is not None and old_hash != new_hash:
            changed = True
            logger.info(f"Monitor '{mon.name}' detected content change at {url}!")
            try:
                bridge.notify("monitor.change_detected", {
                    "monitor_id": monitor_id,
                    "name": mon.name,
                    "url": url,
                    "timestamp": time.time(),
                    "snippet": current_text[:200]
                })
            except Exception:
                pass

        # Update record in DB
        async with AsyncSessionLocal() as session:
            stmt = select(WebsiteMonitor).where(WebsiteMonitor.id == monitor_id)
            res = await session.execute(stmt)
            mon = res.scalars().first()
            if mon:
                mon.last_content_hash = new_hash
                mon.last_text_snippet = current_text[:500]
                mon.last_check_at = time.time()
                if changed:
                    mon.status = "alert"
                await session.commit()

        return {
            "status": "ok",
            "monitor_id": monitor_id,
            "changed": changed,
            "content_hash": new_hash,
            "checked_at": time.time(),
            "snippet": current_text[:200]
        }

    @classmethod
    async def list_monitors(cls) -> List[Dict[str, Any]]:
        """List all active website monitors."""
        async with AsyncSessionLocal() as session:
            repo = Repository(session)
            monitors = await repo.get_website_monitors()
            return [
                {
                    "id": m.id,
                    "name": m.name,
                    "url": m.url,
                    "selector": m.selector,
                    "status": m.status,
                    "check_interval": m.check_interval,
                    "last_check_at": m.last_check_at,
                    "last_text_snippet": m.last_text_snippet
                }
                for m in monitors
            ]

    @classmethod
    async def delete_monitor(cls, monitor_id: str) -> bool:
        """Delete a monitor."""
        async with AsyncSessionLocal() as session:
            repo = Repository(session)
            return await repo.delete_website_monitor(monitor_id)
