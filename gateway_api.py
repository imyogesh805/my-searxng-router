"""
Filename: gateway_api.py
Purpose: FastAPI Web App & Gateway — unified search + streaming AI answer engine.
"""

import os
import json
import time
import requests
from typing import Optional, Iterator
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

app = FastAPI(
    title="Aether Search - Unified Research Gateway",
    version="3.0.0",
    description="Unified API and Web UI combining SearXNG, Vane, and Crawl4AI with SSE streaming.",
)

# Service URLs
RENDER_SEARXNG_URL = os.environ.get("RENDER_SEARXNG_URL", "https://my-searxng-5k3k.onrender.com/search")
HF_CRAWL4AI_URL    = os.environ.get("HF_CRAWL4AI_URL",    "https://imy805-crawl4ai.hf.space/extract")
HF_VANE_URL        = os.environ.get("HF_VANE_URL",        "https://imy805-vane.hf.space")

# Default LLM config
DEFAULT_LLM_URL   = os.environ.get("DEFAULT_LLM_URL",   "https://api.groq.com/openai/v1")
DEFAULT_LLM_KEY   = os.environ.get("DEFAULT_LLM_KEY",   "")
DEFAULT_LLM_MODEL = os.environ.get("DEFAULT_LLM_MODEL", "llama3-8b-8192")

# Domains that block headless browsers
BLOCKED_DOMAINS = [
    "openai.com", "twitter.com", "x.com", "facebook.com",
    "instagram.com", "linkedin.com", "reddit.com", "tiktok.com"
]

# Request Models
class ProviderConfig(BaseModel):
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None

class ResearchRequest(BaseModel):
    query: str
    use_ai: bool = True
    dev_focus: bool = False
    provider: Optional[ProviderConfig] = None


def is_crawlable(url: str) -> bool:
    return not any(domain in url for domain in BLOCKED_DOMAINS)


def detect_provider_id(base_url: str) -> str:
    if not base_url:
        return "groq"
    if "groq.com" in base_url:
        return "groq"
    if "openai.com" in base_url:
        return "openai"
    if "anthropic.com" in base_url:
        return "anthropic"
    if "googleapis.com" in base_url or "gemini" in base_url:
        return "gemini"
    return "custom_openai"


