from pydantic_settings import BaseSettings, SettingsConfigDict
class Settings(BaseSettings):
    database_url: str = "sqlite:///./resolveai.db"
    api_key: str = "resolveai-demo-key"
    admin_api_key: str = "resolveai-admin-key"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:8000"
    fault_mode: str = "NORMAL"
    demo_timezone: str = "Asia/Kolkata"
    log_level: str = "INFO"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    @property
    def origins(self): return [x.strip() for x in self.cors_origins.split(",") if x.strip()]
settings = Settings()
