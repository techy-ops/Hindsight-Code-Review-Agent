"""Diagnostic: verifies API key loading without exposing the secret."""
import os, sys, hashlib
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")
key = os.getenv("GEMINI_API_KEY", "")
model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

sha = hashlib.sha256(key.encode()).hexdigest()[:12] if key else "N/A"
print(f".env key loaded: {bool(key)}")
print(f"  length        : {len(key)}")
print(f"  prefix        : {key[:6]}..." if len(key) >= 6 else f"  prefix        : TOO_SHORT({len(key)})")
print(f"  sha256[:12]   : {sha}")
print(f"  model         : {model}")
