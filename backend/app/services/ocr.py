import re
from pathlib import Path
from pypdf import PdfReader
from PIL import Image
from app.config import settings


def classify_document(filename: str, text: str) -> str:
    sample = f"{filename} {text}".lower()

    if any(word in sample for word in ("anti-ragging", "antiragging", "anti ragging", "ragging", "undertaking by the student", "code of conduct")):
        return "anti_ragging_affidavit"
    if any(word in sample for word in ("senior school certificate", "class xii", "class 12", "higher secondary", "hsc", "10+2", "intermediate")):
        return "class_12_marksheet"
    if any(word in sample for word in ("secondary school examination", "class x", "class 10", "matriculation", "sslc", "high school examination")):
        return "class_10_marksheet"
    if any(word in sample for word in ("seat allotment", "provisional allotment", "allotment letter", "josaa", "csab", "counseling")):
        return "seat_allotment_letter"
    if any(word in sample for word in ("jee main", "jee advanced", "viteee", "met score", "srmjeee", "rank card", "score card", "percentile score")):
        return "jee_scorecard"
    if any(word in sample for word in ("medical fitness", "physical fitness", "medical practitioner", "registered medical", "blood group")):
        return "medical_certificate"
    if any(word in sample for word in ("migration certificate", "transfer certificate", "school leaving certificate", "college leaving certificate", "tc ")):
        return "migration_certificate"
    if any(word in sample for word in ("caste certificate", "community certificate", "obc-ncl", "sc/st", "gen-ews", "non-creamy layer")):
        return "caste_certificate"
    if any(word in sample for word in ("aadhaar", "uidai", "passport", "voter id", "driving license", "identity card", "nationality", "date of birth")):
        return "identity_card"
    if any(word in sample for word in ("income", "annual income", "salary certificate", "earnings")):
        return "income_certificate"
    if any(word in sample for word in ("photo", "photograph", "passport size", "selfie")):
        return "photo"
    if any(word in sample for word in ("marksheet", "transcript", "semester", "grade", "percentage", "total marks")):
        return "marksheet"

    return "unknown"


def detect_empty_or_template(text: str, filename: str = "", doc_type: str = "") -> tuple[bool, list[str]]:
    """
    Detects if a document is an unfilled form, generic blank template, or empty placeholder.
    """
    reasons: list[str] = []
    clean_text = text.strip()

    # 1. Zero or negligible text
    if not clean_text:
        return True, ["Document contains no readable text or is completely blank."]

    # 2. Sample / demonstration / placeholder disclaimer notices
    sample_keywords = [
        "sample anti-ragging",
        "sample format",
        "generic sample format",
        "demonstration purposes only",
        "replace the blank fields",
        "do not present this sample as an official",
        "blank template",
        "sample affidavit",
        "specimen copy",
        "draft format",
        "sample undertaking",
        "for project use:",
    ]
    for kw in sample_keywords:
        if kw in text.lower():
            reasons.append(f"Document contains sample/template notice: '{kw.title()}'.")
            break

    # 3. Form field labels followed by blanks/underscores or empty lines
    unfilled_field_patterns = [
        (r"(?:student\s+name|candidate\s+name)\s*[:=-]?\s*(?:_{2,}|\s*$)", "Student Name"),
        (r"(?:father|mother|guardian)(?:'s)?\s*name\s*[:=-]?\s*(?:_{2,}|\s*$)", "Father/Mother/Guardian Name"),
        (r"(?:roll|registration)\s*(?:no|number)?\.?\s*[:=-]?\s*(?:_{2,}|\s*$)", "Roll / Registration Number"),
        (r"(?:course|programme|branch)\s*[:=-]?\s*(?:_{2,}|\s*$)", "Course / Programme"),
        (r"(?:year|semester)\s*[:=-]?\s*(?:_{2,}|\s*$)", "Year / Semester"),
        (r"(?:name\s+of\s+institution|institution|college|university)\s*[:=-]?\s*(?:_{2,}|\s*$)", "Institution Name"),
        (r"(?:academic\s+year|session)\s*[:=-]?\s*(?:_{2,}|\s*$)", "Academic Year"),
        (r"(?:student\s+signature|signature\s+of\s+student|signature)\s*[:=-]?\s*(?:_{2,}|\s*$)", "Student Signature"),
        (r"(?:parent\s+signature|signature\s+of\s+parent)\s*[:=-]?\s*(?:_{2,}|\s*$)", "Parent Signature"),
        (r"(?:date)\s*[:=-]?\s*(?:_{2,}|\s*$)", "Date"),
        (r"(?:place)\s*[:=-]?\s*(?:_{2,}|\s*$)", "Place"),
    ]

    unfilled_found: list[str] = []
    for pattern, label in unfilled_field_patterns:
        for line in text.splitlines():
            line_str = line.strip()
            if line_str and re.search(pattern, line_str, re.I):
                unfilled_found.append(label)
                break

    if unfilled_found:
        reasons.append(f"Unfilled blank fields detected: {', '.join(unfilled_found[:5])}.")

    # 4. Count raw underscore fill-in runs (e.g. ________)
    underscore_runs = len(re.findall(r"_{3,}", text))
    if underscore_runs >= 3 and not any("Unfilled blank fields" in r for r in reasons):
        reasons.append(f"Detected {underscore_runs} blank fill-in lines in document.")

    # 5. Filename indicates a template
    fn_lower = filename.lower()
    if any(tag in fn_lower for tag in ("sample_anti_ragging", "sample_affidavit", "blank_template", "empty_template", "sample_form")):
        reasons.append(f"Filename '{filename}' indicates a sample or template document.")

    is_empty = len(reasons) > 0
    return is_empty, reasons


