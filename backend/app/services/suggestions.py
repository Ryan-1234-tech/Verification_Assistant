import httpx
from app.config import settings
from app.models import ValidationResult


async def build_suggestions(results: list[ValidationResult]) -> list[str]:
    failures = [result.message for result in results if result.status == "failed"]
    if not failures:
        return ["Your application meets the configured document checks. Submit it before the deadline."]
    fallback = [f"Action needed: {message}" for message in failures]
    if not settings.use_ollama:
        return fallback
    prompt = "Give 2 concise, practical applicant next steps based only on these checks: " + "; ".join(failures)
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(f"{settings.ollama_base_url}/api/generate", json={"model": settings.ollama_model, "prompt": prompt, "stream": False})
            response.raise_for_status()
            return [line.lstrip("- ").strip() for line in response.json()["response"].splitlines() if line.strip()][:3] or fallback
    except httpx.HTTPError:
        return fallback
