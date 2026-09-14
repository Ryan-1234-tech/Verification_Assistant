# Agentic AI University Application Verification Assistant

This is an end-to-end starter implementation of the project in the presentation.
It accepts university application documents, extracts text, retrieves admission rules,
checks the documents deterministically, and returns a readiness dashboard plus a PDF report.

## 1. Prerequisites

- Python 3.11+
- Node.js 20+
- (optional, production OCR) [PaddleOCR system dependencies](https://www.paddleocr.ai/)
- (optional, AI suggestions) Ollama running locally with `ollama pull llama3.2`

## 2. Create the environment

Open two terminals in this folder.

```powershell
# Terminal 1: API
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload --port 8001
```

```powershell
# Terminal 2: React web app
cd frontend
npm install
Copy-Item .env.local.example .env.local
npm run dev
```

Open `http://localhost:5173`. API documentation is at `http://localhost:8001/docs`.

## 3. Demo workflow

1. Choose an application type and enter an applicant name.
2. Upload files whose names indicate their type, such as `passport.pdf`,
   `marksheet.pdf`, `income_certificate.pdf`, and `photo.jpg`.
3. Click **Verify application**. The system extracts text, identifies document types,
   checks the configured rules, calculates readiness, produces suggestions, and makes
   a PDF report available.

For a predictable first demo, upload a readable passport, marksheet/transcript, and
a photo. The filename helps document classification while the OCR parser is still a
starter implementation.

## 4. How the agents map to the design

| Presentation agent | Code | Responsibility |
| --- | --- | --- |
| Planner | `app/agents/planner.py` | creates the verification plan |
| OCR | `app/services/ocr.py` | reads PDF/image text |
| Requirement/RAG | `app/services/rules.py` | retrieves application rules |
| Verification | `app/agents/verifier.py` | runs traceable checks |
| Report | `app/services/report.py` | produces a PDF |
| Orchestrator | `app/graph.py` | runs the LangGraph workflow |

## 5. Production upgrades

1. Replace `app/data/rules.json` with university-controlled rule records in Supabase.
2. Index official prospectuses in ChromaDB and use BAAI `bge-small-en` embeddings to
   retrieve rule passages; keep `verifier.py` deterministic for final pass/fail results.
3. Configure PaddleOCR in `.env`; scanned PDFs then use real OCR. Text PDFs work now
   through `pypdf`.
4. Add document malware scanning, S3/Supabase Storage, authentication, encryption,
   audit logs, consent retention/deletion, and human review before a real deployment.
5. Use Ollama only to word suggestions; never let an LLM make the acceptance decision.

## API contract

`POST /api/v1/verifications` accepts multipart fields: `applicant_name`,
`application_type`, and one or more `documents`. It returns an id, readiness score,
individual validation results, suggestions, audit trail, and a `report_url`.
