"""
Diagnostic: test Gemini generate_content_async using the SAME config path as main.py.
Does NOT expose the key. Reports only pass/fail + safe fingerprint.
"""
import asyncio, os, sys, hashlib, json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")
import google.generativeai as genai

api_key = os.getenv("GEMINI_API_KEY", "")
model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

sha = hashlib.sha256(api_key.encode()).hexdigest()[:12] if api_key else "N/A"
print(f"Key fingerprint: length={len(api_key)} sha256[:12]={sha}")
print(f"Model          : {model_name}")

if not api_key:
    print("ERROR: No API key loaded.")
    sys.exit(1)

genai.configure(api_key=api_key)

async def run():
    model = genai.GenerativeModel(model_name)
    response = await model.generate_content_async(
        "Say exactly: GENERATION_OK",
        generation_config=genai.types.GenerationConfig(
            response_mime_type="text/plain",
        )
    )
    return response.text

try:
    result = asyncio.run(run())
    print(f"generate_content_async: PASS")
    print(f"Response snippet: {result[:80]!r}")
except Exception as e:
    print(f"generate_content_async: FAIL")
    print(f"Error: {type(e).__name__}: {e}")
    sys.exit(1)
