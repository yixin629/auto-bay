from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_name: str = "AutoBay"
    app_env: str = "development"
    debug: bool = True
    secret_key: str = "change-me"
    api_v1_prefix: str = "/api/v1"
    frontend_url: str = "http://localhost:3000"

    # Database
    database_url: str = "postgresql+asyncpg://autobay:autobay@localhost:5432/autobay"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Celery
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # JWT
    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # Credentials encryption (at rest)
    credentials_encryption_key: str = "change-me-credentials-key"

    # AI
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    # eBay
    ebay_app_id: str = ""
    ebay_dev_id: str = ""
    ebay_cert_id: str = ""
    ebay_redirect_uri: str = ""
    ebay_sandbox: bool = True

    # Amazon SP-API
    amazon_sp_client_id: str = ""
    amazon_sp_client_secret: str = ""
    amazon_sp_refresh_token: str = ""
    amazon_sp_role_arn: str = ""

    # Shopify
    shopify_api_key: str = ""
    shopify_api_secret: str = ""
    shopify_store_url: str = ""

    # TikTok Shop
    tiktok_app_key: str = ""
    tiktok_app_secret: str = ""

    # Douyin
    douyin_app_id: str = ""
    douyin_app_secret: str = ""
    douyin_oauth_authorize_url: str = "https://open.douyin.com/platform/oauth/connect"
    douyin_oauth_token_url: str = "https://open.douyin.com/oauth/access_token/"
    douyin_oauth_redirect_uri: str = "http://localhost:8000/api/v1/products/platform-connections/oauth/callback?platform=douyin"

    # Xiaohongshu (RED)
    xiaohongshu_app_id: str = ""
    xiaohongshu_app_secret: str = ""
    xiaohongshu_oauth_authorize_url: str = "https://ark.xiaohongshu.com/open_api/v3/oauth/authorize"
    xiaohongshu_oauth_token_url: str = "https://ark.xiaohongshu.com/open_api/v3/oauth/access_token"
    xiaohongshu_oauth_redirect_uri: str = "http://localhost:8000/api/v1/products/platform-connections/oauth/callback?platform=xiaohongshu"

    # S3/MinIO
    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "autobay"
    s3_region: str = "us-east-1"

    # Exchange Rate
    exchange_rate_api_key: str = ""

    # Sync health rules
    sync_stale_threshold_minutes: int = 120

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


settings = Settings()
