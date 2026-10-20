from app.models import ValidationResult


def verify(state: dict) -> dict:
    docs = state["documents"]
    by_type = {doc.document_type: doc for doc in docs}
    applicant_name = state.get("applicant_name", "").strip()
    results: list[ValidationResult] = []
    audit_notes: list[str] = []

    for rule in state["rules"]:
        document = by_type.get(rule["document_type"])
        source_url = rule.get("source_url")
        source_category = rule.get("source_category", "official")
        source_name = rule.get("source_name", "Official Requirement")
        doc_type = rule.get("document_type", "").lower()
        rule_title = rule.get("title", "")
        rule_desc = rule.get("description", "")

        if not document:
            status = "warning" if not rule.get("required", True) else "failed"
            prefix = "Optional document not submitted" if status == "warning" else "Missing required document"
            results.append(
                ValidationResult(
                    rule_id=rule["id"],
                    title=rule_title,
                    status=status,
                    message=f"{prefix}: {rule_title}.",
                    evidence=None,
                    source_url=source_url,
                    source_category=source_category,
                    source_name=source_name,
                )
            )
            continue

        # Check if the uploaded document is an empty / unfilled template or blank form
        is_empty_template = document.fields.get("is_empty_template") == "true"
        template_issues = document.fields.get("template_issues", "")

        if rule["check"] == "present":
            if is_empty_template:
                status = "failed"
                if "anti_ragging" in doc_type or "anti_ragging" in rule.get("id", ""):
                    message = (
                        "Unfilled / Empty Form Detected: The uploaded Anti-Ragging Affidavit appears to be an unfilled "
                        "sample template with blank fill-in lines (e.g. Student Name, Signatures, Date). "
                        "Please upload a completed and signed affidavit."
                    )
                elif "medical" in doc_type:
                    message = (
                        "Unfilled Form Detected: The uploaded Physical/Medical Fitness Certificate is an empty template "
                        "without doctor signature, medical registration number, or certification."
                    )
                else:
                    message = f"Incomplete Document: {document.filename} is an unfilled template or blank form. {template_issues}".strip()
                audit_notes.append(f"Verification Agent: Rejected unfilled template for {rule_title} ({document.filename}).")
            elif not document.extracted_text.strip() and doc_type != "photo":
                status = "failed"
                message = f"Unreadable file: Could not extract readable text from {document.filename}. Please upload a clear PDF or image."
            else:
                status = "passed"
                doc_name = document.fields.get("name")
                if doc_name and applicant_name and any(tok.lower() in doc_name.lower() for tok in applicant_name.split() if len(tok) > 2):
                    message = f"Verified document present: {rule_title} (Confirmed for candidate: {doc_name})."
                else:
                    message = f"Verified document present: {rule_title}."

            results.append(
                ValidationResult(
                    rule_id=rule["id"],
                    title=rule_title,
                    status=status,
                    message=message,
                    evidence=document.filename,
                    source_url=source_url,
                    source_category=source_category,
                    source_name=source_name,
                )
            )

        elif rule["check"] == "minimum_percentage":
            minimum = float(rule["value"]) if rule.get("value") is not None else 60.0

            if is_empty_template:
                status = "failed"
                message = "Uploaded mark sheet appears to be an empty template or blank document."
            else:
                pcm_pcb = float(document.fields.get("pcm_pcb_percentage", -1))
                pcm = float(document.fields.get("pcm_percentage", -1))
                pcb = float(document.fields.get("pcb_percentage", -1))
                overall = float(document.fields.get("overall_percentage", -1))
                direct_pct = float(document.fields.get("percentage", -1))
                pcm_summary = document.fields.get("pcm_summary", "")
                pcb_summary = document.fields.get("pcb_summary", "")
                subjects_detail = document.fields.get("subjects_detail", "")

                is_pcm_rule = "pcm" in rule_title.lower() or "pcm" in rule_desc.lower() or "pcb" in rule_title.lower()

                # Determine effective score
                if is_pcm_rule and pcm_pcb > 0:
                    effective_score = pcm_pcb
                else:
                    candidates = [s for s in (direct_pct, overall, pcm_pcb) if s >= 0]
                    effective_score = max(candidates) if candidates else -1

                if effective_score >= minimum:
                    status = "passed"
                    if is_pcm_rule and pcm > 0:
                        overall_note = f" (Overall: {overall:g}%)" if overall > 0 else ""
                        message = f"Academic score meets requirements: {pcm_summary}{overall_note}, exceeding the {minimum:g}% minimum threshold."
                    elif is_pcm_rule and pcb > 0:
                        overall_note = f" (Overall: {overall:g}%)" if overall > 0 else ""
                        message = f"Academic score meets requirements: {pcb_summary}{overall_note}, exceeding the {minimum:g}% minimum threshold."
                    elif overall > 0:
                        detail = f" ({subjects_detail})" if subjects_detail else ""
                        message = f"Academic score {effective_score:g}% meets the {minimum:g}% minimum requirement{detail}."
                    else:
                        message = f"Academic score {effective_score:g}% meets the {minimum:g}% minimum requirement."
                elif effective_score >= 0:
                    status = "failed"
                    if is_pcm_rule and pcm > 0:
                        message = f"Academic score {pcm:g}% in PCM does not meet the required {minimum:g}% minimum qualifying aggregate."
                    else:
                        message = f"Academic score {effective_score:g}% is below the required {minimum:g}% minimum qualifying score."
                else:
                    status = "failed"
                    message = f"Could not verify qualifying score of at least {minimum:g}%. Upload a clear Class 12 mark sheet showing subject marks."

            results.append(
                ValidationResult(
                    rule_id=rule["id"],
                    title=rule_title,
                    status=status,
                    message=message,
                    evidence=document.filename,
                    source_url=source_url,
                    source_category=source_category,
                    source_name=source_name,
                )
            )

    updated = dict(state)
    updated["results"] = results
    passed_count = sum(1 for r in results if r.status == "passed")
    failed_count = sum(1 for r in results if r.status == "failed")
    updated["audit_trail"] = list(state.get("audit_trail", [])) + audit_notes + [
        f"Verification Agent: evaluated {len(results)} requirements ({passed_count} passed, {failed_count} failed) against multi-source guidelines."
    ]
    return updated