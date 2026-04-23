from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    
    # keycloak
    keycloak_internal_url: str
    keycloak_public_url: str
    keycloak_realm: str
    keycloak_client_id: str
    keycloak_client_secret: str
    app_secret_key: str
    app_base_url: str

settings = Settings()