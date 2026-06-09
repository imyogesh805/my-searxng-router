"""
Filename: gateway_api.py
Purpose: FastAPI Web App & Gateway providing a unified web UI and research API endpoint.
Target Workspace Environment: Antigravity Agentic Workspace
"""

import os
import requests
from typing import Optional
from fastapi import FastAPI, HTTPException, status
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Initialize FastAPI App
app = FastAPI(
    title="Aether Search - Unified Research Gateway",
    version="2.0.0",
    description="Unified API and Web UI combining SearXNG, Vane, and Crawl4AI.",
)

# Service URLs
RENDER_SEARXNG_URL = os.environ.get("RENDER_SEARXNG_URL", "https://my-searxng-api.onrender.com/search")
HF_CRAWL4AI_URL    = os.environ.get("HF_CRAWL4AI_URL",    "https://imy805-crawl4ai.hf.space/extract")
HF_VANE_URL        = os.environ.get("HF_VANE_URL",        "https://imy805-vane.hf.space")

# Default LLM config (fallback when no provider sent per-request)
DEFAULT_LLM_URL   = os.environ.get("DEFAULT_LLM_URL",   "https://api.groq.com/openai/v1")
DEFAULT_LLM_KEY   = os.environ.get("DEFAULT_LLM_KEY",   "")
DEFAULT_LLM_MODEL = os.environ.get("DEFAULT_LLM_MODEL", "llama3-8b-8192")

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


