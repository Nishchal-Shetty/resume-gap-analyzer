from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from analyzer import analyze_resume
from scraper import extract_text_from_pdf, extract_text_from_url

app = FastAPI(title="Resume Gap Analyzer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class TextRequest(BaseModel):
    resume_text: str
    jd_text: str


class UrlRequest(BaseModel):
    resume_text: str
    jd_url: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze/text")
def analyze_text(body: TextRequest):
    if not body.resume_text.strip():
        raise HTTPException(status_code=400, detail="resume_text must not be empty.")
    if not body.jd_text.strip():
        raise HTTPException(status_code=400, detail="jd_text must not be empty.")
    try:
        return analyze_resume(body.resume_text, body.jd_text)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/analyze/upload")
async def analyze_upload(
    pdf_file: UploadFile = File(...),
    jd_text: str = Form(...),
):
    if not pdf_file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Uploaded file must be a PDF.")
    if not jd_text.strip():
        raise HTTPException(status_code=400, detail="jd_text must not be empty.")
    try:
        pdf_bytes = await pdf_file.read()
        resume_text = extract_text_from_pdf(pdf_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    try:
        return analyze_resume(resume_text, jd_text)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/analyze/url")
async def analyze_url(body: UrlRequest):
    if not body.resume_text.strip():
        raise HTTPException(status_code=400, detail="resume_text must not be empty.")
    if not body.jd_url.strip():
        raise HTTPException(status_code=400, detail="jd_url must not be empty.")
    try:
        jd_text = extract_text_from_url(body.jd_url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    try:
        return analyze_resume(body.resume_text, jd_text)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
