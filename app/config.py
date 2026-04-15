from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    #keycloak
    keycloak_internal_url: str
    keycloak_public_url: str
    keycloak_realm: str
    keycloak_client_id: str
    keycloak_client_secret: str
    app_secret_key: str
    app_base_url: str

    class Config:
        env_file = ".env"

settings = Settings()