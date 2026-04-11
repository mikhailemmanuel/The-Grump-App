from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://postgres:password@localhost:5432/foodgrump"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Auth
    secret_key: str = "change-me"
    algorithm: str = "HS256"

    # Security
    allowed_origins: list[str] = ["http://localhost:8081", "exp://localhost:8081"]
    environment: str = "dev"  # "dev" or "production"
    secrets_backend: str = "env"  # "env" or "aws"

    # Auth tokens
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30

    # Rate limiting
    rate_limit_default: str = "100/minute"
    rate_limit_authenticated: str = "300/minute"
    rate_limit_auth_endpoints: str = "5/minute"

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

    # Reddit
    reddit_client_id: str = ""
    reddit_client_secret: str = ""

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
