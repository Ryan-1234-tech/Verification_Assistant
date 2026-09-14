def plan(state: dict) -> dict:
    updated = dict(state)
    updated["audit_trail"] = list(state.get("audit_trail", [])) + [
        "Planner: created OCR, rule-retrieval, validation, and reporting plan."
    ]
    return updated
