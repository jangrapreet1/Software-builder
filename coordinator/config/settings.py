"""
Configuration settings for the coordinator
"""
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # Google Gemini Configuration
    google_api_key: str
    gemini_model: str = "gemini-2.5-flash"
    
    # Database Configuration
    database_url: str = "postgresql://postgres:postgres@localhost:5432/appbuilder"
    
    # Application Configuration
    coordinator_host: str = "0.0.0.0"
    coordinator_port: int = 5000
    backend_port: int = 8000
    frontend_port: int = 3000
    
    # Generated Apps Directory
    generated_apps_dir: str = Field(
        default_factory=lambda: str((Path(__file__).resolve().parents[2] / "generated").resolve())
    )
    
    # Agent Configuration
    max_retries: int = 3
    agent_timeout: int = 300
    
    # Docker Configuration
    docker_network: str = "appbuilder-network"
    sandbox_read_only_rootfs: bool = True
    sandbox_default_deny_egress: bool = True

    # Object Storage (S3/MinIO)
    object_store_endpoint: str = "http://localhost:9000"
    object_store_region: str | None = None
    object_store_access_key: str | None = None
    object_store_secret_key: str | None = None
    object_store_bucket: str = "appbuilder"
    object_store_use_path_style: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"
