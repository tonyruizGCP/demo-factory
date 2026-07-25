import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "mock_key")
    gcp_project: str = os.getenv("GCP_PROJECT", "demo-sre-project")
    dataset_id: str = os.getenv("DATASET_ID", "sre_logs_dataset")
    table_id: str = os.getenv("TABLE_ID", "application_logs")
    port: int = 8080

settings = Settings()
