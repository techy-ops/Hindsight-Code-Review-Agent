from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from fastapi.responses import HTMLResponse
import os
import json
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend')

api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

class CodeRequest(BaseModel):
    code: str
    language: str



@app.post("/review")
async def review_code(request: CodeRequest):
    if not api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY environment variable is not set. Please set it or add a .env file to the backend directory.")
        
    prompt = f"""You are an expert code reviewer. Analyze the following {request.language} code for vulnerabilities, bugs, and performance issues.
    
    Code:
    {request.code}
    
    Return ONLY a JSON object with this exact structure (no markdown formatting, just raw JSON). Ensure valid JSON:
    {{
      "issues": {{
        "critical": 0,
        "high": 0,
        "medium": 0,
        "low": 0
      }},
      "details": [
        {{
          "severity": "critical|high|medium|low",
          "title": "Short title",
          "description": "Detailed explanation",
          "suggestion": "How to fix"
        }}
      ]
    }}
    """
    for attempt in range(4):
        try:
            model_name = 'gemini-2.5-flash'
            model = genai.GenerativeModel(model_name)
            response = await model.generate_content_async(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    response_mime_type="application/json",
                )
            )
            data = json.loads(response.text)
            return data
        except Exception as e:
            if "429" in str(e) and attempt < 3:
                import asyncio, random, re
                sleep_time = 2.0  # Quick retry on the fallback model
                if True:
                    # If rate limited, parse the exact 429 wait time
                    match = re.search(r"retry in ([\d\.]+)s", str(e))
                    if match:
                        sleep_time = float(match.group(1)) + random.uniform(1.0, 3.0)
                    else:
                        sleep_time = 16.0 + random.uniform(1.0, 3.0)
                await asyncio.sleep(sleep_time)
            else:
                raise HTTPException(status_code=500, detail=f"LLM Error: {str(e)}")

@app.post("/rewrite")
async def rewrite_code(request: CodeRequest):
    if not api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY environment variable is not set. Please set it or add a .env file to the backend directory.")
        
    prompt = f"""You are an expert code optimizing agent. Rewrite the following {request.language} code to be more efficient, secure, and idiomatic.
    
    Code:
    {request.code}
    
    Return ONLY a JSON object with this exact structure (no markdown formatting, just raw JSON). Ensure valid JSON:
    {{
      "optimized_code": "The full rewritten code here as a string",
      "metrics": {{
        "time_complexity": "e.g. O(n^2) -> O(n)",
        "memory_usage": "e.g. -20% Saved or N/A"
      }},
      "diff": [
        {{
          "type": "remove",
          "content": "- old line"
        }},
        {{
          "type": "add",
          "content": "+ new line"
        }}
      ]
    }}
    """
    for attempt in range(4):
        try:
            model_name = 'gemini-2.5-flash'
            model = genai.GenerativeModel(model_name)
            response = await model.generate_content_async(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    response_mime_type="application/json",
                )
            )
            data = json.loads(response.text)
            return data
        except Exception as e:
            if "429" in str(e) and attempt < 3:
                import asyncio, random, re
                sleep_time = 2.0
                if True:
                    match = re.search(r"retry in ([\d\.]+)s", str(e))
                    if match:
                        sleep_time = float(match.group(1)) + random.uniform(1.0, 3.0)
                    else:
                        sleep_time = 16.0 + random.uniform(1.0, 3.0)
                await asyncio.sleep(sleep_time)
            else:
                raise HTTPException(status_code=500, detail=f"LLM Error: {str(e)}")

# Mount the entire frontend directory as static files
app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
