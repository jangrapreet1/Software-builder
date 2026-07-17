"""
Configuration settings for the coordinator
"""
from pathlib import Path

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
    cors_allow_origins: list[str] = ["*"]
    
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
    preview_allowed_hosts: list[str] = [
        "localhost",
        "127.0.0.1",
        "0.0.0.0",
        "::1",
    ]

    # Rate limiting (SlowAPI)
    rate_limit_build: str = "10/minute"
    rate_limit_read: str = "60/minute"
    rate_limit_write: str = "10/minute"
    rate_limit_detect: str = "10/minute"
    rate_limit_problem_resolver: str = "10/minute"
    rate_limit_preview: str = "20/minute"
    rate_limit_chat_message: str = "60/minute"
    rate_limit_chat_patch: str = "30/minute"
    rate_limit_chat_attachment: str = "20/minute"

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
