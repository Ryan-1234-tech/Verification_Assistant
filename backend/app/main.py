import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import httpx
from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import REPORTS_DIR, settings
from app.graph import verification_graph
from app.models import ExtractedDocument, IndianCollege, RequirementChecklist, University, VerificationResponse
from app.services.ocr import read_document
from app.services.report import create_pdf
from app.services.rules import create_checklist, get_requirement_set
from app.services.suggestions import build_suggestions
from app.services.universities import (
    get_categories,
    get_states,
    search_colleges,
    search_universities,
)

app = FastAPI(
    title="Indian Engineering Colleges Application Verification Assistant API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/reports", StaticFiles(directory=REPORTS_DIR), name="reports")


@app.get("/health")
def health():
    return {"status": "ok", "mode": "indian_engineering_colleges"}


@app.get("/api/v1/colleges", response_model=list[IndianCollege])
def get_colleges(
    query: str = Query("", max_length=120),
    state: str = Query("", max_length=60),
    category: str = Query("", max_length=60),
):
    return search_colleges(query=query, state=state, category=category)


@app.get("/api/v1/colleges/states", response_model=list[str])
def states_list():
    return get_states()


@app.get("/api/v1/colleges/categories", response_model=list[str])
def categories_list():
    return get_categories()


@app.get("/api/v1/universities", response_model=list[University])
async def universities(query: str = Query("", max_length=120)):
    return await search_universities(query)


@app.post("/api/v1/requirements", response_model=RequirementChecklist)
async def requirements(
    university_name: str = Form(...),
    university_domain: str = Form(...),
    application_type: str = Form("undergraduate"),
):
    try:
        return await create_checklist(
            university_name=university_name,
            university_domain=university_domain,
            application_type=application_type,
        )
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    except Exception as error:
        raise HTTPException(500, f"Error generating requirements: {error}") from error


@app.post("/api/v1/verifications", response_model=VerificationResponse)
async def verify_application(
    applicant_name: str = Form(...),
    requirement_set_id: str = Form(...),
    documents: list[UploadFile] = File(...),
    document_types: list[str] = Form(...),
):
    checklist = get_requirement_set(requirement_set_id)
    if not checklist:
        raise HTTPException(400, "Checklist expired or not found. Please retrieve requirements again.")

    if not documents or len(documents) != len(document_types):
        raise HTTPException(400, "Each uploaded document must correspond to a checklist requirement.")

    verification_id = str(uuid4())
    extracted: list[ExtractedDocument] = []

    with tempfile.TemporaryDirectory() as temp:
        temp_dir = Path(temp)

        for upload, document_type in zip(documents, document_types):
            payload = await upload.read()
            if len(payload) > settings.max_upload_mb * 1024 * 1024:
                raise HTTPException(
                    413,
                    f"{upload.filename} exceeds maximum allowed size ({settings.max_upload_mb} MB).",
                )

            safe_name = Path(upload.filename or "document").name
            destination = temp_dir / safe_name
            destination.write_bytes(payload)

            text, _, fields = read_document(destination, safe_name)
            extracted.append(
                ExtractedDocument(
                    filename=safe_name,
                    document_type=document_type,
                    extracted_text=text[:5000],
                    fields=fields,
                )
            )

    state = verification_graph.invoke(
        {
            "verification_id": verification_id,
            "applicant_name": applicant_name,
            "university_name": checklist.university_name,
            "application_type": checklist.application_type,
            "documents": extracted,
            "rules": [item.model_dump() for item in checklist.requirements],
            "audit_trail": [
                f"Institution selected: {checklist.university_name} ({checklist.college_category}).",
                f"Multi-source requirement discovery: JoSAA/AICTE/Official/Quora guidelines loaded.",
                f"Upload: received {len(extracted)} candidate document(s).",
                "OCR Agent: parsed document textual content and credential fields.",
            ],
        }
    )

    scored = [result for result in state["results"] if result.status != "warning"]
    readiness = (
        round(100 * sum(result.status == "passed" for result in scored) / len(scored))
        if scored
        else 0
    )

    state["readiness_score"] = readiness
    state["suggestions"] = await build_suggestions(state["results"])
    create_pdf(state)
    state["audit_trail"].append("Report Agent: compiled verified PDF verification audit certificate.")

    return VerificationResponse(
        verification_id=verification_id,
        applicant_name=applicant_name,
        university_name=checklist.university_name,
        application_type=checklist.application_type,
        readiness_score=readiness,
        results=state["results"],
        suggestions=state["suggestions"],
        documents=extracted,
        audit_trail=state["audit_trail"],
        report_url=f"http://localhost:8000/reports/{verification_id}.pdf",
        created_at=datetime.now(timezone.utc),
    )
