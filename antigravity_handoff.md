# ARCHITECTURAL HANDOFF DOCUMENT: MULTI-CLOUD AI PIPELINE
**Target Environment:** Antigravity IDE (Agentic Workflow Environment)
**User Profile Reference:** Yogesh Miglani
**Date Generated:** June 8, 2026
**System Status:** Service 1 (Render) & Service 2 (Hugging Face) are LIVE & VERIFIED.

---

## 1. Architectural Overview
This distributed personal workbench decouples search queries, data crawling, and conversational orchestration to maintain an advanced sandbox pipeline with $0 monthly operating costs. 

```
                             ┌── [ MODE A: Pure TinyFish API Pipeline ] ──> Direct JSON Data Arrays
                             │
[ ANTIGRAVITY IDE SCRIPTS ] ─┼── [ MODE B: Full Answering Engine ] ───────> Northflank Vane Orchestrator ──> Groq LLM Synthesis
│
└──> [ GLOBAL / DEV ENGINE PARAMETERS ] ─────> Modifies SearXNG Routing Rules
```

---

## 2. Active Cloud Infrastructure Topology

### Service 1: Meta-Search Router
- **Platform:** Render (Free Web Service Tier)
- **Engine Core:** SearXNG (Official Docker Base Deployment)
- **Live Base URL:** `https://my-searxng-router.onrender.com`
- **Internal Mapping Port:** `8080` (Proxied automatically)
- **Active Cron Keep-Awake Interval:** 12 minutes (Prevents automatic container sleep)

### Service 2: Unblocked Headless Web Crawler
- **Platform:** Hugging Face Spaces (Custom Free Docker SDK)
- **Engine Core:** Crawl4AI Engine v0.8.9 + Playwright Headless Chromium Backend Layer
- **Live API Endpoint:** `https://imy805-crawl4ai.hf.space/extract`
- **Internal Mapping Port:** `7860` (Hard-coded container configuration)

### Service 3: Pipeline Aggregator & UI Front-End
- **Platform:** Northflank
- **Engine Core:** Vane Engine (Self-Hosted Answering Interface Platform)
- **Encrypted Secure Configuration Path:** Mount target mapping set at `/home/vane/data/config.json`

---

## 3. Production Configuration Arrays

### Northflank Secured Configuration File (`config.json`)
```json
{
  "config": {
    "SEARXNG_API_URL": "https://my-searxng-router.onrender.com",
    "CRAWL_PROVIDER": "custom",
    "CUSTOM_CRAWL_API": "https://imy805-crawl4ai.hf.space/extract"
  },
  "modelProviders": [
    {
      "id": "groq",
      "name": "Groq",
      "type": "openai",
      "config": {
        "apiKey": "YOUR_REAL_GROQ_API_KEY_HERE",
        "baseURL": "https://api.groq.com/openai/v1"
      },
      "chatModels": [
        {
          "id": "llama3-8b-8192",
          "name": "Llama 3 8B"
        }
      ],
      "embeddingModels": []
    }
  ]
}
```

---

## 4. Native Engine URL Routing Parameter Matrices

SearXNG handles targeted queries and structural focus behavior dynamically based on parameters passed into the call query string. This enables precise filtering without requiring system restarts.

| URL Parameter String Key | Functional Operational Toggle Action |
| --- | --- |
| `&format=json` | **Mandatory.** Abstracts frontend HTML rendering, forcing clean JSON outputs. |
| `&engines=google,duckduckgo` | **Global Mode Toggle.** Scrapes generic index parameters across primary consumer portals. |
| `&categories=it&engines=github,stackoverflow` | **Developer Mode Toggle.** Targets programming queries, source trees, and technical forums. |

---

## 5. Unified Dual-Engine Master Orchestrator Script

Create this core orchestration utility file directly within your **Antigravity Workspace Workspace** directory. It houses the precise programmatic routing toggles for both structural text collection and intelligent conversational responses.

