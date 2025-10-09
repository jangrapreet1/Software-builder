"""
Configuration settings for the coordinator
"""
from pydantic_settings import BaseSettings
from typing import Optional


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
    generated_apps_dir: str = "./generated"
    
    # Agent Configuration
    max_retries: int = 3
    agent_timeout: int = 300
    
    # Docker Configuration
    docker_network: str = "appbuilder-network"
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"
