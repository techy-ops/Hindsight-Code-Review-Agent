# 🤖 AI Code Review & Rewrite Agent

An AI-powered developer tool that analyzes source code, detects bugs, security vulnerabilities, and performance issues, and generates optimized code using **Google Gemini AI**.

This project helps developers quickly review and improve their code with automated suggestions.

---

## 🚀 Features

- 🔍 AI-powered code analysis
- ⚡ Automatic code optimization
- 🧠 Detects bugs, security issues, and performance problems
- 💻 Supports multiple programming languages
- 📊 Developer dashboard
- 📜 Code review history
- 📚 API documentation interface

---

## 🏗 Tech Stack

**Frontend**
- HTML
- TailwindCSS
- JavaScript
- Stitch (UI design)

**Backend**
- Python
- FastAPI

**AI**
- Google Gemini API

---

## 📁 Project Structure

```
AI-code-review-agent
│
├── frontend
│   ├── index.html
│   ├── developer_dashboard
│   ├── review_history
│   ├── api_documentation
│   ├── platform_documentation
│   ├── login
│   └── create_account
│
├── backend
│   ├── main.py
│   ├── ai_service.py
│   ├── requirements.txt
│   └── .env
│
└── README.md
```

---

## ⚙️ Setup & Run Locally

### 1️⃣ Clone Repository

```bash
git clone https://github.com/techy-ops/AI-code-review-agent.git
cd AI-code-review-agent
```

### 2️⃣ Install Backend Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 3️⃣ Add Gemini API Key

Create a `.env` file inside the **backend** folder:

```
GEMINI_API_KEY=your_api_key_here
```

Get your API key from:  
https://aistudio.google.com/app/apikey

---

### 4️⃣ Run Backend Server

```bash
uvicorn main:app --reload
```

Server runs at:

```
http://127.0.0.1:8000
```

---

### 5️⃣ Open Frontend

Open the frontend file in a browser:

```
frontend/index.html
```

---

## 📡 API Endpoints

**Code Review**

```
POST /review
```

Request example:

```json
{
  "language": "python",
  "code": "print('hello world')"
}
```

---

**Code Optimization**

```
POST /rewrite
```

Returns an improved and optimized version of the code.

---

## 🧪 Example Test Code

```python
def calculate_sum(numbers):
    total = 0
    for i in range(len(numbers)):
        total = total + numbers[i]
    return total
```

The AI will suggest improvements and optimized code.

---

## 👨‍💻 Author

**Krishna Keerthana**

GitHub  
https://github.com/techy-ops

---

⭐ If you like this project, consider giving it a star!
