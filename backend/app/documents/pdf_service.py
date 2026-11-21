import io
import os
import re
import logging
from typing import Dict, Any, List, Optional
import httpx
from pypdf import PdfReader

logger = logging.getLogger("pdf_service")

class PDFService:
    """
    Document Intelligence Service for PDF extraction, analysis, and page-cited QA.
    """

    @classmethod
    async def _get_pdf_bytes(cls, path_or_url: str) -> bytes:
        if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                resp = await client.get(path_or_url)
                resp.raise_for_status()
                return resp.content
        else:
            if not os.path.exists(path_or_url):
                raise FileNotFoundError(f"PDF file not found at: {path_or_url}")
            with open(path_or_url, "rb") as f:
                return f.read()

    @classmethod
    async def read_pdf(cls, path_or_url: str, max_pages: int = 50) -> Dict[str, Any]:
        """
        Extract page-level text and document metadata from a local or remote PDF.
        """
        try:
            pdf_bytes = await cls._get_pdf_bytes(path_or_url)
            reader = PdfReader(io.BytesIO(pdf_bytes))
            
            total_pages = len(reader.pages)
            meta = reader.metadata or {}
            
            pages_data: List[Dict[str, Any]] = []
            for idx in range(min(total_pages, max_pages)):
                page = reader.pages[idx]
                text = page.extract_text() or ""
                clean_text = " ".join(text.split())
                pages_data.append({
                    "page_number": idx + 1,
                    "character_count": len(clean_text),
                    "text": clean_text
                })

            return {
                "status": "ok",
                "source": path_or_url,
                "title": getattr(meta, "title", None) or os.path.basename(path_or_url),
                "author": getattr(meta, "author", None),
                "total_pages": total_pages,
                "pages_read": len(pages_data),
                "pages": pages_data
            }
        except Exception as e:
            logger.error(f"Error reading PDF {path_or_url}: {e}")
            return {"status": "error", "error": str(e)}

    @classmethod
    async def summarize_pdf(cls, path_or_url: str, query: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate page-cited summary and answers from a PDF.
        """
        read_res = await cls.read_pdf(path_or_url, max_pages=30)
        if read_res.get("status") == "error":
            return read_res

        pages = read_res.get("pages", [])
        total_pages = read_res.get("total_pages", 0)
        title = read_res.get("title", "Document")

        key_takeaways: List[str] = []
        for p in pages:
            text = p.get("text", "")
            page_num = p.get("page_number", 1)
            if not text:
                continue
            
            sentences = [s.strip() for s in text.split(".") if len(s.strip()) > 30]
            if sentences:
                # Pick the most informative sentence
                takeaway = sentences[0]
                key_takeaways.append(f"- **Key Point (Page {page_num})**: {takeaway}. [Page {page_num}]")
            if len(key_takeaways) >= 8:
                break

        summary_text = (
            f"### Document Analysis: {title}\n"
            f"- **Total Pages**: {total_pages}\n"
            f"- **Scope**: Analyzed first {len(pages)} pages.\n\n"
            f"#### Page-Cited Key Takeaways:\n" + "\n".join(key_takeaways)
        )

        return {
            "status": "ok",
            "title": title,
            "total_pages": total_pages,
            "summary": summary_text,
            "citations": [f"Page {p['page_number']}" for p in pages if p.get("text")]
        }

    @classmethod
    async def search_pdf(cls, path_or_url: str, query: str) -> Dict[str, Any]:
        """
        Search for specific terms or concepts with page context.
        """
        read_res = await cls.read_pdf(path_or_url, max_pages=100)
        if read_res.get("status") == "error":
            return read_res

        q_lower = query.lower()
        matches: List[Dict[str, Any]] = []

        for p in read_res.get("pages", []):
            text = p.get("text", "")
            if q_lower in text.lower():
                # Extract surrounding snippet
                idx = text.lower().find(q_lower)
                start = max(0, idx - 80)
                end = min(len(text), idx + len(query) + 80)
                snippet = "..." + text[start:end] + "..."
                matches.append({
                    "page_number": p["page_number"],
                    "snippet": snippet
                })

        return {
            "status": "ok",
            "query": query,
            "matches_count": len(matches),
            "matches": matches
        }