@app.post("/api/research", status_code=status.HTTP_200_OK)
def perform_research(request_data: ResearchRequest):
    """
    Unified search + AI answer endpoint.
    AI OFF: direct SearXNG results.
    AI ON: Vane answer engine (SearXNG + LLM) with crawl4ai deep-crawl of top sources.
    Fallback: direct SearXNG + LLM synthesis if Vane is unavailable.
    """
    query     = request_data.query
    use_ai    = request_data.use_ai
    dev_focus = request_data.dev_focus

    req_provider = request_data.provider
    llm_url   = (req_provider.base_url if req_provider and req_provider.base_url else DEFAULT_LLM_URL)
    llm_key   = (req_provider.api_key  if req_provider and req_provider.api_key  else DEFAULT_LLM_KEY)
    llm_model = (req_provider.model    if req_provider and req_provider.model    else DEFAULT_LLM_MODEL)

    # ── AI OFF: plain SearXNG search ─────────────────────────────────────────
    if not use_ai:
        search_params = {"q": query, "format": "json"}
        if dev_focus:
            search_params["categories"] = "it"
            search_params["engines"]    = "github,stackoverflow"

        try:
            search_response = requests.get(RENDER_SEARXNG_URL, params=search_params, timeout=15)
            if search_response.status_code != 200:
                raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY,
                                    detail="SearXNG returned an error.")
            results = search_response.json().get("results", [])
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY,
                                detail=f"SearXNG connection failed: {str(e)}")

        search_results = [{"title":   r.get("title", "Untitled"),
                           "url":     r.get("url", ""),
                           "content": r.get("content", "")} for r in results]
        return {"status": "success", "query": query,
                "research_summary": "", "search_results": search_results, "crawled_pages": []}

    # ── AI ON: Vane answer engine ─────────────────────────────────────────────
    research_summary = ""
    search_results   = []
    crawled_pages    = []
    vane_succeeded   = False

    if llm_key:
        try:
            vane_payload = {
                "chatModel": {
                    "providerId": detect_provider_id(llm_url),
                    "key": llm_model
                },
                "embeddingModel": {
                    "providerId": "local",
                    "key": "xenova/gte-small"
                },
                "focusMode": "webSearch",
                "optimizationMode": "balanced",
                "query": query,
                "stream": False,
                "systemInstructions": (
                    "You are a professional research assistant. "
                    "Write a comprehensive, well-structured, cited Markdown report."
                )
            }
            vane_headers = {
                "Authorization": f"Bearer {llm_key}",
                "Content-Type": "application/json"
            }
            vane_response = requests.post(
                f"{HF_VANE_URL.rstrip('/')}/api/search",
                json=vane_payload,
                headers=vane_headers,
                timeout=60
            )
            if vane_response.status_code == 200:
                vane_data        = vane_response.json()
                research_summary = vane_data.get("message", "")
                sources          = vane_data.get("sources", [])
                search_results   = [
                    {
                        "title":   s.get("metadata", {}).get("title", "Untitled"),
                        "url":     s.get("metadata", {}).get("url", ""),
                        "content": s.get("pageContent", "")[:500]
                    }
                    for s in sources
                ]
                vane_succeeded = True

                # Deep-crawl top 2 source URLs via crawl4ai
                for source in sources[:2]:
                    url   = source.get("metadata", {}).get("url", "")
                    title = source.get("metadata", {}).get("title", "Untitled")
                    if not url:
                        continue
                    try:
                        crawl_response = requests.post(
                            HF_CRAWL4AI_URL,
                            json={"url": url},
                            timeout=30
                        )
                        if crawl_response.status_code == 200:
                            crawled_pages.append({
                                "title":    title,
                                "url":      url,
                                "markdown": crawl_response.json().get("markdown", "")
                            })
                    except Exception:
                        continue

        except Exception:
            vane_succeeded = False

    # ── Fallback: direct SearXNG + LLM synthesis ─────────────────────────────
    if not vane_succeeded:
        search_params = {"q": query, "format": "json"}
        if dev_focus:
            search_params["categories"] = "it"
            search_params["engines"]    = "github,stackoverflow"

        try:
            search_response = requests.get(RENDER_SEARXNG_URL, params=search_params, timeout=15)
            results = search_response.json().get("results", []) if search_response.status_code == 200 else []
        except Exception:
            results = []

        search_results = [{"title":   r.get("title", "Untitled"),
                           "url":     r.get("url", ""),
                           "content": r.get("content", "")} for r in results]

        for item in results[:2]:
            url   = item.get("url", "")
            title = item.get("title", "Untitled")
            if not url:
                continue
            try:
                crawl_response = requests.post(HF_CRAWL4AI_URL, json={"url": url}, timeout=30)
                if crawl_response.status_code == 200:
                    crawled_pages.append({
                        "title":    title,
                        "url":      url,
                        "markdown": crawl_response.json().get("markdown", "")
                    })
            except Exception:
                continue

        if not llm_key:
            research_summary = "AI API Key is missing. Please configure your API key in settings."
        elif crawled_pages:
            context_str = ""
            for idx, page in enumerate(crawled_pages, 1):
                context_str += f"\nSource #{idx}: {page['title']} ({page['url']})\n"
                context_str += f"---\n{page['markdown'][:4000]}\n---\n"

            prompt = (
                f"You are a professional research assistant. Synthesize a comprehensive research report "
                f"answering the query: \"{query}\".\n"
                f"Use the following source texts crawled from the web:\n{context_str}\n"
                f"Format in Markdown. Cite sources with [1], [2] etc."
            )
            try:
                llm_response = requests.post(
                    f"{llm_url.rstrip('/')}/chat/completions",
                    headers={"Authorization": f"Bearer {llm_key}", "Content-Type": "application/json"},
                    json={
                        "model": llm_model,
                        "messages": [
                            {"role": "system", "content": "You are a precise researcher. Write factual summaries based strictly on the provided context."},
                            {"role": "user",   "content": prompt}
                        ],
                        "temperature": 0.2
                    },
                    timeout=30
                )
                if llm_response.status_code == 200:
                    research_summary = llm_response.json().get("choices", [{}])[0].get("message", {}).get("content", "Failed to generate report.")
                else:
                    research_summary = f"LLM Provider Error: {llm_response.status_code}"
            except Exception as e:
                research_summary = f"LLM connection failed: {str(e)}"
        else:
            research_summary = "Failed to crawl web sources. Cannot synthesize summary."

    return {
        "status": "success",
        "query": query,
        "research_summary": research_summary,
        "search_results": search_results,
        "crawled_pages": crawled_pages
    }


# Mount static files — must be last so it doesn't override API routes
app.mount("/", StaticFiles(directory="static", html=True), name="static")
