from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://postgres:password@localhost:5432/foodgrump"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Auth
    secret_key: str = "change-me"
    access_token_expire_minutes: int = 1440
    algorithm: str = "HS256"

    # Google Places
    google_places_api_key: str = ""

    # OpenAI
    openai_api_key: str = ""

    # AWS S3
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_s3_bucket: str = "foodgrump-photos"
    aws_region: str = "us-east-1"
    aws_cloudfront_domain: str = ""

    # Beli
    beli_email: str = ""
    beli_password: str = ""

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
