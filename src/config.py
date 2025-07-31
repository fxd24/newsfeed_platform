from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration with environment variable support"""
    
    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False


# Global settings instance
settings = Settings()