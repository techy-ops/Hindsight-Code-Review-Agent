"""
Diagnostic endpoint test: call the live /review endpoint and inspect the actual
error to pinpoint if it's a stale key, stale process, or SDK issue.
"""
import httpx, asyncio, json, sys

async def run():
    async with httpx.AsyncClient(timeout=60.0) as client:
        # 1. Check memory status (which shows what config is loaded)
        r = await client.get("http://127.0.0.1:8000/memory/status")
        print("=== /memory/status ===")
        print(json.dumps(r.json(), indent=2))

        # 2. Real /review call
        print("\n=== POST /review ===")
        payload = {
            "code": "def add(a, b):\n    return a + b\n\nresult = add(1, 2)\nprint(result)",
            "language": "python",
            "project_id": "diag-test"
        }
        r2 = await client.post("http://127.0.0.1:8000/review", json=payload)
        print(f"Status: {r2.status_code}")
        try:
            body = r2.json()
            print(json.dumps(body, indent=2)[:600])
        except Exception:
            print(r2.text[:600])

asyncio.run(run())
