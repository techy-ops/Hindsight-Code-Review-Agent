# 🤖 AI Code Review & Rewrite Agent

> **An AI-powered developer tool that reviews, detects, and improves source code using Google Gemini AI.**

AI Code Review & Rewrite Agent helps developers identify **bugs, security vulnerabilities, performance issues, and code-quality problems**, while also generating optimized code automatically.

## ✨ Features

* 🔍 **AI Code Review** — Analyze code and receive intelligent feedback
* 🐛 **Bug Detection** — Identify logical errors and potential code issues
* 🔐 **Security Analysis** — Detect insecure coding patterns
* ⚡ **Performance Optimization** — Find inefficient code and optimization opportunities
* 🧠 **AI Code Rewrite** — Generate cleaner and optimized code
* 🌐 **Multi-Language Support** — Review code across multiple programming languages
* 📊 **Developer Dashboard** — Centralized code review interface
* 📜 **Review History** — Track previous code analyses
* 📚 **API Documentation** — Interactive FastAPI documentation

## 🛠️ Tech Stack

**Frontend:** HTML • TailwindCSS • JavaScript • Stitch

**Backend:** Python • FastAPI

**AI:** Google Gemini API

## 🏗️ Architecture

```text
Developer
    ↓
Frontend
    ↓
FastAPI Backend
    ↓
Gemini AI
    ↓
Code Analysis / Rewrite
    ↓
Improved Code + Insights
```

## 📁 Project Structure

```text
AI-code-review-agent/
├── frontend/
│   ├── index.html
│   ├── developer_dashboard/
│   ├── review_history/
│   ├── api_documentation/
│   ├── platform_documentation/
│   ├── login/
│   └── create_account/
│
├── backend/
│   ├── main.py
│   ├── ai_service.py
│   ├── requirements.txt
│   └── .env
│
└── README.md
```

## 🚀 Run Locally

### 1. Clone

```bash
git clone https://github.com/techy-ops/AI-code-review-agent.git
cd AI-code-review-agent
```

### 2. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 3. Configure Gemini

Create `backend/.env`:

```env
GEMINI_API_KEY=your_api_key_here
```

Get your API key from Google AI Studio.

### 4. Start Server

```bash
uvicorn main:app --reload
```

Backend:

```text
http://127.0.0.1:8000
```

API Docs:

```text
http://127.0.0.1:8000/docs
```

## 📡 API

### `POST /review`

Analyze source code.

```json
{
  "language": "python",
  "code": "print('hello world')"
}
```

### `POST /rewrite`

Generate an optimized version of the submitted code.

## 🧪 Example

**Input:**

```python
def calculate_sum(numbers):
    total = 0
    for i in range(len(numbers)):
        total = total + numbers[i]
    return total
```

**AI-Optimized Output:**

```python
def calculate_sum(numbers):
    return sum(numbers)
```

## 🔮 Future Scope

* GitHub & Pull Request integration
* Code quality scoring
* Persistent review history
* Real-time code editor
* Advanced vulnerability detection
* Performance benchmarking
* Docker & cloud deployment

## 👨‍💻 Author

**Krishna Keerthana**
[GitHub](https://github.com/techy-ops)

---

<!-- update -->