def sse(event: str, data: dict) -> str:
    """Format a Server-Sent Event."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def stream_research(query: str, use_ai: bool, dev_focus: bool,
                    llm_url: str, llm_key: str, llm_model: str) -> Iterator[str]:
    """
    Generator that yields SSE events in order:
    step → sources → crawled (per page) → token (per LLM chunk) → done
    """

    # ── STEP 1: Search SearXNG ────────────────────────────────────────────────
    yield sse("step", {"text": "🔍 Searching SearXNG...", "phase": "search"})

    search_params = {"q": query, "format": "json"}
    if dev_focus:
        search_params["categories"] = "it"
        search_params["engines"]    = "github,stackoverflow"

    try:
        r = requests.get(RENDER_SEARXNG_URL, params=search_params, timeout=15)
        results = r.json().get("results", []) if r.status_code == 200 else []
    except Exception:
        results = []

    if not results:
        yield sse("step", {"text": "⚠️ No results found.", "phase": "error"})
        yield sse("done", {"summary": "", "search_results": [], "crawled_pages": []})
        return

    search_results = [{"title": r.get("title", "Untitled"),
                       "url":   r.get("url", ""),
                       "content": r.get("content", "")} for r in results]

    yield sse("step", {"text": f"✅ Found {len(search_results)} results", "phase": "search_done"})
    yield sse("sources", {"results": search_results})

    # ── AI OFF: done after sources ────────────────────────────────────────────
    if not use_ai:
        yield sse("done", {"summary": "", "search_results": search_results, "crawled_pages": []})
        return

    # ── STEP 2: Crawl top pages ───────────────────────────────────────────────
    crawled_pages = []
    crawlable = [r for r in results if is_crawlable(r.get("url", ""))]

    for item in crawlable[:3]:
        url   = item.get("url", "")
        title = item.get("title", "Untitled")
        if not url:
            continue
        try:
            domain = url.split("/")[2]
            yield sse("step", {"text": f"🕷️ Crawling {domain}...", "phase": "crawl"})
            crawl_r = requests.post(HF_CRAWL4AI_URL, json={"url": url}, timeout=30)
            if crawl_r.status_code == 200:
                markdown = crawl_r.json().get("markdown", "")
                if markdown:
                    page = {"title": title, "url": url, "markdown": markdown}
                    crawled_pages.append(page)
                    yield sse("crawled", {"page": page})
        except Exception:
            continue

    if not llm_key:
        yield sse("step", {"text": "⚠️ No API key configured. Set it in Settings.", "phase": "error"})
        yield sse("done", {"summary": "", "search_results": search_results, "crawled_pages": crawled_pages})
        return

    # ── STEP 3: Stream LLM answer ─────────────────────────────────────────────
    yield sse("step", {"text": "🧠 Generating answer...", "phase": "generate"})

    if crawled_pages:
        context_str = ""
        for idx, page in enumerate(crawled_pages, 1):
            context_str += f"\nSource #{idx}: {page['title']} ({page['url']})\n"
            context_str += f"---\n{page['markdown'][:4000]}\n---\n"
    else:
        # Fall back to search snippets if no pages were crawled
        context_str = "\n".join(
            f"Source #{i+1}: {r['title']} ({r['url']})\n{r['content']}"
            for i, r in enumerate(search_results[:5])
        )

    prompt = (
        f"You are a professional research assistant. Write a comprehensive, well-structured "
        f"Markdown research report answering: \"{query}\".\n\n"
        f"Use these sources:\n{context_str}\n\n"
        f"Format in clean Markdown with headers. Cite sources as [1], [2] etc."
    )

    try:
        llm_response = requests.post(
            f"{llm_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {llm_key}", "Content-Type": "application/json"},
            json={
                "model": llm_model,
                "messages": [
                    {"role": "system", "content": "You are a precise researcher. Write factual reports based strictly on the provided sources."},
                    {"role": "user",   "content": prompt}
                ],
                "temperature": 0.2,
                "stream": True
            },
            stream=True,
            timeout=60
        )

        full_summary = ""
        for line in llm_response.iter_lines():
            if not line:
                continue
            line = line.decode("utf-8") if isinstance(line, bytes) else line
            if line.startswith("data: "):
                chunk = line[6:]
                if chunk.strip() == "[DONE]":
                    break
                try:
                    token = json.loads(chunk)["choices"][0]["delta"].get("content", "")
                    if token:
                        full_summary += token
                        yield sse("token", {"text": token})
                except Exception:
                    continue

        yield sse("done", {
            "summary": full_summary,
            "search_results": search_results,
            "crawled_pages": crawled_pages
        })

    except Exception as e:
        yield sse("step", {"text": f"⚠️ LLM error: {str(e)[:80]}", "phase": "error"})
        yield sse("done", {"summary": "", "search_results": search_results, "crawled_pages": crawled_pages})


class PingRequest(BaseModel):
    base_url: str
    api_key: str
    model: str


@app.post("/api/ping")
def ping_provider(req: PingRequest):
    """Ping an LLM provider with a tiny request and return response time."""
    try:
        start = time.time()
        response = requests.post(
            f"{req.base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {req.api_key}", "Content-Type": "application/json"},
            json={
                "model": req.model,
                "messages": [{"role": "user", "content": "Reply with one word: ready"}],
                "max_tokens": 5,
                "temperature": 0
            },
            timeout=15
        )
        elapsed = round((time.time() - start) * 1000)

        if response.status_code == 200:
            reply = response.json().get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            return {"ok": True, "ms": elapsed, "reply": reply, "model": req.model}
        else:
            return {"ok": False, "ms": elapsed, "error": f"HTTP {response.status_code}: {response.text[:120]}"}

    except requests.exceptions.Timeout:
        return {"ok": False, "ms": 15000, "error": "Request timed out (>15s)"}
    except Exception as e:
        return {"ok": False, "ms": 0, "error": str(e)[:120]}


@app.post("/api/research/stream")
def research_stream(request_data: ResearchRequest):
    """Streaming SSE endpoint — emits step/sources/crawled/token/done events."""
    req_provider = request_data.provider
    llm_url   = (req_provider.base_url if req_provider and req_provider.base_url else DEFAULT_LLM_URL)
    llm_key   = (req_provider.api_key  if req_provider and req_provider.api_key  else DEFAULT_LLM_KEY)
    llm_model = (req_provider.model    if req_provider and req_provider.model    else DEFAULT_LLM_MODEL)

    return StreamingResponse(
        stream_research(
            query=request_data.query,
            use_ai=request_data.use_ai,
            dev_focus=request_data.dev_focus,
            llm_url=llm_url,
            llm_key=llm_key,
            llm_model=llm_model
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )


# Keep old endpoint as fallback for n8n / external API calls
@app.post("/api/research")
def perform_research(request_data: ResearchRequest):
    """Non-streaming endpoint for n8n and external API consumers."""
    req_provider = request_data.provider
    llm_url   = (req_provider.base_url if req_provider and req_provider.base_url else DEFAULT_LLM_URL)
    llm_key   = (req_provider.api_key  if req_provider and req_provider.api_key  else DEFAULT_LLM_KEY)
    llm_model = (req_provider.model    if req_provider and req_provider.model    else DEFAULT_LLM_MODEL)

    summary       = ""
    search_results = []
    crawled_pages  = []

    # Collect all events from the stream generator
    for raw in stream_research(request_data.query, request_data.use_ai,
                                request_data.dev_focus, llm_url, llm_key, llm_model):
        for line in raw.split("\n"):
            if line.startswith("data: "):
                try:
                    d = json.loads(line[6:])
                except Exception:
                    continue
        # Parse done event for final payload
        if raw.startswith("event: done"):
            for line in raw.split("\n"):
                if line.startswith("data: "):
                    try:
                        d = json.loads(line[6:])
                        summary        = d.get("summary", "")
                        search_results = d.get("search_results", [])
                        crawled_pages  = d.get("crawled_pages", [])
                    except Exception:
                        pass
        elif raw.startswith("event: token"):
            for line in raw.split("\n"):
                if line.startswith("data: "):
                    try:
                        summary += json.loads(line[6:]).get("text", "")
                    except Exception:
                        pass
        elif raw.startswith("event: sources"):
            for line in raw.split("\n"):
                if line.startswith("data: "):
                    try:
                        search_results = json.loads(line[6:]).get("results", [])
                    except Exception:
                        pass
        elif raw.startswith("event: crawled"):
            for line in raw.split("\n"):
                if line.startswith("data: "):
                    try:
                        page = json.loads(line[6:]).get("page")
                        if page:
                            crawled_pages.append(page)
                    except Exception:
                        pass

    return {
        "status": "success",
        "query": request_data.query,
        "research_summary": summary,
        "search_results": search_results,
        "crawled_pages": crawled_pages
    }


# Mount static files — must be last
app.mount("/", StaticFiles(directory="static", html=True), name="static")
