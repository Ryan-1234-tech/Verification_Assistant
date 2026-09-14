from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    max_upload_mb: int = 10
    data_dir: Path = Path(__file__).resolve().parent / "data"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    use_ollama: bool = True
    use_paddle_ocr: bool = False

    class Config:
        env_file = ".env"


settings = Settings()
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
# Store reports in backend/reports outside the watched app/ folder to prevent reload aborts
REPORTS_DIR = BASE_DIR.parent / "reports"
REPORTS_DIR.mkdir(exist_ok=True)
