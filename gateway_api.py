"""
Filename: gateway_api.py
Purpose: FastAPI Web App & Gateway providing a unified web UI and research API endpoint.
Target Workspace Environment: Antigravity Agentic Workspace
"""

import os
import requests
from typing import Optional, List
from fastapi import FastAPI, HTTPException, status
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Initialize FastAPI App
app = FastAPI(
    title="Aether Search - Unified Research Gateway",
    version="1.0.0",
    description="Unified API and Web UI combining SearXNG, Crawl4AI, and dynamic LLM providers.",
)

# Load global environment fallbacks
RENDER_SEARXNG_URL = os.environ.get("RENDER_SEARXNG_URL", "https://my-searxng-router.onrender.com/search")
HF_CRAWL4AI_URL    = os.environ.get("HF_CRAWL4AI_URL", "https://imy805-crawl4ai.hf.space/extract")

# Model configurations
DEFAULT_LLM_URL = os.environ.get("DEFAULT_LLM_URL", "https://api.groq.com/openai/v1")
DEFAULT_LLM_KEY = os.environ.get("DEFAULT_LLM_KEY", "")
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

@app.post("/api/research", status_code=status.HTTP_200_OK)
def perform_research(request_data: ResearchRequest):
    """
    Unified search, crawl, and research synthesis API endpoint.
    Queries SearXNG, crawls top pages, and dynamically synthesizes an answer using the provided LLM credentials.
    """
    query = request_data.query
    use_ai = request_data.use_ai
    dev_focus = request_data.dev_focus
    
    # 1. Search SearXNG for top URLs
    search_params = {"q": query, "format": "json"}
    if dev_focus:
        search_params["categories"] = "it"
        search_params["engines"] = "github,stackoverflow"
    else:
        # Default to bing since Google/DuckDuckGo are currently showing captcha/timeouts on this SearXNG instance
        search_params["engines"] = "bing"
        
    try:
        search_response = requests.get(RENDER_SEARXNG_URL, params=search_params, timeout=15)
        if search_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="SearXNG search service returned an error."
            )
        search_data = search_response.json()
        results = search_data.get("results", [])
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"SearXNG connection failed: {str(e)}"
        )
        
    if not results:
        return {
            "status": "success",
            "query": query,
            "research_summary": "Zero web targets located. Cannot synthesize summary.",
            "crawled_pages": []
        }
        
    # 2. Grab top 2 URLs and Crawl them
    crawled_pages = []
    # Limit crawling to top 2 results for speed and request limits
    target_results = results[:2]
    
    for item in target_results:
        url = item.get("url")
        title = item.get("title", "Untitled Source")
        if not url:
            continue
            
        try:
            crawl_response = requests.post(
                HF_CRAWL4AI_URL,
                json={"url": url},
                timeout=20
            )
            if crawl_response.status_code == 200:
                crawl_data = crawl_response.json()
                crawled_pages.append({
                    "title": title,
                    "url": url,
                    "markdown": crawl_data.get("markdown", "")
                })
        except Exception:
            # Continue if one crawl fails, we still want to process other pages
            continue

    # 3. If AI synthesis is requested
    research_summary = ""
    if use_ai:
        if not crawled_pages:
            research_summary = "Failed to crawl web sources. Cannot synthesize summary."
        else:
            # Determine LLM credentials (use request config, falling back to environment values)
            req_provider = request_data.provider
            llm_url = (req_provider.base_url if req_provider and req_provider.base_url 
                       else DEFAULT_LLM_URL)
            llm_key = (req_provider.api_key if req_provider and req_provider.api_key 
                       else DEFAULT_LLM_KEY)
            llm_model = (req_provider.model if req_provider and req_provider.model 
                         else DEFAULT_LLM_MODEL)
            
            if not llm_key:
                research_summary = "AI API Key is missing. Please configure your API key in settings."
            else:
                # Build context from crawled documents
                context_str = ""
                for idx, page in enumerate(crawled_pages, 1):
                    context_str += f"\nSource #{idx}: {page['title']} ({page['url']})\n"
                    context_str += f"---\n{page['markdown'][:4000]}\n---\n" # Truncate markdown to fit context window safely
                
                # Construct Chat Completion payload
                prompt = (
                    f"You are a professional research assistant. Synthesize a comprehensive research report answering the query: \"{query}\".\n"
                    f"Use the following source texts crawled from the web to formulate your response:\n"
                    f"{context_str}\n"
                    f"Format the summary cleanly in Markdown. Cite your sources using numbered bracket annotations (e.g. [1], [2]) corresponding to the Source numbers above."
                )
                
                llm_headers = {
                    "Authorization": f"Bearer {llm_key}",
                    "Content-Type": "application/json"
                }
                llm_payload = {
                    "model": llm_model,
                    "messages": [
                        {"role": "system", "content": "You are a precise researcher and writer. Write factual summaries based strictly on the provided context."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.2
                }
                
                try:
                    # Construct full completion URL
                    completion_url = f"{llm_url.rstrip('/')}/chat/completions"
                    llm_response = requests.post(completion_url, headers=llm_headers, json=llm_payload, timeout=30)
                    
                    if llm_response.status_code == 200:
                        llm_data = llm_response.json()
                        research_summary = llm_data.get("choices", [{}])[0].get("message", {}).get("content", "Failed to generate report.")
                    else:
                        research_summary = f"LLM Provider Error: {llm_response.status_code} - {llm_response.text}"
                except Exception as e:
                    research_summary = f"Connection to LLM Provider failed: {str(e)}"
                    
    return {
        "status": "success",
        "query": query,
        "research_summary": research_summary,
        "crawled_pages": crawled_pages
    }

# Mount static files to serve the web UI at root "/"
# Static files must be mounted last so they don't override the API routes
app.mount("/", StaticFiles(directory="static", html=True), name="static")
