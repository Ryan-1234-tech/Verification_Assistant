import json
from pathlib import Path
from app.config import settings
from app.models import IndianCollege, University

COLLEGES_FILE = settings.data_dir / "indian_engineering_colleges.json"

_cached_colleges: list[IndianCollege] | None = None


def load_colleges() -> list[IndianCollege]:
    global _cached_colleges
    if _cached_colleges is not None:
        return _cached_colleges

    if not COLLEGES_FILE.exists():
        return []

    try:
        data = json.loads(COLLEGES_FILE.read_text(encoding="utf-8"))
        _cached_colleges = [IndianCollege.model_validate(item) for item in data]
    except Exception:
        _cached_colleges = []

    return _cached_colleges


def get_states() -> list[str]:
    colleges = load_colleges()
    states = sorted({college.state for college in colleges if college.state})
    return states


def get_categories() -> list[str]:
    colleges = load_colleges()
    categories = sorted({college.category for college in colleges if college.category})
    return categories


def find_college(identifier: str) -> IndianCollege | None:
    colleges = load_colleges()
    query_clean = identifier.strip().lower()
    if not query_clean:
        return None

    # Exact match by id or domain
    for c in colleges:
        if c.id.lower() == query_clean or c.domain.lower() == query_clean:
            return c

    # Match domain without subdomains or protocol
    clean_domain = (
        query_clean.replace("https://", "")
        .replace("http://", "")
        .split("/")[0]
        .lower()
    )
    for c in colleges:
        if clean_domain in c.domain.lower() or c.domain.lower() in clean_domain:
            return c

    # Match name or short_name
    for c in colleges:
        if query_clean in c.name.lower() or query_clean in c.short_name.lower():
            return c

    return None


def search_colleges(
    query: str = "",
    state: str = "",
    category: str = "",
    limit: int = 150,
) -> list[IndianCollege]:
    colleges = load_colleges()
    q = query.strip().lower()
    state_filter = state.strip().lower()
    cat_filter = category.strip().lower()

    results: list[IndianCollege] = []
    for c in colleges:
        if state_filter and state_filter != "all" and c.state.lower() != state_filter:
            continue
        if cat_filter and cat_filter != "all" and c.category.lower() != cat_filter:
            continue

        if q:
            searchable_text = (
                f"{c.name} {c.short_name} {c.city} {c.state} {c.domain} "
                f"{c.category} {' '.join(c.entrance_exams)} {c.counseling_body}"
            ).lower()
            if q not in searchable_text:
                continue

        results.append(c)

    return results[:limit]


async def search_universities(query: str) -> list[University]:
    """
    Backward compatible search endpoint for Indian Engineering Colleges.
    """
    colleges = search_colleges(query=query)
    return [
        University(
            id=c.id,
            name=c.name,
            short_name=c.short_name,
            category=c.category,
            state=c.state,
            city=c.city,
            domain=c.domain,
            admissions_portal=c.admissions_portal,
            entrance_exams=c.entrance_exams,
            counseling_body=c.counseling_body,
            country="India",
        )
        for c in colleges
    ]


class UniversityDirectoryUnavailable(Exception):
    pass