def extract_fields(text: str, filename: str = "") -> dict[str, str]:
    fields: dict[str, str] = {}

    # Check if empty / template
    is_template, reasons = detect_empty_or_template(text, filename)
    fields["is_empty_template"] = "true" if is_template else "false"
    if reasons:
        fields["template_issues"] = "; ".join(reasons)

    # 1. Candidate Name Extraction
    name_patterns = [
        r"this\s+is\s+to\s+certify\s+that\s+([A-Za-z\s.]{3,40})",
        r"(?:candidate|student)\s*['’]?s?\s*name\s*[:=-]?\s*([A-Za-z\s.]{3,40})",
        r"name\s*[:=-]\s*([A-Za-z\s.]{3,40})",
        r"i,\s*([A-Za-z\s.]{3,40}),\s*(?:s/o|d/o|son|daughter)",
    ]
    for np in name_patterns:
        m = re.search(np, text, re.I)
        if m:
            c_name = m.group(1).strip().split("\n")[0].strip()
            c_name = re.sub(r"_{2,}", "", c_name).strip()
            if len(c_name) >= 3 and not re.search(r"^(?:mother|father|school|roll|the|undersigned)", c_name, re.I):
                fields["name"] = c_name
                break

    # 2. Roll No / Registration No
    roll_m = re.search(r"(?:roll\s*no\.?|registration\s*no\.?)\s*[:=-]?\s*([A-Za-z0-9]+)", text, re.I)
    if roll_m:
        fields["roll_no"] = roll_m.group(1).strip()

    # 3. Direct explicit percentage or totals
    percent_m = re.search(r"(?:percentage|aggregate|marks\s+obtained)\s*[:=-]?\s*(\d{1,3}(?:\.\d+)?)\s*%", text, re.I)
    if percent_m:
        fields["percentage"] = percent_m.group(1)

    # 4. Total marks like 463/500
    grand_total_m = re.search(r"(?:grand\s+total|total\s+marks|total)\s*[:=-]?\s*(\d{2,4})\s*/\s*(\d{2,4})", text, re.I)
    if grand_total_m:
        obt, tot = float(grand_total_m.group(1)), float(grand_total_m.group(2))
        if tot > 0:
            calc_p = round((obt / tot) * 100, 2)
            fields["percentage"] = str(calc_p)
            fields["total_marks"] = f"{obt:g}/{tot:g}"

    # 5. Parse Subject Rows (CBSE / State Boards)
    subjects: dict[str, float] = {}

    # Comprehensive CBSE line pattern:
    # code (3 digits) name (words) theory (2-3 digits) practical (2-3 digits) total (2-3 digits)
    cbse_rows = re.findall(
        r"(\d{3})\s+([A-Z\s&/]+?)\s+(\d{2,3})\s+(\d{2,3})\s+(\d{2,3})\s+([A-Z\s]+)\s+([A-D][1-2]|E)",
        text,
        re.I,
    )
    for code, sname, th, pr, tot, words, grade in cbse_rows:
        sname_clean = sname.strip().upper()
        if "PHYSICS" in sname_clean:
            norm_name = "PHYSICS"
        elif "CHEMISTRY" in sname_clean:
            norm_name = "CHEMISTRY"
        elif "MATHEMATICS" in sname_clean or "MATH" in sname_clean:
            norm_name = "MATHEMATICS"
        elif "BIOLOGY" in sname_clean or "BIOTECHNOLOGY" in sname_clean:
            norm_name = "BIOLOGY"
        elif "ENGLISH" in sname_clean:
            norm_name = "ENGLISH"
        else:
            norm_name = sname_clean

        try:
            subjects[norm_name] = float(tot)
        except ValueError:
            pass

    # Generic subject patterns for other boards/formats
    key_subject_patterns = {
        "PHYSICS": [r"(?:042\s+)?PHYSICS\s*(?:CORE)?\s*.*?(\d{2,3})\s*(?:[A-Z\s]+)?\s*(?:[A-D][1-2]|PASS)?$", r"PHYSICS\s*[:=-]?\s*(\d{2,3})"],
        "CHEMISTRY": [r"(?:043\s+)?CHEMISTRY\s*(?:CORE)?\s*.*?(\d{2,3})\s*(?:[A-Z\s]+)?\s*(?:[A-D][1-2]|PASS)?$", r"CHEMISTRY\s*[:=-]?\s*(\d{2,3})"],
        "MATHEMATICS": [r"(?:041|241\s+)?(?:MATHEMATICS|MATHS|APPLIED MATHEMATICS)\s*.*?(\d{2,3})\s*(?:[A-Z\s]+)?\s*(?:[A-D][1-2]|PASS)?$", r"(?:MATHEMATICS|MATHS)\s*[:=-]?\s*(\d{2,3})"],
        "BIOLOGY": [r"(?:044\s+)?BIOLOGY\s*.*?(\d{2,3})\s*(?:[A-Z\s]+)?\s*(?:[A-D][1-2]|PASS)?$", r"BIOLOGY\s*[:=-]?\s*(\d{2,3})"],
        "ENGLISH": [r"(?:301|101\s+)?ENGLISH\s*(?:CORE|ELECTIVE)?\s*.*?(\d{2,3})\s*(?:[A-Z\s]+)?\s*(?:[A-D][1-2]|PASS)?$", r"ENGLISH\s*[:=-]?\s*(\d{2,3})"],
        "COMPUTER SCIENCE": [r"(?:083\s+)?(?:COMPUTER SCIENCE|INFORMATICS PRACTICES)\s*.*?(\d{2,3})", r"(?:COMPUTER SCIENCE|INFORMATICS)\s*[:=-]?\s*(\d{2,3})"],
    }

    for sub_canonical, patterns in key_subject_patterns.items():
        if sub_canonical not in subjects:
            for pat in patterns:
                m = re.search(pat, text, re.I | re.M)
                if m:
                    try:
                        val = float(m.group(m.lastindex))
                        if 0 <= val <= 100:
                            subjects[sub_canonical] = val
                            break
                    except (ValueError, TypeError):
                        pass

    physics = subjects.get("PHYSICS")
    chemistry = subjects.get("CHEMISTRY")
    math = subjects.get("MATHEMATICS")
    biology = subjects.get("BIOLOGY")

    if physics is not None and chemistry is not None and math is not None:
        pcm = round((physics + chemistry + math) / 3.0, 2)
        fields["pcm_percentage"] = str(pcm)
        fields["pcm_summary"] = f"PCM Aggregate: {pcm}% (Physics: {physics:g}, Chemistry: {chemistry:g}, Maths: {math:g})"

    if physics is not None and chemistry is not None and biology is not None:
        pcb = round((physics + chemistry + biology) / 3.0, 2)
        fields["pcb_percentage"] = str(pcb)
        fields["pcb_summary"] = f"PCB Aggregate: {pcb}% (Physics: {physics:g}, Chemistry: {chemistry:g}, Bio: {biology:g})"

    if "pcm_percentage" in fields or "pcb_percentage" in fields:
        best_science = max(float(fields.get("pcm_percentage", 0)), float(fields.get("pcb_percentage", 0)))
        fields["pcm_pcb_percentage"] = str(best_science)

    academic_scores = [v for k, v in subjects.items() if not any(x in k for x in ("WORK EXPERIENCE", "HEALTH", "PHYSICAL EDUCATION", "GENERAL STUDIES"))]
    if len(academic_scores) >= 3:
        overall = round(sum(academic_scores) / len(academic_scores), 2)
        fields["overall_percentage"] = str(overall)
        if "percentage" not in fields:
            fields["percentage"] = str(fields.get("pcm_pcb_percentage", overall))

    if subjects:
        fields["subjects_detail"] = ", ".join(f"{k}: {v:g}" for k, v in subjects.items())

    # Result pass/fail
    res_m = re.search(r"\bRESULT\s*[:=-]?\s*(PASS|PASSED|QUALIFIED|PROMOTED|FAILED|COMPARTMENT)\b", text, re.I)
    if res_m:
        fields["result"] = res_m.group(1).upper()

    return fields


def read_document(path: Path, filename: str) -> tuple[str, str, dict[str, str]]:
    suffix = path.suffix.lower()
    text = ""
    if suffix == ".pdf":
        try:
            reader = PdfReader(str(path))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception:
            text = ""
    elif suffix in {".txt", ".csv"}:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            text = ""
    elif suffix in {".png", ".jpg", ".jpeg", ".webp"}:
        try:
            with Image.open(str(path)) as img:
                width, height = img.size
                text = f"Image format: {img.format}, Size: {width}x{height}. Valid photo document."
        except Exception:
            text = "Image document submitted."
    elif settings.use_paddle_ocr:
        from paddleocr import PaddleOCR
        ocr = PaddleOCR(use_angle_cls=True, lang="en")
        result = ocr.predict(str(path))
        text = "\n".join(item["rec_text"] for item in result[0])
    else:
        text = "Document submitted."

    classification = classify_document(filename, text)
    fields = extract_fields(text, filename)
    return text, classification, fields

