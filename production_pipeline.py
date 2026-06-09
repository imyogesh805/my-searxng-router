"""
Filename: production_pipeline.py
Purpose: Unified Orchestration Layer managing Multi-Cloud API Toggles 
Target Workspace Environment: Antigravity Agentic Workspace
"""

import sys
import json
import requests
import os

# Live System Environment Variables (loads from environment with hardcoded fallback defaults)
RENDER_SEARXNG_URL = os.environ.get("RENDER_SEARXNG_URL", "https://p02--vane-imy--vkwp6sfj4t5z.code.run/search")
HF_CRAWL4AI_URL    = os.environ.get("HF_CRAWL4AI_URL", "https://imy805-crawl4ai.hf.space/extract")
NORTHFLANK_VANE_URL = os.environ.get("NORTHFLANK_VANE_URL", "https://your-vane-app.northflank.app/api/search")

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
