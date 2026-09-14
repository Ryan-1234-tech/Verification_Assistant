from app.models import ValidationResult


def verify(state: dict) -> dict:
    docs = state["documents"]
    by_type = {doc.document_type: doc for doc in docs}
    results: list[ValidationResult] = []

    for rule in state["rules"]:
        document = by_type.get(rule["document_type"])
        source_url = rule.get("source_url")
        source_category = rule.get("source_category", "official")
        source_name = rule.get("source_name", "Official Requirement")

        if rule["check"] == "present":
            status = "passed" if document else ("warning" if not rule["required"] else "failed")
            prefix = "Verified document present" if document else "Missing required document"
            results.append(
                ValidationResult(
                    rule_id=rule["id"],
                    title=rule["title"],
                    status=status,
                    message=f"{prefix}: {rule['title']}.",
                    evidence=document.filename if document else None,
                    source_url=source_url,
                    source_category=source_category,
                    source_name=source_name,
                )
            )

        elif rule["check"] == "minimum_percentage":
            try:
                score = float(document.fields.get("percentage", -1)) if document else -1
            except ValueError:
                score = -1

            minimum = float(rule["value"]) if rule.get("value") is not None else 60.0
            status = "passed" if score >= minimum else "failed"
            message = (
                f"Academic score {score:g}% meets the {minimum:g}% minimum requirement."
                if status == "passed"
                else f"Could not verify qualifying score of at least {minimum:g}%. Upload a clear Class 12 mark sheet."
            )
            results.append(
                ValidationResult(
                    rule_id=rule["id"],
                    title=rule["title"],
                    status=status,
                    message=message,
                    evidence=document.filename if document else None,
                    source_url=source_url,
                    source_category=source_category,
                    source_name=source_name,
                )
            )

    updated = dict(state)
    updated["results"] = results
    updated["audit_trail"] = list(state.get("audit_trail", [])) + [
        f"Verification Agent: evaluated {len(results)} requirements against multi-source guidelines."
    ]
    return updated