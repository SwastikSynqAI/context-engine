from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://appuser:changeme@localhost:5432/context_engine"

    # ── Anthropic ─────────────────────────────────────────────────────────────
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"
    # Anthropic does not expose a standalone embedding endpoint yet;
    # embeddings are generated via a summarise-then-encode pattern using
    # text-embedding-3-small (OpenAI) or via the claude messages API.
    # We default to the Claude-based approach for consistency.
    embedding_model: str = "claude-sonnet-4-6"
    embedding_dimensions: int = 1536

    # ── Google ────────────────────────────────────────────────────────────────
    google_service_account_json: str = "credentials/google_service_account.json"
    google_oauth_credentials_json: str = "credentials/google_oauth_credentials.json"
    google_oauth_token_json: str = "credentials/google_oauth_token.json"

    sheets_tenant_list_id: str = ""
    sheets_building_inventory_id: str = ""
    sheets_vendor_list_id: str = ""
    sheets_broker_list_id: str = ""

    gmail_user_email: str = ""

    # ── HubSpot ───────────────────────────────────────────────────────────────
    hubspot_api_key: str = ""

    # ── Ingestion schedules (cron strings) ───────────────────────────────────
    schedule_sheets: str = "0 */6 * * *"
    schedule_gmail: str = "0 */2 * * *"
    schedule_hubspot: str = "0 */4 * * *"
    schedule_documents: str = "0 2 * * *"
    schedule_evaluator: str = "0 9 * * 1"

    # ── API ───────────────────────────────────────────────────────────────────
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    log_level: str = "INFO"

    # ── DPDP compliance ───────────────────────────────────────────────────────
    pii_fields: str = "email,phone,mobile,personal_email,address"

    @property
    def pii_field_list(self) -> list[str]:
        return [f.strip() for f in self.pii_fields.split(",") if f.strip()]

    @property
    def sync_database_url(self) -> str:
        """Synchronous URL for Alembic (uses psycopg2 driver)."""
        return self.database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")

    # ── HR Engine (AI Hire) ─────────────────────────────────────────────────
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_whatsapp_number: str = "whatsapp:+14155238886"  # Twilio sandbox default
    hiring_email: str = "hiring@example.com"
    notify_whatsapp: str = ""
    admin_notify_email: str = "admin@example.com"
    careers_form_origin: str = "https://yourcompany.com"
    upload_dir: str = "./uploads"
    hr_resume_score_threshold: float = 65.0
    hr_screen_score_threshold: float = 75.0
    hr_test_pass_threshold: float = 60.0
    linkedin_email: str = ""
    linkedin_password: str = ""
    naukri_email: str = ""
    naukri_password: str = ""
    gmail_client_id: str = ""
    gmail_client_secret: str = ""
    gmail_token_path: str = "./credentials/gmail_token.json"
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    frontend_url: str = "http://localhost:3000"
    gcal_calendar_id: str = "primary"
    gcal_service_account_json: str = ""

    # ── Department Heads ──────────────────────────────────────────────────────
    hod_bd_email: str = ""
    hod_ops_email: str = ""
    hod_it_email: str = ""
    hod_ai_email: str = ""
    hod_marketing_email: str = ""
    hod_finance_email: str = ""
    hod_hr_email: str = ""

    # ── Calendly ──────────────────────────────────────────────────────────────
    calendly_default_link: str = ""
    calendly_bd_link: str = ""
    calendly_ops_link: str = ""

    # ── JWT / Admin Auth ─────────────────────────────────────────────────────
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480
    admin_email: str = "admin@example.com"
    admin_password_hash: str = ""

    @property
    def uploads_resumes_dir(self) -> str:
        return f"{self.upload_dir}/resumes"

    @property
    def uploads_offers_dir(self) -> str:
        return f"{self.upload_dir}/offer_letters"


@lru_cache
def get_settings() -> Settings:
    return Settings()
