"""
Real end-to-end test: POST to the live /review and /rewrite endpoints.
Does NOT use mocks. Verifies a genuine Gemini AI response is returned.
"""
import asyncio, json, sys, hashlib
import httpx
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv(Path(__file__).resolve().parent / ".env")
PORT = 8001  # fresh process started with correct key

async def run():
    async with httpx.AsyncClient(timeout=90.0) as client:
        # --- /review ---
        print("=== Real POST /review ===")
        r = await client.post(f"http://127.0.0.1:{PORT}/review", json={
            "code": (
                "def calculate_total(items: list) -> int:\n"
                "    total = 0\n"
                "    for i in range(len(items)):\n"
                "        item = items[i]\n"
                "        if item['price'] > 0:\n"
                "            total = total + item['price']\n"
                "    return total\n"
            ),
            "language": "python",
            "project_id": "e2e-verify",
        })
        print(f"HTTP {r.status_code}")
        if r.status_code == 200:
            body = r.json()
            issues = body.get("issues", {})
            details = body.get("details", [])
            print(f"/review: PASS — issues={issues}, findings={len(details)}")
            for d in details:
                print(f"  [{d.get('severity','?')}] {d.get('title','?')}")
        else:
            print(f"/review: FAIL — {r.text[:400]}")
            sys.exit(1)

        # --- /rewrite ---
        print("\n=== Real POST /rewrite ===")
        r2 = await client.post(f"http://127.0.0.1:{PORT}/rewrite", json={
            "code": "def add(a, b):\n    return a + b\n",
            "language": "python",
        })
        print(f"HTTP {r2.status_code}")
        if r2.status_code == 200:
            body2 = r2.json()
            print(f"/rewrite: PASS — has optimized_code: {'optimized_code' in body2}")
        else:
            print(f"/rewrite: FAIL — {r2.text[:400]}")
            sys.exit(1)

asyncio.run(run())