```python
"""
Filename: production_pipeline.py
Purpose: Unified Orchestration Layer managing Multi-Cloud API Toggles 
Target Workspace Environment: Antigravity Agentic Workspace
"""

import sys
import json
import requests

# Live System Environment Variables
RENDER_SEARXNG_URL = "https://my-searxng-router.onrender.com/search"
HF_CRAWL4AI_URL    = "https://imy805-crawl4ai.hf.space/extract"
NORTHFLANK_VANE_URL = "https://your-vane-app.northflank.app/api/search"

def execute_pipeline(query: str, use_ai: bool = False, dev_focus: bool = False):
    """
    Dual-action script execution block handling TinyFish Extraction vs Answering Engine modes.
    """
    # =========================================================================
    # CONFIGURATION MATRIX A: RAW TINYFISH DATA PIPELINE (No LLM Overhead)
    # =========================================================================
    if not use_ai:
        print("\n⚡ [TINYFISH ACTIVE]: Initializing high-speed extraction pipeline...")
        
        # Assemble Request Query Parameters for SearXNG
        search_params = {"q": query, "format": "json"}
        if dev_focus:
            print("🛠️ [ENGINE OVERRIDE]: Confining lookup parameters to IT & Repository targets.")
            search_params["categories"] = "it"
            search_params["engines"] = "github,stackoverflow"
        else:
            print("🌍 [ENGINE OVERRIDE]: Broadcasting search parameters globally (Google/DuckDuckGo).")
            search_params["engines"] = "google,duckduckgo"
            
        try:
            search_response = requests.get(RENDER_SEARXNG_URL, params=search_params, timeout=15)
            search_data = search_response.json()
            results = search_data.get("results", [])
            
            if not results:
                return {"status": "error", "message": "Zero active web targets located by search grid."}
                
            target_url = results[0].get("url")
            print(f"🎯 Target Endpoint Resolved: {target_url}")
            
        except Exception as e:
            return {"status": "error", "message": f"Render connection failure: {str(e)}"}
            
        # Dispatch Target Direct Web Link to Crawl4AI Container
        try:
            print("🕷️ Initiating headless chromium pipeline via Hugging Face...")
            crawl_payload = {"url": target_url}
            crawl_response = requests.post(HF_CRAWL4AI_URL, json=crawl_payload, timeout=30)
            return crawl_response.json()
            
        except Exception as e:
            return {"status": "error", "message": f"Hugging Face connection failure: {str(e)}"}

    # =========================================================================
    # CONFIGURATION MATRIX B: FULL AI ANSWERING ENGINE (Orchestrated Synthesis)
    # =========================================================================
    else:
        print("\n🧠 [ANSWERING ENGINE ACTIVE]: Forwarding packet to Northflank Orchestrator...")
        vane_payload = {
            "chatModel": {
                "providerId": "groq", 
                "key": "llama3-8b-8192"
            },
            "sources": ["web"],
            "optimizationMode": "speed",
            "query": query,
            "stream": False
        }
        
        try:
            response = requests.post(NORTHFLANK_VANE_URL, json=vane_payload, timeout=45)
            return response.json()
            
        except Exception as e:
            return {"status": "error", "message": f"Northflank communication failure: {str(e)}"}

if __name__ == "__main__":
    # Test Evaluation Parameter Query Definition
    PROMPT = "python implementation examples for chunking lists efficiently"
    
    # ---------------------------------------------------------------------
    # MODE SELECTION MATRIX (Operational Toggle Panel)
    # ---------------------------------------------------------------------
    # TOGGLE 1: Set True to activate Vane + LLM. Set False for Raw TinyFish Text.
    RUN_WITH_AI  = False  
    
    # TOGGLE 2: Set True to force IT engine indexing. Set False for General Web search.
    DEV_MODE_ONLY = True  
    
    output_payload = execute_pipeline(query=PROMPT, use_ai=RUN_WITH_AI, dev_focus=DEV_MODE_ONLY)
    print("\n--- SYSTEM OUTPUT RECEIVED ---")
    print(json.dumps(output_payload, indent=2))
```

---

## 6. Personal Resource Execution Best Practices

1. **Parallel Execution Safeguards:** When triggering background cron actions inside Antigravity, execute loops sequentially with a structural step latency cushion (`time.sleep(1.5)`) to match the dual-core free allocation limitations on Hugging Face.
2. **Context Threshold Optimization:** For heavy payload collection tasks, fall back to **TinyFish Mode (`use_ai=False`)** to ingest full unedited Markdown streams without risking execution terminations from cloud provider memory ceilings.
