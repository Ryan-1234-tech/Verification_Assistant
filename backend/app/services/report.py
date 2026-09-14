from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from app.config import REPORTS_DIR


def create_pdf(state: dict) -> Path:
    file_path = REPORTS_DIR / f"{state['verification_id']}.pdf"
    pdf = canvas.Canvas(str(file_path), pagesize=A4)
    y = 800

    lines = [
        "University Application Verification Report",
        f"Applicant: {state['applicant_name']}",
        f"University: {state['university_name']}",
        f"Application type: {state['application_type']}",
        f"Readiness: {state['readiness_score']}%",
        "",
        "Validation results:",
    ]

    for line in lines:
        pdf.drawString(48, y, line)
        y -= 22

    for result in state["results"]:
        text = f"[{result.status.upper()}] {result.title}: {result.message}"
        pdf.drawString(54, y, text[:115])
        y -= 18

        if result.source_url:
            pdf.drawString(70, y, f"Source: {result.source_url}"[:110])
            y -= 18

        if y < 70:
            pdf.showPage()
            y = 800

    pdf.save()
    return file_path