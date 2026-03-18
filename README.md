# Resume Gap Analyzer

Analyze any resume against a job description using Claude's tool use API — get a match score, skill gap breakdown, missing ATS keywords, and rewritten bullet points in seconds.

---

## Screenshot

> _Add a screenshot here after first run._
>
> `docs/screenshot.png`

---

## Features

- **Match score** — weighted overall fit score (skills 40%, experience 40%, keywords 20%)
- **Skill gap analysis** — matched and missing skills pulled from both documents
- **Experience assessment** — seniority fit rating and qualitative assessment
- **ATS keyword extraction** — identifies missing keywords and rates your ATS risk (low / medium / high)
- **Bullet point rewrites** — Claude rewrites weak resume bullets to better fit the role
- **Three input modes** — paste text, upload a PDF, or point to a job posting URL
- **Tool use architecture** — four specialized Claude tools run in a single agentic loop, each focused on one dimension of the analysis

---

## Tech Stack

| Layer     | Technology                                      |
|-----------|-------------------------------------------------|
| LLM       | Anthropic Claude (`claude-sonnet-4-6`), tool use pattern |
| Backend   | Python 3.11, FastAPI, Uvicorn                   |
| Scraping  | pdfplumber (PDF), BeautifulSoup4 + requests (URL) |
| Frontend  | React 18, Vite, Tailwind CSS                    |

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- An [Anthropic API key](https://console.anthropic.com/)

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd resume-gap-analyzer
```

### 2. Set up the backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and add your key:

```
ANTHROPIC_API_KEY=sk-ant-...
```

> **Never commit `.env` to version control.** It is listed in `.gitignore` for this reason. Anyone with your API key can make requests billed to your account.

### 4. Start the backend

```bash
# from the backend/ directory, with venv active
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`. Visit `http://localhost:8000/docs` for the interactive Swagger UI.

### 5. Set up and start the frontend

```bash
cd ../frontend
npm install
npm run dev
```

The app will be available at `http://localhost:5173`.

---

## How to Use

Open `http://localhost:5173` in your browser. The left column takes your resume and the right column takes the job description. Each side has two input modes — toggle between them with the buttons above each field.

### Resume input

| Mode | When to use |
|------|-------------|
| **Paste Text** | Copy-paste plain text or Markdown from your resume |
| **Upload PDF** | Upload a `.pdf` file — text is extracted automatically |

### Job description input

| Mode | When to use |
|------|-------------|
| **Paste Text** | Copy-paste the job description directly |
| **Enter URL** | Paste a link to a job posting — the backend scrapes the visible text |

Click **Analyze Match** and wait 10–20 seconds while Claude runs all four analysis tools. Results appear in place with:

- A circular overall match score (green ≥ 75, yellow 50–74, red < 50)
- Skills and experience cards with per-dimension scores
- Missing keyword chips color-coded by ATS risk level
- Side-by-side before/after bullet point rewrite suggestions

Click **← Analyze Another** to reset and run a new analysis.

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/analyze/text` | Analyze from plain text (JSON body) |
| `POST` | `/analyze/upload` | Analyze from PDF upload (multipart form) |
| `POST` | `/analyze/url` | Analyze with JD fetched from URL (JSON body) |

All three analyze endpoints return the same JSON shape:

```json
{
  "overall_score": 72,
  "skills": { "matched": [...], "missing": [...], "score": 80 },
  "experience": { "assessment": "...", "score": 65, "seniority_fit": "good" },
  "keywords": { "missing_keywords": [...], "ats_risk": "medium" },
  "rewrites": { "rewrites": [{ "original": "...", "improved": "...", "reason": "..." }] }
}
```

---

## Project Structure

```
resume-gap-analyzer/
├── backend/
│   ├── main.py          # FastAPI routes
│   ├── analyzer.py      # Claude tool use loop — all LLM logic lives here
│   ├── scraper.py       # PDF and URL text extraction
│   ├── requirements.txt
│   └── .env.example
├── frontend/
    ├── src/
    │   ├── App.jsx      # Single-file React app (input form + results view)
    │   ├── main.jsx
    │   └── index.css
    ├── index.html
    ├── vite.config.js
    └── tailwind.config.js
```
