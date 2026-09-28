import requests

print("Testing /review...")
try:
    res = requests.post("http://localhost:8000/review", json={"code": "def add(a,b): return a+b", "language": "python"})
    print(res.status_code)
    print(res.text)
except Exception as e:
    print(e)

print("\nTesting /rewrite...")
try:
    res = requests.post("http://localhost:8000/rewrite", json={"code": "def add(a,b): return a+b", "language": "python"})
    print(res.status_code)
    print(res.text)
except Exception as e:
    print(e)
